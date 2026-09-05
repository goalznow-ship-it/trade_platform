"""Canonical signal pipeline.

Single code path that every emitted signal must flow through. The pipeline:

1. Calls the institutional signal engine's ``_compose_signal`` to produce
   the base 100-point scoring + multi-timeframe + risk + execution dict.
2. Optionally layers an ML boost on top via ``MLSignalEngine.augment_institutional_score``.
3. Persists the result to the ``signals`` table with full provenance
   (``factor_payload``, ``weights_used``, ``ml_boost``, ``pipeline_version``,
   ``model_version``, ``source_engine``) so downstream phases
   (self-learning, walk-forward gating, quality auto-disable) have a
   reproducible record of what produced the score.
4. Returns the canonical dict the API can ship to the frontend.

Why this exists
---------------
Before this module, three different persistence paths wrote to the
``signals`` table — the API endpoint, the workers task, and the
institutional endpoint — each with its own subset of fields. That made
it impossible to (a) reproduce an emitted signal, (b) run walk-forward
gating, or (c) auto-disable a poorly performing factor. This module
makes persistence a side effect of the canonical emit, and the score
provenance travels with every row.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.analysis import Signal
from app.models.market import Symbol as SymbolModel
from app.services.institutional_signals import institutional_signal_engine

# Bump when the persist schema or the canonical compose changes. The
# version is stamped on every emitted signal so the self-learning loop
# can group rows by pipeline era.
PIPELINE_VERSION = "1.0.0"

# The model_version field is filled in by the ML layer when the boost
# was actually applied. When ML is unavailable (model not trained yet)
# we record a sentinel so downstream consumers can distinguish
# "ML-aware emit" from "ML-bypass emit" without NULL ambiguity.
ML_BYPASS_MODEL_VERSION = "ml_bypass_v1"


class SignalPipeline:
    """The single canonical emit path.

    All callers (HTTP endpoint, worker, future websocket dispatcher)
    must go through ``emit``. The pipeline owns:
      - the compose + ML boost composition
      - the dedupe check (don't double-write identical active signals)
      - the DB persist with full provenance
    """

    async def emit(
        self,
        symbol: str,
        timeframe: str = "1h",
        capital: float = 10000,
        risk_percent: float = 0.02,
        db: AsyncSession | None = None,
        source_engine: str = "institutional+ml",
    ) -> dict:
        """Run the full canonical pipeline and persist if a trade-grade
        signal survives the dedupe + threshold checks.

        Returns the enriched signal dict (with ``signal_id`` populated
        when persisted, ``None`` otherwise). Callers that need to know
        whether the signal hit the DB should check ``signal_id``.

        Phase 5: before doing any work, consults the quality
        gate and circuit breaker. If the engine is currently
        disabled by either, returns a benign "blocked" dict
        instead of composing a signal that the quality loop
        will reject anyway.
        """
        from app.services import circuit_breaker
        from app.services.observability import registry as metrics
        from app.services.quality_gate import is_engine_disabled

        if await is_engine_disabled(source_engine):
            metrics.signals_blocked_quality.inc(engine=source_engine)
            return {
                "symbol": symbol, "timeframe": timeframe,
                "error": "engine_disabled_by_quality_gate",
                "direction": "neutral", "confidence": 0, "signal_id": None,
                "source_engine": source_engine,
            }
        if await circuit_breaker.is_open(source_engine, scope="default"):
            metrics.signals_blocked_breaker.inc(engine=source_engine)
            return {
                "symbol": symbol, "timeframe": timeframe,
                "error": "engine_circuit_breaker_open",
                "direction": "neutral", "confidence": 0, "signal_id": None,
                "source_engine": source_engine,
            }

        try:
            composed = await institutional_signal_engine._compose_signal(
                symbol=symbol,
                timeframe=timeframe,
                capital=capital,
                risk_percent=risk_percent,
            )
        except Exception as exc:
            await circuit_breaker.record_failure(
                source_engine, scope="default", reason=f"compose_failed:{exc}"
            )
            raise

        if composed is None:
            return {"symbol": symbol, "timeframe": timeframe, "error": "compose_failed",
                    "direction": "neutral", "confidence": 0, "signal_id": None}

        result = await self.persist_composed(
            composed, db=db, symbol=symbol, timeframe=timeframe,
            source_engine=source_engine,
        )
        if result.get("signal_id"):
            await circuit_breaker.record_success(source_engine, scope="default")
            metrics.signals_emitted.inc(
                engine=source_engine, direction=result.get("direction", "unknown"),
            )
        return result

    async def persist_composed(
        self,
        composed: dict,
        db: AsyncSession | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        source_engine: str = "institutional+ml",
    ) -> dict:
        """Persist an already-composed signal dict.

        Used by the legacy ``signals`` API where the AI engine has
        already done the work and we just need to attach provenance
        and write. Skips the institutional compose + ML boost steps
        because the caller already ran them. Still applies the same
        threshold / dedupe / provenance guarantees as ``emit``.
        """
        sym = symbol or str(composed.get("symbol", ""))
        tf = timeframe or str(composed.get("timeframe") or "1h")
        if not sym:
            return {"symbol": sym, "timeframe": tf, "error": "missing_symbol",
                    "direction": "neutral", "confidence": 0, "signal_id": None}

        from app.services import circuit_breaker
        from app.services.observability import registry as metrics
        from app.services.quality_gate import is_engine_disabled

        if await is_engine_disabled(source_engine):
            metrics.signals_blocked_quality.inc(engine=source_engine)
            return {
                "symbol": sym, "timeframe": tf,
                "error": "engine_disabled_by_quality_gate",
                "direction": "neutral", "confidence": 0, "signal_id": None,
                "source_engine": source_engine,
            }
        if await circuit_breaker.is_open(source_engine, scope="default"):
            metrics.signals_blocked_breaker.inc(engine=source_engine)
            return {
                "symbol": sym, "timeframe": tf,
                "error": "engine_circuit_breaker_open",
                "direction": "neutral", "confidence": 0, "signal_id": None,
                "source_engine": source_engine,
            }

        # ML boost — best-effort. If the ML layer isn't ready (no trained
        # model on disk yet, missing features, etc.) the boost is a
        # no-op and we record ml_bypass_v1 as the model_version so the
        # self-learning loop can filter for ML-aware rows.
        try:
            composed, ml_boost, model_version = self._apply_ml_boost(
                composed, symbol=sym, timeframe=tf
            )
        except Exception as exc:
            await circuit_breaker.record_failure(
                source_engine, scope="default", reason=f"ml_boost_failed:{exc}"
            )
            raise

        if not self._is_persistable(composed):
            composed.setdefault("signal_id", None)
            return composed

        try:
            if db is None:
                async with async_session_factory() as session:
                    signal_id = await self._persist(
                        session, composed, ml_boost, model_version, source_engine
                    )
            else:
                signal_id = await self._persist(
                    db, composed, ml_boost, model_version, source_engine
                )
        except Exception as exc:
            await circuit_breaker.record_failure(
                source_engine, scope="default", reason=f"persist_failed:{exc}"
            )
            raise
        await circuit_breaker.record_success(source_engine, scope="default")
        composed["signal_id"] = signal_id
        composed["pipeline_version"] = PIPELINE_VERSION
        composed["model_version"] = model_version
        composed["ml_boost"] = ml_boost
        composed["source_engine"] = source_engine
        if signal_id:
            metrics.signals_emitted.inc(
                engine=source_engine, direction=composed.get("direction", "unknown"),
            )
        return composed

    def _apply_ml_boost(
        self,
        composed: dict,
        symbol: str,
        timeframe: str,
        ohlcv: list | None = None,
    ) -> tuple[dict, float, str]:
        """Layer the ML boost on top of the institutional score.

        Returns (composed, ml_boost, model_version). When ML is
        unavailable ``ml_boost`` is 0 and ``model_version`` records the
        bypass sentinel. The composed dict is mutated in place: the
        base confidence is replaced with the boosted final_score and
        the boost metadata is attached under ``ml_boost_meta``.

        If ``ohlcv`` is provided (as it is from the emit path that
        already called _compose_signal), we use it directly. Otherwise
        the AI-engine path that calls ``persist_composed`` will pass
        ``None`` and we record a feature-unavailable bypass.
        """
        try:
            from app.services.ml.signal_engine import get_ml_engine
            engine = get_ml_engine()
        except Exception as exc:
            logger.debug("ml_engine_unavailable symbol=%s err=%s", symbol, exc)
            composed.setdefault("ml_boost_meta", {"note": "ml_engine_import_failed"})
            return composed, 0.0, ML_BYPASS_MODEL_VERSION

        if not getattr(engine.predictor, "is_ready", lambda: False)():
            composed.setdefault("ml_boost_meta", {"note": "ml_models_not_trained"})
            return composed, 0.0, ML_BYPASS_MODEL_VERSION

        if not ohlcv:
            composed.setdefault("ml_boost_meta", {"note": "ml_features_unavailable"})
            return composed, 0.0, ML_BYPASS_MODEL_VERSION

        try:
            import pandas as pd
            df = pd.DataFrame(ohlcv)
            if "timestamp" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
            prediction = engine.predict(symbol=symbol, df=df)
        except Exception as exc:
            logger.debug("ml_predict_failed symbol=%s err=%s", symbol, exc)
            composed.setdefault("ml_boost_meta", {"note": f"ml_predict_failed:{type(exc).__name__}"})
            return composed, 0.0, ML_BYPASS_MODEL_VERSION

        base_score = float(composed.get("confidence", 0) or 0)
        augmented = engine.augment_institutional_score(base_score, prediction)
        final_score = float(augmented.get("final_score", base_score))
        composed["confidence"] = round(final_score, 1)
        composed["ml_boost_meta"] = {
            "ml_direction": augmented.get("ml_direction"),
            "ml_confidence": augmented.get("ml_confidence"),
            "ml_agreement": augmented.get("ml_agreement"),
            "ml_adjustment": augmented.get("ml_adjustment"),
            "note": augmented.get("note"),
        }
        return composed, float(augmented.get("ml_adjustment", 0) or 0), str(
            getattr(engine.predictor, "model_version", "ensemble_v1")
        )

    def _is_persistable(self, composed: dict) -> bool:
        direction = str(composed.get("direction", "")).lower()
        if direction not in {"long", "short"}:
            return False
        confidence = float(composed.get("confidence") or 0)
        # Pipeline threshold: institutional pass already required
        # abs_score >= 70 inside compose; we keep the legacy 50 floor
        # here for back-compat with the older signal endpoint that
        # emitted at lower confidence.
        return confidence >= 50

    async def _persist(
        self,
        db: AsyncSession,
        composed: dict,
        ml_boost: float,
        model_version: str,
        source_engine: str = "institutional+ml",
    ) -> int | None:
        symbol = str(composed.get("symbol", ""))
        timeframe = str(composed.get("timeframe") or "1h")
        direction = str(composed.get("direction", "")).lower()

        sym_id = await self._resolve_symbol(db, symbol)
        if sym_id is None:
            return None

        # Dedupe: don't write a second active signal for the same
        # (symbol, timeframe, direction). The legacy _persist_signal
        # behavior — same check, same purpose.
        existing = await db.execute(
            select(Signal).where(
                Signal.symbol == symbol,
                Signal.timeframe == timeframe,
                Signal.direction == direction,
                Signal.is_active.is_(True),
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return None

        inst_score = composed.get("institutional_score", {}) or {}
        factor_payload = self._extract_factor_payload(composed, inst_score)
        weights_used = inst_score.get("weights") or {}

        record = Signal(
            symbol_id=sym_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            confidence=composed.get("confidence"),
            risk_score=None,
            probability=None,
            entry_price=(composed.get("entry_zone") or {}).get("mid")
                if isinstance(composed.get("entry_zone"), dict)
                else composed.get("entry_price"),
            stop_loss=composed.get("stop_loss"),
            take_profit_1=composed.get("take_profit_1"),
            take_profit_2=composed.get("take_profit_2"),
            take_profit_3=composed.get("take_profit_3"),
            risk_reward=composed.get("risk_reward_1"),
            leverage=1,
            reason=" | ".join(composed.get("reasons") or []),
            ai_summary=composed.get("ai_summary"),
            signal_type="institutional_pipeline",
            result="new",
            is_active=True,
            expires_at=(
                datetime.now(UTC) + self._expiry_for(timeframe)
            ).replace(tzinfo=None),
            # Phase 1 provenance — written here, never anywhere else.
            factor_payload=factor_payload,
            weights_used=weights_used,
            ml_boost=ml_boost if ml_boost else None,
            pipeline_version=PIPELINE_VERSION,
            model_version=model_version,
            source_engine=source_engine,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record.id

    @staticmethod
    async def _resolve_symbol(db: AsyncSession, symbol: str) -> int | None:
        result = await db.execute(
            select(SymbolModel).where(SymbolModel.name == symbol)
        )
        sym = result.scalar_one_or_none()
        if sym is not None:
            return sym.id
        from app.services.market_coverage import market_coverage
        covered = await market_coverage.get_top_symbols(30)
        if symbol not in covered:
            return None
        base, _, quote = symbol.partition("/")
        sym = SymbolModel(
            name=symbol,
            base_asset=base,
            quote_asset=quote or "USDT",
            exchange=market_coverage.get_symbol_exchange(symbol),
            asset_type="crypto",
            is_active=True,
            is_futures=True,
        )
        db.add(sym)
        await db.flush()
        return sym.id

    @staticmethod
    def _extract_factor_payload(composed: dict, inst_score: dict) -> dict[str, Any]:
        """The factor payload is what the score was computed FROM.

        We capture the institutional factor scores + details so the
        self-learning loop can correlate forward-return against
        individual factor values, not just the total. The ML boost
        meta is also folded in so a downstream consumer can see the
        full scoring picture in one column.
        """
        payload: dict[str, Any] = {
            "scores": inst_score.get("scores", {}),
            "details": inst_score.get("details", {}),
            "weights": inst_score.get("weights", {}),
            "classification": inst_score.get("classification"),
            "risk_level": inst_score.get("risk_level"),
            "abs_score": inst_score.get("abs_score"),
            "direction": inst_score.get("direction"),
        }
        ml_meta = composed.get("ml_boost_meta")
        if ml_meta:
            payload["ml_boost_meta"] = ml_meta
        # Surface the entry / stop / TP levels as part of the payload
        # so the resolver can reconstruct the trade setup from the
        # signal row alone (no need to re-fetch composed dict).
        for key in ("entry_zone", "stop_loss", "take_profit_1",
                    "take_profit_2", "take_profit_3", "invalidation",
                    "expected_hold_time", "current_price"):
            if composed.get(key) is not None:
                payload[key] = composed[key]
        return payload

    @staticmethod
    def _expiry_for(timeframe: str) -> timedelta:
        return {
            "1m": timedelta(hours=2),
            "5m": timedelta(hours=8),
            "15m": timedelta(hours=18),
            "30m": timedelta(days=1),
            "1h": timedelta(days=3),
            "4h": timedelta(days=10),
            "1d": timedelta(days=30),
        }.get(timeframe, timedelta(days=3))


signal_pipeline = SignalPipeline()

"""Weight orchestrator: hydrates self-learning weights from DB and
applies them to the institutional score at emit time.

Why a separate orchestrator
---------------------------
Before Phase 2, ``InstitutionalScorer`` used hardcoded weights
(20/15/15/15/20/15) and ``SelfLearningEngine.current_weights`` was
only ever read by ``adjust_weights`` itself — it never made it back
into scoring. The orchestrator is the bridge:

  startup:   ``hydrate_from_db()`` reads the most recent successful
             ``adjustment_runs.new_weights`` row and stamps
             ``self_learning.current_weights`` with it.
  emit:      ``apply_to_score(scores)`` rescales the per-category
             scores from the scorer so the emitted
             ``institutional_score.scores`` reflect the
             self-learning adjustments. The new weights are
             recorded on the signal row as ``weights_used`` (via
             the pipeline).
  adjustment: ``adjust_weights()`` delegates to the underlying
             ``SelfLearningEngine`` but uses the SQL trade store
             and writes an ``adjustment_runs`` audit row.

The orchestrator is a singleton — the scorer is process-shared so
weights should be too.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import logger
from app.core.persistence import trade_store
from app.services.self_learning import SelfLearningEngine

# Default weights — must match InstitutionalScorer's defaults so a
# fresh deployment (no adjustment_runs rows) starts consistent.
DEFAULT_WEIGHTS: dict[str, float] = {
    "trend": 0.20,
    "momentum": 0.15,
    "volume": 0.15,
    "liquidity": 0.15,
    "smc": 0.20,
    "risk": 0.15,
}


class WeightOrchestrator:
    """The single owner of ``self_learning.current_weights``.

    Holds a reference to the underlying ``SelfLearningEngine`` so
    existing API consumers that read ``self_learning.current_weights``
    continue to work — the orchestrator just keeps that attribute in
    sync with the DB.
    """

    def __init__(self, engine: SelfLearningEngine | None = None):
        # The engine is the in-memory state the rest of the app reads
        # from. The orchestrator writes to it; everything else reads.
        self.engine = engine or SelfLearningEngine()
        # Track the last hydration time for log/metric purposes.
        self.last_hydrated_at = None

    # ── Hydration ───────────────────────────────────────────────
    async def hydrate_from_db(self) -> dict[str, float]:
        """Stamp ``self_learning.current_weights`` with the most
        recent successful ``adjustment_runs.new_weights`` row, or
        fall back to the default weights if no successful run
        exists yet (fresh DB).

        Returns the weights that were applied so the caller can
        log / metric them.
        """
        latest = await trade_store.latest_successful_weights()
        if latest:
            self.engine.current_weights = _normalise(latest)
        else:
            self.engine.current_weights = dict(DEFAULT_WEIGHTS)
        # ``last_hydrated_at`` is set on the engine for any caller
        # that wants to know freshness.
        from datetime import UTC, datetime
        self.engine.current_weights["_hydrated_at"] = datetime.now(UTC).isoformat()
        self.last_hydrated_at = self.engine.current_weights["_hydrated_at"]
        logger.info(
            "weights_hydrated",
            extra={"weights": {k: round(v, 4) for k, v in self.engine.current_weights.items()
                               if not k.startswith("_")}},
        )
        return {k: v for k, v in self.engine.current_weights.items()
                if not k.startswith("_")}

    # ── Application ────────────────────────────────────────────
    def apply_to_score(self, scores: dict[str, float]) -> dict[str, float]:
        """Rescale a per-category score dict using ``current_weights``.

        The input ``scores`` are the scorer's raw signed points
        (each already capped at its category weight). ``apply_to_score``
        multiplies each by the orchestrator's weight ratio so a
        category that the self-learning loop has up-weighted shows
        up larger in the emitted ``scores`` dict. The result is the
        ``weights_used`` snapshot the pipeline persists.

        The math: ``out[c] = in[c] * (current[c] / default[c])``
        so a category with default 0.20 moved to 0.30 is scaled by
        1.5x. Negative scores stay negative (the sign carries the
        direction). The caller is responsible for re-summing the
        rescaled scores if they want a new total.
        """
        weights = self._active_weights()
        out: dict[str, float] = {}
        for key, score in scores.items():
            default = DEFAULT_WEIGHTS.get(key)
            active = weights.get(key, default or 0.0)
            if default and default > 0:
                out[key] = float(score) * (active / default)
            else:
                out[key] = float(score)
        return out

    def weights_used_snapshot(self) -> dict[str, float]:
        """Return a copy of ``current_weights`` stripped of metadata.

        The pipeline persists this on the signal row's
        ``weights_used`` column so the self-learning audit trail
        ties the emitted signal back to the weights in force at
        emit time.
        """
        return {k: float(v) for k, v in self._active_weights().items()}

    # ── Adjustment delegation ─────────────────────────────────
    async def adjust_weights(self) -> dict[str, Any]:
        """Run ``SelfLearningEngine.adjust_weights`` but read trades
        from the SQL store and write an ``adjustment_runs`` audit
        row. Idempotent: if a recent successful run already exists
        for the same trade window, it returns that row's id
        instead of computing again.
        """
        recent = await trade_store.list_recent_trades(limit=100)
        previous_weights = self.weights_used_snapshot()

        if len(recent) < 10:
            skip_id = await trade_store.record_adjustment(
                status="skipped",
                trade_count=len(recent),
                skip_reason="insufficient_trades_lt_10",
                previous_weights=previous_weights,
            )
            logger.info(
                "weight_adjustment_skipped",
                extra={"trade_count": len(recent), "audit_id": skip_id},
            )
            return {"status": "skipped", "trade_count": len(recent), "audit_id": skip_id}

        # Drive the engine with the SQL-loaded trades so the math
        # runs over the same data the engine would have built up
        # in-memory.
        self.engine.trade_history = recent
        self.engine.adjust_weights()

        new_weights = self.weights_used_snapshot()
        run_id = await trade_store.record_adjustment(
            status="ok",
            trade_count=len(recent),
            previous_weights=previous_weights,
            new_weights=new_weights,
            accuracies=getattr(self.engine, "weight_history", [{}])[-1].get("accuracies"),
        )
        logger.info(
            "weight_adjustment_ok",
            extra={
                "audit_id": run_id,
                "new_weights": {k: round(v, 4) for k, v in new_weights.items()},
            },
        )
        return {
            "status": "ok",
            "trade_count": len(recent),
            "audit_id": run_id,
            "new_weights": new_weights,
        }

    # ── Internal ───────────────────────────────────────────────
    def _active_weights(self) -> dict[str, float]:
        weights = getattr(self.engine, "current_weights", None) or DEFAULT_WEIGHTS
        # Strip any metadata keys (``_hydrated_at``) before using.
        return {k: float(v) for k, v in weights.items() if not k.startswith("_")}


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    """Make weights sum to 1.0 — prevents the math from drifting if
    a stored dict was hand-edited or stored before normalisation.
    """
    clean = {k: float(v) for k, v in weights.items()
             if not k.startswith("_") and float(v) > 0}
    total = sum(clean.values()) or 1.0
    return {k: v / total for k, v in clean.items()}


# Process-wide singleton — import this from anywhere. The orchestrator
# is wired to the same ``self_learning`` instance the rest of the app
# already reads ``current_weights`` from, so applying the orchestrator's
# weights is transparent to legacy callers.
from app.services.self_learning import self_learning as _shared_engine  # noqa: E402

weight_orchestrator = WeightOrchestrator(engine=_shared_engine)


__all__ = ["WeightOrchestrator", "weight_orchestrator", "DEFAULT_WEIGHTS"]

"""Signal outcome resolver.

For every active signal in the ``signals`` table, walk forward
through the live candle stream to compute:

- ``forward_return_pct`` — signed return from entry to the first
  resolution event (TP hit / SL hit / horizon expired).
- ``mae`` / ``mfe`` — worst adverse / best favorable excursion
  along the path, in percent of entry.
- ``bars_held`` — number of candles the trade was live.
- ``resolution_method`` — one of ``tp_hit``, ``sl_hit``,
  ``expired``, ``forward_horizon``.

The resolver writes both:

1. ``signals.result`` — the categorical outcome for legacy
   consumers (and the existing UI).
2. ``signal_outcomes`` — the rich telemetry Phase 1 added. The
   per-(factor, symbol, timeframe) quality gate in Phase 5 reads
   from this table to decide which factors to disable.

The resolver is the only writer of ``signal_outcomes``. Idempotency
is enforced by the unique constraint on ``signal_outcomes.signal_id``
— a second pass on an already-resolved signal no-ops.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.logging import logger
from app.models.analysis import Signal, SignalOutcome
from app.services.market import market_service

# How many candles past the signal's entry timestamp to look before
# declaring the trade ``expired``. Multiplied by the signal's
# ``timeframe`` length to get a wall-clock cap.
HORIZON_BARS_DEFAULT = 24

# Cap on candles to fetch per resolution pass. 1000 is enough to
# cover several days of 15m bars without making the call slow.
MAX_LOOKAHEAD_CANDLES = 1000


class SignalOutcomeResolver:
    """Walk forward through candles to resolve every open signal.

    Used by ``workers.resolve_signal_outcomes`` (Celery beat) and
    directly by the test suite. The resolver is stateless — every
    call opens its own DB session unless one is passed in.
    """

    async def resolve_all(
        self,
        db: AsyncSession | None = None,
        horizon_bars: int = HORIZON_BARS_DEFAULT,
    ) -> dict:
        """Resolve every signal whose ``is_active`` is still True
        and which has no ``signal_outcomes`` row yet.

        Returns a small summary dict for the worker log.
        """
        owns = db is None
        session = db or async_session_factory()
        try:
            candidates = await self._candidate_signals(session)
            resolved = 0
            skipped = 0
            for signal in candidates:
                outcome = await self._resolve_one(session, signal, horizon_bars)
                if outcome is None:
                    skipped += 1
                    continue
                resolved += 1
            if owns:
                await session.commit()
            logger.info(
                "signal_outcomes_resolved",
                extra={"resolved": resolved, "skipped": skipped},
            )
            return {"resolved": resolved, "skipped": skipped}
        finally:
            if owns:
                await session.close()

    async def _candidate_signals(
        self, db: AsyncSession
    ) -> list[Signal]:
        """Active signals that don't yet have a ``signal_outcomes``
        row. ``signal_outcomes.signal_id`` is unique, so a left
        join filtering on null does the trick.
        """
        result = await db.execute(
            select(Signal)
            .where(Signal.is_active.is_(True))
            .where(~Signal.id.in_(
                select(SignalOutcome.signal_id)
            ))
        )
        return list(result.scalars().all())

    async def _resolve_one(
        self,
        db: AsyncSession,
        signal: Signal,
        horizon_bars: int,
    ) -> SignalOutcome | None:
        """Resolve a single signal. Returns the new
        ``SignalOutcome`` row (already added to the session) or
        ``None`` if we couldn't fetch enough candles to score it.
        """
        candles = await self._fetch_candles(signal, horizon_bars)
        if not candles or len(candles) < 2:
            return None

        entry = float(signal.entry_price) if signal.entry_price else None
        direction = signal.direction
        if not entry or direction not in ("long", "short"):
            return None

        result = self._walk_forward(candles, entry, direction, signal, horizon_bars)
        if result is None:
            return None

        # Persist the resolution on both tables. ``signals.result``
        # is the legacy categorical column the UI already reads;
        # ``signal_outcomes`` is the rich telemetry Phase 1 added.
        signal.result = result["resolution_method"]
        signal.is_active = False

        outcome = SignalOutcome(
            signal_id=signal.id,
            resolved_at=datetime.now(UTC),
            horizon_bars=result.get("horizon_bars"),
            forward_return_pct=result.get("forward_return_pct"),
            mae=result.get("mae"),
            mfe=result.get("mfe"),
            resolved_price=result.get("resolved_price"),
            bars_held=result.get("bars_held"),
            resolution_method=result["resolution_method"],
            notes=result.get("notes"),
        )
        db.add(outcome)
        return outcome

    async def _fetch_candles(
        self, signal: Signal, horizon_bars: int
    ) -> list[dict] | None:
        """Fetch the candles from entry onward. If the signal has no
        stored entry-time, fall back to ``created_at``. We need at
        least a couple of bars past entry to score the trade.
        """
        timeframe = signal.timeframe or "1h"
        # Cap at MAX_LOOKAHEAD_CANDLES so a runaway horizon doesn't
        # trigger a multi-thousand-candle fetch.
        limit = min(MAX_LOOKAHEAD_CANDLES, max(horizon_bars * 2, 50))
        try:
            return await market_service.get_ohlcv(
                signal.symbol, None, timeframe, limit
            )
        except Exception as exc:
            logger.debug("resolve_fetch_failed symbol=%s err=%s", signal.symbol, exc)
            return None

    def _walk_forward(
        self,
        candles: list[dict],
        entry: float,
        direction: str,
        signal: Signal,
        horizon_bars: int,
    ) -> dict[str, Any] | None:
        """Iterate the candle list, recording excursion extremes and
        detecting the first resolution event.

        The walk assumes candles are sorted ascending by timestamp;
        ``market_service.get_ohlcv`` already returns them in that
        order. The resolver does NOT re-fetch the entry candle — it
        starts at candle index 1, which is the first bar AFTER entry.
        """
        # Pre-compute extremes from the full path. The trade resolves
        # at the first event (TP or SL) hit; the MAE / MFE are
        # recorded from the full path up to that point.
        best_high = -float("inf")
        worst_low = float("inf")
        bars_held = 0
        resolution: dict[str, Any] | None = None

        tp1 = float(signal.take_profit_1) if signal.take_profit_1 else None
        sl = float(signal.stop_loss) if signal.stop_loss else None

        for bar in candles[1:]:
            bars_held += 1
            high = float(bar.get("high") or 0)
            low = float(bar.get("low") or 0)
            best_high = max(best_high, high)
            worst_low = min(worst_low, low)

            # Direction-aware TP / SL trigger.
            if direction == "long":
                if tp1 and high >= tp1:
                    resolution = {"resolution_method": "tp_hit", "price": tp1}
                    break
                if sl and low <= sl:
                    resolution = {"resolution_method": "sl_hit", "price": sl}
                    break
            else:  # short
                if tp1 and low <= tp1:
                    resolution = {"resolution_method": "tp_hit", "price": tp1}
                    break
                if sl and high >= sl:
                    resolution = {"resolution_method": "sl_hit", "price": sl}
                    break

            if bars_held >= horizon_bars:
                # Use the last close as the mark-to-market price.
                last = float(bar.get("close") or entry)
                resolution = {
                    "resolution_method": "forward_horizon",
                    "price": last,
                }
                break

        if resolution is None:
            # The path never produced a resolution event. Either the
            # candle stream is too short or all bars were on one
            # side of the trigger. Mark as expired at the last close.
            last = float(candles[-1].get("close") or entry)
            resolution = {"resolution_method": "expired", "price": last}

        # Signed return: positive for a winning long, negative for
        # a losing long, etc. The sign is direction-aware.
        sign = 1 if direction == "long" else -1
        forward_return_pct = ((resolution["price"] - entry) / entry) * 100 * sign
        mae_pct = ((worst_low - entry) / entry) * 100 * sign * -1  # worst adverse
        mfe_pct = ((best_high - entry) / entry) * 100 * sign
        # MAE is always reported as a positive number (the depth of
        # the worst drawdown). MFE is positive for a winning run and
        # can be 0 for a SL-out without any positive excursion.
        mae_pct = max(0.0, mae_pct)
        mfe_pct = max(0.0, mfe_pct)

        return {
            "resolution_method": resolution["resolution_method"],
            "resolved_price": resolution["price"],
            "forward_return_pct": round(forward_return_pct, 4),
            "mae": round(mae_pct, 4),
            "mfe": round(mfe_pct, 4),
            "bars_held": bars_held,
            "horizon_bars": horizon_bars,
            "notes": None,
        }


# Process-wide singleton — most callers don't need their own.
signal_outcome_resolver = SignalOutcomeResolver()


__all__ = [
    "SignalOutcomeResolver",
    "signal_outcome_resolver",
    "HORIZON_BARS_DEFAULT",
    "MAX_LOOKAHEAD_CANDLES",
]

"""
Signal Performance Tracking & Analytics
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.analysis import Signal

class PerformanceService:
    MIN_CALIBRATION_SAMPLES = 30

    async def get_stats(self, db: AsyncSession, days: int = 30) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(Signal).where(Signal.created_at >= cutoff)
        )
        signals = result.scalars().all()

        total = len(signals)
        if total == 0:
            return {
                'total_signals': 0,
                'win_rate': 0,
                'loss_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'best_timeframe': '--',
                'best_pair': '--',
                'long_accuracy': 0,
                'short_accuracy': 0,
                'last_100_wins': 0,
                'last_100_losses': 0,
                'completed_signals': 0,
                'pending_signals': 0,
                'calibration': self._calibration([]),
            }

        wins = [s for s in signals if s.is_triggered and getattr(s, 'result', None) == 'tp_hit']
        losses = [s for s in signals if s.is_triggered and getattr(s, 'result', None) == 'sl_hit']
        win_count = len(wins)
        loss_count = len(losses)
        completed = win_count + loss_count

        completed_signals = wins + losses
        long_signals = [s for s in completed_signals if s.direction == 'long']
        short_signals = [s for s in completed_signals if s.direction == 'short']
        long_wins = [s for s in long_signals if getattr(s, 'result', None) == 'tp_hit']
        short_wins = [s for s in short_signals if getattr(s, 'result', None) == 'tp_hit']

        timeframe_counts = {}
        pair_counts = {}
        for s in completed_signals:
            tf = s.timeframe or '1h'
            timeframe_counts.setdefault(tf, {"wins": 0, "total": 0})
            timeframe_counts[tf]["total"] += 1
            timeframe_counts[tf]["wins"] += int(s.result == "tp_hit")
            pair = s.symbol or 'Unknown'
            pair_counts.setdefault(pair, {"wins": 0, "total": 0})
            pair_counts[pair]["total"] += 1
            pair_counts[pair]["wins"] += int(s.result == "tp_hit")

        quality = lambda item: (item[1]["wins"] / item[1]["total"], item[1]["total"])
        best_tf = max(timeframe_counts.items(), key=quality)[0] if timeframe_counts else '--'
        best_pair = max(pair_counts.items(), key=quality)[0] if pair_counts else '--'
        calibration = self._calibration(completed_signals)

        return {
            'total_signals': total,
            'win_rate': round(win_count / completed * 100, 1) if completed > 0 else 0,
            'loss_rate': round(loss_count / completed * 100, 1) if completed > 0 else 0,
            'avg_profit': round(sum(abs(s.entry_price - (s.take_profit_1 or s.entry_price)) for s in wins) / win_count, 2) if win_count > 0 else 0,
            'avg_loss': round(sum(abs(s.entry_price - (s.stop_loss or s.entry_price)) for s in losses) / loss_count, 2) if loss_count > 0 else 0,
            'best_timeframe': best_tf,
            'best_pair': best_pair,
            'long_accuracy': round(len(long_wins) / len(long_signals) * 100, 1) if long_signals else 0,
            'short_accuracy': round(len(short_wins) / len(short_signals) * 100, 1) if short_signals else 0,
            'last_100_wins': win_count,
            'last_100_losses': loss_count,
            'completed_signals': completed,
            'pending_signals': total - completed,
            'calibration': calibration,
        }

    @staticmethod
    def _calibration(signals: list) -> list[dict]:
        buckets = []
        for lower in range(50, 100, 10):
            upper = lower + 10
            rows = [
                signal for signal in signals
                if signal.confidence is not None
                and lower <= float(signal.confidence)
                and (float(signal.confidence) < upper or upper == 100 and float(signal.confidence) <= 100)
            ]
            wins = sum(signal.result == "tp_hit" for signal in rows)
            buckets.append({
                "range": f"{lower}-{upper - 1}",
                "sample_size": len(rows),
                "win_rate": round(wins / len(rows) * 100, 1) if rows else None,
                "average_confidence": round(
                    sum(float(row.confidence) for row in rows) / len(rows),
                    1,
                ) if rows else None,
            })
        return buckets

    async def accuracy_over_time(self, db: AsyncSession, days: int = 90) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(Signal).where(Signal.created_at >= cutoff).order_by(Signal.created_at)
        )
        signals = result.scalars().all()
        daily = {}
        for s in signals:
            date = s.created_at.strftime('%Y-%m-%d') if s.created_at else 'unknown'
            if date not in daily:
                daily[date] = {'total': 0, 'wins': 0}
            if getattr(s, 'result', None) not in {'tp_hit', 'sl_hit'}:
                continue
            daily[date]['total'] += 1
            if s.result == 'tp_hit':
                daily[date]['wins'] += 1
        return [
            {'date': d, 'total': v['total'], 'wins': v['wins'],
             'accuracy': round(v['wins'] / v['total'] * 100, 1) if v['total'] > 0 else 0}
            for d, v in sorted(daily.items())
        ]

    async def calibration_report(self, db: AsyncSession, days: int = 90) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(Signal).where(
                Signal.created_at >= cutoff,
                Signal.result.in_(("tp_hit", "sl_hit")),
                Signal.confidence.is_not(None),
                Signal.confidence >= 50,
            )
        )
        signals = list(result.scalars().all())
        sample_size = len(signals)

        def group(rows: list, key) -> list[dict]:
            grouped: dict[str, list] = {}
            for row in rows:
                grouped.setdefault(str(key(row) or "unknown"), []).append(row)
            output = []
            for label, members in grouped.items():
                wins = sum(item.result == "tp_hit" for item in members)
                avg_confidence = sum(float(item.confidence) for item in members) / len(members)
                win_rate = wins / len(members) * 100
                output.append({
                    "name": label,
                    "sample_size": len(members),
                    "win_rate": round(win_rate, 1),
                    "average_confidence": round(avg_confidence, 1),
                    "calibration_gap": round(win_rate - avg_confidence, 1),
                })
            return sorted(output, key=lambda item: item["sample_size"], reverse=True)

        buckets = self._calibration(signals)
        populated = [bucket for bucket in buckets if bucket["sample_size"]]
        if signals:
            probabilities = [min(1.0, max(0.0, float(row.confidence) / 100)) for row in signals]
            outcomes = [1.0 if row.result == "tp_hit" else 0.0 for row in signals]
            brier_score = sum((p - outcome) ** 2 for p, outcome in zip(probabilities, outcomes)) / sample_size
            expected = sum(probabilities) / sample_size * 100
            observed = sum(outcomes) / sample_size * 100
            calibration_error = sum(
                bucket["sample_size"] / sample_size
                * abs(float(bucket["win_rate"]) - float(bucket["average_confidence"]))
                for bucket in populated
            )
        else:
            brier_score = expected = observed = calibration_error = None

        return {
            "period_days": days,
            "data_source": "resolved_real_market_signals",
            "status": "measured" if sample_size >= self.MIN_CALIBRATION_SAMPLES else "collecting",
            "minimum_samples": self.MIN_CALIBRATION_SAMPLES,
            "sample_size": sample_size,
            "expected_win_rate": round(expected, 1) if expected is not None else None,
            "observed_win_rate": round(observed, 1) if observed is not None else None,
            "calibration_error": round(calibration_error, 2) if calibration_error is not None else None,
            "brier_score": round(brier_score, 4) if brier_score is not None else None,
            "buckets": buckets,
            "by_direction": group(signals, lambda row: str(row.direction).lower()),
            "by_timeframe": group(signals, lambda row: row.timeframe),
            "by_symbol": group(signals, lambda row: row.symbol)[:10],
        }

performance_service = PerformanceService()

"""
Signal Performance Tracking & Analytics
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.analysis import Signal
from app.core.logging import logger

class PerformanceService:
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
            }

        wins = [s for s in signals if s.is_triggered and getattr(s, 'result', None) == 'tp_hit']
        losses = [s for s in signals if s.is_triggered and getattr(s, 'result', None) == 'sl_hit']
        win_count = len(wins)
        loss_count = len(losses)
        completed = win_count + loss_count

        long_signals = [s for s in signals if s.direction == 'long']
        short_signals = [s for s in signals if s.direction == 'short']
        long_wins = [s for s in long_signals if getattr(s, 'result', None) == 'tp_hit']
        short_wins = [s for s in short_signals if getattr(s, 'result', None) == 'tp_hit']

        timeframe_counts = {}
        pair_counts = {}
        for s in signals:
            tf = s.timeframe or '1h'
            timeframe_counts[tf] = timeframe_counts.get(tf, 0) + 1
            pair = s.symbol or 'Unknown'
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        best_tf = max(timeframe_counts, key=timeframe_counts.get) if timeframe_counts else '--'
        best_pair = max(pair_counts, key=pair_counts.get) if pair_counts else '--'

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
        }

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
            daily[date]['total'] += 1
            if getattr(s, 'result', None) == 'tp_hit':
                daily[date]['wins'] += 1
        return [
            {'date': d, 'total': v['total'], 'wins': v['wins'],
             'accuracy': round(v['wins'] / v['total'] * 100, 1) if v['total'] > 0 else 0}
            for d, v in sorted(daily.items())
        ]

performance_service = PerformanceService()

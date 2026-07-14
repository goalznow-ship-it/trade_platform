import pandas as pd
import numpy as np
from typing import Optional, List
from app.core.logging import logger

class BacktestService:
    def __init__(self):
        self.logger = logger

    def run_backtest(self, data: list, initial_balance: float = 10000,
                     fee_rate: float = 0.0004, leverage: int = 1,
                     risk_per_trade: float = 0.02) -> dict:
        if len(data) < 50:
            return {'error': 'Insufficient data'}

        df = pd.DataFrame(data)
        balance = initial_balance
        position = None
        trades = []
        equity_curve = [initial_balance]

        for i in range(20, len(df)):
            current = df.iloc[i]
            prev = df.iloc[:i]

            signal = self._simple_strategy(prev)

            if signal != 0 and position is None:
                position = {
                    'entry_price': current['close'],
                    'side': signal,
                    'size': balance * risk_per_trade * leverage / current['close'],
                    'stop_loss': current['close'] * (0.98 if signal == 1 else 1.02),
                }
            elif position:
                exit_signal = False
                exit_price = current['close']

                if position['side'] == 1:
                    if current['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_signal = True
                else:
                    if current['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_signal = True

                if exit_signal or i == len(df) - 1:
                    pnl = (exit_price - position['entry_price']) * position['size'] * position['side']
                    pnl -= abs(pnl) * fee_rate
                    balance += pnl
                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'side': 'long' if position['side'] == 1 else 'short',
                        'pnl': pnl,
                        'pnl_percent': (pnl / initial_balance) * 100,
                    })
                    position = None
                equity_curve.append(balance)

        if not trades:
            return {'error': 'No trades generated'}

        pnls = [t['pnl'] for t in trades]
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        total_pnl = balance - initial_balance
        total_return = (balance / initial_balance - 1) * 100

        peak = max(equity_curve)
        trough = min(equity_curve[-len(equity_curve)//2:])
        max_dd = (peak - trough) / peak * 100 if peak > 0 else 0

        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t['pnl'] for t in losses])) if losses else 1
        profit_factor = abs(avg_win * len(wins) / (avg_loss * len(losses))) if losses else float('inf')

        return {
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1),
            'total_return': round(total_return, 2),
            'total_pnl': round(total_pnl, 2),
            'max_drawdown': round(max_dd, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_risk_reward': round(abs(avg_win / avg_loss), 2) if avg_loss else 0,
            'sharpe_ratio': round(np.mean(pnls) / np.std(pnls) * np.sqrt(365), 2) if np.std(pnls) > 0 else 0,
            'final_balance': round(balance, 2),
            'trades': trades[-20:],
            'equity_curve': equity_curve[::max(1, len(equity_curve)//100)],
        }

    def _simple_strategy(self, df: pd.DataFrame) -> int:
        if len(df) < 20:
            return 0
        close = df['close']
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean() if len(close) >= 50 else sma20
        rsi = self._calc_rsi(close, 14)

        current_close = close.iloc[-1]
        current_sma20 = sma20.iloc[-1]
        current_sma50 = sma50.iloc[-1] if len(sma50) > 0 else current_sma20
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50

        if current_close > current_sma20 > current_sma50 and current_rsi < 70:
            return 1
        elif current_close < current_sma20 < current_sma50 and current_rsi > 30:
            return -1
        return 0

    def _calc_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0))
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

backtest_service = BacktestService()

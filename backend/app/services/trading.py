import ccxt
from typing import Optional, List
from datetime import datetime
from app.core.logging import logger

class TradingService:
    def __init__(self):
        self.logger = logger
        self.exchanges = {}

    def _get_exchange(self, exchange: str, api_key: str = None, secret_key: str = None):
        if exchange == 'binance':
            ex = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
            })
            if api_key and secret_key:
                ex.apiKey = api_key
                ex.secret = secret_key
            return ex
        elif exchange == 'bybit':
            ex = ccxt.bybit({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
            })
            if api_key and secret_key:
                ex.apiKey = api_key
                ex.secret = secret_key
            return ex
        return None

    async def create_order(self, exchange: str, symbol: str, side: str, amount: float,
                           order_type: str = 'market', price: float = None,
                           stop_price: float = None, leverage: int = 1,
                           api_key: str = None, secret_key: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret_key)
        if not ex:
            return {'error': 'Exchange not supported'}

        try:
            ex.load_markets()
            ex.set_leverage(leverage, symbol)

            params = {}
            if order_type == 'stop_market' and stop_price:
                params['stopPrice'] = stop_price
                order_type = 'stop'

            if order_type == 'limit' and price:
                order = ex.create_limit_order(symbol, side, amount, price, params)
            elif order_type == 'stop' and stop_price:
                order = ex.create_order(symbol, 'stop', side, amount, stop_price, price, params)
            else:
                order = ex.create_market_order(symbol, side, amount, params)

            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'price': order['price'],
                'amount': order['amount'],
                'filled': order['filled'],
                'status': order['status'],
                'timestamp': order['timestamp'],
            }
        except Exception as e:
            return {'error': str(e)}

    async def cancel_order(self, exchange: str, symbol: str, order_id: str,
                           api_key: str = None, secret_key: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret_key)
        if not ex:
            return {'error': 'Exchange not supported'}
        try:
            result = ex.cancel_order(order_id, symbol)
            return {'success': True, 'order_id': order_id}
        except Exception as e:
            return {'error': str(e)}

    async def get_positions(self, exchange: str, api_key: str = None, secret_key: str = None) -> list:
        ex = self._get_exchange(exchange, api_key, secret_key)
        if not ex:
            return []
        try:
            positions = ex.fetch_positions()
            return [
                {
                    'symbol': p['symbol'],
                    'side': 'long' if p['side'] == 'long' else 'short',
                    'size': p['contracts'],
                    'entry_price': p['entryPrice'],
                    'mark_price': p['markPrice'],
                    'liquidation_price': p['liquidationPrice'],
                    'leverage': p['leverage'],
                    'unrealized_pnl': p['unrealizedPnl'],
                    'realized_pnl': p['realizedPnl'],
                }
                for p in positions if p['contracts'] > 0
            ]
        except Exception:
            return []

    async def get_balance(self, exchange: str, api_key: str = None, secret_key: str = None) -> dict:
        ex = self._get_exchange(exchange, api_key, secret_key)
        if not ex:
            return {}
        try:
            balance = ex.fetch_balance()
            return {
                'total': balance['total'].get('USDT', 0),
                'free': balance['free'].get('USDT', 0),
                'used': balance['used'].get('USDT', 0),
            }
        except Exception:
            return {}

    async def get_open_orders(self, exchange: str, symbol: str = None,
                              api_key: str = None, secret_key: str = None) -> list:
        ex = self._get_exchange(exchange, api_key, secret_key)
        if not ex:
            return []
        try:
            orders = ex.fetch_open_orders(symbol)
            return [
                {
                    'id': o['id'],
                    'symbol': o['symbol'],
                    'side': o['side'],
                    'type': o['type'],
                    'price': o['price'],
                    'amount': o['amount'],
                    'filled': o['filled'],
                    'status': o['status'],
                    'timestamp': o['timestamp'],
                }
                for o in orders
            ]
        except Exception:
            return []

trading_service = TradingService()

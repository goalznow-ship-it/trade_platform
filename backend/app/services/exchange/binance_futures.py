import asyncio
import ccxt
import time as time_module
from typing import Optional, List, Dict
from datetime import datetime, timezone
from app.core.logging import logger
from app.services.exchange.base import (
    BaseExchange, OrderRequest, OrderResult,
    PositionResult, BalanceResult, ExchangeInfo,
)


class BinanceFuturesExchange(BaseExchange):
    def __init__(self):
        super().__init__("binance")
        self._ccxt: Optional[ccxt.binance] = None
        self._last_heartbeat: float = 0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self, api_key: str, secret_key: str, passphrase: Optional[str] = None) -> bool:
        self._api_key = api_key
        self._secret_key = secret_key
        try:
            self._ccxt = ccxt.binance({
                "apiKey": api_key,
                "secret": secret_key,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                    "adjustForTimeDifference": True,
                },
            })
            self._ccxt.load_markets()
            self._connected = True
            self._last_heartbeat = time_module.time()
            self._reconnect_attempts = 0
            logger.info("Binance Futures exchange connected")
            return True
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.error(f"Binance Futures connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._ccxt = None
        logger.info("Binance Futures exchange disconnected")

    async def reconnect(self) -> bool:
        if not self._api_key or not self._secret_key:
            return False
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.warning("Binance reconnect max attempts reached")
            return False
        self._reconnect_attempts += 1
        backoff = min(30, 2 ** self._reconnect_attempts)
        logger.info(f"Binance reconnect attempt {self._reconnect_attempts} in {backoff}s")
        await asyncio.sleep(backoff)
        return await self.connect(self._api_key, self._secret_key)

    async def get_exchange_info(self) -> ExchangeInfo:
        return ExchangeInfo(
            name="binance",
            futures_available=True,
            rate_limit=1200,
            timezone="UTC",
        )

    async def _ensure_connected(self) -> None:
        if not self._connected or not self._ccxt:
            if not await self.reconnect():
                raise ConnectionError("Binance exchange not connected")

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol.replace("/", "").upper()

    def _denormalize_symbol(self, symbol: str) -> str:
        if "/" in symbol:
            return symbol.upper()
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        return symbol

    async def create_order(self, request: OrderRequest) -> OrderResult:
        await self._ensure_connected()
        try:
            symbol = self._normalize_symbol(request.symbol)

            if request.leverage > 1:
                try:
                    self._ccxt.set_leverage(request.leverage, symbol)
                except Exception:
                    pass

            params: Dict = {}
            if request.reduce_only:
                params["reduceOnly"] = True
            if request.time_in_force:
                params["timeInForce"] = request.time_in_force
            if request.client_order_id:
                params["newClientOrderId"] = request.client_order_id
            if request.margin_mode:
                try:
                    self._ccxt.set_margin_mode(request.margin_mode, symbol)
                except Exception:
                    pass

            ccxt_order = None
            if request.order_type == "market":
                ccxt_order = self._ccxt.create_market_order(
                    symbol, request.side, request.quantity, params=params,
                )
            elif request.order_type == "limit":
                if not request.price:
                    raise ValueError("Price required for limit orders")
                ccxt_order = self._ccxt.create_limit_order(
                    symbol, request.side, request.quantity, request.price, params=params,
                )
            elif request.order_type == "stop_market" or request.order_type == "stop":
                params["stopPrice"] = request.stop_price
                params["closePosition"] = request.reduce_only
                ccxt_order = self._ccxt.create_order(
                    symbol, "market", request.side, request.quantity,
                    None, params=params,
                )
            elif request.order_type == "take_profit_market" or request.order_type == "tp_market":
                params["stopPrice"] = request.stop_price
                params["closePosition"] = request.reduce_only
                ccxt_order = self._ccxt.create_order(
                    symbol, "market", request.side, request.quantity,
                    None, params={"stopPrice": request.stop_price, "reduceOnly": request.reduce_only},
                )
            else:
                raise ValueError(f"Unsupported order type: {request.order_type}")

            return self._to_order_result(ccxt_order, request)

        except Exception as e:
            logger.error(f"Binance create_order error: {e}")
            return OrderResult(
                order_id="", symbol=request.symbol, side=request.side,
                order_type=request.order_type, quantity=request.quantity,
                filled_quantity=0, price=request.price, avg_price=None,
                status="rejected", reduce_only=request.reduce_only,
                leverage=request.leverage, margin_mode=request.margin_mode,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                error=str(e),
            )

    def _to_order_result(self, ccxt_order: Dict, req: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=str(ccxt_order.get("id", "")),
            symbol=ccxt_order.get("symbol", req.symbol),
            side=ccxt_order.get("side", req.side),
            order_type=ccxt_order.get("type", req.order_type),
            quantity=float(ccxt_order.get("amount", req.quantity)),
            filled_quantity=float(ccxt_order.get("filled", 0)),
            price=ccxt_order.get("price") or ccxt_order.get("stopPrice"),
            avg_price=ccxt_order.get("average"),
            status=ccxt_order.get("status", "unknown"),
            reduce_only=req.reduce_only,
            leverage=req.leverage,
            margin_mode=req.margin_mode,
            created_at=datetime.fromtimestamp(
                ccxt_order.get("timestamp", time_module.time()) / 1000, tz=timezone.utc,
            ) if ccxt_order.get("timestamp") else datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        await self._ensure_connected()
        try:
            self._ccxt.cancel_order(order_id, self._normalize_symbol(symbol))
            return True
        except Exception as e:
            logger.error(f"Binance cancel_order error: {e}")
            return False

    async def modify_order(self, symbol: str, order_id: str,
                           price: Optional[float] = None,
                           quantity: Optional[float] = None,
                           stop_price: Optional[float] = None) -> OrderResult:
        await self._ensure_connected()
        sym = self._normalize_symbol(symbol)
        try:
            params: Dict = {}
            if stop_price:
                params["stopPrice"] = stop_price
            self._ccxt.edit_order(order_id, sym, "limit" if price else "market",
                                  None, quantity, price, params=params)
            return await self.get_order(symbol, order_id)
        except Exception as e:
            logger.error(f"Binance modify_order error: {e}")
            return OrderResult(
                order_id=order_id, symbol=symbol, side="unknown",
                order_type="unknown", quantity=0, filled_quantity=0,
                price=price, avg_price=None, status="error",
                reduce_only=False, leverage=1, margin_mode="isolated",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                error=str(e),
            )

    async def get_order(self, symbol: str, order_id: str) -> Optional[OrderResult]:
        await self._ensure_connected()
        try:
            order = self._ccxt.fetch_order(order_id, self._normalize_symbol(symbol))
            if not order:
                return None
            return OrderResult(
                order_id=str(order.get("id", order_id)),
                symbol=order.get("symbol", symbol),
                side=order.get("side", "unknown"),
                order_type=order.get("type", "unknown"),
                quantity=float(order.get("amount", 0)),
                filled_quantity=float(order.get("filled", 0)),
                price=order.get("price"),
                avg_price=order.get("average"),
                status=order.get("status", "unknown"),
                reduce_only=False,
                leverage=1,
                margin_mode="isolated",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Binance get_order error: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        await self._ensure_connected()
        try:
            sym = self._normalize_symbol(symbol) if symbol else None
            orders = self._ccxt.fetch_open_orders(sym)
            results = []
            for o in orders:
                results.append(OrderResult(
                    order_id=str(o.get("id", "")),
                    symbol=o.get("symbol", symbol or ""),
                    side=o.get("side", "unknown"),
                    order_type=o.get("type", "unknown"),
                    quantity=float(o.get("amount", 0)),
                    filled_quantity=float(o.get("filled", 0)),
                    price=o.get("price"),
                    avg_price=o.get("average"),
                    status=o.get("status", "unknown"),
                    reduce_only=False,
                    leverage=1,
                    margin_mode="isolated",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ))
            return results
        except Exception as e:
            logger.error(f"Binance get_open_orders error: {e}")
            return []

    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionResult]:
        await self._ensure_connected()
        try:
            positions = self._ccxt.fetch_positions([self._normalize_symbol(symbol)] if symbol else None)
            results = []
            for p in positions:
                size = float(p.get("contracts", 0) or p.get("size", 0))
                if size == 0:
                    continue
                results.append(PositionResult(
                    symbol=p.get("symbol", symbol or ""),
                    side="long" if size > 0 else "short",
                    size=abs(size),
                    entry_price=float(p.get("entryPrice", 0) or p.get("entry_price", 0)),
                    mark_price=float(p.get("markPrice", 0) or p.get("mark_price", 0)),
                    liquidation_price=float(p.get("liquidationPrice", 0) or p.get("liquidation_price", 0)),
                    leverage=int(p.get("leverage", 1)),
                    margin=float(p.get("initialMargin", 0) or p.get("margin", 0)),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0) or p.get("unrealized_pnl", 0)),
                    realized_pnl=float(p.get("realizedPnl", 0) or p.get("realized_pnl", 0)),
                    isolated=p.get("marginMode", "isolated") == "isolated",
                ))
            return results
        except Exception as e:
            logger.error(f"Binance get_positions error: {e}")
            return []

    async def get_balance(self) -> BalanceResult:
        await self._ensure_connected()
        try:
            bal = self._ccxt.fetch_balance()
            usdt = bal.get("USDT", {})
            return BalanceResult(
                total=float(usdt.get("total", 0)),
                free=float(usdt.get("free", 0)),
                used=float(usdt.get("used", 0)),
                unrealized_pnl=float(usdt.get("unrealizedPnl", 0) or 0),
            )
        except Exception as e:
            logger.error(f"Binance get_balance error: {e}")
            return BalanceResult(total=0, free=0, used=0, unrealized_pnl=0)

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        await self._ensure_connected()
        try:
            self._ccxt.set_leverage(leverage, self._normalize_symbol(symbol))
            return True
        except Exception as e:
            logger.error(f"Binance set_leverage error: {e}")
            return False

    async def set_margin_mode(self, symbol: str, mode: str) -> bool:
        await self._ensure_connected()
        try:
            self._ccxt.set_margin_mode(mode, self._normalize_symbol(symbol))
            return True
        except Exception as e:
            logger.error(f"Binance set_margin_mode error: {e}")
            return False

    async def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        await self._ensure_connected()
        try:
            funding = self._ccxt.fetch_funding_rate(self._normalize_symbol(symbol))
            if funding:
                return {
                    "symbol": funding.get("symbol", symbol),
                    "funding_rate": funding.get("fundingRate", 0),
                    "funding_time": funding.get("fundingTimestamp"),
                    "next_funding_time": funding.get("nextFundingTimestamp"),
                    "mark_price": funding.get("markPrice", 0),
                }
            return None
        except Exception as e:
            logger.error(f"Binance get_funding_rate error: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> Optional[Dict]:
        await self._ensure_connected()
        try:
            oi = self._ccxt.fetch_open_interest(self._normalize_symbol(symbol))
            if oi:
                return {
                    "symbol": oi.get("symbol", symbol),
                    "open_interest": oi.get("openInterestAmount", 0) or oi.get("openInterestValue", 0),
                    "open_interest_value": oi.get("openInterestValue", 0),
                    "timestamp": oi.get("timestamp"),
                }
            return None
        except Exception as e:
            logger.error(f"Binance get_open_interest error: {e}")
            return None

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        await self._ensure_connected()
        try:
            t = self._ccxt.fetch_ticker(self._normalize_symbol(symbol))
            if t:
                return {
                    "symbol": t.get("symbol", symbol),
                    "price": t.get("last", 0),
                    "bid": t.get("bid", 0),
                    "ask": t.get("ask", 0),
                    "high_24h": t.get("high", 0),
                    "low_24h": t.get("low", 0),
                    "volume_24h": t.get("baseVolume", 0),
                    "change_24h": t.get("change", 0),
                    "change_percent": t.get("percentage", 0),
                    "funding_rate": t.get("fundingRate", 0),
                }
            return None
        except Exception as e:
            logger.error(f"Binance get_ticker error: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict]:
        await self._ensure_connected()
        try:
            ob = self._ccxt.fetch_order_book(self._normalize_symbol(symbol), limit)
            if ob:
                return {
                    "bids": ob.get("bids", [])[:10],
                    "asks": ob.get("asks", [])[:10],
                    "timestamp": ob.get("timestamp", 0),
                }
            return None
        except Exception as e:
            logger.error(f"Binance get_orderbook error: {e}")
            return None

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> List[Dict]:
        await self._ensure_connected()
        try:
            ohlcvs = self._ccxt.fetch_ohlcv(self._normalize_symbol(symbol), timeframe, limit=limit)
            results = []
            for o in ohlcvs:
                results.append({
                    "time": o[0],
                    "open": o[1],
                    "high": o[2],
                    "low": o[3],
                    "close": o[4],
                    "volume": o[5],
                })
            return results
        except Exception as e:
            logger.error(f"Binance get_ohlcv error: {e}")
            return []

    async def get_leverage_brackets(self, symbol: str) -> Optional[List[Dict]]:
        await self._ensure_connected()
        try:
            return self._ccxt.fetch_leverage_tiers([self._normalize_symbol(symbol)])
        except Exception as e:
            logger.error(f"Binance get_leverage_brackets error: {e}")
            return None

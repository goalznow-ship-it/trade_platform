from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.models.user import User
from app.services.trading import trading_service

router = APIRouter(prefix="/trade", tags=["Trading"])

class OrderRequest(BaseModel):
    exchange: str = "binance"
    symbol: str
    side: str
    amount: float
    order_type: str = "market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    leverage: int = 1

class APIKeyRequest(BaseModel):
    exchange: str
    api_key: str
    secret_key: str

@router.post("/order")
async def create_order(req: OrderRequest, user: User = Depends(get_current_user)):
    api_key = None
    secret_key = None
    if req.exchange == 'binance':
        api_key = user.binance_api_key
        secret_key = user.binance_secret_key
    if not api_key or not secret_key:
        raise HTTPException(400, "Exchange API keys not configured")
    return await trading_service.create_order(
        req.exchange, req.symbol, req.side, req.amount,
        req.order_type, req.price, req.stop_price, req.leverage,
        api_key, secret_key
    )

@router.post("/cancel")
async def cancel_order(exchange: str, symbol: str, order_id: str, user: User = Depends(get_current_user)):
    api_key = user.binance_api_key if exchange == 'binance' else user.bybit_api_key
    secret_key = user.binance_secret_key if exchange == 'binance' else user.bybit_secret_key
    return await trading_service.cancel_order(exchange, symbol, order_id, api_key, secret_key)

@router.get("/positions")
async def get_positions(user: User = Depends(get_current_user)):
    positions = []
    if user.binance_api_key:
        bp = await trading_service.get_positions('binance', user.binance_api_key, user.binance_secret_key)
        positions.extend(bp)
    if user.bybit_api_key:
        byp = await trading_service.get_positions('bybit', user.bybit_api_key, user.bybit_secret_key)
        positions.extend(byp)
    return positions

@router.get("/balance")
async def get_balance(user: User = Depends(get_current_user)):
    balances = {}
    if user.binance_api_key:
        balances['binance'] = await trading_service.get_balance('binance', user.binance_api_key, user.binance_secret_key)
    if user.bybit_api_key:
        balances['bybit'] = await trading_service.get_balance('bybit', user.bybit_api_key, user.bybit_secret_key)
    return balances

@router.get("/orders")
async def get_open_orders(exchange: str = "binance", symbol: str = None, user: User = Depends(get_current_user)):
    api_key = user.binance_api_key if exchange == 'binance' else user.bybit_api_key
    secret_key = user.binance_secret_key if exchange == 'binance' else user.bybit_secret_key
    return await trading_service.get_open_orders(exchange, symbol, api_key, secret_key)

@router.post("/api-keys")
async def save_api_keys(req: APIKeyRequest, user: User = Depends(get_current_user)):
    if req.exchange == 'binance':
        user.binance_api_key = req.api_key
        user.binance_secret_key = req.secret_key
    elif req.exchange == 'bybit':
        user.bybit_api_key = req.api_key
        user.bybit_secret_key = req.secret_key
    else:
        raise HTTPException(400, "Unsupported exchange")
    return {"message": "API keys saved"}

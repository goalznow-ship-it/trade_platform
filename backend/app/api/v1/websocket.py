from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime, timezone
from app.services.market import market_service
from app.services.ai_analysis import ai_engine
from app.services.signals import signal_service
from app.core.logging import logger

router = APIRouter()

connected_clients = {}

@router.websocket("/ws/{symbol:path}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    symbol = symbol.replace("-", "/")
    await websocket.accept()
    client_id = id(websocket)
    connected_clients[client_id] = websocket

    try:
        while True:
            data = await market_service.get_ohlcv(symbol, "binance", "1m", 60)
            if data:
                analysis = await ai_engine.analyze(symbol, data, "1m")
                signals = await signal_service.generate_signals(symbol, data, "1m")
                payload = {
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "price": data[-1]['close'] if data else None,
                    "volume": data[-1]['volume'] if data else None,
                    "high_24h": max(d['high'] for d in data[-24:]) if len(data) >= 24 else None,
                    "low_24h": min(d['low'] for d in data[-24:]) if len(data) >= 24 else None,
                    "change_24h": ((data[-1]['close'] - data[-24]['close']) / data[-24]['close'] * 100) if len(data) >= 24 else 0,
                    "ai_analysis": analysis,
                    "signals": signals.get('signals', []),
                    "confidence": signals.get('confidence', {}),
                }
                try:
                    await websocket.send_text(json.dumps(payload))
                except Exception:
                    break
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
    finally:
        connected_clients.pop(client_id, None)

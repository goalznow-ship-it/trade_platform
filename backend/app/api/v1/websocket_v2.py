from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import ws_manager
from app.core.logging import logger
import json

router = APIRouter()


@router.websocket("/ws/v2")
async def websocket_v2(websocket: WebSocket):
    client = await ws_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket v2 error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.websocket("/ws/v2/{channel}")
async def websocket_v2_channel(websocket: WebSocket, channel: str, token: str = Query("")):
    client = await ws_manager.connect(websocket)
    if token:
        await ws_manager.authenticate(client, token)
    if channel in ws_manager.channel_subscriptions:
        ws_manager._subscribe(client, channel)
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket v2 channel error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.websocket("/ws/v2/ticker/{symbol:path}")
async def websocket_ticker(websocket: WebSocket, symbol: str, token: str = Query("")):
    client = await ws_manager.connect(websocket)
    if token:
        await ws_manager.authenticate(client, token)
    sym = symbol.replace("-", "/")
    await ws_manager.subscribe(client, "ticker", [sym])
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket ticker error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.get("/ws/stats")
async def websocket_stats():
    return ws_manager.stats

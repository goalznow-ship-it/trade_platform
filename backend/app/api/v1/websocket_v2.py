import asyncio
import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.database import async_session_factory
from app.core.logging import logger
from app.core.security import get_user_from_token, require_admin
from app.core.websocket_manager import ws_manager

router = APIRouter()


async def _authenticate_connection(websocket: WebSocket, client, legacy_token: str) -> bool:
    """Authenticate without putting credentials in the WebSocket URL.

    Query-token support remains temporarily available for older clients, while
    current clients send an auth message immediately after the connection opens.
    """
    if legacy_token:
        async with async_session_factory() as db:
            try:
                user = await get_user_from_token(legacy_token, db)
                await ws_manager.mark_authenticated(client, user.id)
                return True
            except Exception:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return False

    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        message = json.loads(raw)
    except (TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        await websocket.close(code=1008, reason="Authentication required")
        return False

    if message.get("type") != "auth" or not isinstance(message.get("data"), dict):
        await websocket.close(code=1008, reason="Authentication required")
        return False

    await ws_manager.handle_message(client, raw)
    if not client.is_authenticated:
        await websocket.close(code=1008, reason="Invalid authentication token")
        return False
    return True


@router.websocket("/ws/v2")
async def websocket_v2(websocket: WebSocket, token: str = Query("")):
    client = await ws_manager.connect(websocket)
    if token:
        async with async_session_factory() as db:
            try:
                user = await get_user_from_token(token, db)
                await ws_manager.mark_authenticated(client, user.id)
            except Exception:
                await websocket.close(code=1008, reason="Invalid authentication token")
                await ws_manager.disconnect(client.client_id)
                return
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        if "not connected" not in str(e).lower():
            logger.error(f"WebSocket v2 error: {e}")
    except Exception as e:
        logger.error(f"WebSocket v2 error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.websocket("/ws/v2/{channel}")
async def websocket_v2_channel(websocket: WebSocket, channel: str, token: str = Query("")):
    client = await ws_manager.connect(websocket)
    if not await _authenticate_connection(websocket, client, token):
        await ws_manager.disconnect(client.client_id)
        return
    await ws_manager.subscribe(client, channel)
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        if "not connected" not in str(e).lower():
            logger.error(f"WebSocket v2 channel error: {e}")
    except Exception as e:
        logger.error(f"WebSocket v2 channel error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.websocket("/ws/v2/ticker/{symbol:path}")
async def websocket_ticker(websocket: WebSocket, symbol: str, token: str = Query("")):
    client = await ws_manager.connect(websocket)
    if not await _authenticate_connection(websocket, client, token):
        await ws_manager.disconnect(client.client_id)
        return
    sym = symbol.replace("-", "/")
    await ws_manager.subscribe(client, "ticker", [sym])
    try:
        while True:
            raw = await websocket.receive_text()
            await ws_manager.handle_message(client, raw)
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        if "not connected" not in str(e).lower():
            logger.error(f"WebSocket ticker error: {e}")
    except Exception as e:
        logger.error(f"WebSocket ticker error: {e}")
    finally:
        await ws_manager.disconnect(client.client_id)


@router.get("/ws/stats")
async def websocket_stats(admin=Depends(require_admin)):
    return ws_manager.stats

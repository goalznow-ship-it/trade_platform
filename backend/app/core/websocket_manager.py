import asyncio
import json
import time
import uuid
from typing import Dict, Set, Optional, Any, Callable
from datetime import datetime, timezone
from fastapi import WebSocket
from jose import jwt, JWTError
from app.core.config import settings
from app.core.redis import redis_client
from app.core.logging import logger
from app.core.rate_limiter import InMemoryRateLimiter


class ConnectionState:
    PENDING = "pending"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"


class Channel:
    MARKET = "market"
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    SIGNALS = "signals"
    TRADES = "trades"
    POSITIONS = "positions"
    PORTFOLIO = "portfolio"
    NOTIFICATIONS = "notifications"
    ORDERFLOW = "orderflow"
    DERIVATIVES = "derivatives"
    NEWS = "news"
    SENTIMENT = "sentiment"
    ONCHAIN = "onchain"
    MACRO = "macro"
    BRAIN = "brain"
    SCANNER = "scanner"
    FEAR_GREED = "fear_greed"
    BREADTH = "breadth"
    SKHY = "skhy"

    ALL = [MARKET, TICKER, ORDERBOOK, SIGNALS, TRADES, POSITIONS, PORTFOLIO,
           NOTIFICATIONS, ORDERFLOW, DERIVATIVES, NEWS, SENTIMENT, ONCHAIN,
           MACRO, BRAIN, SCANNER, FEAR_GREED, BREADTH, SKHY]


class WebSocketClient:
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.user_id: Optional[int] = None
        self.state = ConnectionState.PENDING
        self.subscriptions: Set[str] = set()
        self.symbol_subscriptions: Set[str] = set()
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = time.time()
        self.user_agent: Optional[str] = None

    async def send_json(self, data: dict) -> bool:
        try:
            await self.websocket.send_text(json.dumps(data))
            return True
        except Exception:
            return False

    async def send_personalized(self, event: str, data: Any, channel: str = None):
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if channel:
            payload["channel"] = channel
        return await self.send_json(payload)

    @property
    def is_authenticated(self) -> bool:
        return self.state == ConnectionState.AUTHENTICATED


class WebSocketManager:
    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.channel_subscriptions: Dict[str, Set[str]] = {ch: set() for ch in Channel.ALL}
        self.user_clients: Dict[int, Set[str]] = {}
        self.publishers: Dict[str, Callable] = {}
        self.rate_limiter = InMemoryRateLimiter()
        self._redis_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        self._redis_task = asyncio.create_task(self._redis_listener())
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("WebSocket Manager started")

    async def stop(self):
        if self._redis_task:
            self._redis_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for client in list(self.clients.values()):
            await self.disconnect(client.client_id)
        logger.info("WebSocket Manager stopped")

    async def connect(self, websocket: WebSocket) -> WebSocketClient:
        await websocket.accept()
        client_id = str(uuid.uuid4())
        client = WebSocketClient(websocket, client_id)
        self.clients[client_id] = client

        await client.send_json({
            "event": "connected",
            "data": {"client_id": client_id, "server_time": datetime.now(timezone.utc).isoformat()},
        })
        logger.info(f"WebSocket client connected: {client_id}")
        return client

    async def disconnect(self, client_id: str):
        client = self.clients.pop(client_id, None)
        if not client:
            return

        for channel in list(client.subscriptions):
            self._unsubscribe(client, channel)

        if client.user_id and client.user_id in self.user_clients:
            self.user_clients[client.user_id].discard(client_id)
            if not self.user_clients[client.user_id]:
                del self.user_clients[client.user_id]

        logger.info(f"WebSocket client disconnected: {client_id}, user: {client.user_id}")

    async def authenticate(self, client: WebSocketClient, token: str) -> bool:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "access":
                await client.send_json({"event": "error", "data": {"message": "Invalid token type"}})
                return False
            user_id = payload.get("sub")
            if not user_id:
                await client.send_json({"event": "error", "data": {"message": "Invalid token"}})
                return False
            client.user_id = int(user_id)
            client.state = ConnectionState.AUTHENTICATED

            if client.user_id not in self.user_clients:
                self.user_clients[client.user_id] = set()
            self.user_clients[client.user_id].add(client.client_id)

            await client.send_json({
                "event": "authenticated",
                "data": {"user_id": client.user_id},
            })
            return True
        except JWTError:
            await client.send_json({"event": "error", "data": {"message": "Invalid token"}})
            return False

    async def mark_authenticated(self, client: WebSocketClient, user_id: int) -> None:
        client.user_id = user_id
        client.state = ConnectionState.AUTHENTICATED
        self.user_clients.setdefault(user_id, set()).add(client.client_id)
        await client.send_json({"event": "authenticated", "data": {"user_id": user_id}})

    async def subscribe(self, client: WebSocketClient, channel: str, symbols: list = None):
        if not client.is_authenticated:
            await client.send_json({"event": "error", "data": {"message": "Not authenticated"}})
            return

        if channel not in Channel.ALL:
            await client.send_json({"event": "error", "data": {"message": f"Unknown channel: {channel}"}})
            return

        self._subscribe(client, channel)
        if symbols:
            client.symbol_subscriptions.update(symbols)

        await client.send_json({
            "event": "subscribed",
            "data": {"channel": channel, "symbols": symbols},
        })

    def _subscribe(self, client: WebSocketClient, channel: str):
        client.subscriptions.add(channel)
        self.channel_subscriptions[channel].add(client.client_id)

    def _unsubscribe(self, client: WebSocketClient, channel: str):
        client.subscriptions.discard(channel)
        self.channel_subscriptions[channel].discard(client.client_id)

    async def unsubscribe(self, client: WebSocketClient, channel: str):
        self._unsubscribe(client, channel)
        await client.send_json({"event": "unsubscribed", "data": {"channel": channel}})

    async def broadcast(self, channel: str, event: str, data: Any, exclude: str = None):
        if channel not in self.channel_subscriptions:
            return

        payload = {
            "event": event,
            "channel": channel,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        disconnected = []
        for client_id in self.channel_subscriptions[channel]:
            if client_id == exclude:
                continue
            client = self.clients.get(client_id)
            if not client:
                disconnected.append(client_id)
                continue
            if not await client.send_json(payload):
                disconnected.append(client_id)

        for cid in disconnected:
            await self.disconnect(cid)

    async def send_to_user(self, user_id: int, event: str, data: Any, channel: str = None):
        client_ids = self.user_clients.get(user_id, set())
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if channel:
            payload["channel"] = channel

        for client_id in list(client_ids):
            client = self.clients.get(client_id)
            if client:
                await client.send_json(payload)

    async def handle_heartbeat(self, client: WebSocketClient, data: Optional[dict] = None):
        client.last_heartbeat = time.time()
        response = {"server_time": datetime.now(timezone.utc).isoformat()}
        if data and "t" in data:
            response["t"] = data["t"]
        await client.send_json({"event": "pong", "data": response})

    async def handle_message(self, client: WebSocketClient, raw: str):
        allowed, _ = self.rate_limiter.check(f"ws:{client.client_id}", 30, 1)
        if not allowed:
            await client.send_json({"event": "error", "data": {"message": "Rate limit exceeded"}})
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await client.send_json({"event": "error", "data": {"message": "Invalid JSON"}})
            return

        msg_type = msg.get("type")
        msg_data = msg.get("data", {})

        handlers = {
            "auth": self._handle_auth,
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "ping": self._handle_ping,
            "pong": self._handle_pong,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(client, msg_data)
        else:
            await client.send_json({"event": "error", "data": {"message": f"Unknown message type: {msg_type}"}})

    async def _handle_auth(self, client: WebSocketClient, data: dict):
        token = data.get("token")
        if not token:
            await client.send_json({"event": "error", "data": {"message": "Token required"}})
            return
        await self.authenticate(client, token)

    async def _handle_subscribe(self, client: WebSocketClient, data: dict):
        channel = data.get("channel")
        symbols = data.get("symbols")
        await self.subscribe(client, channel, symbols)

    async def _handle_unsubscribe(self, client: WebSocketClient, data: dict):
        channel = data.get("channel")
        await self.unsubscribe(client, channel)

    async def _handle_ping(self, client: WebSocketClient, data: dict):
        await self.handle_heartbeat(client, data)

    async def _handle_pong(self, client: WebSocketClient, data: dict):
        client.last_heartbeat = time.time()

    async def publish_redis(self, channel: str, event: str, data: Any):
        payload = json.dumps({"event": event, "channel": channel, "data": data})
        await redis_client.publish(f"ws:{channel}", payload)

    async def _redis_listener(self):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ws:*")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        channel = payload.get("channel")
                        if channel:
                            await self.broadcast(channel, payload.get("event"), payload.get("data"))
                    except (json.JSONDecodeError, KeyError):
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe()

    async def _periodic_cleanup(self):
        while True:
            await asyncio.sleep(30)
            now = time.time()
            stale = []
            for client_id, client in self.clients.items():
                if now - client.last_heartbeat > 60:
                    stale.append(client_id)
            for cid in stale:
                await self.disconnect(cid)

    @property
    def stats(self) -> dict:
        return {
            "total_clients": len(self.clients),
            "authenticated_clients": sum(1 for c in self.clients.values() if c.is_authenticated),
            "channel_subscriptions": {ch: len(clients) for ch, clients in self.channel_subscriptions.items()},
            "active_users": len(self.user_clients),
        }


ws_manager = WebSocketManager()

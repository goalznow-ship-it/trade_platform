import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from app.core.logging import logger
from app.services.exchange.base import (
    BaseExchange, OrderRequest, OrderResult,
    PositionResult, BalanceResult,
)
from app.services.exchange.binance_futures import BinanceFuturesExchange
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.exchange import ExchangeCredentials


ENCRYPTION_KEY = None


def get_encryption_key() -> bytes:
    global ENCRYPTION_KEY
    if ENCRYPTION_KEY is None:
        import os
        key = os.environ.get("EXCHANGE_ENCRYPTION_KEY")
        if key:
            ENCRYPTION_KEY = key.encode() if len(key) == 44 else Fernet.generate_key()
        else:
            ENCRYPTION_KEY = Fernet.generate_key()
    return ENCRYPTION_KEY


def encrypt_api_key(value: str) -> str:
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted.encode()).decode()


class ExchangeManager:
    _instance: Optional["ExchangeManager"] = None

    def __new__(cls) -> "ExchangeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._exchanges: Dict[str, BaseExchange] = {}
        self._user_connections: Dict[int, Dict[str, BaseExchange]] = {}
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}

    def register_exchange(self, name: str, exchange: BaseExchange) -> None:
        self._exchanges[name] = exchange

    async def get_user_exchange(self, user_id: int, exchange_name: str,
                                 db: AsyncSession) -> Optional[BaseExchange]:
        if user_id in self._user_connections and exchange_name in self._user_connections[user_id]:
            exchange = self._user_connections[user_id][exchange_name]
            if exchange.is_connected:
                return exchange

        result = await db.execute(
            select(ExchangeCredentials).where(
                ExchangeCredentials.user_id == user_id,
                ExchangeCredentials.exchange == exchange_name,
                ExchangeCredentials.is_active == True,
            )
        )
        creds = result.scalar_one_or_none()
        if not creds:
            return None

        api_key = decrypt_api_key(creds.api_key)
        secret_key = decrypt_api_key(creds.secret_key)
        passphrase = decrypt_api_key(creds.passphrase) if creds.passphrase else None

        exchange_class = self._exchanges.get(exchange_name)
        if not exchange_class:
            return None

        connected = await exchange_class.connect(api_key, secret_key, passphrase)
        if not connected:
            return None

        if user_id not in self._user_connections:
            self._user_connections[user_id] = {}
        self._user_connections[user_id][exchange_name] = exchange_class

        creds.last_used = datetime.now(timezone.utc)
        await db.commit()

        return exchange_class

    async def save_credentials(self, user_id: int, exchange: str,
                                api_key: str, secret_key: str,
                                passphrase: Optional[str] = None,
                                label: Optional[str] = None,
                                db: AsyncSession = None) -> bool:
        try:
            encrypted_key = encrypt_api_key(api_key)
            encrypted_secret = encrypt_api_key(secret_key)
            encrypted_pass = encrypt_api_key(passphrase) if passphrase else None

            result = await db.execute(
                select(ExchangeCredentials).where(
                    ExchangeCredentials.user_id == user_id,
                    ExchangeCredentials.exchange == exchange,
                )
            )
            creds = result.scalar_one_or_none()

            if creds:
                creds.api_key = encrypted_key
                creds.secret_key = encrypted_secret
                creds.passphrase = encrypted_pass
                creds.label = label or creds.label
                creds.is_active = True
            else:
                creds = ExchangeCredentials(
                    user_id=user_id, exchange=exchange,
                    api_key=encrypted_key, secret_key=encrypted_secret,
                    passphrase=encrypted_pass, label=label, is_active=True,
                )
                db.add(creds)

            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Save credentials error: {e}")
            return False

    async def remove_credentials(self, user_id: int, exchange: str,
                                   db: AsyncSession) -> bool:
        try:
            result = await db.execute(
                select(ExchangeCredentials).where(
                    ExchangeCredentials.user_id == user_id,
                    ExchangeCredentials.exchange == exchange,
                )
            )
            creds = result.scalar_one_or_none()
            if creds:
                creds.is_active = False
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Remove credentials error: {e}")
            return False

    async def disconnect_user(self, user_id: int, exchange_name: Optional[str] = None) -> None:
        if user_id not in self._user_connections:
            return
        if exchange_name:
            ex = self._user_connections[user_id].pop(exchange_name, None)
            if ex:
                await ex.disconnect()
        else:
            for name, ex in self._user_connections[user_id].items():
                await ex.disconnect()
            self._user_connections.pop(user_id, None)

    async def start_reconnect_loop(self, exchange_name: str) -> None:
        if exchange_name in self._reconnect_tasks:
            return
        async def loop():
            while True:
                await asyncio.sleep(60)
                for uid, connections in list(self._user_connections.items()):
                    ex = connections.get(exchange_name)
                    if ex and not ex.is_connected:
                        logger.info(f"Reconnecting {exchange_name} for user {uid}")
                        await ex.reconnect()
        self._reconnect_tasks[exchange_name] = asyncio.create_task(loop())

    async def get_position(self, user_id: int, exchange_name: str,
                            symbol: str, db: AsyncSession) -> Optional[PositionResult]:
        ex = await self.get_user_exchange(user_id, exchange_name, db)
        if not ex:
            return None
        positions = await ex.get_positions(symbol)
        return positions[0] if positions else None

    async def get_all_positions(self, user_id: int, exchange_name: str,
                                  db: AsyncSession) -> List[PositionResult]:
        ex = await self.get_user_exchange(user_id, exchange_name, db)
        if not ex:
            return []
        return await ex.get_positions()

    async def get_balance(self, user_id: int, exchange_name: str,
                            db: AsyncSession) -> Optional[BalanceResult]:
        ex = await self.get_user_exchange(user_id, exchange_name, db)
        if not ex:
            return None
        return await ex.get_balance()

    async def create_order(self, user_id: int, exchange_name: str,
                             request: OrderRequest,
                             db: AsyncSession) -> OrderResult:
        ex = await self.get_user_exchange(user_id, exchange_name, db)
        if not ex:
            return OrderResult(
                order_id="", symbol=request.symbol, side=request.side,
                order_type=request.order_type, quantity=request.quantity,
                filled_quantity=0, price=request.price, avg_price=None,
                status="rejected", reduce_only=request.reduce_only,
                leverage=request.leverage, margin_mode=request.margin_mode,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                error="Exchange not connected",
            )
        return await ex.create_order(request)


exchange_manager = ExchangeManager()
exchange_manager.register_exchange("binance", BinanceFuturesExchange())

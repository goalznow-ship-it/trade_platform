from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "TradeAnalyst Pro"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    PORT: int = 8000

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "trading"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    SECRET_KEY: str = "ta-pro-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "*"
    EXCHANGE_ENCRYPTION_KEY: Optional[str] = None
    ENABLE_BACKGROUND_SERVICES: bool = True
    TRADING_ENABLED: bool = False

    RATE_LIMIT_MAX: int = 60
    RATE_LIMIT_WINDOW: int = 60

    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_SECRET_KEY: Optional[str] = None
    COINGECKO_API_KEY: Optional[str] = None

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    DISCORD_BOT_TOKEN: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None

    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.ENVIRONMENT.lower() == "production":
            errors = []
            if self.SECRET_KEY == "ta-pro-secret-key-change-in-production" or len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be unique and at least 32 characters")
            if self.POSTGRES_PASSWORD == "postgres":
                errors.append("POSTGRES_PASSWORD must not use the default")
            if self.CORS_ORIGINS.strip() == "*":
                errors.append("CORS_ORIGINS must list trusted origins")
            if not self.EXCHANGE_ENCRYPTION_KEY:
                errors.append("EXCHANGE_ENCRYPTION_KEY is required")
            if errors:
                raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

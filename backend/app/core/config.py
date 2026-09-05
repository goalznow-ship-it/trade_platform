
from pydantic import model_validator
from pydantic_settings import BaseSettings


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
    EXCHANGE_ENCRYPTION_KEY: str | None = None
    ENABLE_BACKGROUND_SERVICES: bool = True
    TRADING_ENABLED: bool = False

    RATE_LIMIT_MAX: int = 60
    RATE_LIMIT_WINDOW: int = 60

    BINANCE_API_KEY: str | None = None
    BINANCE_SECRET_KEY: str | None = None
    BYBIT_API_KEY: str | None = None
    BYBIT_SECRET_KEY: str | None = None
    COINGECKO_API_KEY: str | None = None

    TELEGRAM_BOT_TOKEN: str | None = None
    DISCORD_BOT_TOKEN: str | None = None
    SENDGRID_API_KEY: str | None = None

    SSL_CERT_PATH: str | None = None
    SSL_KEY_PATH: str | None = None

    # ── ML / backtest / retrain (Phase 4) ──────────────────────
    # Where MLflow writes runs. Default is the local ./mlruns
    # directory so a single-host dev install Just Works; in
    # production, set this to the MLflow tracking server URI.
    MLFLOW_TRACKING_URI: str = "file:./mlruns"
    MLFLOW_EXPERIMENT_NAME: str = "ml-signal-engine"
    # How often the celery beat schedule wants a fresh model.
    # ``MLSignalEngine.needs_retrain`` reads this and also
    # honours the ``force_retrain`` Redis flag.
    ML_RETRAIN_HOURS: int = 24
    # Minimum out-of-sample hit rate a freshly-trained model must
    # reach to be promoted into ``model_dir/registry.json`` and
    # become the live ensemble. Below this, the registry keeps
    # the previous version.
    ML_MIN_OOS_HIT_RATE: float = 0.45
    # Top-N symbols the scheduled retrain pulls historical data
    # for. Smaller = faster retrain, larger = more robust.
    ML_RETRAIN_SYMBOLS_TOP_N: int = 15
    # OHLCV bars per symbol to fetch for training. 5000 15m bars
    # is ~52 days, enough for walk-forward splits to make sense.
    ML_RETRAIN_BARS_PER_SYMBOL: int = 5000
    # Cache TTL for the ML-mode backtest endpoint. The backtest
    # is expensive (OOS walk-forward) so we cache for an hour.
    BACKTEST_ML_CACHE_TTL: int = 3600

    # ── Quality gate (Phase 5) ────────────────────────────────────
    # Minimum rolling hit rate an engine must keep over the
    # evaluation window. Below this, the engine is auto-disabled
    # and the pipeline stops emitting until an operator (or a
    # successful probe) re-enables it.
    QUALITY_MIN_HIT_RATE: float = 0.40
    # Window the quality gate reads from (hours). 24h gives
    # the per-engine aggregator enough resolved signals to
    # make a stable decision without lagging the live state.
    QUALITY_WINDOW_HOURS: int = 24
    # How often the cron job recomputes the quality row.
    # 15 min is a good balance between DB load and freshness.
    QUALITY_EVAL_INTERVAL_MINUTES: int = 15
    # Per-engine circuit breaker. ``CB_FAILURE_THRESHOLD``
    # consecutive failures trip the breaker; ``CB_OPEN_SECONDS``
    # is how long the engine stays blocked before the
    # half-open transition allows one probe.
    CB_FAILURE_THRESHOLD: int = 5
    CB_OPEN_SECONDS: int = 86_400  # 24h
    # When the quality gate disables an engine, this is the
    # minimum gap between evaluation runs before the gate may
    # re-enable the engine on a fresh successful probe.
    QUALITY_REENABLE_GRACE_MINUTES: int = 60
    # Phase 6 SLO: p95 API latency must stay under this budget.
    # The latency test reads the histogram and fails if the
    # computed p95 exceeds the budget. A 1.0s budget is a common
    # web SLO — anything slower and the dashboard starts feeling
    # sluggish under real load.
    SLO_API_P95_SECONDS: float = 1.0

    @model_validator(mode="after")
    def validate_production_settings(self):
        # Use exact comparison for production gating — previous
        # implementation used .lower() which let ENVIRONMENT=Production
        # slip through, defeating the check.
        if self.ENVIRONMENT == "production":
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
        else:
            # In development, warn loudly if someone is running with the
            # well-known default secret key — this exact string appears
            # in the repo and is on every attacker's wordlist.
            if self.SECRET_KEY == "ta-pro-secret-key-change-in-production":
                import warnings
                warnings.warn(
                    "SECRET_KEY is set to the public default. "
                    "Tokens signed with this key are forgeable. "
                    "Set a unique SECRET_KEY (>= 32 chars) in .env.",
                    stacklevel=2,
                )
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
        extra = "ignore"


settings = Settings()

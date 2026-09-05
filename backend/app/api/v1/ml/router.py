"""
ML API routes — exposed to the frontend.

Endpoints:
- GET  /api/v1/ml/predict/{symbol}              — single prediction
- POST /api/v1/ml/predict-batch                 — multi-symbol batch
- GET  /api/v1/ml/feature-importance            — top features
- GET  /api/v1/ml/status                        — model health
- POST /api/v1/ml/retrain                       — trigger retraining (admin)
- POST /api/v1/ml/augment-score                 — augment institutional score
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.security import get_current_user
from app.services.exchange.manager import exchange_manager
from app.services.ml import get_ml_engine

router = APIRouter(prefix="/ml", tags=["ml"])


# ── Response models ─────────────────────────────────────────────────
class PredictionResponse(BaseModel):
    symbol: str
    direction: int = Field(..., description="-1=sell, 0=hold, 1=buy")
    direction_label: str
    confidence: float = Field(..., ge=0, le=1)
    agreement: float = Field(..., ge=0, le=1)
    proba: dict
    per_model: dict
    feature_version: str
    timestamp: str


class BatchPredictionRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "15m"


class AugmentScoreRequest(BaseModel):
    symbol: str
    base_score: float = Field(..., ge=0, le=100)


# ── Helpers ─────────────────────────────────────────────────────────
def _build_ohlcv_df(ohlcv: list) -> pd.DataFrame:
    """
    Pure CPU work: build a sorted, indexed DataFrame from raw OHLCV rows.
    No I/O — safe to call inside asyncio.to_thread.
    """
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.set_index("timestamp").sort_index()


async def _fetch_ohlcv_df(exchange, symbol: str, timeframe: str, limit: int = 500):
    """
    Async wrapper. The network call is awaited; DataFrame construction
    is dispatched to a worker thread so it does not block the event loop.
    """
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            return None
        return await asyncio.to_thread(_build_ohlcv_df, ohlcv)
    except Exception as e:
        logger.error(f"OHLCV fetch failed for {symbol}: {e}")
        return None


# ── Endpoints ───────────────────────────────────────────────────────
@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def predict_symbol(
    symbol: str,
    timeframe: str = Query("15m", regex="^(1m|5m|15m|1h|4h)$"),
    user=Depends(get_current_user),
):
    """Generate ML prediction for a single symbol."""
    engine = get_ml_engine()
    if not engine.predictor.is_ready():
        raise HTTPException(503, "ML model not loaded. Train first via /ml/retrain.")

    exchange = await exchange_manager.get_primary()
    if exchange is None:
        raise HTTPException(503, "No exchange client available")

    # Fetch in parallel — both calls are network I/O, so asyncio.gather is
    # the right tool (no thread needed for the wait itself).
    if symbol == "BTC/USDT":
        df, btc_df = await _fetch_ohlcv_df(exchange, symbol, timeframe), None
    else:
        df, btc_df = await asyncio.gather(
            _fetch_ohlcv_df(exchange, symbol, timeframe),
            _fetch_ohlcv_df(exchange, "BTC/USDT", timeframe),
        )

    if df is None or df.empty or len(df) < 200:
        raise HTTPException(400, f"Insufficient data for {symbol}")

    # ML inference is CPU-bound (XGBoost + LightGBM + Transformer) — run in thread
    pred = await asyncio.to_thread(engine.predict, symbol, df, btc_df)
    if "error" in pred:
        # Don't echo pred["error"] verbatim — that came from the
        # inference layer and may include file paths or feature
        # names. Log it server-side, return a generic message with
        # a correlation id the user can quote to support.
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            RuntimeError(pred["error"]),
            user_message="ML prediction failed",
            context=f"ml.predict {symbol} {timeframe}",
        )
        raise HTTPException(500, detail={"error": msg, "correlation_id": corr})

    pred["symbol"] = symbol
    return pred


@router.post("/predict-batch")
async def predict_batch(req: BatchPredictionRequest, user=Depends(get_current_user)):
    """Run predictions for many symbols in parallel."""
    engine = get_ml_engine()
    if not engine.predictor.is_ready():
        raise HTTPException(503, "ML model not loaded")

    exchange = await exchange_manager.get_primary()
    if exchange is None:
        raise HTTPException(503, "No exchange client available")

    symbols = req.symbols[:30]  # cap to 30
    if not symbols:
        return {"count": 0, "results": [], "timestamp": datetime.now(UTC).isoformat()}

    # Fetch BTC context + all symbol DataFrames in parallel. Network I/O
    # only — never blocks the event loop.
    fetch_tasks = [_fetch_ohlcv_df(exchange, s, req.timeframe) for s in symbols]
    btc_task = _fetch_ohlcv_df(exchange, "BTC/USDT", req.timeframe)
    gathered = await asyncio.gather(*fetch_tasks, btc_task)
    btc_df = gathered[-1]
    dfs = gathered[:-1]

    # Inference is CPU-bound — run all predictions on a single thread so
    # we serialize XGBoost/LightGBM/Transformer calls but never block
    # the event loop with them.
    def _infer_all() -> list:
        out: list = []
        for sym, df in zip(symbols, dfs, strict=False):
            if df is None or df.empty or len(df) < 200:
                continue
            ctx = btc_df if (btc_df is not None and not btc_df.empty) else df
            try:
                pred = engine.predict(sym, df, ctx)
                pred["symbol"] = sym
                out.append(pred)
            except Exception as e:
                logger.error(f"Batch infer failed for {sym}: {e}")
        return out

    results = await asyncio.to_thread(_infer_all)
    return {
        "count": len(results),
        "results": results,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/feature-importance")
async def feature_importance(user=Depends(get_current_user)):
    """Top features contributing to the model."""
    engine = get_ml_engine()
    if not engine.predictor.is_ready():
        return {"error": "model not ready", "importance": {}}
    return engine.predictor.feature_importance(top_n=25)


@router.get("/status")
async def ml_status(user=Depends(get_current_user)):
    """Model health and metadata."""
    engine = get_ml_engine()
    ens = engine.predictor.ensemble
    return {
        "is_ready": engine.predictor.is_ready(),
        "last_train_at": engine.last_train_at.isoformat() if engine.last_train_at else None,
        "needs_retrain": engine.needs_retrain(),
        "feature_version": engine.fe.FEATURE_VERSION,
        "weights": ens.weights,
        "models_loaded": {
            "xgboost": ens.xgb is not None,
            "lightgbm": ens.lgb is not None,
            "transformer": ens.transformer is not None,
        },
        "model_metrics": {
            "xgboost": ens.xgb.metrics if ens.xgb else None,
            "lightgbm": ens.lgb.metrics if ens.lgb else None,
            "transformer": ens.transformer.metrics if ens.transformer else None,
        },
    }


@router.post("/augment-score")
async def augment_score(req: AugmentScoreRequest, user=Depends(get_current_user)):
    """
    Take the existing 100-point institutional score and add ML adjustment.
    This is the integration point with the existing scoring system.
    """
    engine = get_ml_engine()
    if not engine.predictor.is_ready():
        return {
            "final_score": req.base_score,
            "ml_adjustment": 0,
            "note": "ml_unavailable",
        }

    exchange = await exchange_manager.get_primary()
    if exchange is None:
        return {
            "final_score": req.base_score,
            "ml_adjustment": 0,
            "note": "exchange_unavailable",
        }

    df, btc_df = await asyncio.gather(
        _fetch_ohlcv_df(exchange, req.symbol, "15m"),
        _fetch_ohlcv_df(exchange, "BTC/USDT", "15m"),
    )
    if df is None or df.empty:
        return {
            "final_score": req.base_score,
            "ml_adjustment": 0,
            "note": "data_unavailable",
        }

    # CPU-bound — never run on the event loop.
    pred = await asyncio.to_thread(engine.predict, req.symbol, df, btc_df)
    return await asyncio.to_thread(
        engine.augment_institutional_score, req.base_score, pred
    )


@router.post("/retrain")
async def trigger_retrain(
    symbols: list[str] | None = None,
    timeframe: str = "15m",
    include_transformer: bool = True,
    user=Depends(get_current_user),
):
    """
    Trigger ML retraining on the dedicated Celery worker.
    Admin-only.

    Why not BackgroundTasks: a single retrain runs XGBoost +
    LightGBM + a PyTorch Transformer on up to 30 symbols. The
    model weights are CPU-bound native code; a `BackgroundTasks`
    task runs in the same event loop as live user requests and
    would stall every other endpoint for the duration of
    training — a self-inflicted DoS. The Celery worker runs
    the job in a separate process (and, in production, a
    separate container with the ml-training profile).
    """
    if not getattr(user, "is_admin", False):
        raise HTTPException(403, "Admin access required")

    from app.services.ml.training.train_script import DEFAULT_SYMBOLS
    from app.workers import retrain_ml_models

    syms = symbols or DEFAULT_SYMBOLS
    async_result = retrain_ml_models.delay(
        symbols=syms,
        timeframe=timeframe,
        include_transformer=include_transformer,
    )
    return {
        "status": "queued",
        "task_id": async_result.id,
        "symbols": len(syms),
        "timeframe": timeframe,
        "include_transformer": include_transformer,
    }


@router.get("/retrain/{task_id}")
async def retrain_status(task_id: str, user=Depends(get_current_user)):
    """
    Poll the status of a previously-queued retrain task.
    """
    if not getattr(user, "is_admin", False):
        raise HTTPException(403, "Admin access required")

    from app.workers import celery_app
    result = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
    }
    if result.ready():
        try:
            response["result"] = result.get(timeout=1)
        except Exception as e:
            response["error"] = str(e)
    return response

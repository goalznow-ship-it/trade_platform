import asyncio
import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.core.cache import cache_get, cache_set
from app.core.logging import logger
from app.services.market_coverage import market_coverage
from app.services.skhy_analysis_engine import skhy_analysis
from app.services.skhy_market_data import normalize_symbol, skhy_market_data
from app.services.skhy_signal_history import skhy_history

router = APIRouter(prefix="/api/v1/skhy", tags=["skhy"])

TF_PATTERN = "^(1m|5m|15m|30m|1h|4h|1d)$"
_ranking_refresh_tasks: dict[str, asyncio.Task] = {}


@router.get("/symbols")
async def get_symbols():
    symbols = [normalize_symbol(item) for item in await market_coverage.get_top_symbols(30)]
    return {"symbols": symbols, "count": len(symbols), "source": "Binance USDT perpetual volume ranking"}


async def _compute_rankings(timeframe: str) -> dict:
    symbols = [normalize_symbol(item) for item in await market_coverage.get_top_symbols(30)]
    semaphore = asyncio.Semaphore(10)

    async def analyze(symbol: str) -> dict:
        async with semaphore:
            try:
                analysis = await skhy_analysis.get_full_analysis(timeframe, symbol)
                scores = analysis.get("scores") or {}
                confidence = float(scores.get("signal_confidence") or 0)
                long_probability = float(scores.get("long_probability") or 0)
                short_probability = float(scores.get("short_probability") or 0)
                direction = "long" if long_probability > short_probability else "short" if short_probability > long_probability else "neutral"
                return {
                    "symbol": symbol,
                    "confidence": confidence,
                    "quality_score": float(scores.get("overall") or 0),
                    "direction": direction,
                    "status": str(scores.get("status") or "WAIT"),
                }
            except Exception as exc:
                logger.warning(f"SKHY ranking analysis failed for {symbol}: {exc}")
                return {
                    "symbol": symbol, "confidence": 0, "quality_score": 0,
                    "direction": "neutral", "status": "NO_DATA",
                }

    rankings = await asyncio.gather(*(analyze(symbol) for symbol in symbols))
    rankings.sort(
        key=lambda item: (item["confidence"], item["quality_score"]),
        reverse=True,
    )
    for index, item in enumerate(rankings, start=1):
        item["rank"] = index

    response = {
        "rankings": rankings,
        "count": len(rankings),
        "timeframe": timeframe,
        "sort": "signal_confidence_desc",
        "source": "SKHY analysis engine",
        "updated_at": datetime.now(UTC).isoformat(),
        "stale": False,
    }
    await cache_set(f"skhy:rankings:{timeframe}", response, ttl=45)
    await cache_set(f"skhy:rankings:last_valid:{timeframe}", response, ttl=86400)
    return response


async def _refresh_rankings(timeframe: str) -> None:
    try:
        await _compute_rankings(timeframe)
    except Exception as exc:
        logger.error(f"SKHY ranking refresh failed for {timeframe}: {exc}")
    finally:
        _ranking_refresh_tasks.pop(timeframe, None)


@router.get("/rankings")
async def get_rankings(timeframe: str = Query(default="1h", pattern=TF_PATTERN)):
    cached = await cache_get(f"skhy:rankings:{timeframe}")
    if isinstance(cached, dict) and cached.get("rankings"):
        return cached

    last_valid = await cache_get(f"skhy:rankings:last_valid:{timeframe}")
    if isinstance(last_valid, dict) and last_valid.get("rankings"):
        task = _ranking_refresh_tasks.get(timeframe)
        if task is None or task.done():
            _ranking_refresh_tasks[timeframe] = asyncio.create_task(_refresh_rankings(timeframe))
        return {**last_valid, "stale": True, "refreshing": True}

    return await _compute_rankings(timeframe)

async def _allowed_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    covered = {normalize_symbol(item) for item in await market_coverage.get_top_symbols(30)}
    if normalized not in covered:
        raise ValueError(f"{normalized} top-30 SKHY Intelligence siyahısında deyil")
    return normalized


async def _build_snapshot_payload(timeframe: str, symbol: str = "SKHYUSDT") -> dict:
    symbol = await _allowed_symbol(symbol)
    snapshot = await skhy_market_data.get_snapshot(symbol)
    ticker = snapshot.get("ticker", {})
    if not ticker:
        raise RuntimeError("Binance Futures API cavab vermir")

    funding = snapshot.get("funding", {})
    oi = snapshot.get("open_interest", {})
    ls = snapshot.get("long_short_ratio", {})
    taker = snapshot.get("taker_buy_sell_ratio", {})
    ob = snapshot.get("orderbook", {})
    ohlcv = await skhy_market_data.get_ohlcv(timeframe, 5, symbol=symbol)
    current_candle = ohlcv[-1] if ohlcv else None

    return {
        "symbol": symbol,
        "exchange": "Binance Futures",
        "market": "USDT Perpetual",
        "timeframe": timeframe,
        "live_price": ticker.get("price"),
        "mark_price": ticker.get("mark_price"),
        "index_price": ticker.get("index_price"),
        "change_24h": ticker.get("change_percent"),
        "high_24h": ticker.get("high_24h"),
        "low_24h": ticker.get("low_24h"),
        "volume_24h": ticker.get("volume_24h"),
        "funding_rate": funding.get("funding_rate"),
        "next_funding_time": funding.get("next_funding_time"),
        "open_interest": oi.get("open_interest"),
        "oi_change": None,
        "long_short_ratio": ls.get("long_short_ratio"),
        "taker_buy_sell_ratio": taker.get("buy_sell_ratio"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "spread": ob.get("bid_ask_spread"),
        "current_candle_open": current_candle["open"] if current_candle else None,
        "current_candle_close": current_candle["close"] if current_candle else None,
        "current_candle_high": current_candle["high"] if current_candle else None,
        "current_candle_low": current_candle["low"] if current_candle else None,
        "latest_update": datetime.now(UTC).isoformat(),
        "provider_status": "connected",
        "data_freshness": snapshot.get("data_freshness", "live"),
    }


@router.get("/ohlcv")
async def get_ohlcv(timeframe: str = "1h", limit: int = 200, symbol: str = "SKHYUSDT"):
    symbol = await _allowed_symbol(symbol)
    try:
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, limit, symbol=symbol)
        if not ohlcv:
            return {"symbol": symbol, "timeframe": timeframe, "data": [], "error": f"{symbol} OHLCV məlumatı yoxdur ({timeframe})"}
        return {"symbol": symbol, "timeframe": timeframe, "data": ohlcv}
    except Exception as e:
        # safe_error_response: in DEBUG we include str(e) for the dev,
        # in production we return a generic phrase + a correlation id
        # so support can find the matching server log.
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="OHLCV məlumatı əldə edilə bilmir", context=f"skhy.ohlcv {symbol} {timeframe}",
        )
        return {"symbol": symbol, "timeframe": timeframe, "data": [], "error": msg, "correlation_id": corr}

@router.get("/snapshot")
async def get_snapshot(timeframe: str = Query(default="1h", pattern=TF_PATTERN), symbol: str = "SKHYUSDT"):
    try:
        return await _build_snapshot_payload(timeframe, symbol)
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message=f"{normalize_symbol(symbol)} məlumatı əldə edilə bilmir", context=f"skhy.snapshot {symbol} {timeframe}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr, "status": "unavailable"}
        )

@router.get("/analysis")
async def get_analysis(timeframe: str = Query(default=None, pattern=TF_PATTERN), symbol: str = "SKHYUSDT"):
    try:
        symbol = await _allowed_symbol(symbol)
        result = await skhy_analysis.get_full_analysis(timeframe, symbol)
        if "error" in result:
            return JSONResponse(status_code=503, content=result)
        return result
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="Analiz xətası", context=f"skhy.analysis {symbol} {timeframe}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr, "status": "unavailable"}
        )

@router.get("/scenarios")
async def get_scenarios(timeframe: str = Query(default=None, pattern=TF_PATTERN), symbol: str = "SKHYUSDT"):
    try:
        symbol = await _allowed_symbol(symbol)
        return await skhy_analysis.get_scenarios(timeframe, symbol)
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="Ssenari xətası", context=f"skhy.scenarios {symbol} {timeframe}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr, "status": "unavailable"}
        )

@router.get("/history")
async def get_history(timeframe: str = Query(default="1h", pattern=TF_PATTERN), limit: int = Query(30, ge=1, le=100), symbol: str = "SKHYUSDT"):
    try:
        symbol = await _allowed_symbol(symbol)
        history = await skhy_history.get_history(limit)
        history = [item for item in history if normalize_symbol((item.get("signal") or {}).get("symbol")) == symbol]
        performance = await skhy_history.get_performance(symbol)
        return {
            "signals": history,
            "performance": performance,
            "symbol": symbol,
            "timeframe": timeframe,
        }
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="Tarixçə xətası", context=f"skhy.history {symbol} {timeframe}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr, "status": "unavailable"}
        )

@router.get("/backtest")
async def run_backtest(
    timeframe: str = Query("1h", pattern=TF_PATTERN),
    mode: str = Query("balanced", pattern="^(strict|balanced|exploratory)$"),
    limit: int = Query(500, ge=100, le=2000),
    symbol: str = "SKHYUSDT",
):
    try:
        symbol = await _allowed_symbol(symbol)
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, limit, skip_cache=True, symbol=symbol)
        if len(ohlcv) < 100:
            return JSONResponse(
                status_code=503,
                content={"error": f"Backtest üçün kifayət qədər məlumat yoxdur ({len(ohlcv)}/{limit})"}
            )
        results = _run_backtest_internal(ohlcv, timeframe, mode)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "mode": mode,
            "candles_analyzed": len(ohlcv),
            "results": results,
        }
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="Backtest xətası", context=f"skhy.backtest {symbol} {timeframe} {mode}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr}
        )

@router.get("/diagnostics")
async def get_diagnostics(timeframe: str = Query(default="1h", pattern=TF_PATTERN), symbol: str = "SKHYUSDT"):
    try:
        symbol = await _allowed_symbol(symbol)
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, 200, skip_cache=True, symbol=symbol)
        snapshot = await skhy_market_data.get_snapshot(symbol)
        ticker = snapshot.get("ticker", {})
        funding = snapshot.get("funding", {})
        oi = snapshot.get("open_interest", {})
        ls = snapshot.get("long_short_ratio", {})

        candle_count = len(ohlcv)
        min_required = 30
        has_sufficient = candle_count >= min_required

        return {
            "symbol": symbol,
            "exchange": "Binance Futures",
            "market": "USDT Perpetual",
            "timeframe": timeframe,
            "diagnostics": {
                "candles_requested": 200,
                "candles_loaded": candle_count,
                "candles_min_required": min_required,
                "candles_sufficient": has_sufficient,
                "candles_reason": f"Loaded {candle_count} candles, need {min_required}" if not has_sufficient else None,
                "last_candle_time": ohlcv[-1]["time"] if ohlcv else None,
                "last_candle_close": ohlcv[-1]["close"] if ohlcv else None,
            },
            "market_data": {
                "last_price": ticker.get("price"),
                "mark_price": ticker.get("mark_price"),
                "funding_rate": funding.get("funding_rate"),
                "open_interest": oi.get("open_interest"),
                "open_interest_value": oi.get("open_interest_value"),
                "volume_24h": ticker.get("volume_24h"),
                "change_24h": ticker.get("change_percent"),
                "high_24h": ticker.get("high_24h"),
                "low_24h": ticker.get("low_24h"),
                "long_short_ratio": ls.get("long_short_ratio"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "data_freshness": snapshot.get("data_freshness", "unknown"),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        from app.core.error_helpers import safe_error_response
        msg, corr = safe_error_response(
            e, user_message="Diagnostics xətası", context=f"skhy.diagnostics {symbol} {timeframe}",
        )
        return JSONResponse(
            status_code=503,
            content={"error": msg, "correlation_id": corr, "status": "unavailable"}
        )

def _run_backtest_internal(ohlcv: list, timeframe: str, mode: str) -> dict:
    from app.services.skhy_indicators import skhy_indicators
    from app.services.skhy_structure import skhy_structure

    commission = 0.0004
    slippage = 0.0005
    initial_balance = 10000
    balance = initial_balance
    trades = []
    in_position = False
    position_direction = None
    entry_price = 0
    position_size = 0

    threshold_map = {"strict": 75, "balanced": 60, "exploratory": 45}
    min_signal = threshold_map.get(mode, 60)

    for i in range(100, len(ohlcv)):
        window = ohlcv[:i + 1]
        indicators = skhy_indicators.analyze(window)
        structure = skhy_structure.analyze(window)
        interp = indicators.get("interpretation", {})
        overall = interp.get("overall", "neutral")
        ms = structure.get("market_structure", {})
        ms_trend = ms.get("trend", "undefined")

        signal = None
        if overall == "bullish" and ms_trend == "bullish":
            signal = "long"
        elif overall == "bearish" and ms_trend == "bearish":
            signal = "short"

        current_price = ohlcv[i]["close"]

        if not in_position and signal:
            confidence = 70
            if confidence >= min_signal:
                entry_price = current_price * (1 + slippage)
                position_size = balance * 0.02 / entry_price
                in_position = True
                position_direction = signal
                trades.append({
                    "entry_time": ohlcv[i]["time"],
                    "entry_index": i,
                    "direction": signal,
                    "entry_price": entry_price,
                })

        elif in_position:
            exit_reason = None
            exit_price = None
            bars_held = i - trades[-1]["entry_index"] if trades else 0

            if position_direction == "long":
                tp = entry_price * 1.03
                sl = entry_price * 0.98
                if current_price >= tp:
                    exit_price = tp * (1 - slippage)
                    exit_reason = "tp"
                elif current_price <= sl:
                    exit_price = sl * (1 - slippage)
                    exit_reason = "sl"
                elif bars_held >= 48:
                    exit_price = current_price * (1 - slippage)
                    exit_reason = "timeout"
            elif position_direction == "short":
                tp = entry_price * 0.97
                sl = entry_price * 1.02
                if current_price <= tp:
                    exit_price = tp * (1 + slippage)
                    exit_reason = "tp"
                elif current_price >= sl:
                    exit_price = sl * (1 + slippage)
                    exit_reason = "sl"
                elif bars_held >= 48:
                    exit_price = current_price * (1 + slippage)
                    exit_reason = "timeout"

            if exit_price:
                if position_direction == "long":
                    pnl = (exit_price - entry_price) / entry_price * position_size * (1 - commission)
                else:
                    pnl = (entry_price - exit_price) / entry_price * position_size * (1 - commission)
                balance += pnl
                trades[-1].update({
                    "exit_time": ohlcv[i]["time"],
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl": round(pnl, 2),
                    "balance": round(balance, 2),
                    "rr": round(abs(exit_price - entry_price) / (entry_price * 0.02), 2) if entry_price else 0,
                })
                in_position = False

    total_pnl = balance - initial_balance
    closed_trades = [t for t in trades if "pnl" in t]
    wins = sum(1 for t in closed_trades if t["pnl"] > 0)
    losses = sum(1 for t in closed_trades if t["pnl"] <= 0)
    total_trades = len(closed_trades)
    gross_profit = sum(t["pnl"] for t in closed_trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in closed_trades if t["pnl"] < 0))

    return {
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_pnl": round(total_pnl, 2),
        "return_pct": round(total_pnl / initial_balance * 100, 2),
        "total_trades": total_trades,
        "win_rate": round(wins / total_trades * 100, 1) if total_trades > 0 else 0,
        "wins": wins,
        "losses": losses,
        "avg_win": round(gross_profit / wins, 2) if wins > 0 else 0,
        "avg_loss": round(gross_loss / losses, 2) if losses > 0 else 0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "open_positions": 1 if in_position else 0,
        "trades": trades[-50:],
        "commission_model": f"{commission*100}% per trade",
        "slippage_model": f"{slippage*100}% per entry/exit",
    }

@router.websocket("/stream")
async def skhy_websocket(websocket: WebSocket, timeframe: str = "1h", symbol: str = "SKHYUSDT"):
    await websocket.accept()
    symbol = await _allowed_symbol(symbol)
    client_id = f"skhy_ws_{id(websocket)}"
    logger.info(f"SKHY WS connected: {client_id} (timeframe={timeframe})")

    async def stream_data():
        last_analysis_sent = 0.0
        while True:
            try:
                snapshot = await _build_snapshot_payload(timeframe, symbol)
                payload = {"snapshot": snapshot}
                now = time.monotonic()
                if now - last_analysis_sent >= 15:
                    analysis = await skhy_analysis.get_full_analysis(timeframe, symbol)
                    payload["analysis"] = analysis
                    payload["scenarios"] = {
                        "main_scenario": analysis.get("scenario_paths", {}).get("main_scenario", {}),
                        "alternative_scenario": analysis.get("scenario_paths", {}).get("alternative_scenario", {}),
                        "risk_fakeout_scenario": analysis.get("scenario_paths", {}).get("fakeout_scenario", {}),
                        "target_hierarchy": analysis.get("target_hierarchy", {}),
                        "time_estimates": analysis.get("time_estimates", {}),
                        "activation_conditions": analysis.get("activation_conditions", {}),
                        "confidence_breakdown": analysis.get("confidence_breakdown", {}),
                    }
                    last_analysis_sent = now

                await websocket.send_json({
                    "event": "skhy_update",
                    "data": payload,
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"SKHY stream error: {e}")
                await asyncio.sleep(5)

    stream_task = asyncio.create_task(stream_data())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"event": "pong", "data": {"t": msg.get("data", {}).get("t")}})
    except WebSocketDisconnect:
        logger.info(f"SKHY WS disconnected: {client_id}")
    except Exception as e:
        logger.error(f"SKHY WS error: {e}")
    finally:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import JSONResponse
import asyncio
import json
from datetime import datetime, timezone
from app.core.websocket_manager import ws_manager, Channel
from app.core.security import get_current_user
from app.services.skhy_market_data import skhy_market_data
from app.services.skhy_analysis_engine import skhy_analysis
from app.services.skhy_signal_history import skhy_history
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/skhy", tags=["skhy"])

TF_REGEX = "^(1m|5m|15m|30m|1h|4h|1d)$"

@router.get("/ohlcv")
async def get_ohlcv(timeframe: str = "1h", limit: int = 200):
    try:
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, limit)
        if not ohlcv:
            return {"symbol": "SKHYUSDT", "timeframe": timeframe, "data": [], "error": f"SKHYUSDT OHLCV məlumatı yoxdur ({timeframe})"}
        return {"symbol": "SKHYUSDT", "timeframe": timeframe, "data": ohlcv}
    except Exception as e:
        return {"symbol": "SKHYUSDT", "timeframe": timeframe, "data": [], "error": str(e)}

@router.get("/snapshot")
async def get_snapshot(timeframe: str = Query(default="1h", regex=TF_REGEX)):
    try:
        snapshot = await skhy_market_data.get_snapshot()
        ticker = snapshot.get("ticker", {})
        funding = snapshot.get("funding", {})
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, 5, skip_cache=True)
        if not ticker:
            return JSONResponse(
                status_code=503,
                content={"error": "SKHYUSDT məlumatı əldə edilə bilmir", "status": "unavailable", "reason": "Binance Futures API cavab vermir"}
            )
        oi = snapshot.get("open_interest", {})
        ls = snapshot.get("long_short_ratio", {})
        taker = snapshot.get("taker_buy_sell_ratio", {})
        ob = snapshot.get("orderbook", {})

        current_candle = ohlcv[-1] if ohlcv else None

        return {
            "symbol": "SKHYUSDT",
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
            "latest_update": datetime.now(timezone.utc).isoformat(),
            "provider_status": "connected",
            "data_freshness": snapshot.get("data_freshness", "live"),
        }
    except Exception as e:
        logger.error(f"SKHY snapshot error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"SKHYUSDT məlumatı əldə edilə bilmir: {str(e)}", "status": "unavailable"}
        )

@router.get("/analysis")
async def get_analysis(timeframe: str = Query(default=None, regex=TF_REGEX)):
    try:
        result = await skhy_analysis.get_full_analysis(timeframe)
        if "error" in result:
            return JSONResponse(status_code=503, content=result)
        return result
    except Exception as e:
        logger.error(f"SKHY analysis error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Analiz xətası: {str(e)}", "status": "unavailable"}
        )

@router.get("/scenarios")
async def get_scenarios(timeframe: str = Query(default=None, regex=TF_REGEX)):
    try:
        return await skhy_analysis.get_scenarios(timeframe)
    except Exception as e:
        logger.error(f"SKHY scenarios error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Ssenari xətası: {str(e)}", "status": "unavailable"}
        )

@router.get("/history")
async def get_history(timeframe: str = Query(default="1h", regex=TF_REGEX), limit: int = Query(30, ge=1, le=100)):
    try:
        history = await skhy_history.get_history(limit)
        performance = await skhy_history.get_performance()
        return {
            "signals": history,
            "performance": performance,
            "symbol": "SKHYUSDT",
            "timeframe": timeframe,
        }
    except Exception as e:
        logger.error(f"SKHY history error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Tarixçə xətası: {str(e)}", "status": "unavailable"}
        )

@router.get("/backtest")
async def run_backtest(
    timeframe: str = Query("1h", regex=TF_REGEX),
    mode: str = Query("balanced", regex="^(strict|balanced|exploratory)$"),
    limit: int = Query(500, ge=100, le=2000),
):
    try:
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, limit, skip_cache=True)
        if len(ohlcv) < 100:
            return JSONResponse(
                status_code=503,
                content={"error": f"Backtest üçün kifayət qədər məlumat yoxdur ({len(ohlcv)}/{limit})"}
            )
        results = _run_backtest_internal(ohlcv, timeframe, mode)
        return {
            "symbol": "SKHYUSDT",
            "timeframe": timeframe,
            "mode": mode,
            "candles_analyzed": len(ohlcv),
            "results": results,
        }
    except Exception as e:
        logger.error(f"SKHY backtest error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Backtest xətası: {str(e)}"}
        )

@router.get("/diagnostics")
async def get_diagnostics(timeframe: str = Query(default="1h", regex=TF_REGEX)):
    try:
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, 200, skip_cache=True)
        snapshot = await skhy_market_data.get_snapshot()
        ticker = snapshot.get("ticker", {})
        funding = snapshot.get("funding", {})
        oi = snapshot.get("open_interest", {})
        ls = snapshot.get("long_short_ratio", {})

        candle_count = len(ohlcv)
        min_required = 30
        has_sufficient = candle_count >= min_required

        return {
            "symbol": "SKHYUSDT",
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"SKHY diagnostics error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Diagnostics xətası: {str(e)}", "status": "unavailable"}
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
                    "direction": signal,
                    "entry_price": entry_price,
                })

        elif in_position:
            exit_reason = None
            exit_price = None
            bars_held = i - (trades[-1]["entry_index"] if trades and "entry_index" in trades[-1] else 0) if trades else 0
            if not trades[-1].get("entry_index"):
                trades[-1]["entry_index"] = i

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
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0) if trades else 0
    losses = sum(1 for t in trades if t.get("pnl", 0) <= 0) if trades else 0
    total_trades = len(trades)

    return {
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_pnl": round(total_pnl, 2),
        "return_pct": round(total_pnl / initial_balance * 100, 2),
        "total_trades": total_trades,
        "win_rate": round(wins / total_trades * 100, 1) if total_trades > 0 else 0,
        "wins": wins,
        "losses": losses,
        "avg_win": round(sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0) / wins, 2) if wins > 0 else 0,
        "avg_loss": round(abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0)) / losses, 2) if losses > 0 else 0,
        "profit_factor": round(sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0) / abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0)), 2) if any(t.get("pnl", 0) < 0 for t in trades) else float("inf"),
        "trades": trades[-50:],
        "commission_model": f"{commission*100}% per trade",
        "slippage_model": f"{slippage*100}% per entry/exit",
    }

@router.websocket("/stream")
async def skhy_websocket(websocket: WebSocket, timeframe: str = "1h"):
    await websocket.accept()
    client_id = f"skhy_ws_{id(websocket)}"
    logger.info(f"SKHY WS connected: {client_id} (timeframe={timeframe})")

    async def stream_data():
        while True:
            try:
                snapshot = await skhy_market_data.get_snapshot()
                analysis = await skhy_analysis.get_full_analysis(timeframe)
                scenarios = await skhy_analysis.get_scenarios(timeframe)

                await websocket.send_json({
                    "event": "skhy_update",
                    "data": {
                        "snapshot": snapshot,
                        "analysis": analysis,
                        "scenarios": scenarios,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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

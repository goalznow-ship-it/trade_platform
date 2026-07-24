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
async def get_snapshot():
    try:
        snapshot = await skhy_market_data.get_snapshot()
        ticker = snapshot.get("ticker", {})
        funding = snapshot.get("funding", {})
        if not ticker:
            return JSONResponse(
                status_code=503,
                content={"error": "SKHYUSDT məlumatı əldə edilə bilmir", "status": "unavailable", "reason": "Binance Futures API cavab vermir"}
            )
        oi = snapshot.get("open_interest", {})
        ls = snapshot.get("long_short_ratio", {})
        taker = snapshot.get("taker_buy_sell_ratio", {})
        ob = snapshot.get("orderbook", {})

        return {
            "symbol": "SKHYUSDT",
            "exchange": "Binance Futures",
            "market": "USDT Perpetual",
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
async def get_analysis():
    try:
        result = await skhy_analysis.get_full_analysis()
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
async def get_scenarios():
    try:
        return await skhy_analysis.get_scenarios()
    except Exception as e:
        logger.error(f"SKHY scenarios error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Ssenari xətası: {str(e)}", "status": "unavailable"}
        )

@router.get("/history")
async def get_history(limit: int = Query(30, ge=1, le=100)):
    try:
        history = await skhy_history.get_history(limit)
        performance = await skhy_history.get_performance()
        return {
            "signals": history,
            "performance": performance,
            "symbol": "SKHYUSDT",
        }
    except Exception as e:
        logger.error(f"SKHY history error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Tarixçə xətası: {str(e)}", "status": "unavailable"}
        )

@router.get("/backtest")
async def run_backtest(
    timeframe: str = Query("1h", regex="^(5m|15m|1h|4h)$"),
    mode: str = Query("balanced", regex="^(strict|balanced|exploratory)$"),
    limit: int = Query(500, ge=100, le=2000),
):
    try:
        ohlcv = await skhy_market_data.get_ohlcv(timeframe, limit)
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
            confidence = 70 if overall == "bullish" else 70
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
            bars_held = i - len(trades[-1]) if trades else 0

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
                pnl = (exit_price - entry_price) / entry_price * position_size * (1 - commission) if position_direction == "long" else (entry_price - exit_price) / entry_price * position_size * (1 - commission)
                balance += pnl
                trades[-1].update({
                    "exit_time": ohlcv[i]["time"],
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl": round(pnl, 2),
                    "balance": round(balance, 2),
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
async def skhy_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = f"skhy_ws_{id(websocket)}"
    logger.info(f"SKHY WS connected: {client_id}")

    async def stream_data():
        while True:
            try:
                snapshot = await skhy_market_data.get_snapshot()
                analysis = await skhy_analysis.get_full_analysis()
                scenarios = await skhy_analysis.get_scenarios()

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

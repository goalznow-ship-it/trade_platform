"""
Institutional API Routes

High-quality signal generation, market coverage,
multi-timeframe analysis, and risk engine.
"""
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.services.market_coverage import market_coverage
from app.services.institutional_signals import institutional_signal_engine
from app.services.multi_timeframe import multi_timeframe
from app.services.smc_engine import smc_engine
from app.services.professional_risk import professional_risk
from app.services.institutional_scoring import institutional_scorer
from app.services.market import market_service
from app.services.pattern_analysis import pattern_engine, _convert_numpy
from app.services.canonical_signal import canonical_signal

router = APIRouter(prefix="/api/v1/institutional", tags=["institutional"])


@router.get("/signal/{symbol}")
async def get_institutional_signal(
    symbol: str,
    timeframe: str = Query("1h", pattern="^(1w|1d|4h|1h|15m|5m)$"),
    capital: float = Query(10000, ge=100),
    risk_percent: float = Query(0.02, ge=0.001, le=0.1),
    user: dict = Depends(get_current_user),
):
    """Generate an institutional-grade signal with full analysis"""
    signal = await institutional_signal_engine.generate_signal(
        symbol=symbol.replace("-", "/"),
        timeframe=timeframe,
        capital=capital,
        risk_percent=risk_percent,
    )
    return signal


@router.get("/scan")
async def scan_institutional(
    min_score: float = Query(70, ge=0, le=100),
    limit: int = Query(10, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """Scan top symbols for institutional-grade signals"""
    results = await institutional_signal_engine.scan_all(
        min_score=min_score,
        limit=limit,
    )
    return {"signals": results, "count": len(results), "min_score": min_score}


@router.get("/multi-timeframe/{symbol}")
async def get_multi_timeframe(
    symbol: str,
    user: dict = Depends(get_current_user),
):
    """Multi-timeframe analysis for a symbol"""
    result = await multi_timeframe.analyze(symbol.replace("-", "/"))
    return result


@router.get("/smc/{symbol}")
async def get_smc_analysis(
    symbol: str,
    timeframe: str = Query("1h", pattern="^(1w|1d|4h|1h|15m|5m)$"),
    user: dict = Depends(get_current_user),
):
    """Complete SMC/ICT analysis for a symbol"""
    from app.services.market import market_service
    data = await market_service.get_ohlcv(symbol.replace("-", "/"), "binance", timeframe, 200)
    if not data or len(data) < 30:
        return {"error": "Insufficient data", "symbol": symbol}
    result = smc_engine.analyze(data)
    result["symbol"] = symbol
    result["timeframe"] = timeframe
    return result


@router.get("/score/{symbol}")
async def get_institutional_score(
    symbol: str,
    timeframe: str = Query("1h", pattern="^(1w|1d|4h|1h|15m|5m)$"),
    user: dict = Depends(get_current_user),
):
    """Institutional 100-point scoring for a symbol"""
    from app.services.market import market_service
    sym = symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, "binance", timeframe, 200)
    if not data or len(data) < 50:
        return {"error": "Insufficient data", "symbol": sym}
    score = await institutional_scorer.score(sym, data, timeframe)
    return score


@router.get("/risk/position-size")
async def calculate_position_size(
    entry_price: float = Query(..., gt=0),
    stop_loss: float = Query(..., gt=0),
    capital: float = Query(10000, ge=100),
    risk_percent: float = Query(0.02, ge=0.001, le=0.1),
    leverage: int = Query(None, ge=1, le=125),
    user: dict = Depends(get_current_user),
):
    """Calculate professional position sizing"""
    result = professional_risk.calculate_position_size(
        capital=capital,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_percent=risk_percent,
        leverage=leverage,
    )
    return result


@router.get("/risk/kelly")
async def calculate_kelly(
    win_rate: float = Query(..., ge=0, le=1),
    avg_win: float = Query(..., gt=0),
    avg_loss: float = Query(..., gt=0),
    user: dict = Depends(get_current_user),
):
    """Calculate Kelly Criterion for position sizing"""
    result = professional_risk.calculate_kelly_fraction(
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )
    return result


@router.get("/risk/validate")
async def validate_trade(
    symbol: str = Query(...),
    direction: str = Query(..., pattern="^(long|short)$"),
    entry_price: float = Query(..., gt=0),
    stop_loss: float = Query(..., gt=0),
    take_profit: float = Query(..., gt=0),
    leverage: int = Query(1, ge=1, le=125),
    balance: float = Query(10000, ge=0),
    user: dict = Depends(get_current_user),
):
    """Validate a trade before execution"""
    from app.services.market import market_service
    sym = symbol.replace("-", "/")
    data = await market_service.get_ohlcv(sym, "binance", "1h", 50)
    result = professional_risk.validate_trade(
        symbol=sym,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        leverage=leverage,
        balance=balance,
        data=data,
    )
    return result


# === Market Coverage Routes ===

@router.get("/market/top")
async def get_top_markets(
    count: int = Query(30, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """Get top symbols by Binance volume ranking"""
    symbols = await market_coverage.get_top_symbols(count=count)
    tickers = []
    for s in symbols[:count]:
        try:
            t = await market_service.get_ticker(s)
            if t and t.get("price"):
                tickers.append(t)
        except Exception:
            continue
    return {"symbols": symbols, "tickers": tickers, "count": len(symbols)}


@router.get("/market/gainers")
async def get_market_gainers(
    count: int = Query(10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Top gainers in the last 24h"""
    gainers = await market_coverage.get_market_gainers(count=count)
    return {"gainers": gainers, "count": len(gainers)}


@router.get("/market/losers")
async def get_market_losers(
    count: int = Query(10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Top losers in the last 24h"""
    losers = await market_coverage.get_market_losers(count=count)
    return {"losers": losers, "count": len(losers)}


@router.get("/market/volume-leaders")
async def get_volume_leaders(
    count: int = Query(10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Top by 24h volume"""
    leaders = await market_coverage.get_volume_leaders(count=count)
    return {"leaders": leaders, "count": len(leaders)}


@router.get("/market/funding")
async def get_funding_rates(
    count: int = Query(20, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """Funding rates across top symbols"""
    rates = await market_coverage.get_funding_rates(count=count)
    return {"funding_rates": rates, "count": len(rates)}


@router.get("/market/open-interest")
async def get_open_interest(
    count: int = Query(20, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """Open interest across top symbols"""
    oi = await market_coverage.get_open_interest_data(count=count)
    return {"open_interest": oi, "count": len(oi)}


@router.get("/market/trending")
async def get_trending_coins(
    count: int = Query(10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Trending coins (volume + gainers composite)"""
    trending = await market_coverage.get_trending_coins(count=count)
    return {"trending": trending, "count": len(trending)}


@router.get("/market/matrix")
async def get_market_matrix(
    count: int = Query(30, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """30-asset Market Matrix with full canonical signals for each symbol"""
    from app.core.cache import cache_get, cache_set
    cache_key = "institutional:market:matrix"
    cached = await cache_get(cache_key)
    if isinstance(cached, dict) and len(cached.get("symbols", [])) == count:
        return cached

    symbols = await market_coverage.get_top_symbols(count=30)
    import asyncio

    async def analyze_one(symbol: str) -> dict:
        try:
            exchange = market_coverage.get_symbol_exchange(symbol)
            ohlcv = await market_service.get_ohlcv(symbol, exchange, "1h", 200) or []
            signal, mtf, pattern = await asyncio.gather(
                institutional_signal_engine.generate_signal(symbol, "1h"),
                multi_timeframe.analyze(symbol),
                pattern_engine.comprehensive_analysis(symbol, "1h", ohlcv) if ohlcv else asyncio.sleep(0),
                return_exceptions=True,
            )
            if isinstance(pattern, Exception):
                pattern = None
            if isinstance(mtf, Exception):
                mtf = None
            if isinstance(signal, Exception):
                signal = None
            canonical = canonical_signal.build(
                symbol=symbol,
                exchange=exchange,
                signal_data=signal if isinstance(signal, dict) else None,
                pattern_data=pattern if isinstance(pattern, dict) else None,
                mtf_data=mtf if isinstance(mtf, dict) else None,
            )
            return canonical
        except Exception:
            return {
                "symbol": symbol,
                "exchange": market_coverage.get_symbol_exchange(symbol),
                "error": "analysis_failed",
                "status": "reject",
                "direction": "neutral",
                "confidence": 0,
            }

    semaphore = asyncio.Semaphore(5)
    async def limited(sym: str):
        async with semaphore:
            return await analyze_one(sym)

    results = await asyncio.gather(*(limited(s) for s in symbols))
    response = {"symbols": results, "count": len(results)}
    await cache_set(cache_key, response, ttl=30)
    return response


@router.get("/ai-analysis/{symbol}")
async def get_ai_analysis(
    symbol: str,
    timeframe: str = Query("1h", pattern="^(1w|1d|4h|1h|15m|5m)$"),
    user: dict = Depends(get_current_user),
):
    """Comprehensive AI analysis: patterns, trends, Elliott Wave, Fibonacci, liquidity zones"""
    sym = symbol.replace("-", "/")
    ohlcv = await market_service.get_ohlcv(sym, "binance", timeframe, 200)
    if not ohlcv or len(ohlcv) < 30:
        return {"error": "Insufficient data", "symbol": sym}

    smc_result = smc_engine.analyze(ohlcv)
    result = await pattern_engine.comprehensive_analysis(sym, timeframe, ohlcv, smc_result)

    module_errors = result.pop("module_errors", None)

    try:
        score_result = await institutional_scorer.score(sym, ohlcv, timeframe, smc_result)
    except Exception as e:
        score_result = {"abs_score": 0, "direction": "neutral", "classification": "error",
                        "scores": {}, "weights": {}, "risk_level": "unknown"}
        module_errors = module_errors or {}
        module_errors["institutional_score"] = f"{type(e).__name__}: {e}"

    result["institutional_score"] = score_result
    result["smc"] = {
        "trend": smc_result.get("trend", "unknown"),
        "bos_count": smc_result.get("bos_count", 0),
        "choch_count": smc_result.get("choch_count", 0),
        "net_bos": smc_result.get("net_bos", 0),
        "liquidity_sweep": smc_result.get("liquidity_sweep"),
        "premium_discount": smc_result.get("premium_discount", {}),
    }

    combined_dir = result.get("direction", "neutral")
    score_dir = score_result.get("direction", "neutral") if isinstance(score_result, dict) else "neutral"
    if combined_dir == score_dir:
        confidence_boost = 15
    elif combined_dir != score_dir and combined_dir != "neutral":
        confidence_boost = -10
    else:
        confidence_boost = 0

    result["combined_direction"] = combined_dir if combined_dir != "neutral" else score_dir
    abs_score = score_result.get("abs_score", 50) if isinstance(score_result, dict) else 50
    result["confidence"] = min(100, max(0, abs(abs_score) + confidence_boost))
    result["confidence"] = int(result["confidence"])

    if module_errors:
        result["module_errors"] = module_errors

    return _convert_numpy(result)

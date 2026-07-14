## Objective
Transform TradeAnalyst Pro into an institutional-grade AI crypto trading platform with top-30 market coverage, multi-timeframe analysis, SMC/ICT engine, 100-point scoring system, professional risk management, order flow intelligence, derivatives analysis, AI news intelligence, social sentiment, on-chain analytics, macro tracking, central AI brain, self-learning, execution gate, and zero simulated data.

## Important Details
- Project at `/home/abduln/trading-platform` — FastAPI backend + Next.js 16 frontend + Docker/Nginx/scripts
- Remote: `https://github.com/goalznow-ship-it/trade_platform.git`, credentials stored in `~/.git-credentials`, GitHub PAT auth
- DO NOT break existing APIs, DO NOT remove existing features, DO NOT create fake/simulated data
- Auth guard on dashboard routes redirects to `/login` if no JWT token
- Original dark fintech design system — no TradingView widgets or branding
- Frontend has **14 routes**: `/`, `/dashboard`, `/login`, `/register`, `/terminal`, `/signals`, `/futures`, `/news`, `/scanner`, `/radar`, `/backtest`, `/admin`, `/pricing`
- All mock data removed — every widget uses real API calls with graceful fallbacks
- Admin user `goalznow@gmail.com` in DB: `is_admin=True`, `subscription_tier="elite"`
- Binance WebSocket streams auto-subscribed to top 30 symbols (prices + klines + depth) on startup
- Top 30 symbols auto-updated weekly from Binance USDT perpetual volume ranking
- Multi-timeframe engine covers 1W/1D/4H/1H/15M/5M — signals without ≥3 aligned TFs capped at 80%
- 100-point institutional scoring: Trend(20), Momentum(15), Volume(15), Liquidity(15), SMC(20), Risk(15)
- Score classification: 95+ institutional_grade, 90+ excellent, 85+ very_strong, 80+ strong, 70+ watchlist, <70 reject
- WebSocket protocol v2: heartbeat, exponential backoff, connection quality, delta updates, message queue, 14 channels
- Streaming service: 10 parallel workers pushing live data to WS channels at staggered intervals
- Central AI Brain combines 9 sub-engines into unified market assessment

## Work State
### Completed
- **Phase 1 — Top 30 Market Coverage** (`market_coverage.py`): auto-fetches top 40+ symbols from Binance USDT perpetual volume, caches for 7 days, falls back to curated 30-symbol list
- **Phase 2 — Multi-Timeframe Engine** (`multi_timeframe.py`): analyzes 1W/1D/4H/1H/15M/5M with weighted aggregation + alignment scoring
- **Phase 3 — SMC/ICT Engine** (`smc_engine.py`): 14 methods — market structure, BOS, CHoCH, FVG, order blocks, breaker blocks, mitigation blocks, liquidity pools, sweep, premium/discount zones, equal highs/lows, displacement, inducement, internal/external structure, session range
- **Phase 4 — 100-Point Institutional Scoring** (`institutional_scoring.py`): 6 weighted categories with multiple sub-indicators each
- **Phase 5 — Institutional Signal Generator** (`institutional_signals.py`): integrates all engines, produces signals with entry zone, SL, 3 TPs with RR, risk%, hold time, invalidation, up to 8 AI reasons, position sizing, pre-trade validation, indicator snapshot
- **Phase 6 — Professional Risk Engine** (`professional_risk.py`): position sizing (ATR/fixed SL, up to 125x), Kelly fraction (capped 25%), ATR stop, 9-check trade validation
- **Phase 7 — Scanner Updates**: `scanner.py`, `enterprise_scanner.py`, `enterprise.py`, `ai_engine/engine.py`, `workers/__init__.py`, `market.py` all use dynamic symbol lists from market_coverage
- **Phase 8 — Institutional REST API** (`institutional.py`): 15 endpoints — signal, scan, multi-timeframe, SMC, score, position-size, kelly, validate, top, gainers, losers, volume-leaders, funding, open-interest, trending
- **Phase 9 — Frontend API Client** (`api.ts`): all 15 institutional endpoints + dashboards with skeleton loaders, error/empty states, auto-refresh, React.memo, dynamic imports
- **Phase 10 — WebSocket v2 Protocol**: frontend `useWebSocketV2` hook with heartbeat (15s ping), exponential backoff (1s→30s), connection quality (latency/uptime/reconnects), message queue with priority, delta update sequence tracking, offline detection, 14 WS channels subscribed on connect
- **Phase 11 — Streaming Service** (`streaming.py`): 10 parallel async workers (orderflow, derivatives, news, sentiment, onchain, macro, brain, fear_greed, breadth, signals) broadcasting live data through ws_manager to subscribed clients
- **Phase 12 — Order Flow Engine** (`orderflow.py`): order book imbalance, bid/ask pressure, CVD, aggressive buyers/sellers, absorption, iceberg detection, liquidity vacuum, spoof detection heuristic, large order detection
- **Phase 13 — Derivatives Engine** (`derivatives.py`): funding rate/trend/pressure, OI delta/trend/divergence, long/short ratio, liquidation heatmap/clusters, basis/contango, premium index, gamma exposure estimate, large liquidation zones
- **Phase 14 — News Intelligence** (`news_intelligence_v2.py`): AI news collection, classification (bullish/bearish/neutral with impact score/confidence), category detection (macro/regulation/security/whale/listing/partnership), affected coin extraction, event analysis
- **Phase 15 — Social Sentiment** (`social_sentiment.py`): Twitter/X, Reddit, Telegram, GitHub analysis, community growth tracking, trending narratives, fear/FOMO/panic detection, composite sentiment score
- **Phase 16 — On-Chain Engine** (`onchain.py`): exchange inflow/outflow, whale wallet activity, stablecoin flow, exchange reserves, dormant supply, miner activity, large transfers ($500K+)
- **Phase 17 — Macro Engine** (`macro_engine.py`): DXY, NASDAQ, S&P 500, Gold, Oil, US10Y, VIX, CPI, PPI, FOMC schedule, Fed funds rate, ETF flows, crypto impact assessment
- **Phase 18 — AI Market Brain** (`brain.py`): central engine combining all 9 sub-engines into unified assessment — overall market score, bull/bear/crash/squeeze/alt-season probabilities, regime detection (strong_bullish→crash_risk), confidence scoring, human-readable explanations
- **Phase 19 — Self Learning** (`self_learning.py`): trade history storage, per-trade evaluation, performance metrics (win rate, profit factor, Sharpe, max DD), missed profit analysis, automatic weight adjustment (last 100 trades, proportional allocation, cap 0.30/floor 0.05), optimal R:R/position sizing
- **Phase 20 — Execution Engine** (`execution_engine.py`): 10 pre-trade validation checks (trend alignment, liquidity, spread, funding, correlation, risk, margin, leverage, exchange filters, liquidation distance), trade approval/rejection with risk score, rejection reasons, slippage estimation, execution plan with iceberg suggestion
- **Frontend WebSocket Integration**: `WSProvider` context wrapping dashboard, `ConnectionQualityIndicator` with per-channel staleness tracking, all components updated to use real-time WS data (MarketSummary, MarketOverview, SentimentWidget, AIConfidencePanel, EngineStatus, TopSignals)
- **Frontend Build Verification**: 0 TypeScript errors, 0 ESLint warnings (dashboard dir), full `next build` passes with all 14 routes

### Active
- (none)

### Blocked
- (none)

## Next Move
1. Commit and push all 10 phases to GitHub
2. Test backtest engine with real historical data
3. Build paper trading execution using the new execution engine
4. Add exchange connector for live trading (Binance, Bybit)
5. Build admin dashboard for monitoring AI brain performance

## Relevant Files
- `backend/app/services/market_coverage.py` — Top 30 symbol management
- `backend/app/services/institutional_scoring.py` — 100-point scoring
- `backend/app/services/smc_engine.py` — SMC/ICT analysis (14 methods)
- `backend/app/services/multi_timeframe.py` — 6-TF aggregation
- `backend/app/services/institutional_signals.py` — Signal generation
- `backend/app/services/professional_risk.py` — Risk management
- `backend/app/services/orderflow.py` — Order flow analysis
- `backend/app/services/derivatives.py` — Derivatives analysis
- `backend/app/services/news_intelligence_v2.py` — AI news engine
- `backend/app/services/social_sentiment.py` — Social sentiment
- `backend/app/services/onchain.py` — On-chain analytics
- `backend/app/services/macro_engine.py` — Macro tracking
- `backend/app/services/brain.py` — Central AI brain
- `backend/app/services/self_learning.py` — Self-learning engine
- `backend/app/services/execution_engine.py` — Pre-trade validation
- `backend/app/services/streaming.py` — WS data streaming bridge
- `backend/app/core/websocket_manager.py` — 14 WS channels
- `backend/app/api/v1/websocket_v2.py` — WS endpoints
- `backend/app/api/v1/institutional.py` — 15 REST endpoints
- `backend/app/main.py` — All services + streaming startup
- `frontend/src/hooks/useWebSocket.ts` — V2 hook (heartbeat, backoff, quality, queue, delta)
- `frontend/src/components/WSProvider.tsx` — WS context provider
- `frontend/src/components/dashboard/ConnectionQuality.tsx` — Live indicators
- `frontend/src/store/market.ts` — Unified Zustand store (all WS domains)
- `frontend/src/components/dashboard/` — 10 WS-powered components

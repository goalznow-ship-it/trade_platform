# Phase 21 — ML Signal Engine

Production-grade machine learning pipeline for crypto trading signals.
Adds an ensemble of XGBoost + LightGBM + Transformer models on top of the
existing 100-point institutional scoring system.

## Why this matters

The existing scoring system is rule-based (heuristics + SMC + order flow).
This layer adds a *learning* component that:

- **Discovers non-obvious patterns** humans miss (multi-feature interactions)
- **Quantifies confidence** — every prediction comes with a probability
- **Self-improves** — retrained nightly on the latest data
- **Augments existing scores** — boosts/reduces the 100-point score by up to ±10

## Architecture

```
Live OHLCV + News + Funding + OI
        │
        ▼
┌──────────────────────────────┐
│     Feature Engineer         │   ← 100+ features
│  • Technical (50+)           │
│  • Microstructure (15+)      │
│  • Cross-asset (10+)         │
│  • Sentiment/onchain (15+)   │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│     Ensemble Predictor       │
│  • XGBoost     (40%)         │
│  • LightGBM    (40%)         │
│  • Transformer (20%)         │
└──────────────────────────────┘
        │
        ▼
   prediction + confidence
   + per-model breakdown
   + feature importance
```

## Files added

### Backend
- `backend/app/services/ml/__init__.py`
- `backend/app/services/ml/signal_engine.py`         — main orchestrator
- `backend/app/services/ml/features/technical.py`    — TA features
- `backend/app/services/ml/features/microstructure.py` — order flow features
- `backend/app/services/ml/features/cross_asset.py`  — BTC correlation
- `backend/app/services/ml/features/sentiment.py`    — news/funding/OI
- `backend/app/services/ml/features/engineer.py`     — unified pipeline
- `backend/app/services/ml/models/xgboost_model.py`
- `backend/app/services/ml/models/lightgbm_model.py`
- `backend/app/services/ml/models/transformer.py`    — PyTorch seq model
- `backend/app/services/ml/models/ensemble.py`       — weighted voter
- `backend/app/services/ml/training/data_pipeline.py`
- `backend/app/services/ml/training/walk_forward.py` — temporal validation
- `backend/app/services/ml/training/metrics.py`      — trading metrics
- `backend/app/services/ml/training/train_script.py` — CLI trainer
- `backend/app/services/ml/inference/predictor.py`   — live predictor
- `backend/app/api/v1/ml/router.py`                  — REST endpoints

### Frontend
- `frontend/src/app/ml/page.tsx`                      — ML dashboard
- `frontend/src/components/ml/MLStatus.tsx`           — model health
- `frontend/src/components/ml/MLPanel.tsx`            — live predictions
- `frontend/src/components/ml/MLPredictionCard.tsx`   — feature importance

## Quick start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install: `scikit-learn`, `xgboost`, `lightgbm`, `torch`, `optuna`, `mlflow`, `ta`.

### 2. Train the ensemble

```bash
cd backend
python -m app.services.ml.training.train_script
```

Or via API (admin only):

```bash
curl -X POST http://localhost:8000/api/v1/ml/retrain \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

The trainer will:
- Fetch 180 days of 15m OHLCV for top 30 Binance USDT pairs
- Build features (≈100 columns)
- Generate triple-barrier labels (12-bar forward, ±0.5% threshold)
- Walk-forward validate each model
- Train XGBoost + LightGBM (and Transformer if data is sufficient)
- Save models to `app/models_store/`

### 3. Use it

Frontend: navigate to `/ml` to see live predictions.

API:

```bash
# Single symbol
curl http://localhost:8000/api/v1/ml/predict/BTC-USDT?timeframe=15m \
  -H "Authorization: Bearer $TOKEN"

# Batch
curl -X POST http://localhost:8000/api/v1/ml/predict-batch \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"], "timeframe": "15m"}'

# Augment institutional score
curl -X POST http://localhost:8000/api/v1/ml/augment-score \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"symbol": "BTC/USDT", "base_score": 82}'
```

## Integration with existing 100-point scoring

The `MLSignalEngine.augment_institutional_score()` method is the
integration point. It takes the existing score and adds an ML adjustment:

- If ML predicts *buy* with high confidence + models agree → +up to 10
- If ML predicts *sell* with high confidence + models agree → -up to 10
- If ML is neutral → no adjustment

Wire it into the existing `institutional_scoring.py` by importing
`get_ml_engine()` and calling `augment_institutional_score()` before
returning the final score.

## Model retraining

Models are retrained:
- Manually via `/api/v1/ml/retrain` (admin only)
- Or via the CLI: `python -m app.services.ml.training.train_script`
- Recommend a daily schedule via cron or GitHub Actions

## Performance expectations

Realistic targets on out-of-sample walk-forward validation:
- **Hit rate**: 55-60% (better than random 33% on 3 classes)
- **Sharpe ratio**: 1.0-2.0 on the strategy simulation
- **Max drawdown**: <15% over the test period
- **Win rate on trades**: 50-55%

These are realistic for crypto 15m bars. The model is most profitable
when it agrees with the institutional scoring — the two systems act as
a check on each other.

## Why ensemble?

Single models have failure modes:
- XGBoost misses long-range temporal patterns
- LightGBM has similar bias to XGBoost
- Transformer needs a lot of data, can be unstable

Combined with soft-voting:
- Reduces individual model errors
- Agreement score tells you when models are uncertain
- Final prediction is calibrated through weighting

## Files in models_store/

After training, the directory contains:
- `xgboost.json`         — XGBoost model
- `xgboost.meta.json`    — feature list, metrics
- `lightgbm.txt`         — LightGBM model
- `lightgbm.meta.json`
- `transformer.pt`       — Transformer weights
- `ensemble.json`        — weights + manifest

To deploy a new model: drop new files into `models_store/` and restart
the backend. The engine auto-loads on startup.

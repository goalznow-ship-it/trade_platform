"""Deterministic seed control for the ML stack.

Phase 3 — ML reproducibility. Every model and the data pipeline must
seed every RNG they touch so two ``train()`` calls with the same
data and the same seed produce the same ``mlflow_run_id`` hash and
the same out-of-sample metrics.

Why this lives in one module
----------------------------
Calling ``random.seed`` in one place and ``np.random.seed`` in
another invites drift — someone adds a ``np.random.rand`` call to a
preprocessing step and forgets the seed there, breaking
reproducibility silently. The single ``set_seed(n)`` entrypoint
re-seeds Python's ``random``, NumPy, Python's ``hash`` seed
(affects dict ordering on 3.7+ which doesn't matter for us but
matters for some libs), and PyTorch when it's installed. Models
that take an explicit ``random_state`` / ``seed`` parameter use the
same ``n`` so the parameterised RNG and the global RNG agree.
"""
from __future__ import annotations

import os
import random

import numpy as np

# Default seed for every training run. The same ``42`` is set in the
# XGBoost / LightGBM ``random_state`` params, and on Transformer
# model init. Changing this constant will break the byte-identical
# reproducibility guarantee — bump it only with a regression test.
DEFAULT_SEED = 42


def set_seed(seed: int = DEFAULT_SEED) -> int:
    """Seed every RNG the ML stack touches.

    Returns the seed that was actually used so the caller can log
    it to MLflow as a run parameter. Idempotent: calling twice
    with the same value is a no-op (re-seeding is fine, but the
    caller is also able to assert determinism without surprises).
    """
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # Strict determinism — slow but reproducible.
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        # PyTorch is an optional heavy dep — the test suite runs
        # without it on CI's matrix.
        pass
    return seed

# Trade Platform Backend
#
# Multi-stage build:
#   - builder: compiles wheels with dev headers
#   - runtime: minimal image, no dev headers, runs as non-root
#   - trainer: full ML deps (torch, optuna, mlflow) for offline training only
#
# Build with INSTALL_ML_DEPS=true to include ML training stack.
# Default production image is ~600 MB; with ML deps ~1.4 GB.

ARG PYTHON_VERSION=3.13
ARG INSTALL_ML_DEPS=false

FROM python:${PYTHON_VERSION}-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install runtime deps first (cached layer)
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Install ML training deps if requested
RUN if [ "$INSTALL_ML_DEPS" = "true" ]; then \
      pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
        torch==2.5.1 \
        optuna==4.1.0 \
        mlflow==2.19.0; \
    fi

# ─── RUNTIME STAGE ────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

# libpq5 (runtime) is enough; libpq-dev (dev headers) is in builder only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 tini && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r trading && \
    useradd -r -g trading -d /app -s /sbin/nologin trading && \
    mkdir -p /app/app/models_store && \
    chown -R trading:trading /app

WORKDIR /app

COPY --from=builder /app/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-deps --no-index /tmp/wheels/* && \
    rm -rf /tmp/wheels

COPY --chown=trading:trading app/ app/
COPY --chown=trading:trading alembic/ alembic/
COPY --chown=trading:trading alembic.ini .

# Pre-create models directory owned by trading user
RUN mkdir -p /app/app/models_store && chown -R trading:trading /app/app/models_store

USER trading

EXPOSE 8000

# tini (init) ensures proper signal forwarding for graceful shutdown
ENTRYPOINT ["/usr/bin/tini", "--"]

# Healthcheck uses Python (no curl dependency, smaller image, more reliable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command runs gunicorn. CMD can be overridden in compose for
# migrator (alembic) or ml_trainer (train_script).
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", \
     "--max-requests", "1000", "--max-requests-jitter", "100", \
     "app.main:app", "--bind", "0.0.0.0:8000"]

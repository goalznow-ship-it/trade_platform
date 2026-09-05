"""Phase 5 admin: quality gate + circuit breaker + observability.

Endpoints
---------
* ``GET  /admin/quality``         — per-engine quality snapshot
* ``GET  /admin/quality/{engine}`` — single-engine detail
* ``POST /admin/quality/{engine}/re-enable`` — operator override
* ``GET  /admin/breakers``         — every circuit-breaker state
* ``POST /admin/breakers/{engine}/close`` — close a breaker
* ``GET  /admin/metrics``          — Prometheus text format

All write endpoints require an admin user.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models.quality import EnginePerformance
from app.models.user import User
from app.services import circuit_breaker
from app.services.observability import registry as metrics_registry
from app.services.quality_gate import (
    evaluate_engine,
    is_engine_disabled,
    list_active_engines,
    re_enable_engine,
)

router = APIRouter(prefix="/admin", tags=["Admin:Quality"])


class ReEnableRequest(BaseModel):
    reason: str = "operator_override"


# ── Quality gate ───────────────────────────────────────────────
@router.get("/quality")
async def get_quality_snapshot(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Latest quality row per engine. The dashboard reads
    this to render the per-engine health table.
    """
    engines = await list_active_engines(db)
    out = []
    for engine in engines:
        # Latest row per engine (ORDER BY recorded_at DESC LIMIT 1).
        stmt = (
            select(EnginePerformance)
            .where(EnginePerformance.engine == engine)
            .order_by(EnginePerformance.recorded_at.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            out.append({
                "engine": engine, "n_signals": 0, "n_resolved": 0,
                "n_wins": 0, "hit_rate": None, "status": "ok",
                "is_disabled": False, "disabled_reason": None,
                "recorded_at": None,
            })
        else:
            out.append({
                "engine": row.engine,
                "n_signals": row.n_signals,
                "n_resolved": row.n_resolved,
                "n_wins": row.n_wins,
                "hit_rate": row.hit_rate,
                "avg_forward_return": row.avg_forward_return,
                "avg_mae_bps": row.avg_mae_bps,
                "avg_mfe_bps": row.avg_mfe_bps,
                "status": row.status,
                "is_disabled": row.is_disabled,
                "disabled_reason": row.disabled_reason,
                "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
            })
    return {"engines": out}


@router.get("/quality/{engine}")
async def get_quality_for_engine(
    engine: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Full quality history for one engine. The detail view
    charts hit rate over time.
    """
    stmt = (
        select(EnginePerformance)
        .where(EnginePerformance.engine == engine)
        .order_by(EnginePerformance.recorded_at.desc())
        .limit(50)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "engine": engine,
        "history": [
            {
                "id": r.id,
                "window_start": r.window_start.isoformat() if r.window_start else None,
                "window_end": r.window_end.isoformat() if r.window_end else None,
                "n_signals": r.n_signals,
                "n_resolved": r.n_resolved,
                "n_wins": r.n_wins,
                "hit_rate": r.hit_rate,
                "avg_forward_return": r.avg_forward_return,
                "avg_mae_bps": r.avg_mae_bps,
                "avg_mfe_bps": r.avg_mfe_bps,
                "status": r.status,
                "is_disabled": r.is_disabled,
                "disabled_reason": r.disabled_reason,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ],
        "currently_disabled": await is_engine_disabled(engine),
    }


@router.post("/quality/{engine}/evaluate")
async def force_evaluate(
    engine: str,
    admin: User = Depends(require_admin),
):
    """Run the quality evaluation for a single engine right
    now. Used by operators who want to verify a fix without
    waiting for the next cron tick.
    """
    result = await evaluate_engine(engine)
    return result.to_dict()


@router.post("/quality/{engine}/re-enable")
async def re_enable_quality(
    engine: str,
    body: ReEnableRequest | None = None,
    admin: User = Depends(require_admin),
):
    """Flip ``is_disabled`` off for the engine. The pipeline
    will start emitting from it again on the next call. The
    reason is recorded in the audit log.
    """
    reason = (body.reason if body else "operator_override") or "operator_override"
    ok = await re_enable_engine(engine, reason=reason)
    if not ok:
        raise HTTPException(404, f"engine {engine!r} not currently disabled")
    return {"engine": engine, "re_enabled": True, "reason": reason}


# ── Circuit breaker ────────────────────────────────────────────
@router.get("/breakers")
async def list_breakers(admin: User = Depends(require_admin)):
    return {"breakers": await circuit_breaker.list_all_states()}


@router.get("/breakers/{engine}")
async def get_breaker(
    engine: str, admin: User = Depends(require_admin)
):
    return await circuit_breaker.get_state(engine)


@router.post("/breakers/{engine}/close")
async def close_breaker(
    engine: str, admin: User = Depends(require_admin)
):
    """Force-close a breaker regardless of failure state.
    Use after the underlying cause (e.g. exchange outage) is
    resolved.
    """
    await circuit_breaker.force_close(engine, reason="admin_endpoint")
    return {"engine": engine, "state": "closed"}


# ── Observability ──────────────────────────────────────────────
@router.get("/metrics")
async def metrics():
    """Prometheus text-format exporter. No auth — the
    ``/metrics`` path is conventionally scraped from inside
    the cluster. Lock this down at the ingress if exposed
    externally.
    """
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=metrics_registry.render(),
        media_type="text/plain; version=0.0.4",
    )


__all__ = ["router"]

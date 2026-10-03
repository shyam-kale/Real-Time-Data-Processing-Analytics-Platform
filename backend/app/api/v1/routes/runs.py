from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.pipeline import PipelineRunOut
from app.services.pipeline_service import list_runs
from app.models.pipeline import PipelineRun, Pipeline

router = APIRouter(prefix="/orgs/{org_id}/runs", tags=["runs"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


@router.get("", response_model=dict)
async def list_all_runs(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        runs, total = await list_runs(db, org_id, skip=(page-1)*page_size, limit=page_size)
        return {
            "items": [
                {
                    "id": str(r.id),
                    "pipeline_id": str(r.pipeline_id),
                    "triggered_by": str(r.triggered_by) if r.triggered_by else None,
                    "status": _fmt(r.status),
                    "started_at": _fmt(r.started_at),
                    "ended_at": _fmt(r.ended_at),
                    "created_at": _fmt(r.created_at),
                }
                for r in runs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.get("/{run_id}", response_model=dict)
async def get_run(
    org_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        result = await db.execute(
            select(PipelineRun).join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
            .where(PipelineRun.id == run_id, Pipeline.organization_id == org_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(404, "Run not found")
        return {
            "id": str(run.id),
            "pipeline_id": str(run.pipeline_id),
            "triggered_by": str(run.triggered_by) if run.triggered_by else None,
            "status": _fmt(run.status),
            "started_at": _fmt(run.started_at),
            "ended_at": _fmt(run.ended_at),
            "created_at": _fmt(run.created_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})

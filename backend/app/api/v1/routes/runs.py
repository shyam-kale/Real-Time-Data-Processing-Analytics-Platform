from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.pipeline import PipelineRunOut
from app.services.pipeline_service import list_runs
from app.models.pipeline import PipelineRun, Pipeline

router = APIRouter(prefix="/orgs/{org_id}/runs", tags=["runs"])


@router.get("", response_model=dict)
async def list_all_runs(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    runs, total = await list_runs(db, org_id, skip=(page-1)*page_size, limit=page_size)
    return {"items": [PipelineRunOut.model_validate(r) for r in runs], "total": total, "page": page, "page_size": page_size}


@router.get("/{run_id}", response_model=PipelineRunOut)
async def get_run(
    org_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    result = await db.execute(
        select(PipelineRun).join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(PipelineRun.id == run_id, Pipeline.organization_id == org_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run

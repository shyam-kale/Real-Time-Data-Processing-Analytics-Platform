from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.pipeline import PipelineCreate, PipelineUpdate, PipelineOut, PipelineDetailOut, PipelineRunOut
from app.services.pipeline_service import create_pipeline, update_pipeline, get_pipeline, list_pipelines, delete_pipeline, list_runs
from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, RunStatus

router = APIRouter(prefix="/orgs/{org_id}/pipelines", tags=["pipelines"])


@router.post("", response_model=PipelineDetailOut, status_code=201)
async def create(
    org_id: str,
    data: PipelineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    pipeline = await create_pipeline(db, org_id, current_user.id, data)
    await db.commit()
    await db.refresh(pipeline)
    pipeline.nodes = (await db.execute(select(PipelineNode).where(PipelineNode.pipeline_id == pipeline.id))).scalars().all()
    pipeline.edges = (await db.execute(select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline.id))).scalars().all()
    return pipeline


@router.get("", response_model=dict)
async def list_all(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    pipelines, total = await list_pipelines(db, org_id, skip=(page-1)*page_size, limit=page_size)
    return {"items": [PipelineOut.model_validate(p) for p in pipelines], "total": total, "page": page, "page_size": page_size}


@router.get("/{pipeline_id}", response_model=PipelineDetailOut)
async def get_one(
    org_id: str,
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    pipeline = await get_pipeline(db, pipeline_id, org_id)
    pipeline.nodes = (await db.execute(select(PipelineNode).where(PipelineNode.pipeline_id == pipeline_id))).scalars().all()
    pipeline.edges = (await db.execute(select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline_id))).scalars().all()
    return pipeline


@router.put("/{pipeline_id}", response_model=PipelineDetailOut)
async def update(
    org_id: str,
    pipeline_id: str,
    data: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    pipeline = await update_pipeline(db, pipeline_id, org_id, current_user.id, data)
    await db.commit()
    await db.refresh(pipeline)
    pipeline.nodes = (await db.execute(select(PipelineNode).where(PipelineNode.pipeline_id == pipeline_id))).scalars().all()
    pipeline.edges = (await db.execute(select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline_id))).scalars().all()
    return pipeline


@router.delete("/{pipeline_id}", status_code=204)
async def delete(
    org_id: str,
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await delete_pipeline(db, pipeline_id, org_id, current_user.id)
    await db.commit()


@router.post("/{pipeline_id}/run", response_model=PipelineRunOut)
async def run_pipeline(
    org_id: str,
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await get_pipeline(db, pipeline_id, org_id)
    run = PipelineRun(pipeline_id=pipeline_id, triggered_by=current_user.id, status=RunStatus.PENDING)
    db.add(run)
    await db.flush()
    run_id = run.id
    await db.commit()

    def _dispatch_pipeline(rid: str):
        try:
            from app.workers.tasks import task_execute_pipeline
            task_execute_pipeline.delay(rid)
        except Exception:
            pass

    background_tasks.add_task(_dispatch_pipeline, run_id)
    return run


@router.get("/{pipeline_id}/runs", response_model=dict)
async def get_runs(
    org_id: str,
    pipeline_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    runs, total = await list_runs(db, org_id, pipeline_id=pipeline_id, skip=(page-1)*page_size, limit=page_size)
    return {"items": [PipelineRunOut.model_validate(r) for r in runs], "total": total, "page": page, "page_size": page_size}

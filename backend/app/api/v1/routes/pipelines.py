from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.pipeline import PipelineCreate, PipelineUpdate, PipelineOut, PipelineDetailOut, PipelineRunOut
from app.services.pipeline_service import create_pipeline, update_pipeline, get_pipeline, list_pipelines, delete_pipeline, list_runs
from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, RunStatus

router = APIRouter(prefix="/orgs/{org_id}/pipelines", tags=["pipelines"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


async def _load_pipeline_detail(db: AsyncSession, pipeline_id: str) -> Pipeline:
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.nodes), selectinload(Pipeline.edges))
        .where(Pipeline.id == pipeline_id)
    )
    return result.scalar_one_or_none()


def _serialize_pipeline(p):
    if not p:
        return None
    return {
        "id": str(p.id),
        "organization_id": str(p.organization_id),
        "name": p.name,
        "description": p.description,
        "config": p.config,
        "is_enabled": p.is_enabled,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": _fmt(p.created_at),
        "updated_at": _fmt(p.updated_at),
    }


def _serialize_pipeline_detail(p):
    if not p:
        return None
    return {
        "id": str(p.id),
        "organization_id": str(p.organization_id),
        "name": p.name,
        "description": p.description,
        "config": p.config,
        "is_enabled": p.is_enabled,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": _fmt(p.created_at),
        "updated_at": _fmt(p.updated_at),
        "nodes": [
            {
                "id": str(n.id),
                "pipeline_id": str(n.pipeline_id),
                "node_type": n.node_type,
                "config": n.config,
                "position": n.position,
            }
            for n in (p.nodes or [])
        ],
        "edges": [
            {
                "id": str(e.id),
                "pipeline_id": str(e.pipeline_id),
                "source": str(e.source),
                "target": str(e.target),
            }
            for e in (p.edges or [])
        ],
    }


@router.post("", response_model=dict, status_code=201)
async def create(
    org_id: str,
    data: PipelineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        pipeline = await create_pipeline(db, org_id, current_user.id, data)
        await db.commit()
        detail = await _load_pipeline_detail(db, pipeline.id)
        return _serialize_pipeline_detail(detail)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.get("", response_model=dict)
async def list_all(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        pipelines, total = await list_pipelines(db, org_id, skip=(page-1)*page_size, limit=page_size)
        return {
            "items": [_serialize_pipeline(p) for p in pipelines],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.get("/{pipeline_id}", response_model=dict)
async def get_one(
    org_id: str,
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        await get_pipeline(db, pipeline_id, org_id)
        detail = await _load_pipeline_detail(db, pipeline_id)
        return _serialize_pipeline_detail(detail)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.put("/{pipeline_id}", response_model=dict)
async def update(
    org_id: str,
    pipeline_id: str,
    data: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        pipeline = await update_pipeline(db, pipeline_id, org_id, current_user.id, data)
        await db.commit()
        detail = await _load_pipeline_detail(db, pipeline.id)
        return _serialize_pipeline_detail(detail)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


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


@router.post("/{pipeline_id}/run", response_model=dict)
async def run_pipeline(
    org_id: str,
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        await get_pipeline(db, pipeline_id, org_id)
        run = PipelineRun(pipeline_id=pipeline_id, triggered_by=current_user.id, status=RunStatus.PENDING)
        db.add(run)
        await db.flush()
        run_id = run.id
        await db.commit()
        from app.workers.tasks import task_execute_pipeline
        background_tasks.add_task(lambda: task_execute_pipeline.delay(run_id))
        return {
            "id": str(run.id),
            "pipeline_id": str(run.pipeline_id),
            "triggered_by": str(run.triggered_by),
            "status": _fmt(run.status),
            "started_at": _fmt(run.started_at),
            "ended_at": _fmt(run.ended_at),
            "created_at": _fmt(run.created_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


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
    try:
        runs, total = await list_runs(db, org_id, pipeline_id=pipeline_id, skip=(page-1)*page_size, limit=page_size)
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

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
        "status": _fmt(p.status),
        "schedule": p.schedule,
        "tags": p.tags,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": _fmt(p.created_at),
        "updated_at": _fmt(p.updated_at),
        "last_run_at": _fmt(p.last_run_at),
        "last_run_status": _fmt(p.last_run_status),
    }


def _serialize_pipeline_detail(p):
    if not p:
        return None
    return {
        "id": str(p.id),
        "organization_id": str(p.organization_id),
        "name": p.name,
        "description": p.description,
        "status": _fmt(p.status),
        "schedule": p.schedule,
        "tags": p.tags,
        "is_enabled": p.is_enabled if hasattr(p, 'is_enabled') else True,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": _fmt(p.created_at),
        "updated_at": _fmt(p.updated_at),
        "last_run_at": _fmt(p.last_run_at),
        "last_run_status": _fmt(p.last_run_status),
        "nodes": [
            {
                "id": str(n.id),
                "pipeline_id": str(n.pipeline_id),
                "node_type": _fmt(n.node_type),
                "label": n.label,
                "config": n.config or {},
                "position": {
                    "x": n.position_x,
                    "y": n.position_y,
                },
            }
            for n in (p.nodes or [])
        ],
        "edges": [
            {
                "id": str(e.id),
                "pipeline_id": str(e.pipeline_id),
                "source": str(e.source_node_id),
                "target": str(e.target_node_id),
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
        run = PipelineRun(
            pipeline_id=pipeline_id,
            triggered_by=current_user.id,
            status=RunStatus.PENDING,
        )
        db.add(run)
        await db.flush()
        run_id = str(run.id)
        await db.commit()

        # Execute real pipeline graph in background (no Celery needed)
        background_tasks.add_task(_execute_pipeline_bg, run_id, pipeline_id)

        return {
            "id": run_id,
            "pipeline_id": str(run.pipeline_id),
            "triggered_by": str(run.triggered_by),
            "status": _fmt(run.status),
            "input_records": run.input_records,
            "output_records": run.output_records,
            "failed_records": run.failed_records,
            "duration_seconds": run.duration_seconds,
            "error_message": run.error_message,
            "started_at": _fmt(run.started_at),
            "completed_at": _fmt(run.completed_at),
            "created_at": _fmt(run.created_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


async def _execute_pipeline_bg(run_id: str, pipeline_id: str):
    """Run the real pipeline executor in a thread pool, update DB with results."""
    import asyncio
    import time
    from datetime import datetime, timezone
    from app.db.base import AsyncSessionLocal
    from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, RunStatus
    from app.processing.pipeline_executor import execute_pipeline_graph
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))).scalar_one_or_none()
        if not run:
            return

        nodes_q = (await db.execute(select(PipelineNode).where(PipelineNode.pipeline_id == pipeline_id))).scalars().all()
        edges_q = (await db.execute(select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline_id))).scalars().all()
        pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()

        nodes = [{"id": n.id, "node_type": n.node_type, "label": n.label, "config": n.config} for n in nodes_q]
        edges = [{"source_node_id": e.source_node_id, "target_node_id": e.target_node_id} for e in edges_q]

        run.status     = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        start = time.time()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, execute_pipeline_graph, nodes, edges, None
            )
            duration = round(time.time() - start, 2)
            run.status         = RunStatus.SUCCESS if result["failed_records"] == 0 else RunStatus.WARNING
            run.input_records  = result["input_records"]
            run.output_records = result["output_records"]
            run.failed_records = result["failed_records"]
            run.duration_seconds = duration
            run.logs           = result["logs"]
            run.metrics        = result["metrics"]
            run.current_stage  = "complete"
            run.completed_at   = datetime.now(timezone.utc)
            if pipeline:
                pipeline.last_run_at     = run.completed_at
                pipeline.last_run_status = run.status
        except Exception as exc:
            import traceback; traceback.print_exc()
            run.status        = RunStatus.FAILED
            run.error_message = str(exc)
            run.duration_seconds = round(time.time() - start, 2)
            run.completed_at  = datetime.now(timezone.utc)
            if pipeline:
                pipeline.last_run_at     = run.completed_at
                pipeline.last_run_status = RunStatus.FAILED

        await db.commit()


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
                    "input_records": r.input_records,
                    "output_records": r.output_records,
                    "failed_records": r.failed_records,
                    "duration_seconds": r.duration_seconds,
                    "error_message": r.error_message,
                    "started_at": _fmt(r.started_at),
                    "completed_at": _fmt(r.completed_at),
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

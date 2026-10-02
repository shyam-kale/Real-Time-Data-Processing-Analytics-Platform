from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.dataset import Dataset
from app.models.pipeline import Pipeline, PipelineRun
from app.models.quality import QualityReport
from app.models.activity import ActivityLog

router = APIRouter(prefix="/orgs/{org_id}/overview", tags=["overview"])


@router.get("")
async def get_overview(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    ds_count = (await db.execute(select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id))).scalar() or 0
    total_records = (await db.execute(select(func.sum(Dataset.row_count)).where(Dataset.organization_id == org_id))).scalar() or 0
    pl_count = (await db.execute(select(func.count()).select_from(Pipeline).where(Pipeline.organization_id == org_id))).scalar() or 0
    active_pl = (await db.execute(select(func.count()).select_from(Pipeline).where(Pipeline.organization_id == org_id, Pipeline.status == "active"))).scalar() or 0
    avg_quality = (await db.execute(
        select(func.avg(QualityReport.overall_score))
        .join(Dataset, Dataset.id == QualityReport.dataset_id)
        .where(Dataset.organization_id == org_id)
    )).scalar()

    runs_result = await db.execute(
        select(PipelineRun, Pipeline.name)
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(Pipeline.organization_id == org_id)
        .order_by(PipelineRun.created_at.desc()).limit(10)
    )
    recent_runs = [
        {"id": r.id, "pipeline_id": r.pipeline_id, "pipeline_name": name,
         "status": r.status, "input_records": r.input_records,
         "output_records": r.output_records, "duration_seconds": r.duration_seconds,
         "created_at": r.created_at}
        for r, name in runs_result.all()
    ]

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    activity_result = await db.execute(
        select(func.date(PipelineRun.created_at).label("day"),
               func.count().label("runs"),
               func.sum(PipelineRun.output_records).label("records"))
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(Pipeline.organization_id == org_id, PipelineRun.created_at >= thirty_days_ago)
        .group_by(func.date(PipelineRun.created_at))
        .order_by(func.date(PipelineRun.created_at))
    )
    activity_data = [{"date": str(r.day), "runs": r.runs, "records": r.records or 0} for r in activity_result.all()]

    recent_activity = (await db.execute(
        select(ActivityLog).where(ActivityLog.organization_id == org_id)
        .order_by(ActivityLog.created_at.desc()).limit(8)
    )).scalars().all()

    status_rows = (await db.execute(
        select(PipelineRun.status, func.count().label("count"))
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(Pipeline.organization_id == org_id)
        .group_by(PipelineRun.status)
    )).all()

    return {
        "total_datasets": ds_count,
        "total_records": int(total_records),
        "total_pipelines": pl_count,
        "active_pipelines": active_pl,
        "quality_score": round(avg_quality, 1) if avg_quality else None,
        "recent_runs": recent_runs,
        "processing_activity": activity_data,
        "recent_activity": [{"id": l.id, "action": l.action, "resource_type": l.resource_type,
                              "resource_name": l.resource_name, "user_id": l.user_id,
                              "created_at": l.created_at} for l in recent_activity],
        "run_statuses": {str(r.status): r.count for r in status_rows},
    }

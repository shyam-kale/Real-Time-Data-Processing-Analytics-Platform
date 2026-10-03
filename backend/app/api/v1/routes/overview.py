from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.dataset import Dataset
from app.models.pipeline import Pipeline, PipelineRun, PipelineStatus
from app.models.quality import QualityReport
from app.models.activity import ActivityLog

router = APIRouter(prefix="/orgs/{org_id}/overview", tags=["overview"])


def _str(v):
    """Safely convert any value to JSON-serializable form."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, 'value'):  # Enum
        return v.value
    return v


@router.get("")
async def get_overview(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        ds_count = (await db.execute(
            select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id)
        )).scalar() or 0

        total_records = (await db.execute(
            select(func.sum(Dataset.row_count)).where(Dataset.organization_id == org_id)
        )).scalar() or 0

        pl_count = (await db.execute(
            select(func.count()).select_from(Pipeline).where(Pipeline.organization_id == org_id)
        )).scalar() or 0

        active_pl = (await db.execute(
            select(func.count()).select_from(Pipeline)
            .where(Pipeline.organization_id == org_id, Pipeline.status == PipelineStatus.ACTIVE)
        )).scalar() or 0

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
            {
                "id": str(r.id),
                "pipeline_id": str(r.pipeline_id),
                "pipeline_name": str(name),
                "status": _str(r.status),
                "input_records": r.input_records,
                "output_records": r.output_records,
                "duration_seconds": r.duration_seconds,
                "created_at": _str(r.created_at),
            }
            for r, name in runs_result.all()
        ]

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        activity_result = await db.execute(
            select(
                func.date(PipelineRun.created_at).label("day"),
                func.count().label("runs"),
                func.sum(PipelineRun.output_records).label("records"),
            )
            .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
            .where(Pipeline.organization_id == org_id, PipelineRun.created_at >= thirty_days_ago)
            .group_by(func.date(PipelineRun.created_at))
            .order_by(func.date(PipelineRun.created_at))
        )
        activity_data = [
            {"date": str(r.day), "runs": r.runs, "records": r.records or 0}
            for r in activity_result.all()
        ]

        recent_activity_rows = (await db.execute(
            select(ActivityLog)
            .where(ActivityLog.organization_id == org_id)
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
            "quality_score": round(float(avg_quality), 1) if avg_quality else None,
            "recent_runs": recent_runs,
            "processing_activity": activity_data,
            "recent_activity": [
                {
                    "id": str(l.id),
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "resource_name": l.resource_name,
                    "user_id": str(l.user_id) if l.user_id else None,
                    "created_at": _str(l.created_at),
                }
                for l in recent_activity_rows
            ],
            "run_statuses": {_str(r.status): r.count for r in status_rows},
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})

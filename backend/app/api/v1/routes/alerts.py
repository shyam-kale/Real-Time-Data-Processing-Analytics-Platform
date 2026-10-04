from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertOut
from app.models.alert import Alert

router = APIRouter(prefix="/orgs/{org_id}/alerts", tags=["alerts"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


@router.post("", response_model=AlertOut, status_code=201)
async def create(
    org_id: str, data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        alert = Alert(organization_id=org_id, created_by=current_user.id,
                      name=data.name, description=data.description,
                      condition_type=data.condition_type, threshold=data.threshold,
                      dataset_id=data.dataset_id, pipeline_id=data.pipeline_id,
                      severity=data.severity, notification_channels=data.notification_channels)
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return {
            "id": str(alert.id),
            "organization_id": str(alert.organization_id),
            "created_by": str(alert.created_by),
            "name": alert.name,
            "description": alert.description,
            "condition_type": _fmt(alert.condition_type),
            "threshold": alert.threshold,
            "dataset_id": str(alert.dataset_id) if alert.dataset_id else None,
            "pipeline_id": str(alert.pipeline_id) if alert.pipeline_id else None,
            "severity": _fmt(alert.severity),
            "status": _fmt(alert.status),
            "notification_channels": alert.notification_channels or [],
            "last_triggered_at": _fmt(alert.last_triggered_at),
            "created_at": _fmt(alert.created_at),
            "updated_at": _fmt(alert.updated_at),
        }
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
        total = (await db.execute(select(func.count()).select_from(Alert).where(Alert.organization_id == org_id))).scalar() or 0
        items = (await db.execute(select(Alert).where(Alert.organization_id == org_id).order_by(Alert.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()
        return {
            "items": [
                {
                    "id": str(a.id),
                    "organization_id": str(a.organization_id),
                    "created_by": str(a.created_by),
                    "name": a.name,
                    "description": a.description,
                    "condition_type": _fmt(a.condition_type),
                    "threshold": a.threshold,
                    "dataset_id": str(a.dataset_id) if a.dataset_id else None,
                    "pipeline_id": str(a.pipeline_id) if a.pipeline_id else None,
                    "severity": _fmt(a.severity),
                    "status": _fmt(a.status),
                    "notification_channels": a.notification_channels or [],
                    "last_triggered_at": _fmt(a.last_triggered_at),
                    "created_at": _fmt(a.created_at),
                    "updated_at": _fmt(a.updated_at),
                }
                for a in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.put("/{alert_id}", response_model=dict)
async def update(
    org_id: str, alert_id: str, data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        a = (await db.execute(select(Alert).where(Alert.id == alert_id, Alert.organization_id == org_id))).scalar_one_or_none()
        if not a: raise HTTPException(404, "Alert not found")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(a, k, v)
        await db.commit()
        return {
            "id": str(a.id),
            "organization_id": str(a.organization_id),
            "created_by": str(a.created_by),
            "name": a.name,
            "description": a.description,
            "condition_type": _fmt(a.condition_type),
            "threshold": a.threshold,
            "dataset_id": str(a.dataset_id) if a.dataset_id else None,
            "pipeline_id": str(a.pipeline_id) if a.pipeline_id else None,
            "severity": _fmt(a.severity),
            "status": _fmt(a.status),
            "notification_channels": a.notification_channels or [],
            "last_triggered_at": _fmt(a.last_triggered_at),
            "created_at": _fmt(a.created_at),
            "updated_at": _fmt(a.updated_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.delete("/{alert_id}", status_code=204)
async def delete(
    org_id: str, alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    a = (await db.execute(select(Alert).where(Alert.id == alert_id, Alert.organization_id == org_id))).scalar_one_or_none()
    if not a: raise HTTPException(404, "Alert not found")
    await db.delete(a)
    await db.commit()

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertOut
from app.models.alert import Alert

router = APIRouter(prefix="/orgs/{org_id}/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=201)
async def create(
    org_id: str, data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    alert = Alert(organization_id=org_id, created_by=current_user.id,
                  name=data.name, description=data.description,
                  condition_type=data.condition_type, threshold=data.threshold,
                  dataset_id=data.dataset_id, pipeline_id=data.pipeline_id,
                  severity=data.severity, notification_channels=data.notification_channels)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("", response_model=dict)
async def list_all(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    total = (await db.execute(select(func.count()).select_from(Alert).where(Alert.organization_id == org_id))).scalar()
    items = (await db.execute(select(Alert).where(Alert.organization_id == org_id).order_by(Alert.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()
    return {"items": [AlertOut.model_validate(a) for a in items], "total": total}


@router.put("/{alert_id}", response_model=AlertOut)
async def update(
    org_id: str, alert_id: str, data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    a = (await db.execute(select(Alert).where(Alert.id == alert_id, Alert.organization_id == org_id))).scalar_one_or_none()
    if not a: raise HTTPException(404, "Alert not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(a, k, v)
    await db.commit()
    return a


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

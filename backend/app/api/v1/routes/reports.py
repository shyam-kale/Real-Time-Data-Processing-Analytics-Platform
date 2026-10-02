from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportOut
from app.models.report import Report
from app.services.activity_service import log_activity

router = APIRouter(prefix="/orgs/{org_id}/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
async def create(
    org_id: str,
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    report = Report(organization_id=org_id, created_by=current_user.id,
                    name=data.name, description=data.description,
                    config=data.config, is_public=data.is_public, tags=data.tags)
    db.add(report)
    await db.flush()
    await log_activity(db, org_id, current_user.id, "report.created", "report", report.id, data.name)
    await db.commit()
    return report


@router.get("", response_model=dict)
async def list_all(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    q = select(Report).where(Report.organization_id == org_id).order_by(Report.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(Report).where(Report.organization_id == org_id))).scalar()
    items = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
    return {"items": [ReportOut.model_validate(r) for r in items], "total": total, "page": page}


@router.get("/{report_id}", response_model=ReportOut)
async def get_one(
    org_id: str, report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    r = (await db.execute(select(Report).where(Report.id == report_id, Report.organization_id == org_id))).scalar_one_or_none()
    if not r: raise HTTPException(404, "Report not found")
    return r


@router.put("/{report_id}", response_model=ReportOut)
async def update(
    org_id: str, report_id: str, data: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    r = (await db.execute(select(Report).where(Report.id == report_id, Report.organization_id == org_id))).scalar_one_or_none()
    if not r: raise HTTPException(404, "Report not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    await db.commit()
    return r


@router.delete("/{report_id}", status_code=204)
async def delete(
    org_id: str, report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    r = (await db.execute(select(Report).where(Report.id == report_id, Report.organization_id == org_id))).scalar_one_or_none()
    if not r: raise HTTPException(404, "Report not found")
    await db.delete(r)
    await db.commit()

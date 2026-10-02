from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.activity import ActivityLog

router = APIRouter(prefix="/orgs/{org_id}/activity", tags=["activity"])


@router.get("")
async def list_activity(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    q = select(ActivityLog).where(ActivityLog.organization_id == org_id)
    cq = select(func.count()).select_from(ActivityLog).where(ActivityLog.organization_id == org_id)
    if action:
        q = q.where(ActivityLog.action.ilike(f"%{action}%"))
        cq = cq.where(ActivityLog.action.ilike(f"%{action}%"))
    q = q.order_by(ActivityLog.created_at.desc())
    items = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
    total = (await db.execute(cq)).scalar()
    return {
        "items": [{"id": l.id, "action": l.action, "resource_type": l.resource_type,
                   "resource_id": l.resource_id, "resource_name": l.resource_name,
                   "user_id": l.user_id, "details": l.details,
                   "ip_address": l.ip_address, "created_at": l.created_at} for l in items],
        "total": total, "page": page,
    }

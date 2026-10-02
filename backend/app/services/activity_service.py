from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity import ActivityLog


async def log_activity(
    db: AsyncSession,
    org_id: str,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    log = ActivityLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    # Don't flush here — let the calling service control the transaction

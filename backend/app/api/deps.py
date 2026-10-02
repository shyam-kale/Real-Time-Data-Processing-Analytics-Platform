from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.security import decode_token, verify_api_key
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.api_key import ApiKey

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_api_key: Optional[str] = Header(default=None),
) -> User:
    # ── API key ──────────────────────────────────────────────────────────────
    if x_api_key:
        from datetime import datetime, timezone
        prefix = x_api_key[:8]
        res = await db.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)
        )
        key = res.scalar_one_or_none()
        if key and verify_api_key(x_api_key, key.hashed_key):
            key.last_used_at = datetime.now(timezone.utc)
            res2 = await db.execute(select(User).where(User.id == key.user_id))
            user = res2.scalar_one_or_none()
            if user and user.is_active:
                return user

    # ── JWT Bearer ────────────────────────────────────────────────────────────
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            res = await db.execute(select(User).where(User.id == payload["sub"]))
            user = res.scalar_one_or_none()
            if user and user.is_active:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_org_member(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationMember:
    res = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return member

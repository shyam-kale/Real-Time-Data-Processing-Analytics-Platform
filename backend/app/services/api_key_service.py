import secrets
import uuid
from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.api_key import ApiKey
from app.core.security import create_api_key_hash
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedOut, ApiKeyOut
from app.services.activity_service import log_activity


def _generate_api_key() -> str:
    return f"df_{secrets.token_urlsafe(32)}"


async def create_api_key(
    db: AsyncSession, org_id: str, user_id: str, data: ApiKeyCreate
) -> ApiKeyCreatedOut:
    raw_key = _generate_api_key()
    prefix = raw_key[:8]

    key = ApiKey(
        organization_id=org_id,
        user_id=user_id,
        name=data.name,
        key_prefix=prefix,
        hashed_key=create_api_key_hash(raw_key),
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    db.add(key)
    await db.flush()

    await log_activity(db, org_id, user_id, "api_key.created", "api_key", key.id, data.name)

    return ApiKeyCreatedOut(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=key.scopes,
        is_active=key.is_active,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        created_at=key.created_at,
        raw_key=raw_key,
    )


async def list_api_keys(db: AsyncSession, org_id: str, user_id: str) -> List[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.organization_id == org_id,
            ApiKey.user_id == user_id,
        ).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


async def revoke_api_key(db: AsyncSession, key_id: str, org_id: str, user_id: str) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == org_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, "API key not found")
    key.is_active = False
    await log_activity(db, org_id, user_id, "api_key.revoked", "api_key", key_id, key.name)

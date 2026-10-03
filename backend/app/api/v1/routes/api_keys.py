from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/orgs/{org_id}/api-keys", tags=["api-keys"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


@router.post("", status_code=201)
async def create(
    org_id: str,
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        result = await create_api_key(db, org_id, current_user.id, data)
        await db.commit()
        return {
            "id": str(result.id),
            "name": result.name,
            "key_prefix": result.key_prefix,
            "scopes": result.scopes or [],
            "is_active": result.is_active,
            "last_used_at": _fmt(result.last_used_at),
            "expires_at": _fmt(result.expires_at),
            "created_at": _fmt(result.created_at),
            "raw_key": result.raw_key,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("")
async def list_keys(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        keys = await list_api_keys(db, org_id, current_user.id)
        return [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes or [],
                "is_active": k.is_active,
                "last_used_at": _fmt(k.last_used_at),
                "expires_at": _fmt(k.expires_at),
                "created_at": _fmt(k.created_at),
            }
            for k in keys
        ]
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.delete("/{key_id}", status_code=204)
async def revoke(
    org_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await revoke_api_key(db, key_id, org_id, current_user.id)
    await db.commit()

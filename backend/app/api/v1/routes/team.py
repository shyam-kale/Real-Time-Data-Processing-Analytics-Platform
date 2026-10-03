from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.organization import InviteMemberRequest, UpdateMemberRoleRequest
from app.services.org_service import get_org_members, invite_member, update_member_role, remove_member

router = APIRouter(prefix="/orgs/{org_id}/team", tags=["team"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


@router.get("")
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        members = await get_org_members(db, org_id)
        return {
            "items": [
                {
                    "id": str(m.id),
                    "organization_id": str(m.organization_id),
                    "user_id": str(m.user_id),
                    "role": m.role,
                    "joined_at": _fmt(m.joined_at),
                }
                for m in members
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.post("/invite", status_code=201)
async def invite(
    org_id: str,
    data: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        result = await invite_member(db, org_id, current_user.id, data)
        await db.commit()
        return {
            "id": str(result.id),
            "organization_id": str(result.organization_id),
            "user_id": str(result.user_id),
            "role": result.role,
            "joined_at": _fmt(result.joined_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.put("/{member_id}")
async def update_role(
    org_id: str,
    member_id: str,
    data: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        member = await update_member_role(db, org_id, member_id, current_user.id, data)
        await db.commit()
        return {
            "id": str(member.id),
            "organization_id": str(member.organization_id),
            "user_id": str(member.user_id),
            "role": member.role,
            "joined_at": _fmt(member.joined_at),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


@router.delete("/{member_id}", status_code=204)
async def remove(
    org_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await remove_member(db, org_id, member_id, current_user.id)
    await db.commit()

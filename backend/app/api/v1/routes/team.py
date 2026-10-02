from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.organization import InviteMemberRequest, UpdateMemberRoleRequest
from app.services.org_service import get_org_members, invite_member, update_member_role, remove_member

router = APIRouter(prefix="/orgs/{org_id}/team", tags=["team"])


@router.get("")
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    return await get_org_members(db, org_id)


@router.post("/invite", status_code=201)
async def invite(
    org_id: str,
    data: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    result = await invite_member(db, org_id, current_user.id, data)
    await db.commit()
    return result


@router.put("/{member_id}")
async def update_role(
    org_id: str,
    member_id: str,
    data: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    member = await update_member_role(db, org_id, member_id, current_user.id, data)
    await db.commit()
    return {"id": member.id, "role": member.role}


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

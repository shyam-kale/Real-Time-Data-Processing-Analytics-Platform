from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.schemas.organization import InviteMemberRequest, UpdateMemberRoleRequest
from app.services.activity_service import log_activity


async def get_org_members(db: AsyncSession, org_id: str) -> List[dict]:
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == org_id)
    )
    rows = result.all()
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "organization_id": m.organization_id,
            "role": m.role,
            "user_email": u.email,
            "user_full_name": u.full_name,
            "user_avatar_url": u.avatar_url,
            "joined_at": m.joined_at,
        }
        for m, u in rows
    ]


async def invite_member(
    db: AsyncSession, org_id: str, inviter_id: str, data: InviteMemberRequest
) -> dict:
    # Find user by email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, f"User with email {data.email} not found. They must register first.")

    # Check already a member
    existing = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "User is already a member")

    member = OrganizationMember(
        organization_id=org_id,
        user_id=user.id,
        role=data.role,
        invited_by=inviter_id,
    )
    db.add(member)
    await db.flush()

    await log_activity(db, org_id, inviter_id, "member.invited", "user", user.id, user.full_name)

    return {
        "id": member.id,
        "user_id": user.id,
        "organization_id": org_id,
        "role": member.role,
        "user_email": user.email,
        "user_full_name": user.full_name,
        "user_avatar_url": user.avatar_url,
        "joined_at": member.joined_at,
    }


async def update_member_role(
    db: AsyncSession, org_id: str, member_id: str, actor_id: str, data: UpdateMemberRoleRequest
) -> OrganizationMember:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")
    if member.role == OrgRole.OWNER:
        raise HTTPException(400, "Cannot change owner role")

    member.role = data.role
    await log_activity(db, org_id, actor_id, "member.role_updated", "user", member.user_id)
    return member


async def remove_member(db: AsyncSession, org_id: str, member_id: str, actor_id: str) -> None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")
    if member.role == OrgRole.OWNER:
        raise HTTPException(400, "Cannot remove the owner")
    await log_activity(db, org_id, actor_id, "member.removed", "user", member.user_id)
    await db.delete(member)

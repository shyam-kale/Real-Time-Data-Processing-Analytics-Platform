from pydantic import BaseModel, Field
from typing import Optional
from app.models.organization import OrgRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    logo_url: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class MemberOut(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: OrgRole
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    user_avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: OrgRole = OrgRole.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: OrgRole

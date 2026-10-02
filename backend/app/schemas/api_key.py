from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: List[str] = ["read"]
    expires_at: Optional[datetime] = None


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str  # only returned on creation

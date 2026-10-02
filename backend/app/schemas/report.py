from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    config: Dict[str, Any] = {}
    is_public: bool = False
    tags: Optional[str] = None


class ReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    tags: Optional[str] = None


class ReportOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    is_public: bool
    tags: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

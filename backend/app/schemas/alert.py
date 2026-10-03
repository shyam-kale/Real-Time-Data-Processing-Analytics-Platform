from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.alert import AlertConditionType, AlertSeverity, AlertStatus

_CFG = ConfigDict(from_attributes=True, use_enum_values=True)


class AlertCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    condition_type: AlertConditionType
    threshold: Optional[float] = None
    dataset_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.MEDIUM
    notification_channels: dict = {}


class AlertUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None


class AlertOut(BaseModel):
    model_config = _CFG
    id: str
    name: str
    description: Optional[str] = None
    condition_type: AlertConditionType
    threshold: Optional[float] = None
    dataset_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    severity: AlertSeverity
    status: AlertStatus
    last_triggered_at: Optional[datetime] = None
    created_at: datetime

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.alert import AlertConditionType, AlertSeverity, AlertStatus


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
    id: str
    name: str
    description: Optional[str]
    condition_type: AlertConditionType
    threshold: Optional[float]
    dataset_id: Optional[str]
    pipeline_id: Optional[str]
    severity: AlertSeverity
    status: AlertStatus
    last_triggered_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

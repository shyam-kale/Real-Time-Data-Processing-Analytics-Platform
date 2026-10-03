from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from app.models.quality import QualitySeverity, QualityIssueType

_CFG = ConfigDict(from_attributes=True, use_enum_values=True)


class QualityIssueOut(BaseModel):
    model_config = _CFG
    id: str
    issue_type: QualityIssueType
    severity: QualitySeverity
    column_name: Optional[str] = None
    description: str
    affected_rows: int
    affected_percentage: float
    sample_values: Optional[List[Any]] = None
    suggestion: Optional[str] = None


class QualityReportOut(BaseModel):
    model_config = _CFG
    id: str
    dataset_id: str
    overall_score: float
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    consistency_score: float
    total_rows: int
    passed_rows: int
    failed_rows: int
    issue_count: int
    summary: Optional[dict] = None
    created_at: datetime
    issues: List[QualityIssueOut] = []

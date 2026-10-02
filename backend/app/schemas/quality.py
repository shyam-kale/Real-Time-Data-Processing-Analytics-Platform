from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.quality import QualitySeverity, QualityIssueType


class QualityIssueOut(BaseModel):
    id: str
    issue_type: QualityIssueType
    severity: QualitySeverity
    column_name: Optional[str]
    description: str
    affected_rows: int
    affected_percentage: float
    sample_values: Optional[List[Any]]
    suggestion: Optional[str]

    model_config = {"from_attributes": True}


class QualityReportOut(BaseModel):
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
    summary: Optional[dict]
    created_at: datetime
    issues: List[QualityIssueOut] = []

    model_config = {"from_attributes": True}

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AnalyticsQuery(BaseModel):
    dataset_id: str
    dimensions: List[str] = []
    measures: List[str] = []
    aggregation: str = "count"  # count, sum, avg, min, max
    filters: Optional[List[Dict[str, Any]]] = None
    date_column: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    chart_type: str = "bar"
    limit: int = 1000


class AnalyticsResult(BaseModel):
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    query_time_ms: float

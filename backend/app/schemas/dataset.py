from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.dataset import DatasetStatus, FileFormat, ColumnDataType


class DatasetOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    file_format: FileFormat
    file_size_bytes: int
    status: DatasetStatus
    row_count: Optional[int]
    column_count: Optional[int]
    null_count: Optional[int]
    duplicate_count: Optional[int]
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_profiled_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DatasetColumnOut(BaseModel):
    id: str
    name: str
    position: int
    data_type: ColumnDataType
    nullable: bool
    null_count: Optional[int]
    unique_count: Optional[int]
    min_value: Optional[str]
    max_value: Optional[str]
    mean_value: Optional[float]
    std_value: Optional[float]
    sample_values: Optional[List[Any]]

    model_config = {"from_attributes": True}


class DatasetDetailOut(DatasetOut):
    columns: List[DatasetColumnOut] = []
    profile_data: Optional[Dict] = None


class DataExplorerQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
    search: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: str = "asc"
    filters: Optional[List[Dict]] = None


class DataExplorerResponse(BaseModel):
    rows: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    columns: List[str]

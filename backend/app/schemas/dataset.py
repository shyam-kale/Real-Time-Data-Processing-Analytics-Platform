from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.dataset import DatasetStatus, FileFormat, ColumnDataType

_CFG = ConfigDict(from_attributes=True, use_enum_values=True)


class DatasetOut(BaseModel):
    model_config = _CFG
    id: str
    name: str
    description: Optional[str] = None
    file_format: FileFormat
    file_size_bytes: int
    status: DatasetStatus
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    null_count: Optional[int] = None
    duplicate_count: Optional[int] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_profiled_at: Optional[datetime] = None


class DatasetColumnOut(BaseModel):
    model_config = _CFG
    id: str
    name: str
    position: int
    data_type: ColumnDataType
    nullable: bool
    null_count: Optional[int] = None
    unique_count: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    sample_values: Optional[List[Any]] = None


class DatasetDetailOut(DatasetOut):
    columns: List[DatasetColumnOut] = []
    profile_data: Optional[Dict] = None
    schema_snapshot: Optional[Dict[str, str]] = None


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

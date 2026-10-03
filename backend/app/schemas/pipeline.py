from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.pipeline import PipelineStatus, RunStatus, NodeType

_CFG = ConfigDict(from_attributes=True, use_enum_values=True)


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class PipelineNodeCreate(BaseModel):
    id: str
    node_type: NodeType
    label: str
    config: Dict[str, Any] = {}
    position: NodePosition = NodePosition()


class PipelineEdgeCreate(BaseModel):
    id: str
    source: str
    target: str


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    nodes: List[PipelineNodeCreate] = []
    edges: List[PipelineEdgeCreate] = []
    tags: Optional[str] = None


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[PipelineNodeCreate]] = None
    edges: Optional[List[PipelineEdgeCreate]] = None
    status: Optional[PipelineStatus] = None
    tags: Optional[str] = None


class PipelineNodeOut(BaseModel):
    model_config = _CFG
    id: str
    node_type: NodeType
    label: str
    config: Dict[str, Any]
    position_x: float
    position_y: float


class PipelineEdgeOut(BaseModel):
    model_config = _CFG
    id: str
    source_node_id: str
    target_node_id: str


class PipelineOut(BaseModel):
    model_config = _CFG
    id: str
    name: str
    description: Optional[str] = None
    status: PipelineStatus
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[RunStatus] = None


class PipelineDetailOut(PipelineOut):
    nodes: List[PipelineNodeOut] = []
    edges: List[PipelineEdgeOut] = []


class PipelineRunOut(BaseModel):
    model_config = _CFG
    id: str
    pipeline_id: str
    status: RunStatus
    current_stage: Optional[str] = None
    input_records: Optional[int] = None
    output_records: Optional[int] = None
    failed_records: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    logs: Optional[List] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

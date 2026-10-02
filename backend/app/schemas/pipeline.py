from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.pipeline import PipelineStatus, RunStatus, NodeType


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
    id: str
    node_type: NodeType
    label: str
    config: Dict[str, Any]
    position_x: float
    position_y: float

    model_config = {"from_attributes": True}


class PipelineEdgeOut(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str

    model_config = {"from_attributes": True}


class PipelineOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: PipelineStatus
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime]
    last_run_status: Optional[RunStatus]

    model_config = {"from_attributes": True}


class PipelineDetailOut(PipelineOut):
    nodes: List[PipelineNodeOut] = []
    edges: List[PipelineEdgeOut] = []


class PipelineRunOut(BaseModel):
    id: str
    pipeline_id: str
    status: RunStatus
    current_stage: Optional[str]
    input_records: Optional[int]
    output_records: Optional[int]
    failed_records: Optional[int]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    logs: Optional[List]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

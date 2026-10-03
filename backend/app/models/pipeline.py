import enum
import uuid
from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, DateTime,
    Enum, ForeignKey, Text, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base


def _enum(e):
    """Helper: create a non-native Enum that stores lowercase values."""
    return Enum(e, values_callable=lambda x: [i.value for i in x], native_enum=False)


class PipelineStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, enum.Enum):
    SOURCE = "source"
    VALIDATION = "validation"
    FILTER = "filter"
    TRANSFORM = "transform"
    DEDUPLICATE = "deduplicate"
    AGGREGATE = "aggregate"
    QUALITY_CHECK = "quality_check"
    OUTPUT = "output"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PipelineStatus] = mapped_column(_enum(PipelineStatus), default=PipelineStatus.DRAFT)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_run_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[RunStatus | None] = mapped_column(_enum(RunStatus), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="pipelines")
    nodes: Mapped[list["PipelineNode"]] = relationship(
        "PipelineNode", back_populates="pipeline", cascade="all, delete-orphan"
    )
    edges: Mapped[list["PipelineEdge"]] = relationship(
        "PipelineEdge", back_populates="pipeline", cascade="all, delete-orphan"
    )
    runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun", back_populates="pipeline", cascade="all, delete-orphan"
    )


class PipelineNode(Base):
    __tablename__ = "pipeline_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type: Mapped[NodeType] = mapped_column(_enum(NodeType), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="nodes")


class PipelineEdge(Base):
    __tablename__ = "pipeline_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_nodes.id", ondelete="CASCADE"), nullable=False)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="edges")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus), default=RunStatus.PENDING)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_records: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_records: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    failed_records: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="runs")

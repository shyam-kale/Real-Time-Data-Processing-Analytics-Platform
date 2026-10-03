import enum
import uuid
from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, DateTime,
    Enum, ForeignKey, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base


def _enum(e):
    return Enum(e, values_callable=lambda x: [i.value for i in x], native_enum=False)


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class FileFormat(str, enum.Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_format: Mapped[FileFormat] = mapped_column(_enum(FileFormat), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[DatasetStatus] = mapped_column(_enum(DatasetStatus), default=DatasetStatus.PENDING)

    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    null_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duplicate_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    schema_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    profile_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_profiled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="datasets")
    columns: Mapped[list["DatasetColumn"]] = relationship(
        "DatasetColumn", back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetColumn.position"
    )
    quality_reports: Mapped[list["QualityReport"]] = relationship(
        "QualityReport", back_populates="dataset", cascade="all, delete-orphan"
    )


class ColumnDataType(str, enum.Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    UNKNOWN = "unknown"


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    data_type: Mapped[ColumnDataType] = mapped_column(_enum(ColumnDataType), nullable=False)
    nullable: Mapped[bool] = mapped_column(Boolean, default=True)

    null_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    unique_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    min_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    std_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    value_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="columns")

import enum
import uuid
from sqlalchemy import String, Integer, BigInteger, Float, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base


class QualitySeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class QualityIssueType(str, enum.Enum):
    MISSING_VALUES = "missing_values"
    DUPLICATES = "duplicates"
    INVALID_TYPE = "invalid_type"
    INVALID_FORMAT = "invalid_format"
    OUTLIER = "outlier"
    SCHEMA_DRIFT = "schema_drift"
    CONSTRAINT_VIOLATION = "constraint_violation"


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    uniqueness_score: Mapped[float] = mapped_column(Float, nullable=False)
    validity_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Counts
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    passed_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failed_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)

    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="quality_reports")
    issues: Mapped[list["QualityIssue"]] = relationship(
        "QualityIssue", back_populates="report", cascade="all, delete-orphan"
    )


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("quality_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_type: Mapped[QualityIssueType] = mapped_column(Enum(QualityIssueType), nullable=False)
    severity: Mapped[QualitySeverity] = mapped_column(Enum(QualitySeverity), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_rows: Mapped[int] = mapped_column(BigInteger, default=0)
    affected_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    sample_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped["QualityReport"] = relationship("QualityReport", back_populates="issues")

"""
Development seed script — creates a demo org, users, datasets, pipelines, and runs.
Run: python database/seeds/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import uuid
import random
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileFormat, ColumnDataType
from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, PipelineStatus, RunStatus, NodeType
from app.models.quality import QualityReport, QualityIssue, QualitySeverity, QualityIssueType
from app.models.alert import Alert, AlertConditionType, AlertSeverity, AlertStatus
from app.models.activity import ActivityLog
from app.db.base import Base

sync_url = settings.effective_sync_database_url
engine_kwargs = {"connect_args": {"check_same_thread": False}} if sync_url.startswith("sqlite") else {}
engine = create_engine(sync_url, **engine_kwargs)
Session = sessionmaker(engine)

Base.metadata.create_all(engine)

with Session() as db:
    # Users
    users_data = [
        ("shyam@dataflow.io", "Shyam Kumar", True),
        ("alice@dataflow.io", "Alice Chen", False),
        ("bob@dataflow.io", "Bob Martinez", False),
    ]
    users = []
    for email, name, is_owner in users_data:
        existing = db.query(User).filter_by(email=email).first()
        if not existing:
            u = User(email=email, full_name=name, hashed_password=hash_password("dataflow123"), is_active=True)
            db.add(u)
            users.append(u)
        else:
            users.append(existing)
    db.flush()

    # Organization
    org = db.query(Organization).filter_by(slug="acme-corp-demo").first()
    if not org:
        org = Organization(name="Acme Corp", slug="acme-corp-demo", description="Demo data platform workspace")
        db.add(org)
        db.flush()

        roles = [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.MEMBER]
        for u, role in zip(users, roles):
            db.add(OrganizationMember(organization_id=org.id, user_id=u.id, role=role))
        db.flush()

    owner = users[0]

    # Datasets (metadata only — no actual files in seed)
    datasets_meta = [
        ("Sales Transactions 2024", "csv", 1820000, 250421, 12, 18420, 312),
        ("Customer Master Data", "csv", 450000, 120312, 8, 3240, 98),
        ("Inventory Records", "excel", 280000, 82100, 10, 5120, 241),
        ("Marketing Campaigns", "json", 95000, 34500, 6, 890, 12),
        ("Support Tickets Q1", "csv", 62000, 18900, 9, 2340, 67),
    ]
    datasets = []
    for name, fmt_str, file_size, rows, cols, null_cnt, dup_cnt in datasets_meta:
        existing = db.query(Dataset).filter_by(name=name, organization_id=org.id).first()
        if not existing:
            fmt = {"csv": FileFormat.CSV, "json": FileFormat.JSON, "excel": FileFormat.EXCEL}[fmt_str]
            d = Dataset(
                organization_id=org.id,
                created_by=owner.id,
                name=name,
                file_format=fmt,
                file_path=f"/seed/placeholder/{name.lower().replace(' ', '_')}.{fmt_str}",
                file_size_bytes=file_size,
                status=DatasetStatus.READY,
                row_count=rows,
                column_count=cols,
                null_count=null_cnt,
                duplicate_count=dup_cnt,
                last_profiled_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
                schema_snapshot={"id": "integer", "amount": "float", "date": "datetime", "status": "string"},
                profile_data={"row_count": rows, "column_count": cols},
            )
            db.add(d)
            datasets.append(d)
        else:
            datasets.append(existing)
    db.flush()

    # Quality reports
    for d in datasets:
        existing = db.query(QualityReport).filter_by(dataset_id=d.id).first()
        if not existing:
            score = round(random.uniform(82, 99), 1)
            qr = QualityReport(
                dataset_id=d.id,
                created_by=owner.id,
                overall_score=score,
                completeness_score=round(score + random.uniform(-3, 3), 1),
                uniqueness_score=round(score + random.uniform(-5, 5), 1),
                validity_score=round(score + random.uniform(-4, 4), 1),
                consistency_score=round(score + random.uniform(-2, 2), 1),
                total_rows=d.row_count or 10000,
                passed_rows=int((d.row_count or 10000) * (score / 100)),
                failed_rows=int((d.row_count or 10000) * (1 - score / 100)),
                issue_count=random.randint(1, 5),
            )
            db.add(qr)
            db.flush()
            # Add sample issues
            issue_types = [QualityIssueType.MISSING_VALUES, QualityIssueType.DUPLICATES, QualityIssueType.OUTLIER]
            for issue_type in random.sample(issue_types, min(2, len(issue_types))):
                db.add(QualityIssue(
                    report_id=qr.id,
                    issue_type=issue_type,
                    severity=random.choice([QualitySeverity.WARNING, QualitySeverity.ERROR]),
                    column_name="amount" if issue_type == QualityIssueType.OUTLIER else None,
                    description=f"Sample {issue_type} detected in dataset",
                    affected_rows=random.randint(100, 5000),
                    affected_percentage=round(random.uniform(0.1, 5.0), 2),
                ))

    # Pipelines
    pipelines_data = [
        ("Sales ETL Pipeline", "Extract, validate and transform sales data"),
        ("Customer 360 Pipeline", "Merge and enrich customer records"),
        ("Inventory Sync Pipeline", "Sync inventory from ERP system"),
    ]
    pipelines = []
    for pname, pdesc in pipelines_data:
        existing = db.query(Pipeline).filter_by(name=pname, organization_id=org.id).first()
        if not existing:
            p = Pipeline(
                organization_id=org.id,
                created_by=owner.id,
                name=pname,
                description=pdesc,
                status=PipelineStatus.ACTIVE,
                last_run_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24)),
                last_run_status=random.choice([RunStatus.SUCCESS, RunStatus.WARNING]),
            )
            db.add(p)
            db.flush()

            # Add nodes
            source_id = str(uuid.uuid4())
            validate_id = str(uuid.uuid4())
            output_id = str(uuid.uuid4())

            if datasets:
                src_config = {
                    "file_path": datasets[0].file_path,
                    "file_format": datasets[0].file_format,
                }
            else:
                src_config = {}

            nodes = [
                PipelineNode(id=source_id, pipeline_id=p.id, node_type=NodeType.SOURCE, label="Source Data", config=src_config, position_x=100, position_y=200),
                PipelineNode(id=validate_id, pipeline_id=p.id, node_type=NodeType.VALIDATION, label="Validate", config={"rules": [{"column": "id", "check": "not_null"}]}, position_x=350, position_y=200),
                PipelineNode(id=output_id, pipeline_id=p.id, node_type=NodeType.OUTPUT, label="Output", config={}, position_x=600, position_y=200),
            ]
            for n in nodes:
                db.add(n)
            db.flush()

            edges = [
                PipelineEdge(pipeline_id=p.id, source_node_id=source_id, target_node_id=validate_id),
                PipelineEdge(pipeline_id=p.id, source_node_id=validate_id, target_node_id=output_id),
            ]
            for e in edges:
                db.add(e)

            # Add runs
            for i in range(5):
                run_status = random.choice([RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.WARNING, RunStatus.FAILED])
                run = PipelineRun(
                    pipeline_id=p.id,
                    triggered_by=owner.id,
                    status=run_status,
                    input_records=random.randint(50000, 300000),
                    output_records=random.randint(45000, 295000),
                    failed_records=random.randint(0, 500),
                    duration_seconds=round(random.uniform(5, 120), 1),
                    current_stage="complete",
                    started_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168)),
                    completed_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 167)),
                )
                db.add(run)
            pipelines.append(p)
        else:
            pipelines.append(existing)

    # Alerts
    alert_data = [
        ("Low Quality Score Alert", AlertConditionType.QUALITY_SCORE_BELOW, 85.0),
        ("High Missing Values", AlertConditionType.MISSING_VALUES_ABOVE, 5.0),
        ("Pipeline Failure Alert", AlertConditionType.PIPELINE_FAILURE, None),
    ]
    for aname, ctype, threshold in alert_data:
        existing = db.query(Alert).filter_by(name=aname, organization_id=org.id).first()
        if not existing:
            db.add(Alert(
                organization_id=org.id,
                created_by=owner.id,
                name=aname,
                condition_type=ctype,
                threshold=threshold,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.ACTIVE,
            ))

    # Activity logs
    actions = [
        ("dataset.uploaded", "dataset", "Sales Transactions 2024"),
        ("pipeline.created", "pipeline", "Sales ETL Pipeline"),
        ("pipeline.executed", "pipeline", "Customer 360 Pipeline"),
        ("dataset.profiled", "dataset", "Customer Master Data"),
        ("alert.triggered", "alert", "Low Quality Score Alert"),
        ("member.invited", "user", "alice@dataflow.io"),
        ("report.created", "report", "Monthly Sales Report"),
        ("api_key.created", "api_key", "Production Key"),
    ]
    for action, rtype, rname in actions:
        db.add(ActivityLog(
            organization_id=org.id,
            user_id=owner.id,
            action=action,
            resource_type=rtype,
            resource_name=rname,
            details={"source": "seed"},
        ))

    db.commit()
    print("[OK] Seed data inserted successfully")
    print(f"  Organization: {org.name} (id={org.id})")
    print(f"  Owner login: shyam@dataflow.io / dataflow123")

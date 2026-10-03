"""Seed dev data into SQLite — run after create_tables.py"""
import asyncio, sys, os, uuid, random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.dataset import Dataset, DatasetStatus, FileFormat
from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, PipelineStatus, RunStatus, NodeType
from app.models.quality import QualityReport, QualityIssue, QualitySeverity, QualityIssueType
from app.models.alert import Alert, AlertConditionType, AlertSeverity, AlertStatus
from app.models.activity import ActivityLog

engine = create_async_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
Session = async_sessionmaker(engine, expire_on_commit=False)


async def main():
    async with Session() as db:
        # ── Users ──────────────────────────────────────────────────────────
        existing = await db.execute(select(User).where(User.email == "shyam@dataflow.io"))
        if existing.scalar_one_or_none():
            print("Seed data already exists -- skipping")
            return

        owner = User(email="shyam@dataflow.io", full_name="Shyam Patil", hashed_password=hash_password("dataflow123"))
        alice = User(email="alice@dataflow.io",  full_name="Alice Chen",   hashed_password=hash_password("dataflow123"))
        bob   = User(email="bob@dataflow.io",    full_name="Bob Martinez", hashed_password=hash_password("dataflow123"))
        db.add_all([owner, alice, bob])
        await db.flush()

        # ── Organization ───────────────────────────────────────────────────
        org = Organization(name="Acme Analytics", slug="acme-analytics", description="Demo data platform workspace")
        db.add(org)
        await db.flush()

        db.add_all([
            OrganizationMember(organization_id=org.id, user_id=owner.id, role=OrgRole.OWNER),
            OrganizationMember(organization_id=org.id, user_id=alice.id, role=OrgRole.ADMIN),
            OrganizationMember(organization_id=org.id, user_id=bob.id,   role=OrgRole.MEMBER),
        ])

        # ── Datasets (metadata only — no real files for seed) ──────────────
        ds_data = [
            ("Sales Transactions 2024", FileFormat.CSV,   1_820_421, 14, 450_000),
            ("Customer Master Data",    FileFormat.CSV,     120_312,  8,  92_000),
            ("Inventory Records",       FileFormat.EXCEL,    82_100, 10, 280_000),
            ("Marketing Campaigns",     FileFormat.JSON,     34_500,  6,  95_000),
            ("Support Tickets Q1",      FileFormat.CSV,      18_900,  9,  62_000),
        ]
        datasets = []
        for name, fmt, rows, cols, size in ds_data:
            d = Dataset(
                organization_id=org.id, created_by=owner.id,
                name=name, file_format=fmt,
                file_path=f"./uploads/seed_{name.lower().replace(' ','_')}.{fmt.value}",
                file_size_bytes=size, status=DatasetStatus.READY,
                row_count=rows, column_count=cols,
                null_count=int(rows * 0.02), duplicate_count=int(rows * 0.005),
                last_profiled_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1,48)),
                schema_snapshot={"id":"integer","name":"string","amount":"float","date":"datetime","status":"string"},
            )
            db.add(d)
            datasets.append(d)
        await db.flush()

        # ── Quality reports ────────────────────────────────────────────────
        for d in datasets:
            score = round(random.uniform(84, 99), 1)
            qr = QualityReport(
                dataset_id=d.id, created_by=owner.id,
                overall_score=score,
                completeness_score=min(100, score + random.uniform(-3,3)),
                uniqueness_score=min(100, score + random.uniform(-5,5)),
                validity_score=min(100, score + random.uniform(-4,4)),
                consistency_score=min(100, score + random.uniform(-2,2)),
                total_rows=d.row_count, passed_rows=int(d.row_count*(score/100)),
                failed_rows=int(d.row_count*(1-score/100)), issue_count=random.randint(1,4),
            )
            db.add(qr)
            await db.flush()
            db.add(QualityIssue(
                report_id=qr.id, issue_type=QualityIssueType.MISSING_VALUES,
                severity=QualitySeverity.WARNING, column_name="amount",
                description=f"Column 'amount' has {int(d.row_count*0.02):,} missing values",
                affected_rows=int(d.row_count*0.02), affected_percentage=2.0,
                suggestion="Impute with median or remove rows",
            ))
            if score < 92:
                db.add(QualityIssue(
                    report_id=qr.id, issue_type=QualityIssueType.DUPLICATES,
                    severity=QualitySeverity.ERROR, column_name=None,
                    description=f"Dataset contains {int(d.row_count*0.005):,} duplicate rows",
                    affected_rows=int(d.row_count*0.005), affected_percentage=0.5,
                    suggestion="Run deduplication step in pipeline",
                ))

        # ── Pipelines ─────────────────────────────────────────────────────
        pl_defs = [
            ("Sales ETL Pipeline",    "Extract, validate and transform sales transactions"),
            ("Customer 360 Pipeline", "Merge and enrich customer records from multiple sources"),
            ("Inventory Sync",        "Sync inventory records and detect schema drift"),
        ]
        for pname, pdesc in pl_defs:
            p = Pipeline(
                organization_id=org.id, created_by=owner.id,
                name=pname, description=pdesc, status=PipelineStatus.ACTIVE,
                last_run_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1,24)),
                last_run_status=random.choice([RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.WARNING]),
            )
            db.add(p)
            await db.flush()

            src_id = str(uuid.uuid4())
            val_id = str(uuid.uuid4())
            out_id = str(uuid.uuid4())
            db.add_all([
                PipelineNode(id=src_id, pipeline_id=p.id, node_type=NodeType.SOURCE,     label="Source Data",  config={"file_format":"csv"}, position_x=100, position_y=150),
                PipelineNode(id=val_id, pipeline_id=p.id, node_type=NodeType.VALIDATION, label="Validate",     config={"rules":[]},          position_x=350, position_y=150),
                PipelineNode(id=out_id, pipeline_id=p.id, node_type=NodeType.OUTPUT,     label="Output",       config={},                    position_x=600, position_y=150),
            ])
            await db.flush()
            db.add_all([
                PipelineEdge(pipeline_id=p.id, source_node_id=src_id, target_node_id=val_id),
                PipelineEdge(pipeline_id=p.id, source_node_id=val_id, target_node_id=out_id),
            ])

            for i in range(6):
                st = random.choice([RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.WARNING, RunStatus.FAILED])
                inp = random.randint(50_000, 300_000)
                db.add(PipelineRun(
                    pipeline_id=p.id, triggered_by=owner.id, status=st,
                    input_records=inp, output_records=int(inp*0.97),
                    failed_records=int(inp*0.03),
                    duration_seconds=round(random.uniform(5,120),1),
                    current_stage="complete",
                    started_at=datetime.now(timezone.utc)-timedelta(hours=random.randint(1,200)),
                    completed_at=datetime.now(timezone.utc)-timedelta(hours=random.randint(1,199)),
                ))

        # ── Alerts ────────────────────────────────────────────────────────
        db.add_all([
            Alert(organization_id=org.id, created_by=owner.id, name="Low Quality Score",
                  condition_type=AlertConditionType.QUALITY_SCORE_BELOW, threshold=85.0,
                  severity=AlertSeverity.HIGH, status=AlertStatus.ACTIVE),
            Alert(organization_id=org.id, created_by=owner.id, name="Pipeline Failure",
                  condition_type=AlertConditionType.PIPELINE_FAILURE,
                  severity=AlertSeverity.CRITICAL, status=AlertStatus.ACTIVE),
            Alert(organization_id=org.id, created_by=owner.id, name="High Missing Values",
                  condition_type=AlertConditionType.MISSING_VALUES_ABOVE, threshold=5.0,
                  severity=AlertSeverity.MEDIUM, status=AlertStatus.ACTIVE),
        ])

        # ── Activity logs ──────────────────────────────────────────────────
        actions = [
            ("dataset.uploaded", "dataset", "Sales Transactions 2024"),
            ("pipeline.created", "pipeline", "Sales ETL Pipeline"),
            ("pipeline.executed","pipeline", "Customer 360 Pipeline"),
            ("dataset.profiled", "dataset",  "Customer Master Data"),
            ("member.invited",   "user",     "alice@dataflow.io"),
            ("alert.created",    "alert",    "Low Quality Score"),
            ("api_key.created",  "api_key",  "Production Key"),
            ("report.created",   "report",   "Monthly Sales Report"),
        ]
        for i, (action, rtype, rname) in enumerate(actions):
            db.add(ActivityLog(
                organization_id=org.id, user_id=owner.id,
                action=action, resource_type=rtype, resource_name=rname,
                created_at=datetime.now(timezone.utc)-timedelta(hours=i*3),
            ))

        await db.commit()
        print("Seed complete!")
        print("  Login: shyam@dataflow.io / dataflow123")
        print(f"  Org:   {org.name}  (id={org.id})")

asyncio.run(main())

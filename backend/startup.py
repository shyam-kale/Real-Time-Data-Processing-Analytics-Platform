"""Initialize database on startup — always uses SQLite"""
import asyncio
import os
import sys

# Force SQLite before any imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dataflow.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./dataflow.db"

sys.path.insert(0, os.path.dirname(__file__))


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(
        "sqlite+aiosqlite:///./dataflow.db",
        connect_args={"check_same_thread": False}
    )

    # Import all models so metadata is populated
    import app.models  # noqa: F401
    from app.db.base import Base

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        # Check if already seeded
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count > 0:
            print("✅ Already seeded, skipping")
            await engine.dispose()
            return

        from app.core.security import hash_password
        pwd_hash = hash_password("dataflow123")

        # ── Organization ──────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
            VALUES ('org-1', 'DataFlow Demo', 'dataflow-demo', 'Demo organization for DataFlow platform', 1, datetime('now'), datetime('now'))
        """))

        # ── User ──────────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO users (id, email, full_name, hashed_password, is_active, is_superuser, created_at, updated_at)
            VALUES ('user-1', 'shyam@dataflow.io', 'Shyam Patil', :pwd, 1, 1, datetime('now'), datetime('now'))
        """), {"pwd": pwd_hash})

        # ── Member ────────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO organization_members (id, user_id, organization_id, role, joined_at)
            VALUES ('member-1', 'user-1', 'org-1', 'owner', datetime('now'))
        """))

        # ── Datasets ─────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO datasets (id, organization_id, created_by, name, description, file_format, file_path, file_size_bytes, status, row_count, column_count, null_count, duplicate_count, tags, created_at, updated_at)
            VALUES
            ('ds-1', 'org-1', 'user-1', 'Customer Transactions 2024', 'Monthly customer transaction records', 'csv', '/data/transactions.csv', 2048000, 'ready', 150000, 12, 320, 45, 'finance,customers', datetime('now', '-5 days'), datetime('now', '-5 days')),
            ('ds-2', 'org-1', 'user-1', 'Product Inventory', 'Current product inventory snapshot', 'excel', '/data/inventory.xlsx', 512000, 'ready', 8500, 8, 12, 3, 'inventory,products', datetime('now', '-3 days'), datetime('now', '-3 days')),
            ('ds-3', 'org-1', 'user-1', 'Web Analytics Events', 'User clickstream and page view events', 'json', '/data/events.json', 10240000, 'ready', 500000, 15, 1200, 890, 'analytics,web', datetime('now', '-2 days'), datetime('now', '-2 days')),
            ('ds-4', 'org-1', 'user-1', 'HR Employee Data', 'Employee records and performance metrics', 'csv', '/data/employees.csv', 256000, 'processing', 2400, 20, 8, 0, 'hr,people', datetime('now', '-1 days'), datetime('now', '-1 days')),
            ('ds-5', 'org-1', 'user-1', 'Sales Forecast Q1', 'Quarterly sales forecast data', 'csv', '/data/forecast.csv', 128000, 'pending', NULL, NULL, NULL, NULL, 'sales,forecast', datetime('now'), datetime('now'))
        """))

        # ── Pipelines ─────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO pipelines (id, organization_id, created_by, name, description, status, schedule, tags, created_at, updated_at, last_run_at, last_run_status)
            VALUES
            ('pl-1', 'org-1', 'user-1', 'Transaction ETL', 'Extract, transform and load customer transactions', 'active', '0 2 * * *', 'etl,finance', datetime('now', '-7 days'), datetime('now', '-1 days'), datetime('now', '-1 days'), 'success'),
            ('pl-2', 'org-1', 'user-1', 'Inventory Sync', 'Sync product inventory from ERP system', 'active', '0 6 * * 1', 'inventory,sync', datetime('now', '-5 days'), datetime('now', '-2 days'), datetime('now', '-2 days'), 'success'),
            ('pl-3', 'org-1', 'user-1', 'Analytics Aggregator', 'Aggregate web analytics events into summaries', 'active', '0 * * * *', 'analytics,aggregation', datetime('now', '-4 days'), datetime('now'), datetime('now'), 'running'),
            ('pl-4', 'org-1', 'user-1', 'Data Quality Monitor', 'Run quality checks on all active datasets', 'draft', NULL, 'quality,monitoring', datetime('now', '-2 days'), datetime('now', '-2 days'), NULL, NULL),
            ('pl-5', 'org-1', 'user-1', 'Sales Report Generator', 'Generate weekly sales reports', 'archived', '0 8 * * 1', 'sales,reports', datetime('now', '-10 days'), datetime('now', '-3 days'), datetime('now', '-3 days'), 'failed')
        """))

        # ── Pipeline Runs ────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO pipeline_runs (id, pipeline_id, triggered_by, status, input_records, output_records, failed_records, duration_seconds, started_at, completed_at, created_at)
            VALUES
            ('run-1',  'pl-1', 'user-1', 'success',   150000, 149655, 345,  42.3, datetime('now', '-1 days', '-5 minutes'), datetime('now', '-1 days'), datetime('now', '-1 days')),
            ('run-2',  'pl-1', 'user-1', 'success',   148200, 147900, 300,  38.1, datetime('now', '-2 days', '-5 minutes'), datetime('now', '-2 days'), datetime('now', '-2 days')),
            ('run-3',  'pl-1', 'user-1', 'failed',    150500, 0,      150500, 5.2, datetime('now', '-3 days', '-5 minutes'), datetime('now', '-3 days'), datetime('now', '-3 days')),
            ('run-4',  'pl-2', 'user-1', 'success',   8500,   8498,   2,    12.7, datetime('now', '-2 days', '-5 minutes'), datetime('now', '-2 days'), datetime('now', '-2 days')),
            ('run-5',  'pl-3', 'user-1', 'running',   500000, NULL,   NULL, NULL, datetime('now', '-10 minutes'), NULL, datetime('now', '-10 minutes')),
            ('run-6',  'pl-1', 'user-1', 'success',   149000, 148700, 300,  40.5, datetime('now', '-4 days', '-5 minutes'), datetime('now', '-4 days'), datetime('now', '-4 days')),
            ('run-7',  'pl-5', 'user-1', 'failed',    12000,  0,      12000, 8.9, datetime('now', '-3 days', '-5 minutes'), datetime('now', '-3 days'), datetime('now', '-3 days')),
            ('run-8',  'pl-2', 'user-1', 'success',   8200,   8200,   0,    11.3, datetime('now', '-9 days', '-5 minutes'), datetime('now', '-9 days'), datetime('now', '-9 days')),
            ('run-9',  'pl-1', 'user-1', 'success',   147500, 147200, 300,  39.8, datetime('now', '-5 days', '-5 minutes'), datetime('now', '-5 days'), datetime('now', '-5 days')),
            ('run-10', 'pl-1', 'user-1', 'warning',   150200, 149100, 1100, 44.2, datetime('now', '-6 days', '-5 minutes'), datetime('now', '-6 days'), datetime('now', '-6 days'))
        """))

        # ── Reports ──────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO reports (id, organization_id, created_by, name, description, config, is_public, tags, created_at, updated_at)
            VALUES
            ('rpt-1', 'org-1', 'user-1', 'Monthly Data Quality Summary', 'Overview of data quality scores across all datasets', '{}', 1, 'quality,monthly', datetime('now', '-5 days'), datetime('now', '-5 days')),
            ('rpt-2', 'org-1', 'user-1', 'Transaction Pipeline Health', 'Performance metrics for transaction ETL pipeline', '{}', 0, 'pipeline,health', datetime('now', '-3 days'), datetime('now', '-3 days')),
            ('rpt-3', 'org-1', 'user-1', 'Dataset Growth Trends', 'Track dataset size and record count growth over time', '{}', 1, 'growth,trends', datetime('now', '-1 days'), datetime('now', '-1 days'))
        """))

        # ── Alerts ───────────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO alerts (id, organization_id, created_by, name, description, condition_type, threshold, dataset_id, pipeline_id, severity, status, notification_channels, created_at, updated_at)
            VALUES
            ('alt-1', 'org-1', 'user-1', 'High Null Rate Alert', 'Trigger when null values exceed 5%', 'missing_values_above', 5.0, 'ds-1', NULL, 'high', 'active', '[]', datetime('now', '-5 days'), datetime('now', '-5 days')),
            ('alt-2', 'org-1', 'user-1', 'Pipeline Failure Monitor', 'Alert on any pipeline failure', 'pipeline_failure', NULL, NULL, 'pl-1', 'critical', 'active', '[]', datetime('now', '-4 days'), datetime('now', '-4 days')),
            ('alt-3', 'org-1', 'user-1', 'Quality Score Drop', 'Alert when quality score falls below 80', 'quality_score_below', 80.0, 'ds-3', NULL, 'medium', 'active', '[]', datetime('now', '-3 days'), datetime('now', '-3 days')),
            ('alt-4', 'org-1', 'user-1', 'Duplicate Rate Warning', 'Warn when duplicate rows exceed 2%', 'duplicate_percentage_above', 2.0, 'ds-2', NULL, 'low', 'inactive', '[]', datetime('now', '-2 days'), datetime('now', '-2 days'))
        """))

        # ── Activity Logs ────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO activity_logs (id, organization_id, user_id, action, resource_type, resource_id, resource_name, created_at)
            VALUES
            ('act-1',  'org-1', 'user-1', 'dataset.uploaded',   'dataset',  'ds-1', 'Customer Transactions 2024',  datetime('now', '-5 days')),
            ('act-2',  'org-1', 'user-1', 'pipeline.created',   'pipeline', 'pl-1', 'Transaction ETL',             datetime('now', '-7 days')),
            ('act-3',  'org-1', 'user-1', 'pipeline.run',       'pipeline', 'pl-1', 'Transaction ETL',             datetime('now', '-1 days')),
            ('act-4',  'org-1', 'user-1', 'dataset.uploaded',   'dataset',  'ds-2', 'Product Inventory',           datetime('now', '-3 days')),
            ('act-5',  'org-1', 'user-1', 'report.created',     'report',   'rpt-1','Monthly Data Quality Summary', datetime('now', '-5 days')),
            ('act-6',  'org-1', 'user-1', 'alert.created',      'alert',    'alt-1','High Null Rate Alert',         datetime('now', '-5 days')),
            ('act-7',  'org-1', 'user-1', 'pipeline.failed',    'pipeline', 'pl-1', 'Transaction ETL',             datetime('now', '-3 days')),
            ('act-8',  'org-1', 'user-1', 'dataset.uploaded',   'dataset',  'ds-3', 'Web Analytics Events',        datetime('now', '-2 days')),
            ('act-9',  'org-1', 'user-1', 'pipeline.run',       'pipeline', 'pl-2', 'Inventory Sync',              datetime('now', '-2 days')),
            ('act-10', 'org-1', 'user-1', 'user.registered',    'user',     'user-1','Shyam Patil',                datetime('now', '-7 days'))
        """))

        await db.commit()
        print("✅ Demo data seeded successfully:")
        print("   📧 Email:    shyam@dataflow.io")
        print("   🔑 Password: dataflow123")
        print("   📊 5 datasets, 5 pipelines, 10 runs, 3 reports, 4 alerts, 10 activity logs")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

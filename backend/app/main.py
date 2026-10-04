import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import get_db
from app.api.v1.routes import (
    auth, datasets, pipelines, runs, analytics,
    reports, alerts, team, api_keys, activity, overview, ws
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # ── Auto-create tables and seed demo data on every startup ────────────────
    try:
        from app.db.base import engine, Base
        import app.models  # noqa: ensure all models registered
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from app.db.base import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            user_count = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()
            ds_count = (await db.execute(text("SELECT COUNT(*) FROM datasets"))).scalar()

            if user_count == 0:
                from app.core.security import hash_password
                pwd = hash_password("dataflow123")
                await db.execute(text("INSERT INTO organizations (id,name,slug,description,is_active,created_at,updated_at) VALUES ('org-1','DataFlow Demo','dataflow-demo','Demo org',1,datetime('now'),datetime('now'))"))
                await db.execute(text("INSERT INTO users (id,email,full_name,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES ('user-1','shyam@dataflow.io','Shyam Patil',:pwd,1,1,datetime('now'),datetime('now'))"), {"pwd": pwd})
                await db.execute(text("INSERT INTO organization_members (id,user_id,organization_id,role,joined_at) VALUES ('member-1','user-1','org-1','owner',datetime('now'))"))
                await db.commit()
                print("✅ User seeded")

            if ds_count == 0:
                await db.execute(text("""INSERT INTO datasets (id,organization_id,created_by,name,description,file_format,file_path,file_size_bytes,status,row_count,column_count,null_count,duplicate_count,tags,created_at,updated_at) VALUES
                    ('ds-1','org-1','user-1','Customer Transactions 2024','Monthly transaction records','csv','/data/t.csv',2048000,'ready',150000,12,320,45,'finance,customers',datetime('now','-5 days'),datetime('now','-5 days')),
                    ('ds-2','org-1','user-1','Product Inventory','Inventory snapshot','excel','/data/i.xlsx',512000,'ready',8500,8,12,3,'inventory,products',datetime('now','-3 days'),datetime('now','-3 days')),
                    ('ds-3','org-1','user-1','Web Analytics Events','Clickstream events','json','/data/e.json',10240000,'ready',500000,15,1200,890,'analytics,web',datetime('now','-2 days'),datetime('now','-2 days')),
                    ('ds-4','org-1','user-1','HR Employee Data','Employee records','csv','/data/hr.csv',256000,'processing',2400,20,8,0,'hr,people',datetime('now','-1 days'),datetime('now','-1 days')),
                    ('ds-5','org-1','user-1','Sales Forecast Q1','Sales forecast','csv','/data/s.csv',128000,'pending',NULL,NULL,NULL,NULL,'sales,forecast',datetime('now'),datetime('now'))"""))
                await db.execute(text("""INSERT INTO pipelines (id,organization_id,created_by,name,description,status,schedule,tags,created_at,updated_at,last_run_at,last_run_status) VALUES
                    ('pl-1','org-1','user-1','Transaction ETL','ETL pipeline','active','0 2 * * *','etl,finance',datetime('now','-7 days'),datetime('now','-1 days'),datetime('now','-1 days'),'success'),
                    ('pl-2','org-1','user-1','Inventory Sync','Inventory sync','active','0 6 * * 1','inventory,sync',datetime('now','-5 days'),datetime('now','-2 days'),datetime('now','-2 days'),'success'),
                    ('pl-3','org-1','user-1','Analytics Aggregator','Aggregation pipeline','active','0 * * * *','analytics',datetime('now','-4 days'),datetime('now'),datetime('now'),'running'),
                    ('pl-4','org-1','user-1','Data Quality Monitor','Quality checks','draft',NULL,'quality',datetime('now','-2 days'),datetime('now','-2 days'),NULL,NULL),
                    ('pl-5','org-1','user-1','Sales Report Generator','Report generator','archived','0 8 * * 1','sales',datetime('now','-10 days'),datetime('now','-3 days'),datetime('now','-3 days'),'failed')"""))
                await db.execute(text("""INSERT INTO pipeline_runs (id,pipeline_id,triggered_by,status,input_records,output_records,failed_records,duration_seconds,started_at,completed_at,created_at) VALUES
                    ('run-1','pl-1','user-1','success',150000,149655,345,42.3,datetime('now','-1 days','-5 minutes'),datetime('now','-1 days'),datetime('now','-1 days')),
                    ('run-2','pl-1','user-1','success',148200,147900,300,38.1,datetime('now','-2 days','-5 minutes'),datetime('now','-2 days'),datetime('now','-2 days')),
                    ('run-3','pl-1','user-1','failed',150500,0,150500,5.2,datetime('now','-3 days','-5 minutes'),datetime('now','-3 days'),datetime('now','-3 days')),
                    ('run-4','pl-2','user-1','success',8500,8498,2,12.7,datetime('now','-2 days','-5 minutes'),datetime('now','-2 days'),datetime('now','-2 days')),
                    ('run-5','pl-3','user-1','running',500000,NULL,NULL,NULL,datetime('now','-10 minutes'),NULL,datetime('now','-10 minutes'))"""))
                await db.execute(text("""INSERT INTO reports (id,organization_id,created_by,name,description,config,is_public,tags,created_at,updated_at) VALUES
                    ('rpt-1','org-1','user-1','Monthly Data Quality Summary','Quality overview','{}',1,'quality,monthly',datetime('now','-5 days'),datetime('now','-5 days')),
                    ('rpt-2','org-1','user-1','Transaction Pipeline Health','Pipeline metrics','{}',0,'pipeline,health',datetime('now','-3 days'),datetime('now','-3 days')),
                    ('rpt-3','org-1','user-1','Dataset Growth Trends','Growth trends','{}',1,'growth,trends',datetime('now','-1 days'),datetime('now','-1 days'))"""))
                await db.execute(text("""INSERT INTO alerts (id,organization_id,created_by,name,description,condition_type,threshold,dataset_id,pipeline_id,severity,status,notification_channels,created_at,updated_at) VALUES
                    ('alt-1','org-1','user-1','High Null Rate Alert','Nulls exceed 5%','missing_values_above',5.0,'ds-1',NULL,'high','active','[]',datetime('now','-5 days'),datetime('now','-5 days')),
                    ('alt-2','org-1','user-1','Pipeline Failure Monitor','Pipeline failure','pipeline_failure',NULL,NULL,'pl-1','critical','active','[]',datetime('now','-4 days'),datetime('now','-4 days')),
                    ('alt-3','org-1','user-1','Quality Score Drop','Score below 80','quality_score_below',80.0,'ds-3',NULL,'medium','active','[]',datetime('now','-3 days'),datetime('now','-3 days')),
                    ('alt-4','org-1','user-1','Duplicate Rate Warning','Duplicates exceed 2%','duplicate_percentage_above',2.0,'ds-2',NULL,'low','inactive','[]',datetime('now','-2 days'),datetime('now','-2 days'))"""))
                await db.execute(text("""INSERT INTO activity_logs (id,organization_id,user_id,action,resource_type,resource_id,resource_name,created_at) VALUES
                    ('act-1','org-1','user-1','dataset.uploaded','dataset','ds-1','Customer Transactions 2024',datetime('now','-5 days')),
                    ('act-2','org-1','user-1','pipeline.created','pipeline','pl-1','Transaction ETL',datetime('now','-7 days')),
                    ('act-3','org-1','user-1','pipeline.run','pipeline','pl-1','Transaction ETL',datetime('now','-1 days')),
                    ('act-4','org-1','user-1','dataset.uploaded','dataset','ds-2','Product Inventory',datetime('now','-3 days')),
                    ('act-5','org-1','user-1','report.created','report','rpt-1','Monthly Data Quality Summary',datetime('now','-5 days'))"""))
                await db.execute(text("""INSERT INTO dataset_columns (id,dataset_id,name,position,data_type,nullable,null_count,unique_count,min_value,max_value) VALUES
                    ('dc-1-1','ds-1','transaction_id',0,'string',0,0,150000,NULL,NULL),
                    ('dc-1-2','ds-1','customer_id',1,'string',0,0,42000,NULL,NULL),
                    ('dc-1-3','ds-1','amount',2,'float',0,0,149200,'0.5','9999.99'),
                    ('dc-1-4','ds-1','category',3,'string',1,120,18,NULL,NULL),
                    ('dc-1-5','ds-1','transaction_date',4,'datetime',0,0,148000,NULL,NULL),
                    ('dc-1-6','ds-1','status',5,'string',0,0,4,NULL,NULL),
                    ('dc-2-1','ds-2','product_id',0,'string',0,0,8500,NULL,NULL),
                    ('dc-2-2','ds-2','product_name',1,'string',0,0,8490,NULL,NULL),
                    ('dc-2-3','ds-2','category',2,'string',0,0,24,NULL,NULL),
                    ('dc-2-4','ds-2','quantity',3,'integer',0,0,320,'0','9999'),
                    ('dc-2-5','ds-2','unit_price',4,'float',0,0,8490,'0.99','4999.99'),
                    ('dc-3-1','ds-3','event_id',0,'string',0,0,500000,NULL,NULL),
                    ('dc-3-2','ds-3','user_id',1,'string',1,1200,95000,NULL,NULL),
                    ('dc-3-3','ds-3','event_type',3,'string',0,0,12,NULL,NULL),
                    ('dc-3-4','ds-3','page_url',4,'string',0,0,42000,NULL,NULL),
                    ('dc-3-5','ds-3','timestamp',6,'datetime',0,0,500000,NULL,NULL)"""))
                await db.commit()
                print("✅ All demo data seeded")
    except Exception as e:
        print(f"⚠️  DB setup error: {e}")

    # ── Redis websocket relay — silently skip if unavailable ──────────────────
    try:
        from app.websockets.manager import redis_subscriber
        task = asyncio.create_task(redis_subscriber())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except Exception:
        yield


app = FastAPI(
    title="DataFlow API",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────────
API = "/api/v1"
app.include_router(auth.router,      prefix=API)
app.include_router(overview.router,  prefix=API)
app.include_router(datasets.router,  prefix=API)
app.include_router(pipelines.router, prefix=API)
app.include_router(runs.router,      prefix=API)
app.include_router(analytics.router, prefix=API)
app.include_router(reports.router,   prefix=API)
app.include_router(alerts.router,    prefix=API)
app.include_router(team.router,      prefix=API)
app.include_router(api_keys.router,  prefix=API)
app.include_router(activity.router,  prefix=API)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/api/v1/init")
async def init_endpoint(db: AsyncSession = Depends(get_db)):
    """Re-seed the database - always ensures demo data exists"""
    from app.core.security import hash_password

    # Check what exists
    user_count = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()
    ds_count = (await db.execute(text("SELECT COUNT(*) FROM datasets"))).scalar()

    # Get the actual org and user IDs from DB
    if user_count > 0:
        row = (await db.execute(text("SELECT id FROM users WHERE email='shyam@dataflow.io' LIMIT 1"))).fetchone()
        user_id = row[0] if row else 'user-1'
        row2 = (await db.execute(text("SELECT organization_id FROM organization_members WHERE user_id=:uid LIMIT 1"), {"uid": user_id})).fetchone()
        org_id = row2[0] if row2 else 'org-1'
    else:
        user_id = 'user-1'
        org_id = 'org-1'
        pwd = hash_password("dataflow123")
        await db.execute(text("INSERT OR IGNORE INTO organizations (id,name,slug,description,is_active,created_at,updated_at) VALUES ('org-1','DataFlow Demo','dataflow-demo','Demo organization',1,datetime('now'),datetime('now'))"))
        await db.execute(text("INSERT OR IGNORE INTO users (id,email,full_name,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES ('user-1','shyam@dataflow.io','Shyam Patil',:pwd,1,1,datetime('now'),datetime('now'))"), {"pwd": pwd})
        await db.execute(text("INSERT OR IGNORE INTO organization_members (id,user_id,organization_id,role,joined_at) VALUES ('member-1','user-1','org-1','owner',datetime('now'))"))

    if ds_count > 0:
        return {"status": "already seeded", "users": user_count, "datasets": ds_count, "org_id": org_id, "user_id": user_id}

    # Seed datasets using actual org_id and user_id
    await db.execute(text("""INSERT INTO datasets (id,organization_id,created_by,name,description,file_format,file_path,file_size_bytes,status,row_count,column_count,null_count,duplicate_count,tags,created_at,updated_at) VALUES
        ('ds-1',:oid,:uid,'Customer Transactions 2024','Monthly customer transaction records','csv','/data/transactions.csv',2048000,'ready',150000,12,320,45,'finance,customers',datetime('now','-5 days'),datetime('now','-5 days')),
        ('ds-2',:oid,:uid,'Product Inventory','Current product inventory snapshot','excel','/data/inventory.xlsx',512000,'ready',8500,8,12,3,'inventory,products',datetime('now','-3 days'),datetime('now','-3 days')),
        ('ds-3',:oid,:uid,'Web Analytics Events','User clickstream and page view events','json','/data/events.json',10240000,'ready',500000,15,1200,890,'analytics,web',datetime('now','-2 days'),datetime('now','-2 days')),
        ('ds-4',:oid,:uid,'HR Employee Data','Employee records and performance metrics','csv','/data/employees.csv',256000,'processing',2400,20,8,0,'hr,people',datetime('now','-1 days'),datetime('now','-1 days')),
        ('ds-5',:oid,:uid,'Sales Forecast Q1','Quarterly sales forecast data','csv','/data/forecast.csv',128000,'pending',NULL,NULL,NULL,NULL,'sales,forecast',datetime('now'),datetime('now'))"""), {"oid": org_id, "uid": user_id}))

    # Pipelines
    await db.execute(text("""INSERT INTO pipelines (id,organization_id,created_by,name,description,status,schedule,tags,created_at,updated_at,last_run_at,last_run_status) VALUES
        ('pl-1',:oid,:uid,'Transaction ETL','Extract, transform and load customer transactions','active','0 2 * * *','etl,finance',datetime('now','-7 days'),datetime('now','-1 days'),datetime('now','-1 days'),'success'),
        ('pl-2',:oid,:uid,'Inventory Sync','Sync product inventory from ERP system','active','0 6 * * 1','inventory,sync',datetime('now','-5 days'),datetime('now','-2 days'),datetime('now','-2 days'),'success'),
        ('pl-3',:oid,:uid,'Analytics Aggregator','Aggregate web analytics events into summaries','active','0 * * * *','analytics,aggregation',datetime('now','-4 days'),datetime('now'),datetime('now'),'running'),
        ('pl-4',:oid,:uid,'Data Quality Monitor','Run quality checks on all active datasets','draft',NULL,'quality,monitoring',datetime('now','-2 days'),datetime('now','-2 days'),NULL,NULL),
        ('pl-5',:oid,:uid,'Sales Report Generator','Generate weekly sales reports','archived','0 8 * * 1','sales,reports',datetime('now','-10 days'),datetime('now','-3 days'),datetime('now','-3 days'),'failed')"""), {"oid": org_id, "uid": user_id}))

    # Pipeline Runs
    await db.execute(text("""INSERT INTO pipeline_runs (id,pipeline_id,triggered_by,status,input_records,output_records,failed_records,duration_seconds,started_at,completed_at,created_at) VALUES
        ('run-1','pl-1',:uid,'success',150000,149655,345,42.3,datetime('now','-1 days','-5 minutes'),datetime('now','-1 days'),datetime('now','-1 days')),
        ('run-2','pl-1',:uid,'success',148200,147900,300,38.1,datetime('now','-2 days','-5 minutes'),datetime('now','-2 days'),datetime('now','-2 days')),
        ('run-3','pl-1',:uid,'failed',150500,0,150500,5.2,datetime('now','-3 days','-5 minutes'),datetime('now','-3 days'),datetime('now','-3 days')),
        ('run-4','pl-2',:uid,'success',8500,8498,2,12.7,datetime('now','-2 days','-5 minutes'),datetime('now','-2 days'),datetime('now','-2 days')),
        ('run-5','pl-3',:uid,'running',500000,NULL,NULL,NULL,datetime('now','-10 minutes'),NULL,datetime('now','-10 minutes')),
        ('run-6','pl-1',:uid,'success',149000,148700,300,40.5,datetime('now','-4 days','-5 minutes'),datetime('now','-4 days'),datetime('now','-4 days')),
        ('run-7','pl-5',:uid,'failed',12000,0,12000,8.9,datetime('now','-3 days','-5 minutes'),datetime('now','-3 days'),datetime('now','-3 days')),
        ('run-8','pl-2',:uid,'success',8200,8200,0,11.3,datetime('now','-9 days','-5 minutes'),datetime('now','-9 days'),datetime('now','-9 days')),
        ('run-9','pl-1',:uid,'success',147500,147200,300,39.8,datetime('now','-5 days','-5 minutes'),datetime('now','-5 days'),datetime('now','-5 days')),
        ('run-10','pl-1',:uid,'warning',150200,149100,1100,44.2,datetime('now','-6 days','-5 minutes'),datetime('now','-6 days'),datetime('now','-6 days'))"""), {"uid": user_id}))

    # Reports
    await db.execute(text("""INSERT INTO reports (id,organization_id,created_by,name,description,config,is_public,tags,created_at,updated_at) VALUES
        ('rpt-1',:oid,:uid,'Monthly Data Quality Summary','Overview of data quality scores across all datasets','{}',1,'quality,monthly',datetime('now','-5 days'),datetime('now','-5 days')),
        ('rpt-2',:oid,:uid,'Transaction Pipeline Health','Performance metrics for transaction ETL pipeline','{}',0,'pipeline,health',datetime('now','-3 days'),datetime('now','-3 days')),
        ('rpt-3',:oid,:uid,'Dataset Growth Trends','Track dataset size and record count growth over time','{}',1,'growth,trends',datetime('now','-1 days'),datetime('now','-1 days'))"""), {"oid": org_id, "uid": user_id}))

    # Alerts
    await db.execute(text("""INSERT INTO alerts (id,organization_id,created_by,name,description,condition_type,threshold,dataset_id,pipeline_id,severity,status,notification_channels,created_at,updated_at) VALUES
        ('alt-1',:oid,:uid,'High Null Rate Alert','Trigger when null values exceed 5%','missing_values_above',5.0,'ds-1',NULL,'high','active','[]',datetime('now','-5 days'),datetime('now','-5 days')),
        ('alt-2',:oid,:uid,'Pipeline Failure Monitor','Alert on any pipeline failure','pipeline_failure',NULL,NULL,'pl-1','critical','active','[]',datetime('now','-4 days'),datetime('now','-4 days')),
        ('alt-3',:oid,:uid,'Quality Score Drop','Alert when quality score falls below 80','quality_score_below',80.0,'ds-3',NULL,'medium','active','[]',datetime('now','-3 days'),datetime('now','-3 days')),
        ('alt-4',:oid,:uid,'Duplicate Rate Warning','Warn when duplicate rows exceed 2%','duplicate_percentage_above',2.0,'ds-2',NULL,'low','inactive','[]',datetime('now','-2 days'),datetime('now','-2 days'))"""), {"oid": org_id, "uid": user_id}))

    # Activity logs
    await db.execute(text("""INSERT INTO activity_logs (id,organization_id,user_id,action,resource_type,resource_id,resource_name,created_at) VALUES
        ('act-1',:oid,:uid,'dataset.uploaded','dataset','ds-1','Customer Transactions 2024',datetime('now','-5 days')),
        ('act-2',:oid,:uid,'pipeline.created','pipeline','pl-1','Transaction ETL',datetime('now','-7 days')),
        ('act-3',:oid,:uid,'pipeline.run','pipeline','pl-1','Transaction ETL',datetime('now','-1 days')),
        ('act-4',:oid,:uid,'dataset.uploaded','dataset','ds-2','Product Inventory',datetime('now','-3 days')),
        ('act-5',:oid,:uid,'report.created','report','rpt-1','Monthly Data Quality Summary',datetime('now','-5 days')),
        ('act-6',:oid,:uid,'alert.created','alert','alt-1','High Null Rate Alert',datetime('now','-5 days')),
        ('act-7',:oid,:uid,'pipeline.failed','pipeline','pl-1','Transaction ETL',datetime('now','-3 days')),
        ('act-8',:oid,:uid,'dataset.uploaded','dataset','ds-3','Web Analytics Events',datetime('now','-2 days')),
        ('act-9',:oid,:uid,'pipeline.run','pipeline','pl-2','Inventory Sync',datetime('now','-2 days')),
        ('act-10',:oid,:uid,'user.registered','user',:uid,'Shyam Patil',datetime('now','-7 days'))"""), {"oid": org_id, "uid": user_id}))

    # Dataset Columns
    await db.execute(text("""INSERT INTO dataset_columns (id,dataset_id,name,position,data_type,nullable,null_count,unique_count,min_value,max_value) VALUES
        ('dc-1-1','ds-1','transaction_id',0,'string',0,0,150000,NULL,NULL),
        ('dc-1-2','ds-1','customer_id',1,'string',0,0,42000,NULL,NULL),
        ('dc-1-3','ds-1','amount',2,'float',0,0,149200,'0.5','9999.99'),
        ('dc-1-4','ds-1','category',3,'string',1,120,18,NULL,NULL),
        ('dc-1-5','ds-1','transaction_date',4,'datetime',0,0,148000,NULL,NULL),
        ('dc-1-6','ds-1','status',5,'string',0,0,4,NULL,NULL),
        ('dc-1-7','ds-1','channel',6,'string',1,200,3,NULL,NULL),
        ('dc-1-8','ds-1','region',7,'string',1,0,12,NULL,NULL),
        ('dc-1-9','ds-1','currency',8,'string',0,0,5,NULL,NULL),
        ('dc-1-10','ds-1','fee',9,'float',1,45000,8000,'0.0','50.0'),
        ('dc-1-11','ds-1','is_flagged',10,'boolean',0,0,2,NULL,NULL),
        ('dc-1-12','ds-1','notes',11,'string',1,320,80000,NULL,NULL),
        ('dc-2-1','ds-2','product_id',0,'string',0,0,8500,NULL,NULL),
        ('dc-2-2','ds-2','product_name',1,'string',0,0,8490,NULL,NULL),
        ('dc-2-3','ds-2','category',2,'string',0,0,24,NULL,NULL),
        ('dc-2-4','ds-2','quantity',3,'integer',0,0,320,'0','9999'),
        ('dc-2-5','ds-2','unit_price',4,'float',0,0,8490,'0.99','4999.99'),
        ('dc-2-6','ds-2','warehouse',5,'string',1,12,8,NULL,NULL),
        ('dc-2-7','ds-2','last_updated',6,'datetime',0,0,8500,NULL,NULL),
        ('dc-2-8','ds-2','sku',7,'string',0,0,8500,NULL,NULL),
        ('dc-3-1','ds-3','event_id',0,'string',0,0,500000,NULL,NULL),
        ('dc-3-2','ds-3','user_id',1,'string',1,1200,95000,NULL,NULL),
        ('dc-3-3','ds-3','session_id',2,'string',0,0,180000,NULL,NULL),
        ('dc-3-4','ds-3','event_type',3,'string',0,0,12,NULL,NULL),
        ('dc-3-5','ds-3','page_url',4,'string',0,0,42000,NULL,NULL),
        ('dc-3-6','ds-3','duration_ms',5,'integer',1,890,48000,'0','300000'),
        ('dc-3-7','ds-3','timestamp',6,'datetime',0,0,500000,NULL,NULL),
        ('dc-3-8','ds-3','country',7,'string',1,200,85,NULL,NULL),
        ('dc-3-9','ds-3','device_type',8,'string',0,0,4,NULL,NULL),
        ('dc-3-10','ds-3','browser',9,'string',0,0,8,NULL,NULL),
        ('dc-3-11','ds-3','referrer',10,'string',1,280000,18000,NULL,NULL),
        ('dc-3-12','ds-3','is_bounce',11,'boolean',0,0,2,NULL,NULL),
        ('dc-3-13','ds-3','scroll_depth',12,'float',1,400,101,'0.0','1.0'),
        ('dc-3-14','ds-3','clicks',13,'integer',1,0,45,'0','200'),
        ('dc-3-15','ds-3','conversion',14,'boolean',0,0,2,NULL,NULL)"""))

    await db.commit()
    return {"status": "seeded", "email": "shyam@dataflow.io", "password": "dataflow123", "datasets": 5, "pipelines": 5, "runs": 10, "reports": 3, "alerts": 4}


# ── Serve React frontend static files ─────────────────────────────────────────
# main.py is at /app/app/main.py → ../static = /app/static
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
STATIC_DIR = os.path.normpath(STATIC_DIR)

if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Never intercept API or WebSocket routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        index = os.path.join(STATIC_DIR, "index.html")
        if not os.path.isfile(index):
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Frontend not built")
        return FileResponse(index)
else:
    @app.get("/")
    async def root():
        return {"name": settings.APP_NAME, "version": settings.VERSION, "docs": "/docs"}

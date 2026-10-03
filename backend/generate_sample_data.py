"""
Generate real CSV sample files for all seeded datasets.
Run: py generate_sample_data.py
"""
import asyncio, sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dataflow.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./dataflow.db"

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.dataset import Dataset, DatasetStatus
from app.models.organization import Organization

engine = create_async_engine("sqlite+aiosqlite:///./dataflow.db", connect_args={"check_same_thread": False})
Session = async_sessionmaker(engine, expire_on_commit=False)

rng = np.random.default_rng(42)

def gen_sales(n=50000):
    dates = pd.date_range("2024-01-01", "2024-12-31", periods=n)
    statuses = rng.choice(["completed","pending","refunded","failed"], n, p=[0.75,0.12,0.08,0.05])
    categories = rng.choice(["Electronics","Clothing","Food","Books","Sports","Home","Beauty"], n)
    return pd.DataFrame({
        "id":              range(1, n+1),
        "transaction_date": dates.strftime("%Y-%m-%d"),
        "amount":          np.round(rng.uniform(10, 5000, n), 2),
        "status":          statuses,
        "category":        categories,
        "customer_id":     rng.integers(1000, 9999, n),
        "product":         [f"Product_{rng.integers(1,500)}" for _ in range(n)],
        "quantity":        rng.integers(1, 20, n),
        "discount_pct":    np.round(rng.uniform(0, 30, n), 1),
        "region":          rng.choice(["North","South","East","West","Central"], n),
    })

def gen_customers(n=15000):
    tiers = rng.choice(["Bronze","Silver","Gold","Platinum"], n, p=[0.45,0.30,0.18,0.07])
    return pd.DataFrame({
        "id":           range(1, n+1),
        "name":         [f"Customer {i}" for i in range(1, n+1)],
        "email":        [f"user{i}@example.com" for i in range(1, n+1)],
        "city":         rng.choice(["Mumbai","Delhi","Bangalore","Chennai","Hyderabad","Pune","Kolkata"], n),
        "country":      "India",
        "signup_date":  pd.date_range("2020-01-01", "2024-12-31", periods=n).strftime("%Y-%m-%d"),
        "tier":         tiers,
        "total_spend":  np.round(rng.uniform(100, 50000, n), 2),
        "is_active":    rng.choice([True, False], n, p=[0.85, 0.15]),
        "age_group":    rng.choice(["18-25","26-35","36-45","46-55","55+"], n),
    })

def gen_inventory(n=10000):
    return pd.DataFrame({
        "id":           range(1, n+1),
        "product_name": [f"Product {i}" for i in range(1, n+1)],
        "sku":          [f"SKU-{rng.integers(10000,99999)}" for _ in range(n)],
        "category":     rng.choice(["Electronics","Clothing","Food","Books","Sports"], n),
        "quantity":     rng.integers(0, 500, n),
        "unit_price":   np.round(rng.uniform(5, 2000, n), 2),
        "warehouse":    rng.choice(["WH-North","WH-South","WH-East","WH-West"], n),
        "supplier":     rng.choice(["Supplier A","Supplier B","Supplier C","Supplier D"], n),
        "last_updated": pd.date_range("2024-01-01", "2024-12-31", periods=n).strftime("%Y-%m-%d"),
        "reorder_level": rng.integers(10, 100, n),
    })

def gen_campaigns(n=5000):
    channels = rng.choice(["Email","Social","Search","Display","Affiliate"], n)
    return pd.DataFrame({
        "id":            range(1, n+1),
        "campaign_name": [f"Campaign_{i}" for i in range(1, n+1)],
        "channel":       channels,
        "budget":        np.round(rng.uniform(1000, 100000, n), 2),
        "clicks":        rng.integers(100, 50000, n),
        "impressions":   rng.integers(1000, 500000, n),
        "conversions":   rng.integers(10, 5000, n),
        "ctr":           np.round(rng.uniform(0.5, 10, n), 2),
        "start_date":    pd.date_range("2024-01-01", "2024-12-31", periods=n).strftime("%Y-%m-%d"),
        "status":        rng.choice(["active","paused","completed","draft"], n),
    })

def gen_tickets(n=8000):
    priorities = rng.choice(["low","medium","high","critical"], n, p=[0.30,0.40,0.20,0.10])
    statuses   = rng.choice(["open","in_progress","resolved","closed"], n, p=[0.15,0.25,0.35,0.25])
    return pd.DataFrame({
        "id":           range(1, n+1),
        "subject":      [f"Issue with {rng.choice(['login','payment','delivery','product','account'])}" for _ in range(n)],
        "status":       statuses,
        "priority":     priorities,
        "category":     rng.choice(["Technical","Billing","Shipping","Returns","General"], n),
        "created_date": pd.date_range("2024-01-01", "2024-12-31", periods=n).strftime("%Y-%m-%d"),
        "resolved_date":pd.date_range("2024-01-15", "2025-01-15", periods=n).strftime("%Y-%m-%d"),
        "agent":        rng.choice(["Agent A","Agent B","Agent C","Agent D","Agent E"], n),
        "rating":       rng.integers(1, 6, n),
        "resolution_hours": np.round(rng.uniform(0.5, 72, n), 1),
    })

GENERATORS = {
    "Sales Transactions 2024": gen_sales,
    "Customer Master Data":    gen_customers,
    "Inventory Records":       gen_inventory,
    "Marketing Campaigns":     gen_campaigns,
    "Support Tickets Q1":      gen_tickets,
}

async def main():
    async with Session() as db:
        result = await db.execute(select(Organization))
        org = result.scalars().first()
        if not org:
            print("No organization found. Run seed.py first.")
            return

        upload_dir = Path(f"./uploads/{org.id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        for ds_name, gen_fn in GENERATORS.items():
            result = await db.execute(select(Dataset).where(Dataset.name == ds_name))
            ds = result.scalar_one_or_none()
            if not ds:
                print(f"Dataset not found: {ds_name}")
                continue

            print(f"Generating {ds_name}...")
            df = gen_fn()

            # Save to CSV
            file_path = upload_dir / f"{ds.id}.csv"
            df.to_csv(file_path, index=False)

            # Update dataset record
            ds.file_path    = str(file_path)
            ds.file_size_bytes = file_path.stat().st_size
            ds.row_count    = len(df)
            ds.column_count = len(df.columns)
            ds.null_count   = int(df.isnull().sum().sum())
            ds.duplicate_count = int(df.duplicated().sum())
            ds.status       = DatasetStatus.READY
            ds.schema_snapshot = {col: str(df[col].dtype) for col in df.columns}

            print(f"  {len(df):,} rows, {len(df.columns)} cols -> {file_path}")

        await db.commit()
        print("\nAll sample files generated!")
        print("Now run profiling from the Datasets page or via API.")

asyncio.run(main())

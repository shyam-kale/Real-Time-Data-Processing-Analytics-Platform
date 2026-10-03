import asyncio, sys, os
sys.path.insert(0, r'C:\Users\shyam\OneDrive\Desktop\API\backend')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///C:/Users/shyam/OneDrive/Desktop/API/backend/dataflow.db'
os.environ['DATABASE_URL_SYNC'] = 'sqlite:///C:/Users/shyam/OneDrive/Desktop/API/backend/dataflow.db'
import numpy as np, pandas as pd
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.dataset import Dataset, DatasetStatus
from app.models.organization import Organization

engine = create_async_engine('sqlite+aiosqlite:///C:/Users/shyam/OneDrive/Desktop/API/backend/dataflow.db', connect_args={'check_same_thread':False})
Session = async_sessionmaker(engine, expire_on_commit=False)
rng = np.random.default_rng(42)
n = 10000

async def main():
    async with Session() as db:
        org = (await db.execute(select(Organization))).scalars().first()
        upload_dir = Path(f'C:/Users/shyam/OneDrive/Desktop/API/backend/uploads/{org.id}')
        upload_dir.mkdir(parents=True, exist_ok=True)
        datasets = (await db.execute(select(Dataset).where(Dataset.organization_id == org.id))).scalars().all()
        for ds in datasets:
            df = pd.DataFrame({
                'id': range(1, n+1),
                'date': pd.date_range('2024-01-01','2024-12-31',periods=n).strftime('%Y-%m-%d'),
                'amount': np.round(rng.uniform(10, 5000, n), 2),
                'status': rng.choice(['completed','pending','failed','refunded'], n, p=[0.7,0.15,0.1,0.05]),
                'category': rng.choice(['Electronics','Clothing','Food','Books','Sports','Home'], n),
                'region': rng.choice(['North','South','East','West','Central'], n),
                'quantity': rng.integers(1, 50, n).astype(int),
                'rating': rng.integers(1, 6, n).astype(int),
            })
            fp = upload_dir / f'{ds.id}.csv'
            df.to_csv(fp, index=False)
            ds.file_path = str(fp)
            ds.file_size_bytes = fp.stat().st_size
            ds.row_count = len(df)
            ds.column_count = len(df.columns)
            ds.status = DatasetStatus.READY
            ds.schema_snapshot = {'id':'integer','date':'datetime','amount':'float','status':'string','category':'string','region':'string','quantity':'integer','rating':'integer'}
            sys.stdout.write(f'OK: {ds.name} - {len(df)} rows\n')
            sys.stdout.flush()
        await db.commit()
        sys.stdout.write('ALL DONE\n')
        sys.stdout.flush()

asyncio.run(main())

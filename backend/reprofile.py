import asyncio, sys, os
sys.path.insert(0, r'C:\Users\shyam\OneDrive\Desktop\API\backend')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///C:/Users/shyam/OneDrive/Desktop/API/backend/dataflow.db'

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileFormat, ColumnDataType
from app.processing.profiler import profile_dataset
from datetime import datetime, timezone

engine = create_async_engine('sqlite+aiosqlite:///C:/Users/shyam/OneDrive/Desktop/API/backend/dataflow.db', connect_args={'check_same_thread':False})
Session = async_sessionmaker(engine, expire_on_commit=False)
type_map = {'integer':ColumnDataType.INTEGER,'float':ColumnDataType.FLOAT,'string':ColumnDataType.STRING,'boolean':ColumnDataType.BOOLEAN,'datetime':ColumnDataType.DATETIME,'unknown':ColumnDataType.UNKNOWN}

async def main():
    async with Session() as db:
        datasets = (await db.execute(select(Dataset))).scalars().all()
        for ds in datasets:
            # Force CSV format for all (we generated all as CSV)
            ds.file_format = FileFormat.CSV
            try:
                profile = profile_dataset(ds.file_path, FileFormat.CSV)
                ds.row_count = profile['row_count']
                ds.column_count = profile['column_count']
                ds.null_count = profile['null_count']
                ds.duplicate_count = profile['duplicate_count']
                ds.schema_snapshot = profile['schema_snapshot']
                ds.profile_data = {'row_count':profile['row_count'],'column_count':profile['column_count']}
                ds.status = DatasetStatus.READY
                ds.last_profiled_at = datetime.now(timezone.utc)
                old = (await db.execute(select(DatasetColumn).where(DatasetColumn.dataset_id==ds.id))).scalars().all()
                for c in old: await db.delete(c)
                await db.flush()
                for col in profile['columns']:
                    db.add(DatasetColumn(
                        dataset_id=ds.id, name=col['name'], position=col['position'],
                        data_type=type_map.get(col['data_type'], ColumnDataType.STRING),
                        nullable=col['nullable'], null_count=col['null_count'],
                        unique_count=col['unique_count'], min_value=col.get('min_value'),
                        max_value=col.get('max_value'), mean_value=col.get('mean_value'),
                        std_value=col.get('std_value'), sample_values=col.get('sample_values'),
                    ))
                sys.stdout.write(f'OK: {ds.name} - {profile[chr(114)+chr(111)+chr(119)+"_count"]} rows, {profile["column_count"]} cols\n')
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(f'ERR {ds.name}: {e}\n'); sys.stdout.flush()
        await db.commit()
        sys.stdout.write('ALL PROFILED\n'); sys.stdout.flush()

asyncio.run(main())

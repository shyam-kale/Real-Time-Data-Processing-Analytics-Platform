import os
import uuid
import shutil
from typing import Optional, List
from pathlib import Path
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, FileFormat
from app.core.config import settings
from app.services.activity_service import log_activity


ALLOWED_EXTENSIONS = {
    "csv": FileFormat.CSV,
    "json": FileFormat.JSON,
    "xlsx": FileFormat.EXCEL,
    "xls": FileFormat.EXCEL,
}


async def upload_dataset(
    db: AsyncSession,
    org_id: str,
    user_id: str,
    file: UploadFile,
    name: str,
    description: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dataset:
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Use CSV, JSON, or Excel.")

    upload_dir = Path(settings.UPLOAD_DIR) / org_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    file_path = upload_dir / f"{file_id}.{ext}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = file_path.stat().st_size

    dataset = Dataset(
        organization_id=org_id,
        created_by=user_id,
        name=name,
        description=description,
        file_format=ALLOWED_EXTENSIONS[ext],
        file_path=str(file_path),
        file_size_bytes=file_size,
        status=DatasetStatus.PENDING,
        tags=tags,
    )
    db.add(dataset)
    await db.flush()

    await log_activity(db, org_id, user_id, "dataset.uploaded", "dataset", dataset.id, name)

    return dataset


async def list_datasets(
    db: AsyncSession,
    org_id: str,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
) -> tuple[List[Dataset], int]:
    query = select(Dataset).where(Dataset.organization_id == org_id)
    count_query = select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id)

    if search:
        query = query.where(Dataset.name.ilike(f"%{search}%"))
        count_query = count_query.where(Dataset.name.ilike(f"%{search}%"))

    query = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    count_result = await db.execute(count_query)

    return result.scalars().all(), count_result.scalar()


async def get_dataset(db: AsyncSession, dataset_id: str, org_id: str) -> Dataset:
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    return dataset


async def delete_dataset(db: AsyncSession, dataset_id: str, org_id: str, user_id: str) -> None:
    dataset = await get_dataset(db, dataset_id, org_id)
    # Remove physical file
    try:
        if os.path.exists(dataset.file_path):
            os.remove(dataset.file_path)
    except OSError:
        pass
    await log_activity(db, org_id, user_id, "dataset.deleted", "dataset", dataset_id, dataset.name)
    await db.delete(dataset)

import os
import uuid
import shutil
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.dataset import Dataset, DatasetStatus, FileFormat

router = APIRouter(prefix="/orgs/{org_id}/datasets", tags=["datasets"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


def _serialize(d):
    return {
        "id": str(d.id),
        "organization_id": str(d.organization_id),
        "created_by": str(d.created_by),
        "name": d.name,
        "description": d.description,
        "file_format": _fmt(d.file_format),
        "file_size_bytes": d.file_size_bytes or 0,
        "status": _fmt(d.status),
        "row_count": d.row_count,
        "column_count": d.column_count,
        "null_count": d.null_count,
        "duplicate_count": d.duplicate_count,
        "tags": d.tags or "",
        "created_at": _fmt(d.created_at),
        "updated_at": _fmt(d.updated_at),
        "last_profiled_at": _fmt(d.last_profiled_at),
    }


@router.get("")
async def list_datasets(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        q = select(Dataset).where(Dataset.organization_id == org_id)
        cq = select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id)
        if search:
            q = q.where(Dataset.name.ilike(f"%{search}%"))
            cq = cq.where(Dataset.name.ilike(f"%{search}%"))
        total = (await db.execute(cq)).scalar() or 0
        items = (await db.execute(q.order_by(Dataset.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()
        return {"items": [_serialize(d) for d in items], "total": total, "page": page, "page_size": page_size}
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("")
async def upload_dataset(
    org_id: str,
    file: UploadFile = File(...),
    name: str = Form(None),
    description: str = Form(None),
    tags: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.filename or "")[-1].lower()
        fmt_map = {".csv": "csv", ".json": "json", ".xlsx": "excel", ".xls": "excel"}
        fmt = fmt_map.get(ext, "csv")
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        size = os.path.getsize(file_path)
        ds = Dataset(
            organization_id=org_id,
            created_by=current_user.id,
            name=name or file.filename or "Untitled",
            description=description,
            file_format=fmt,
            file_path=file_path,
            file_size_bytes=size,
            status="pending",
            tags=tags,
        )
        db.add(ds)
        await db.commit()
        await db.refresh(ds)
        return _serialize(ds)
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/{dataset_id}")
async def get_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        d = (await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id))).scalar_one_or_none()
        if not d:
            raise HTTPException(404, "Dataset not found")
        return _serialize(d)
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    await db.delete(d)
    await db.commit()


@router.post("/{dataset_id}/profile")
async def profile_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    # Mark as processing — real profiling would be a background task
    d.status = "processing"
    await db.commit()
    return {"status": "profiling started", "dataset_id": dataset_id}


@router.post("/{dataset_id}/quality")
async def trigger_quality(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    return {"report_id": str(uuid.uuid4()), "status": "queued"}


@router.get("/{dataset_id}/quality")
async def get_quality_reports(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    return []


@router.post("/{dataset_id}/explore")
async def explore_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    return {"rows": [], "columns": [], "total": 0}

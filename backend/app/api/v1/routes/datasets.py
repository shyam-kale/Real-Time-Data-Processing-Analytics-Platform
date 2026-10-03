from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.dataset import Dataset

router = APIRouter(prefix="/orgs/{org_id}/datasets", tags=["datasets"])


def _fmt(v):
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if hasattr(v, 'value'):
        return v.value
    return v


@router.get("")
async def list_datasets(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        q = select(Dataset).where(Dataset.organization_id == org_id)
        cq = select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id)
        
        total = (await db.execute(cq)).scalar() or 0
        items = (await db.execute(q.offset((page-1)*page_size).limit(page_size))).scalars().all()
        
        return {
            "items": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "description": d.description,
                    "file_format": _fmt(d.file_format),
                    "file_size_bytes": d.file_size_bytes or 0,
                    "status": _fmt(d.status),
                    "row_count": d.row_count,
                    "column_count": d.column_count,
                    "null_count": d.null_count,
                    "duplicate_count": d.duplicate_count,
                    "tags": d.tags or [],
                    "created_at": _fmt(d.created_at),
                    "updated_at": _fmt(d.updated_at),
                    "last_profiled_at": _fmt(d.last_profiled_at),
                }
                for d in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error: {str(e)}"})


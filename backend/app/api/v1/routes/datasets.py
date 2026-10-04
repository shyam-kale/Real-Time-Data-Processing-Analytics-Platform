import asyncio
import math
import os
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.models.dataset import Dataset, DatasetStatus, FileFormat, DatasetColumn, ColumnDataType

router = APIRouter(prefix="/orgs/{org_id}/datasets", tags=["datasets"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")


# ── helpers ───────────────────────────────────────────────────────────────────

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


TYPE_MAP = {
    "integer":  ColumnDataType.INTEGER,
    "float":    ColumnDataType.FLOAT,
    "string":   ColumnDataType.STRING,
    "boolean":  ColumnDataType.BOOLEAN,
    "datetime": ColumnDataType.DATETIME,
    "date":     ColumnDataType.DATE,
}


# ── background: real profiler ─────────────────────────────────────────────────

async def _run_profiler(dataset_id: str, file_path: str, file_format: FileFormat):
    """Run profiler.py in a thread pool so it doesn't block the event loop."""
    from app.processing.profiler import profile_dataset
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        d = (await db.execute(select(Dataset).where(Dataset.id == dataset_id))).scalar_one_or_none()
        if not d:
            return
        try:
            # CPU-bound work in thread pool
            profile = await asyncio.get_event_loop().run_in_executor(
                None, profile_dataset, file_path, file_format
            )

            d.row_count      = profile["row_count"]
            d.column_count   = profile["column_count"]
            d.null_count     = profile["null_count"]
            d.duplicate_count = profile["duplicate_count"]
            d.schema_snapshot = profile["schema_snapshot"]
            d.profile_data   = profile
            d.status         = DatasetStatus.READY
            d.last_profiled_at = datetime.now(timezone.utc)

            # Replace column records with fresh profiled data
            existing = (await db.execute(
                select(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
            )).scalars().all()
            for col in existing:
                await db.delete(col)
            await db.flush()

            for col_data in profile["columns"]:
                db.add(DatasetColumn(
                    dataset_id  = dataset_id,
                    name        = col_data["name"],
                    position    = col_data["position"],
                    data_type   = TYPE_MAP.get(col_data["data_type"], ColumnDataType.UNKNOWN),
                    nullable    = col_data["nullable"],
                    null_count  = col_data["null_count"],
                    unique_count = col_data["unique_count"],
                    min_value   = col_data.get("min_value"),
                    max_value   = col_data.get("max_value"),
                    mean_value  = col_data.get("mean_value"),
                    std_value   = col_data.get("std_value"),
                    sample_values      = col_data.get("sample_values"),
                    value_distribution = col_data.get("value_distribution"),
                ))

            await db.commit()

        except Exception as exc:
            import traceback; traceback.print_exc()
            d.status = DatasetStatus.ERROR
            await db.commit()


# ── list ──────────────────────────────────────────────────────────────────────

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
        q  = select(Dataset).where(Dataset.organization_id == org_id)
        cq = select(func.count()).select_from(Dataset).where(Dataset.organization_id == org_id)
        if search:
            q  = q.where(Dataset.name.ilike(f"%{search}%"))
            cq = cq.where(Dataset.name.ilike(f"%{search}%"))
        total = (await db.execute(cq)).scalar() or 0
        items = (await db.execute(
            q.order_by(Dataset.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
        )).scalars().all()
        return {"items": [_serialize(d) for d in items], "total": total, "page": page, "page_size": page_size}
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── upload ────────────────────────────────────────────────────────────────────

@router.post("")
async def upload_dataset(
    org_id: str,
    background_tasks: BackgroundTasks,
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
        fmt_map = {".csv": FileFormat.CSV, ".json": FileFormat.JSON,
                   ".xlsx": FileFormat.EXCEL, ".xls": FileFormat.EXCEL}
        fmt = fmt_map.get(ext, FileFormat.CSV)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        size = os.path.getsize(file_path)

        ds = Dataset(
            organization_id = org_id,
            created_by      = current_user.id,
            name            = name or file.filename or "Untitled",
            description     = description,
            file_format     = fmt,
            file_path       = file_path,
            file_size_bytes = size,
            status          = DatasetStatus.PROCESSING,
            tags            = tags,
        )
        db.add(ds)
        await db.commit()
        await db.refresh(ds)

        # Kick off real profiler in the background immediately after upload
        background_tasks.add_task(_run_profiler, str(ds.id), file_path, fmt)

        return _serialize(ds)
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── get one ───────────────────────────────────────────────────────────────────

@router.get("/{dataset_id}")
async def get_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        d = (await db.execute(
            select(Dataset)
            .options(selectinload(Dataset.columns))
            .where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
        )).scalar_one_or_none()
        if not d:
            raise HTTPException(404, "Dataset not found")
        result = _serialize(d)
        result["columns"] = [
            {
                "id": str(c.id),
                "name": c.name,
                "position": c.position,
                "data_type": _fmt(c.data_type),
                "nullable": c.nullable,
                "null_count": c.null_count,
                "unique_count": c.unique_count,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "mean_value": c.mean_value,
                "sample_values": c.sample_values,
                "value_distribution": c.value_distribution,
            }
            for c in sorted(d.columns, key=lambda x: x.position)
        ]
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── delete ────────────────────────────────────────────────────────────────────

@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    # Also delete the file from disk
    if d.file_path and os.path.isfile(d.file_path):
        try:
            os.remove(d.file_path)
        except OSError:
            pass
    await db.delete(d)
    await db.commit()


# ── profile (re-profile on demand) ───────────────────────────────────────────

@router.post("/{dataset_id}/profile")
async def profile_dataset_endpoint(
    org_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    if not d.file_path or not os.path.isfile(d.file_path):
        raise HTTPException(400, "Dataset file not found on disk — upload the file again")

    d.status = DatasetStatus.PROCESSING
    await db.commit()

    background_tasks.add_task(_run_profiler, dataset_id, d.file_path, d.file_format)
    return {"status": "profiling started", "dataset_id": dataset_id}


# ── quality: trigger (runs real engine) ──────────────────────────────────────

@router.post("/{dataset_id}/quality")
async def trigger_quality(
    org_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    d = (await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Dataset not found")
    if not d.file_path or not os.path.isfile(d.file_path):
        raise HTTPException(400, "Dataset file not found on disk — upload the file again")

    report_id = str(uuid.uuid4())
    background_tasks.add_task(_run_quality, dataset_id, report_id, d.file_path, d.file_format, str(current_user.id))
    return {"report_id": report_id, "status": "running"}


async def _run_quality(dataset_id: str, report_id: str, file_path: str, file_format: FileFormat, user_id: str):
    from app.processing.quality_engine import analyze_quality
    from app.models.quality import QualityReport, QualityIssue, QualityIssueType, QualitySeverity
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, analyze_quality, file_path, file_format
            )

            issue_type_map = {t.value: t for t in QualityIssueType}
            severity_map   = {s.value: s for s in QualitySeverity}

            report = QualityReport(
                id                 = report_id,
                dataset_id         = dataset_id,
                created_by         = user_id,
                overall_score      = result["overall_score"],
                completeness_score = result["completeness_score"],
                uniqueness_score   = result["uniqueness_score"],
                validity_score     = result["validity_score"],
                consistency_score  = result["consistency_score"],
                total_rows         = result["total_rows"],
                passed_rows        = result["passed_rows"],
                failed_rows        = result["failed_rows"],
                issue_count        = len(result["issues"]),
                summary            = result.get("summary"),
            )
            db.add(report)
            await db.flush()

            for issue_data in result["issues"]:
                db.add(QualityIssue(
                    report_id          = report_id,
                    issue_type         = issue_type_map.get(issue_data["issue_type"], QualityIssueType.MISSING_VALUES),
                    severity           = severity_map.get(issue_data["severity"], QualitySeverity.WARNING),
                    column_name        = issue_data.get("column_name"),
                    description        = issue_data["description"],
                    affected_rows      = issue_data["affected_rows"],
                    affected_percentage = issue_data["affected_percentage"],
                    sample_values      = issue_data.get("sample_values"),
                    suggestion         = issue_data.get("suggestion"),
                ))

            await db.commit()
        except Exception:
            import traceback; traceback.print_exc()


# ── quality: fetch stored reports ────────────────────────────────────────────

@router.get("/{dataset_id}/quality")
async def get_quality_reports(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        d = (await db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
        )).scalar_one_or_none()
        if not d:
            raise HTTPException(404, "Dataset not found")

        from app.models.quality import QualityReport, QualityIssue

        reports = (await db.execute(
            select(QualityReport)
            .options(selectinload(QualityReport.issues))
            .where(QualityReport.dataset_id == dataset_id)
            .order_by(QualityReport.created_at.desc())
            .limit(10)
        )).scalars().all()

        def _fmt_report(r):
            return {
                "id": str(r.id),
                "dataset_id": str(r.dataset_id),
                "overall_score": r.overall_score,
                "completeness_score": r.completeness_score,
                "uniqueness_score": r.uniqueness_score,
                "validity_score": r.validity_score,
                "consistency_score": r.consistency_score,
                "total_rows": r.total_rows,
                "passed_rows": r.passed_rows,
                "failed_rows": r.failed_rows,
                "issue_count": r.issue_count,
                "summary": r.summary,
                "created_at": _fmt(r.created_at),
                "issues": [
                    {
                        "id": str(i.id),
                        "issue_type": _fmt(i.issue_type),
                        "severity": _fmt(i.severity),
                        "column_name": i.column_name,
                        "description": i.description,
                        "affected_rows": i.affected_rows,
                        "affected_percentage": i.affected_percentage,
                        "sample_values": i.sample_values,
                        "suggestion": i.suggestion,
                    }
                    for i in (r.issues or [])
                ],
            }

        return [_fmt_report(r) for r in reports]
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── explore: real rows from file ─────────────────────────────────────────────

@router.post("/{dataset_id}/explore")
async def explore_dataset(
    org_id: str,
    dataset_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    try:
        d = (await db.execute(
            select(Dataset)
            .where(Dataset.id == dataset_id, Dataset.organization_id == org_id)
        )).scalar_one_or_none()
        if not d:
            raise HTTPException(404, "Dataset not found")

        try:
            body = await req.json()
        except Exception:
            body = {}

        page      = int(body.get("page", 1))
        page_size = int(body.get("page_size", 50))
        search    = str(body.get("search", "")).strip()
        sort_col  = body.get("sort_column")
        sort_dir  = body.get("sort_direction", "asc")

        if not d.file_path or not os.path.isfile(d.file_path):
            raise HTTPException(400, "Dataset file not found on disk. Re-upload to explore real data.")

        # Load the actual file in a thread pool (pandas I/O is blocking)
        from app.processing.loader import load_dataset_to_df
        import pandas as pd

        df = await asyncio.get_event_loop().run_in_executor(
            None, load_dataset_to_df, d.file_path, d.file_format
        )

        col_names = list(df.columns)

        # Apply search across all columns
        if search:
            mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
            df = df[mask]

        # Apply sort
        if sort_col and sort_col in df.columns:
            df = df.sort_values(by=sort_col, ascending=(sort_dir != "desc"), na_position="last")

        filtered_total = len(df)
        total_pages    = max(1, math.ceil(filtered_total / page_size))
        start          = (page - 1) * page_size
        page_df        = df.iloc[start: start + page_size]

        # Convert to JSON-safe records (handle NaN, NaT, numpy types)
        import numpy as np
        rows = []
        for _, row in page_df.iterrows():
            record = {}
            for col in col_names:
                val = row[col]
                if pd.isna(val) if not isinstance(val, (list, dict)) else False:
                    val = None
                elif isinstance(val, (np.integer,)):
                    val = int(val)
                elif isinstance(val, (np.floating,)):
                    val = None if np.isnan(val) or np.isinf(val) else float(val)
                elif isinstance(val, (np.bool_,)):
                    val = bool(val)
                elif hasattr(val, 'isoformat'):
                    val = val.isoformat()
                else:
                    val = str(val) if not isinstance(val, (str, int, float, bool, type(None))) else val
                record[col] = val
            rows.append(record)

        return {
            "rows":        rows,
            "columns":     col_names,
            "total_rows":  filtered_total,
            "page":        page,
            "page_size":   page_size,
            "total_pages": total_pages,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})

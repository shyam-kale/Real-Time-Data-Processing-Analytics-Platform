from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.dataset import DatasetOut, DatasetDetailOut, DataExplorerQuery, DataExplorerResponse
from app.services.dataset_service import upload_dataset, list_datasets, get_dataset, delete_dataset
from app.models.dataset import DatasetColumn
from app.models.quality import QualityReport, QualityIssue
from app.schemas.quality import QualityReportOut

router = APIRouter(prefix="/orgs/{org_id}/datasets", tags=["datasets"])


@router.post("", response_model=DatasetOut, status_code=201)
async def upload(
    org_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    dataset = await upload_dataset(db, org_id, current_user.id, file, name, description, tags)
    await db.commit()
    from app.workers.tasks import task_profile_dataset
    background_tasks.add_task(lambda: task_profile_dataset.delay(dataset.id))
    return dataset


@router.get("", response_model=dict)
async def list_all(
    org_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    skip = (page - 1) * page_size
    datasets, total = await list_datasets(db, org_id, skip=skip, limit=page_size, search=search)
    return {
        "items": [DatasetOut.model_validate(d) for d in datasets],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
async def get_one(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    result = await db.execute(
        select(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id).order_by(DatasetColumn.position)
    )
    columns = result.scalars().all()
    dataset = await get_dataset(db, dataset_id, org_id)
    dataset.columns = columns
    return dataset


@router.delete("/{dataset_id}", status_code=204)
async def delete(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await delete_dataset(db, dataset_id, org_id, current_user.id)
    await db.commit()


@router.post("/{dataset_id}/profile")
async def trigger_profile(
    org_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await get_dataset(db, dataset_id, org_id)
    from app.workers.tasks import task_profile_dataset
    background_tasks.add_task(lambda: task_profile_dataset.delay(dataset_id))
    return {"message": "Profiling started", "dataset_id": dataset_id}


@router.post("/{dataset_id}/quality", response_model=dict)
async def trigger_quality(
    org_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await get_dataset(db, dataset_id, org_id)
    from app.models.quality import QualityReport as QR
    report = QR(
        dataset_id=dataset_id, created_by=current_user.id,
        overall_score=0, completeness_score=0, uniqueness_score=0,
        validity_score=0, consistency_score=0,
        total_rows=0, passed_rows=0, failed_rows=0,
    )
    db.add(report)
    await db.flush()
    report_id = report.id
    await db.commit()
    from app.workers.tasks import task_run_quality_analysis
    background_tasks.add_task(lambda: task_run_quality_analysis.delay(dataset_id, report_id))
    return {"message": "Quality analysis started", "report_id": report_id}


@router.get("/{dataset_id}/quality", response_model=List[QualityReportOut])
async def get_quality_reports(
    org_id: str,
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    await get_dataset(db, dataset_id, org_id)
    # Use selectinload to eagerly load issues in the same async context
    result = await db.execute(
        select(QualityReport)
        .options(selectinload(QualityReport.issues))
        .where(QualityReport.dataset_id == dataset_id)
        .order_by(QualityReport.created_at.desc())
        .limit(10)
    )
    reports = result.scalars().all()
    return reports


@router.post("/{dataset_id}/explore", response_model=DataExplorerResponse)
async def explore_data(
    org_id: str,
    dataset_id: str,
    query: DataExplorerQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    import pandas as pd
    from app.processing.loader import load_dataset_to_df
    dataset = await get_dataset(db, dataset_id, org_id)
    df = load_dataset_to_df(dataset.file_path, dataset.file_format)
    total_rows = len(df)

    if query.search:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= df[col].astype(str).str.contains(query.search, case=False, na=False)
        df = df[mask]
        total_rows = len(df)

    if query.filters:
        for f in query.filters:
            col, op, val = f.get("column"), f.get("operator", "eq"), f.get("value")
            if col and col in df.columns:
                if op == "eq":       df = df[df[col].astype(str) == str(val)]
                elif op == "contains": df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
                elif op == "gt":     df = df[pd.to_numeric(df[col], errors="coerce") > float(val)]
                elif op == "lt":     df = df[pd.to_numeric(df[col], errors="coerce") < float(val)]
                elif op == "not_null": df = df[df[col].notna()]
        total_rows = len(df)

    if query.sort_column and query.sort_column in df.columns:
        df = df.sort_values(by=query.sort_column, ascending=(query.sort_direction == "asc"))

    start = (query.page - 1) * query.page_size
    page_df = df.iloc[start:start + query.page_size].replace({float("nan"): None})

    return DataExplorerResponse(
        rows=page_df.to_dict(orient="records"),
        total_rows=total_rows,
        page=query.page,
        page_size=query.page_size,
        total_pages=(total_rows + query.page_size - 1) // query.page_size,
        columns=list(df.columns),
    )

import time
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import numpy as np

from app.models.dataset import Dataset
from app.services.dataset_service import get_dataset
from app.schemas.analytics import AnalyticsQuery, AnalyticsResult
from app.processing.loader import load_dataset_to_df


async def run_analytics_query(
    db: AsyncSession, org_id: str, query: AnalyticsQuery
) -> AnalyticsResult:
    dataset = await get_dataset(db, query.dataset_id, org_id)
    start_ms = time.time() * 1000

    df = load_dataset_to_df(dataset.file_path, dataset.file_format)

    # Apply date filter
    if query.date_column and query.date_from:
        try:
            df[query.date_column] = pd.to_datetime(df[query.date_column], errors="coerce")
            df = df[df[query.date_column] >= pd.to_datetime(query.date_from)]
            if query.date_to:
                df = df[df[query.date_column] <= pd.to_datetime(query.date_to)]
        except Exception:
            pass

    # Apply filters
    if query.filters:
        for f in query.filters:
            col, op, val = f.get("column"), f.get("operator"), f.get("value")
            if col not in df.columns:
                continue
            if op == "eq":
                df = df[df[col] == val]
            elif op == "neq":
                df = df[df[col] != val]
            elif op == "gt":
                df = df[df[col] > val]
            elif op == "lt":
                df = df[df[col] < val]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(str(val), na=False)]

    # Group and aggregate
    result_df = pd.DataFrame()

    if query.dimensions:
        valid_dims = [d for d in query.dimensions if d in df.columns]
        if not valid_dims:
            raise HTTPException(400, "No valid dimension columns found")

        if query.measures:
            valid_measures = [m for m in query.measures if m in df.columns]
            if valid_measures:
                agg_map = {
                    "count": "count",
                    "sum": "sum",
                    "avg": "mean",
                    "min": "min",
                    "max": "max",
                }
                agg_func = agg_map.get(query.aggregation, "count")

                if agg_func == "count":
                    result_df = df.groupby(valid_dims).size().reset_index(name="count")
                else:
                    result_df = df.groupby(valid_dims)[valid_measures].agg(agg_func).reset_index()
            else:
                result_df = df.groupby(valid_dims).size().reset_index(name="count")
        else:
            result_df = df.groupby(valid_dims).size().reset_index(name="count")

        result_df = result_df.head(query.limit)
    else:
        # Just return first N rows
        result_df = df.head(query.limit)

    # Clean for JSON serialization
    result_df = result_df.replace({np.nan: None, np.inf: None, -np.inf: None})

    rows = result_df.to_dict(orient="records")
    elapsed = time.time() * 1000 - start_ms

    return AnalyticsResult(
        data=rows,
        columns=list(result_df.columns),
        row_count=len(rows),
        query_time_ms=round(elapsed, 2),
    )

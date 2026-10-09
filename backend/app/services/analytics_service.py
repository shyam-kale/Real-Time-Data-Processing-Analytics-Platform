import time
import time
import json
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dataset_service import get_dataset
from app.schemas.analytics import AnalyticsQuery, AnalyticsResult


async def run_analytics_query(db: AsyncSession, org_id: str, query: AnalyticsQuery) -> AnalyticsResult:
    import pandas as pd
    import numpy as np
    dataset = await get_dataset(db, query.dataset_id, org_id)
    start_ms = time.time() * 1000

    import os
    file_exists = os.path.exists(dataset.file_path) if dataset.file_path else False

    if file_exists:
        from app.processing.loader import load_dataset_to_df
        df = load_dataset_to_df(dataset.file_path, dataset.file_format)
    else:
        # Generate synthetic data from schema_snapshot for demo/seeded datasets
        df = _generate_demo_df(dataset)

    if df is None or len(df) == 0:
        raise HTTPException(400, "Dataset has no data. Upload a real file to use Analytics.")

    # Apply date filter
    if query.date_column and query.date_from and query.date_column in df.columns:
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
            try:
                if op == "eq":   df = df[df[col] == val]
                elif op == "neq": df = df[df[col] != val]
                elif op == "gt":  df = df[df[col] > val]
                elif op == "lt":  df = df[df[col] < val]
                elif op == "contains": df = df[df[col].astype(str).str.contains(str(val), na=False)]
            except Exception:
                pass

    # Group and aggregate
    result_df = pd.DataFrame()

    if query.dimensions:
        valid_dims = [d for d in query.dimensions if d in df.columns]
        if not valid_dims:
            raise HTTPException(400, f"Dimension columns not found: {query.dimensions}")

        if query.measures:
            valid_measures = [m for m in query.measures if m in df.columns]
            if valid_measures:
                agg_map = {"count": "count", "sum": "sum", "avg": "mean", "min": "min", "max": "max"}
                agg_func = agg_map.get(query.aggregation, "count")
                if agg_func == "count":
                    # Name the column after the measure so the frontend yKey resolves correctly
                    result_df = df.groupby(valid_dims).size().reset_index(name=valid_measures[0])
                else:
                    result_df = df.groupby(valid_dims)[valid_measures].agg(agg_func).reset_index()
            else:
                result_df = df.groupby(valid_dims).size().reset_index(name="count")
        else:
            result_df = df.groupby(valid_dims).size().reset_index(name="count")

        result_df = result_df.head(query.limit)
    else:
        result_df = df.head(query.limit)

    result_df = result_df.replace({np.nan: None, np.inf: None, -np.inf: None})
    rows = result_df.to_dict(orient="records")
    elapsed = time.time() * 1000 - start_ms

    return AnalyticsResult(
        data=rows,
        columns=list(result_df.columns),
        row_count=len(rows),
        query_time_ms=round(elapsed, 2),
    )


def _generate_demo_df(dataset) -> "Optional[pd.DataFrame]":
    """Generate synthetic demo data from schema_snapshot for seeded datasets."""
    import pandas as pd
    import random
    from datetime import datetime, timedelta
    import hashlib

    schema = dataset.schema_snapshot or {}
    if not schema:
        return None

    # Use dataset ID to seed random — ensures same dataset always has same data
    # but different datasets have different data
    seed = int(hashlib.md5(dataset.id.encode()).hexdigest(), 16) % (2**32)
    random.seed(seed)

    rows = min(dataset.row_count or 1000, 5000)
    data = {}

    statuses = ["active", "inactive", "pending", "completed", "failed"]
    categories = ["Electronics", "Clothing", "Food", "Books", "Sports"]

    for col, dtype in schema.items():
        if dtype == "integer":
            data[col] = [random.randint(1, 10000) for _ in range(rows)]
        elif dtype == "float":
            data[col] = [round(random.uniform(10, 10000), 2) for _ in range(rows)]
        elif dtype == "datetime":
            base = datetime(2024, 1, 1)
            data[col] = [(base + timedelta(days=random.randint(0, 364))).strftime("%Y-%m-%d") for _ in range(rows)]
        elif dtype == "boolean":
            data[col] = [random.choice([True, False]) for _ in range(rows)]
        else:
            # string — generate meaningful categorical data
            if "status" in col.lower():
                data[col] = [random.choice(statuses) for _ in range(rows)]
            elif "category" in col.lower() or "type" in col.lower():
                data[col] = [random.choice(categories) for _ in range(rows)]
            elif "name" in col.lower():
                data[col] = [f"Item {random.randint(1, 100)}" for _ in range(rows)]
            else:
                data[col] = [random.choice(["A", "B", "C", "D"]) for _ in range(rows)]

    return pd.DataFrame(data)

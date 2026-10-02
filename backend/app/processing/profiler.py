import numpy as np
import pandas as pd
from typing import Dict, Any
from app.processing.loader import load_dataset_to_df, detect_column_type
from app.models.dataset import FileFormat


def profile_dataset(file_path: str, file_format: FileFormat) -> Dict[str, Any]:
    """
    Full dataset profiling: returns row count, column profiles, null/duplicate counts,
    and per-column statistics.
    """
    df = load_dataset_to_df(file_path, file_format)
    row_count = len(df)
    column_count = len(df.columns)
    total_null_count = int(df.isnull().sum().sum())
    duplicate_count = int(df.duplicated().sum())

    columns = []
    for i, col in enumerate(df.columns):
        series = df[col]
        dtype = detect_column_type(series)
        null_count = int(series.isnull().sum())
        unique_count = int(series.nunique())
        sample = series.dropna().head(5).tolist()

        col_profile: Dict[str, Any] = {
            "name": col,
            "position": i,
            "data_type": dtype,
            "nullable": null_count > 0,
            "null_count": null_count,
            "unique_count": unique_count,
            "sample_values": [str(v) for v in sample],
        }

        if dtype in ("integer", "float"):
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if len(numeric) > 0:
                col_profile["min_value"] = str(float(numeric.min()))
                col_profile["max_value"] = str(float(numeric.max()))
                col_profile["mean_value"] = float(round(numeric.mean(), 4))
                col_profile["std_value"] = float(round(numeric.std(), 4))
                # Distribution histogram
                try:
                    hist, edges = np.histogram(numeric.astype(float), bins=min(20, unique_count))
                    col_profile["value_distribution"] = {
                        "bins": [float(e) for e in edges],
                        "counts": [int(c) for c in hist],
                    }
                except Exception:
                    pass
        elif dtype == "string":
            top_values = series.value_counts().head(10)
            col_profile["value_distribution"] = {
                "labels": [str(v) for v in top_values.index.tolist()],
                "counts": [int(c) for c in top_values.values.tolist()],
            }
            if len(series.dropna()) > 0:
                lengths = series.dropna().astype(str).map(len)
                col_profile["min_value"] = str(int(lengths.min()))
                col_profile["max_value"] = str(int(lengths.max()))
                col_profile["mean_value"] = float(round(lengths.mean(), 2))
        elif dtype == "datetime":
            try:
                parsed = pd.to_datetime(series, errors="coerce").dropna()
                if len(parsed) > 0:
                    col_profile["min_value"] = str(parsed.min())
                    col_profile["max_value"] = str(parsed.max())
            except Exception:
                pass

        columns.append(col_profile)

    return {
        "row_count": row_count,
        "column_count": column_count,
        "null_count": total_null_count,
        "duplicate_count": duplicate_count,
        "columns": columns,
        "schema_snapshot": {c["name"]: c["data_type"] for c in columns},
    }

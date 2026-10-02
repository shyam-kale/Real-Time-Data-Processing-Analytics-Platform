"""
Data quality engine — detects missing values, duplicates, type issues,
outliers, format problems, and calculates quality scores.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from app.processing.loader import load_dataset_to_df, detect_column_type
from app.models.dataset import FileFormat


def _zscore_outliers(series: pd.Series, threshold: float = 3.5) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    mean = numeric.mean()
    std = numeric.std()
    if std == 0:
        return pd.Series(False, index=series.index)
    z = (numeric - mean).abs() / std
    return z > threshold


def analyze_quality(file_path: str, file_format: FileFormat) -> Dict[str, Any]:
    """Run full quality analysis on a dataset file."""
    df = load_dataset_to_df(file_path, file_format)
    total_rows = len(df)
    issues: List[Dict[str, Any]] = []

    if total_rows == 0:
        return {
            "overall_score": 0.0,
            "completeness_score": 0.0,
            "uniqueness_score": 0.0,
            "validity_score": 0.0,
            "consistency_score": 0.0,
            "total_rows": 0,
            "passed_rows": 0,
            "failed_rows": 0,
            "issues": [],
        }

    failed_row_indices = set()

    # ── Completeness: missing values ─────────────────────────────────────────
    null_cells = 0
    for col in df.columns:
        null_mask = df[col].isnull()
        null_count = int(null_mask.sum())
        if null_count > 0:
            null_cells += null_count
            pct = round(null_count / total_rows * 100, 2)
            severity = "critical" if pct > 30 else "error" if pct > 10 else "warning"
            issues.append({
                "issue_type": "missing_values",
                "severity": severity,
                "column_name": col,
                "description": f"Column '{col}' has {null_count:,} missing values ({pct}%)",
                "affected_rows": null_count,
                "affected_percentage": pct,
                "sample_values": [],
                "suggestion": f"Consider imputing or removing rows with missing '{col}' values.",
            })
            failed_row_indices.update(df[null_mask].index.tolist())

    total_cells = total_rows * len(df.columns)
    completeness_score = round((1 - null_cells / max(total_cells, 1)) * 100, 2)

    # ── Uniqueness: duplicates ────────────────────────────────────────────────
    dup_mask = df.duplicated()
    dup_count = int(dup_mask.sum())
    uniqueness_score = round((1 - dup_count / max(total_rows, 1)) * 100, 2)
    if dup_count > 0:
        pct = round(dup_count / total_rows * 100, 2)
        severity = "error" if pct > 10 else "warning"
        issues.append({
            "issue_type": "duplicates",
            "severity": severity,
            "column_name": None,
            "description": f"Dataset contains {dup_count:,} fully duplicate rows ({pct}%)",
            "affected_rows": dup_count,
            "affected_percentage": pct,
            "sample_values": [],
            "suggestion": "Remove duplicate rows with df.drop_duplicates().",
        })
        failed_row_indices.update(df[dup_mask].index.tolist())

    # ── Validity: outliers and type issues ────────────────────────────────────
    outlier_count = 0
    type_issue_count = 0
    for col in df.columns:
        inferred = detect_column_type(df[col])

        if inferred in ("integer", "float"):
            outlier_mask = _zscore_outliers(df[col])
            col_outliers = int(outlier_mask.sum())
            if col_outliers > 0:
                outlier_count += col_outliers
                pct = round(col_outliers / total_rows * 100, 2)
                sample = df[col][outlier_mask].head(5).tolist()
                issues.append({
                    "issue_type": "outlier",
                    "severity": "warning",
                    "column_name": col,
                    "description": f"Column '{col}' has {col_outliers:,} statistical outliers (z-score > 3.5)",
                    "affected_rows": col_outliers,
                    "affected_percentage": pct,
                    "sample_values": [str(v) for v in sample],
                    "suggestion": "Review or cap outlier values.",
                })
                failed_row_indices.update(df[outlier_mask].index.tolist())

        # Type consistency: detect mixed types in string columns
        if inferred == "string":
            numeric_coerce = pd.to_numeric(df[col], errors="coerce")
            partial_numeric = numeric_coerce.notna().sum()
            if 0 < partial_numeric < len(df[col].dropna()) * 0.9:
                type_issue_count += partial_numeric
                issues.append({
                    "issue_type": "invalid_type",
                    "severity": "warning",
                    "column_name": col,
                    "description": f"Column '{col}' has mixed numeric and string values",
                    "affected_rows": int(partial_numeric),
                    "affected_percentage": round(partial_numeric / total_rows * 100, 2),
                    "sample_values": [],
                    "suggestion": f"Standardize the data type for column '{col}'.",
                })

    validity_score = round(
        max(0, (1 - (outlier_count + type_issue_count) / max(total_rows * len(df.columns), 1)) * 100), 2
    )

    # ── Consistency score (heuristic) ────────────────────────────────────────
    consistency_issues = sum(1 for i in issues if i["issue_type"] in ("invalid_format", "schema_drift"))
    consistency_score = round(max(0, 100 - consistency_issues * 10), 2)

    # ── Overall ──────────────────────────────────────────────────────────────
    overall_score = round(
        (completeness_score * 0.35 + uniqueness_score * 0.25 + validity_score * 0.25 + consistency_score * 0.15),
        2,
    )

    failed_rows = len(failed_row_indices)
    passed_rows = total_rows - failed_rows

    return {
        "overall_score": overall_score,
        "completeness_score": completeness_score,
        "uniqueness_score": uniqueness_score,
        "validity_score": validity_score,
        "consistency_score": consistency_score,
        "total_rows": total_rows,
        "passed_rows": passed_rows,
        "failed_rows": failed_rows,
        "issues": issues,
        "summary": {
            "null_cells": null_cells,
            "duplicate_rows": dup_count,
            "outlier_cells": outlier_count,
            "issue_count": len(issues),
        },
    }

import pandas as pd
from pathlib import Path
from app.models.dataset import FileFormat


def load_dataset_to_df(file_path: str, file_format: FileFormat) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Always try CSV first if file ends in .csv regardless of format label
    suffix = path.suffix.lower()
    if suffix == ".csv" or file_format == FileFormat.CSV:
        return pd.read_csv(file_path, low_memory=False)
    elif suffix in (".xlsx", ".xls") or file_format == FileFormat.EXCEL:
        return pd.read_excel(file_path)
    elif suffix == ".json" or file_format == FileFormat.JSON:
        try:
            return pd.read_json(file_path)
        except ValueError:
            return pd.read_json(file_path, lines=True)
    else:
        # Fallback: try CSV
        return pd.read_csv(file_path, low_memory=False)


def detect_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if len(non_null) == 0:
        return "unknown"

    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    numeric_try = pd.to_numeric(non_null, errors="coerce")
    non_null_numeric = numeric_try.dropna()
    if len(non_null_numeric) / max(len(non_null), 1) > 0.9:
        if (non_null_numeric % 1 == 0).all():
            return "integer"
        return "float"

    # Try datetime (no deprecated flags)
    try:
        parsed = pd.to_datetime(non_null.head(100), errors="coerce")
        if parsed.notna().mean() > 0.9:
            return "datetime"
    except Exception:
        pass

    return "string"

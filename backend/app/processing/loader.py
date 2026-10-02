import pandas as pd
from pathlib import Path
from app.models.dataset import FileFormat


def load_dataset_to_df(file_path: str, file_format: FileFormat) -> pd.DataFrame:
    """Load a dataset file into a pandas DataFrame."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_format == FileFormat.CSV:
        return pd.read_csv(file_path, low_memory=False)
    elif file_format == FileFormat.JSON:
        try:
            return pd.read_json(file_path)
        except ValueError:
            # Try lines format
            return pd.read_json(file_path, lines=True)
    elif file_format == FileFormat.EXCEL:
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


def detect_column_type(series: pd.Series) -> str:
    """Infer the semantic type of a pandas Series."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return "unknown"

    # Try numeric
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Try coerce to numeric
    numeric_try = pd.to_numeric(non_null, errors="coerce")
    non_null_numeric = numeric_try.dropna()
    if len(non_null_numeric) / max(len(non_null), 1) > 0.9:
        if (non_null_numeric % 1 == 0).all():
            return "integer"
        return "float"

    # Try datetime
    try:
        parsed = pd.to_datetime(non_null.head(100), errors="coerce", infer_datetime_format=True)
        if parsed.notna().mean() > 0.9:
            return "datetime"
    except Exception:
        pass

    return "string"

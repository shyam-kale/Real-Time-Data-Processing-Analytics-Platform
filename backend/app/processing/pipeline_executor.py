"""
Pipeline execution engine — processes node graph, applies each transform step.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from app.processing.loader import load_dataset_to_df
from app.models.pipeline import NodeType
from app.models.dataset import FileFormat


def _log(logs: List[dict], stage: str, message: str, level: str = "info") -> None:
    import time
    logs.append({"ts": time.time(), "stage": stage, "message": message, "level": level})


def execute_pipeline_graph(
    nodes: List[Dict], edges: List[Dict], progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Execute a pipeline graph.
    nodes: list of {id, node_type, label, config}
    edges: list of {source_node_id, target_node_id}
    Returns: {output_df, input_records, output_records, failed_records, logs, metrics}
    """
    logs: List[dict] = []
    metrics: Dict[str, Any] = {}

    # Build adjacency
    adj: Dict[str, List[str]] = {}
    for e in edges:
        adj.setdefault(e["source_node_id"], []).append(e["target_node_id"])

    node_map = {n["id"]: n for n in nodes}

    # Topological sort
    visited = set()
    order = []

    def dfs(nid: str):
        if nid in visited:
            return
        visited.add(nid)
        for child in adj.get(nid, []):
            dfs(child)
        order.insert(0, nid)

    for n in nodes:
        dfs(n["id"])

    # Find source node
    source_nodes = [n for n in nodes if n["node_type"] == NodeType.SOURCE]
    if not source_nodes:
        raise ValueError("Pipeline must have at least one SOURCE node")

    # Load data from source
    source = source_nodes[0]
    cfg = source.get("config", {})
    file_path = cfg.get("file_path", "")
    file_format_str = cfg.get("file_format", "csv")
    fmt_map = {"csv": FileFormat.CSV, "json": FileFormat.JSON, "excel": FileFormat.EXCEL}
    fmt = fmt_map.get(file_format_str, FileFormat.CSV)

    _log(logs, "source", f"Loading data from {file_path}")
    df = load_dataset_to_df(file_path, fmt)
    input_records = len(df)
    _log(logs, "source", f"Loaded {input_records:,} records, {len(df.columns)} columns")

    if progress_callback:
        progress_callback("source", 10, input_records)

    failed_records = 0

    # Process each node in topological order (skip source)
    processed_nodes = set([source["id"]])
    step_pct = 80 // max(len(order) - 1, 1)
    current_pct = 10

    for nid in order:
        if nid in processed_nodes:
            continue
        node = node_map.get(nid)
        if not node:
            continue

        ntype = node["node_type"]
        cfg = node.get("config", {})
        label = node.get("label", ntype)

        _log(logs, ntype, f"Executing node: {label}")

        try:
            if ntype == NodeType.FILTER:
                col = cfg.get("column")
                op = cfg.get("operator", "eq")
                val = cfg.get("value")
                if col and col in df.columns:
                    before = len(df)
                    if op == "eq":
                        df = df[df[col].astype(str) == str(val)]
                    elif op == "neq":
                        df = df[df[col].astype(str) != str(val)]
                    elif op == "gt":
                        df = df[pd.to_numeric(df[col], errors="coerce") > float(val)]
                    elif op == "lt":
                        df = df[pd.to_numeric(df[col], errors="coerce") < float(val)]
                    elif op == "contains":
                        df = df[df[col].astype(str).str.contains(str(val), na=False)]
                    elif op == "not_null":
                        df = df[df[col].notna()]
                    dropped = before - len(df)
                    failed_records += dropped
                    _log(logs, ntype, f"Filter removed {dropped:,} rows → {len(df):,} remain")

            elif ntype == NodeType.DEDUPLICATE:
                before = len(df)
                subset = cfg.get("subset")  # list of columns or None
                df = df.drop_duplicates(subset=subset if subset else None)
                dropped = before - len(df)
                failed_records += dropped
                _log(logs, ntype, f"Deduplicate removed {dropped:,} duplicates")

            elif ntype == NodeType.TRANSFORM:
                transforms = cfg.get("transforms", [])
                for t in transforms:
                    op = t.get("op")
                    col = t.get("column")
                    if col not in df.columns:
                        continue
                    if op == "uppercase":
                        df[col] = df[col].astype(str).str.upper()
                    elif op == "lowercase":
                        df[col] = df[col].astype(str).str.lower()
                    elif op == "strip":
                        df[col] = df[col].astype(str).str.strip()
                    elif op == "fill_null":
                        df[col] = df[col].fillna(t.get("value", ""))
                    elif op == "to_numeric":
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    elif op == "to_datetime":
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                    elif op == "rename":
                        new_name = t.get("new_name")
                        if new_name:
                            df = df.rename(columns={col: new_name})
                _log(logs, ntype, f"Applied {len(transforms)} transforms")

            elif ntype == NodeType.VALIDATION:
                rules = cfg.get("rules", [])
                mask = pd.Series(True, index=df.index)
                for rule in rules:
                    col = rule.get("column")
                    check = rule.get("check")
                    if col not in df.columns:
                        continue
                    if check == "not_null":
                        mask &= df[col].notna()
                    elif check == "positive":
                        mask &= pd.to_numeric(df[col], errors="coerce") > 0
                    elif check == "unique":
                        mask &= ~df[col].duplicated(keep="first")
                before = len(df)
                df = df[mask]
                dropped = before - len(df)
                failed_records += dropped
                _log(logs, ntype, f"Validation dropped {dropped:,} invalid rows")

            elif ntype == NodeType.AGGREGATE:
                group_cols = cfg.get("group_by", [])
                agg_col = cfg.get("column")
                func_name = cfg.get("function", "count")
                if group_cols and all(c in df.columns for c in group_cols):
                    if func_name == "count":
                        df = df.groupby(group_cols).size().reset_index(name=agg_col or "count")
                    elif agg_col and agg_col in df.columns:
                        df = df.groupby(group_cols)[agg_col].agg(func_name).reset_index()
                _log(logs, ntype, f"Aggregated to {len(df):,} rows")

            elif ntype == NodeType.QUALITY_CHECK:
                threshold = float(cfg.get("min_completeness", 90))
                for col in df.columns:
                    null_pct = df[col].isnull().mean() * 100
                    if null_pct > (100 - threshold):
                        _log(logs, ntype, f"Quality warning: '{col}' has {null_pct:.1f}% nulls", "warning")

            elif ntype == NodeType.OUTPUT:
                _log(logs, ntype, f"Output: {len(df):,} records ready")

        except Exception as ex:
            _log(logs, ntype, f"Error in node {label}: {ex}", "error")

        processed_nodes.add(nid)
        current_pct = min(current_pct + step_pct, 90)
        if progress_callback:
            progress_callback(ntype, current_pct, len(df))

    output_records = len(df)
    metrics["input_records"] = input_records
    metrics["output_records"] = output_records
    metrics["failed_records"] = failed_records

    if progress_callback:
        progress_callback("complete", 100, output_records)

    return {
        "input_records": input_records,
        "output_records": output_records,
        "failed_records": failed_records,
        "logs": logs,
        "metrics": metrics,
    }

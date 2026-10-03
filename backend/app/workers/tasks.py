"""
Celery tasks for async processing: dataset profiling, quality analysis, pipeline execution.
Guards all imports so the web server starts cleanly even without Celery/Redis.
"""
import time
import json
from datetime import datetime, timezone
from typing import Optional

# ── Lazy Celery/Redis setup — only executed when Celery worker is running ──────
try:
    import redis as _redis_module
    from app.workers.celery_app import celery_app
    from app.core.config import settings
    from app.models.dataset import DatasetStatus, FileFormat
    from app.models.pipeline import RunStatus
    from sqlalchemy import create_engine, select, update
    from sqlalchemy.orm import sessionmaker

    is_sync_sqlite = settings.DATABASE_URL_SYNC.startswith("sqlite")
    _engine_kwargs = {"connect_args": {"check_same_thread": False}} if is_sync_sqlite else {"pool_pre_ping": True}
    sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_engine_kwargs)
    SyncSession = sessionmaker(sync_engine)
    redis_client = _redis_module.from_url(settings.REDIS_URL, decode_responses=True)
    _CELERY_AVAILABLE = True
except Exception:
    _CELERY_AVAILABLE = False
    # Provide a no-op decorator so the route import doesn't crash
    class _FakeTask:
        def delay(self, *a, **kw): pass
    class _FakeCelery:
        def task(self, *a, **kw):
            def decorator(fn): return _FakeTask()
            return decorator
    celery_app = _FakeCelery()
    SyncSession = None
    redis_client = None


def _publish(channel: str, data: dict) -> None:
    try:
        if redis_client:
            redis_client.publish(channel, json.dumps(data))
    except Exception:
        pass


@celery_app.task(bind=True, name="tasks.profile_dataset")
def task_profile_dataset(self, dataset_id: str) -> dict:
    from app.models.dataset import Dataset, DatasetColumn, ColumnDataType

    with SyncSession() as db:
        dataset = db.execute(select(Dataset).where(Dataset.id == dataset_id)).scalar_one_or_none()
        if not dataset:
            return {"error": "Dataset not found"}

        # Mark processing
        dataset.status = DatasetStatus.PROCESSING
        db.commit()

        _publish(f"dataset:{dataset_id}", {"event": "profiling_started", "dataset_id": dataset_id})

        try:
            profile = profile_dataset(dataset.file_path, dataset.file_format)

            dataset.row_count = profile["row_count"]
            dataset.column_count = profile["column_count"]
            dataset.null_count = profile["null_count"]
            dataset.duplicate_count = profile["duplicate_count"]
            dataset.schema_snapshot = profile["schema_snapshot"]
            dataset.profile_data = profile
            dataset.status = DatasetStatus.READY
            dataset.last_profiled_at = datetime.now(timezone.utc)

            # Update/create column records
            existing_cols = db.execute(
                select(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
            ).scalars().all()
            for col in existing_cols:
                db.delete(col)
            db.flush()

            type_map = {
                "integer": ColumnDataType.INTEGER,
                "float": ColumnDataType.FLOAT,
                "string": ColumnDataType.STRING,
                "boolean": ColumnDataType.BOOLEAN,
                "datetime": ColumnDataType.DATETIME,
                "date": ColumnDataType.DATE,
            }

            for col_data in profile["columns"]:
                col = DatasetColumn(
                    dataset_id=dataset_id,
                    name=col_data["name"],
                    position=col_data["position"],
                    data_type=type_map.get(col_data["data_type"], ColumnDataType.UNKNOWN),
                    nullable=col_data["nullable"],
                    null_count=col_data["null_count"],
                    unique_count=col_data["unique_count"],
                    min_value=col_data.get("min_value"),
                    max_value=col_data.get("max_value"),
                    mean_value=col_data.get("mean_value"),
                    std_value=col_data.get("std_value"),
                    sample_values=col_data.get("sample_values"),
                    value_distribution=col_data.get("value_distribution"),
                )
                db.add(col)

            db.commit()
            _publish(f"dataset:{dataset_id}", {"event": "profiling_complete", "dataset_id": dataset_id, "row_count": profile["row_count"]})
            return {"status": "success", "row_count": profile["row_count"]}

        except Exception as ex:
            dataset.status = DatasetStatus.ERROR
            db.commit()
            _publish(f"dataset:{dataset_id}", {"event": "profiling_error", "dataset_id": dataset_id, "error": str(ex)})
            raise


@celery_app.task(bind=True, name="tasks.run_quality_analysis")
def task_run_quality_analysis(self, dataset_id: str, report_id: str) -> dict:
    from app.models.quality import QualityReport, QualityIssue, QualityIssueType, QualitySeverity
    from app.models.dataset import Dataset

    with SyncSession() as db:
        dataset = db.execute(select(Dataset).where(Dataset.id == dataset_id)).scalar_one_or_none()
        report = db.execute(select(QualityReport).where(QualityReport.id == report_id)).scalar_one_or_none()

        if not dataset or not report:
            return {"error": "Not found"}

        _publish(f"quality:{report_id}", {"event": "analysis_started", "report_id": report_id})

        try:
            result = analyze_quality(dataset.file_path, dataset.file_format)

            report.overall_score = result["overall_score"]
            report.completeness_score = result["completeness_score"]
            report.uniqueness_score = result["uniqueness_score"]
            report.validity_score = result["validity_score"]
            report.consistency_score = result["consistency_score"]
            report.total_rows = result["total_rows"]
            report.passed_rows = result["passed_rows"]
            report.failed_rows = result["failed_rows"]
            report.issue_count = len(result["issues"])
            report.summary = result.get("summary")

            issue_type_map = {t.value: t for t in QualityIssueType}
            severity_map = {s.value: s for s in QualitySeverity}

            for issue_data in result["issues"]:
                issue = QualityIssue(
                    report_id=report_id,
                    issue_type=issue_type_map.get(issue_data["issue_type"], QualityIssueType.MISSING_VALUES),
                    severity=severity_map.get(issue_data["severity"], QualitySeverity.WARNING),
                    column_name=issue_data.get("column_name"),
                    description=issue_data["description"],
                    affected_rows=issue_data["affected_rows"],
                    affected_percentage=issue_data["affected_percentage"],
                    sample_values=issue_data.get("sample_values"),
                    suggestion=issue_data.get("suggestion"),
                )
                db.add(issue)

            db.commit()
            _publish(f"quality:{report_id}", {"event": "analysis_complete", "report_id": report_id, "score": result["overall_score"]})
            return {"status": "success", "score": result["overall_score"]}

        except Exception as ex:
            _publish(f"quality:{report_id}", {"event": "analysis_error", "report_id": report_id, "error": str(ex)})
            raise


@celery_app.task(bind=True, name="tasks.execute_pipeline")
def task_execute_pipeline(self, run_id: str) -> dict:
    from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun

    with SyncSession() as db:
        run = db.execute(select(PipelineRun).where(PipelineRun.id == run_id)).scalar_one_or_none()
        if not run:
            return {"error": "Run not found"}

        pipeline = db.execute(
            select(Pipeline).where(Pipeline.id == run.pipeline_id)
        ).scalar_one_or_none()
        if not pipeline:
            return {"error": "Pipeline not found"}

        nodes_q = db.execute(
            select(PipelineNode).where(PipelineNode.pipeline_id == pipeline.id)
        ).scalars().all()
        edges_q = db.execute(
            select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline.id)
        ).scalars().all()

        nodes = [
            {"id": n.id, "node_type": n.node_type, "label": n.label, "config": n.config}
            for n in nodes_q
        ]
        edges = [
            {"source_node_id": e.source_node_id, "target_node_id": e.target_node_id}
            for e in edges_q
        ]

        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.celery_task_id = self.request.id
        db.commit()

        _publish(f"pipeline_run:{run_id}", {
            "event": "run_started", "run_id": run_id,
            "status": RunStatus.RUNNING, "pipeline_id": pipeline.id
        })

        def progress_callback(stage: str, pct: int, records: int):
            run.current_stage = stage
            db.commit()
            _publish(f"pipeline_run:{run_id}", {
                "event": "progress",
                "run_id": run_id,
                "stage": stage,
                "progress": pct,
                "records": records,
            })

        start = time.time()
        try:
            result = execute_pipeline_graph(nodes, edges, progress_callback)
            duration = round(time.time() - start, 2)

            run.status = RunStatus.SUCCESS if result["failed_records"] == 0 else RunStatus.WARNING
            run.input_records = result["input_records"]
            run.output_records = result["output_records"]
            run.failed_records = result["failed_records"]
            run.duration_seconds = duration
            run.logs = result["logs"]
            run.metrics = result["metrics"]
            run.current_stage = "complete"
            run.completed_at = datetime.now(timezone.utc)

            pipeline.last_run_at = run.completed_at
            pipeline.last_run_status = run.status
            db.commit()

            _publish(f"pipeline_run:{run_id}", {
                "event": "run_complete",
                "run_id": run_id,
                "status": run.status,
                "input_records": run.input_records,
                "output_records": run.output_records,
                "failed_records": run.failed_records,
                "duration_seconds": duration,
            })
            return {"status": "success", "output_records": run.output_records}

        except Exception as ex:
            duration = round(time.time() - start, 2)
            run.status = RunStatus.FAILED
            run.error_message = str(ex)
            run.duration_seconds = duration
            run.completed_at = datetime.now(timezone.utc)
            pipeline.last_run_at = run.completed_at
            pipeline.last_run_status = RunStatus.FAILED
            db.commit()

            _publish(f"pipeline_run:{run_id}", {
                "event": "run_failed",
                "run_id": run_id,
                "status": RunStatus.FAILED,
                "error": str(ex),
            })
            raise

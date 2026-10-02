# DataFlow Worker

Celery worker process that handles:
- **Dataset profiling** — `tasks.profile_dataset`
- **Quality analysis** — `tasks.run_quality_analysis`  
- **Pipeline execution** — `tasks.execute_pipeline`

## Running locally

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

## Queues

| Task | Queue | Description |
|------|-------|-------------|
| `tasks.profile_dataset` | default | Pandas profiling of uploaded files |
| `tasks.run_quality_analysis` | default | Quality scoring and issue detection |
| `tasks.execute_pipeline` | default | Full pipeline graph execution |

## Progress updates

The worker publishes Redis pub/sub events to channels like `pipeline_run:{id}`,
`dataset:{id}`, and `quality:{id}`. The FastAPI WebSocket relay picks these up
and pushes them to connected browser clients.

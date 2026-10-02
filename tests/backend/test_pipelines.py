"""Tests: pipeline CRUD, execution engine."""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization


def pipeline_payload(name="Test Pipeline"):
    src_id = str(uuid.uuid4())
    out_id = str(uuid.uuid4())
    return {
        "name": name,
        "description": "Automated test pipeline",
        "nodes": [
            {"id": src_id, "node_type": "source", "label": "Source", "config": {"file_path": "/tmp/test.csv", "file_format": "csv"}, "position": {"x": 100, "y": 100}},
            {"id": out_id, "node_type": "output", "label": "Output", "config": {}, "position": {"x": 400, "y": 100}},
        ],
        "edges": [
            {"id": str(uuid.uuid4()), "source": src_id, "target": out_id},
        ],
    }


@pytest.mark.asyncio
async def test_create_pipeline(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    res = await client.post(
        f"/api/v1/orgs/{org.id}/pipelines",
        headers=auth_headers,
        json=pipeline_payload(),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Test Pipeline"
    assert len(body["nodes"]) == 2
    assert len(body["edges"]) == 1


@pytest.mark.asyncio
async def test_list_pipelines(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    res = await client.get(f"/api/v1/orgs/{org.id}/pipelines", headers=auth_headers)
    assert res.status_code == 200
    assert "items" in res.json()


@pytest.mark.asyncio
async def test_get_pipeline(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    create = await client.post(
        f"/api/v1/orgs/{org.id}/pipelines",
        headers=auth_headers,
        json=pipeline_payload("Get Test"),
    )
    pid = create.json()["id"]

    res = await client.get(f"/api/v1/orgs/{org.id}/pipelines/{pid}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == pid


@pytest.mark.asyncio
async def test_update_pipeline(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    create = await client.post(
        f"/api/v1/orgs/{org.id}/pipelines",
        headers=auth_headers,
        json=pipeline_payload("Before Update"),
    )
    pid = create.json()["id"]

    res = await client.put(
        f"/api/v1/orgs/{org.id}/pipelines/{pid}",
        headers=auth_headers,
        json={"name": "After Update", "status": "active"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "After Update"


@pytest.mark.asyncio
async def test_delete_pipeline(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    create = await client.post(
        f"/api/v1/orgs/{org.id}/pipelines",
        headers=auth_headers,
        json=pipeline_payload("To Delete"),
    )
    pid = create.json()["id"]

    res = await client.delete(f"/api/v1/orgs/{org.id}/pipelines/{pid}", headers=auth_headers)
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_pipeline_executor_unit():
    """Unit test the execution engine without DB."""
    import tempfile, os, csv, io
    from app.processing.pipeline_executor import execute_pipeline_graph
    from app.models.pipeline import NodeType

    # Create a real temp CSV
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "amount", "status"])
    for i in range(100):
        w.writerow([i, float(i * 10), "active" if i % 2 == 0 else "inactive"])

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(buf.getvalue().encode())
        path = f.name

    src_id = "n1"
    filter_id = "n2"
    out_id = "n3"

    nodes = [
        {"id": src_id,    "node_type": NodeType.SOURCE,    "label": "Source",    "config": {"file_path": path, "file_format": "csv"}},
        {"id": filter_id, "node_type": NodeType.FILTER,    "label": "Filter",    "config": {"column": "status", "operator": "eq", "value": "active"}},
        {"id": out_id,    "node_type": NodeType.OUTPUT,    "label": "Output",    "config": {}},
    ]
    edges = [
        {"source_node_id": src_id, "target_node_id": filter_id},
        {"source_node_id": filter_id, "target_node_id": out_id},
    ]

    result = execute_pipeline_graph(nodes, edges)

    assert result["input_records"] == 100
    assert result["output_records"] == 50  # only "active" rows
    assert len(result["logs"]) > 0
    os.unlink(path)

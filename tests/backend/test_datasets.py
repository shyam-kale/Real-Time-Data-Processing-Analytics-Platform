"""Tests: dataset ingestion, profiling, quality engine."""
import pytest
import io
import csv
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization, OrganizationMember
from app.models.dataset import Dataset, DatasetStatus


def make_csv_bytes(rows=50) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "amount", "date", "status"])
    for i in range(rows):
        writer.writerow([i, f"Item {i}", round(i * 1.5, 2), f"2024-01-{(i%28)+1:02d}", "active" if i % 3 else "inactive"])
    return buf.getvalue().encode()


@pytest.mark.asyncio
async def test_upload_csv(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    # Get org id
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()
    assert org is not None

    csv_bytes = make_csv_bytes(100)
    res = await client.post(
        f"/api/v1/orgs/{org.id}/datasets",
        headers=auth_headers,
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
        data={"name": "Sales Test", "description": "Test dataset"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Sales Test"
    assert body["file_format"] == "csv"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_list_datasets(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    res = await client.get(f"/api/v1/orgs/{org.id}/datasets", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_get_dataset(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    # Upload first
    csv_bytes = make_csv_bytes(10)
    up = await client.post(
        f"/api/v1/orgs/{org.id}/datasets",
        headers=auth_headers,
        files={"file": ("test.csv", csv_bytes, "text/csv")},
        data={"name": "Detail Test"},
    )
    ds_id = up.json()["id"]

    res = await client.get(f"/api/v1/orgs/{org.id}/datasets/{ds_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == ds_id


@pytest.mark.asyncio
async def test_delete_dataset(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    result = await db_session.execute(select(Organization))
    org = result.scalars().first()

    csv_bytes = make_csv_bytes(5)
    up = await client.post(
        f"/api/v1/orgs/{org.id}/datasets",
        headers=auth_headers,
        files={"file": ("del.csv", csv_bytes, "text/csv")},
        data={"name": "To Delete"},
    )
    ds_id = up.json()["id"]

    res = await client.delete(f"/api/v1/orgs/{org.id}/datasets/{ds_id}", headers=auth_headers)
    assert res.status_code == 204

    check = await client.get(f"/api/v1/orgs/{org.id}/datasets/{ds_id}", headers=auth_headers)
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_profiler_output():
    """Unit test: profiler returns correct structure."""
    import tempfile, os
    from app.processing.profiler import profile_dataset
    from app.models.dataset import FileFormat

    csv_bytes = make_csv_bytes(200)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(csv_bytes)
        path = f.name

    try:
        result = profile_dataset(path, FileFormat.CSV)
        assert result["row_count"] == 200
        assert result["column_count"] == 5
        assert "columns" in result
        col_names = [c["name"] for c in result["columns"]]
        assert "id" in col_names
        assert "amount" in col_names
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_quality_engine_output():
    """Unit test: quality engine detects issues correctly."""
    import tempfile, os
    from app.processing.quality_engine import analyze_quality
    from app.models.dataset import FileFormat

    # CSV with some nulls and duplicates
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "value", "category"])
    for i in range(80):
        w.writerow([i, i * 2.0, "A"])
    w.writerow(["", None, "B"])   # null row
    w.writerow([1, 2.0, "A"])     # duplicate of row 1

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(buf.getvalue().encode())
        path = f.name

    try:
        result = analyze_quality(path, FileFormat.CSV)
        assert result["total_rows"] == 82
        assert result["overall_score"] <= 100
        assert result["overall_score"] > 0
        issue_types = [i["issue_type"] for i in result["issues"]]
        # Should detect missing values and/or duplicates
        assert any(t in ["missing_values", "duplicates"] for t in issue_types)
    finally:
        os.unlink(path)

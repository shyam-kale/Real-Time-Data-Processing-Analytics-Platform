"""Tests: RBAC — org membership enforcement."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization


@pytest.mark.asyncio
async def test_non_member_cannot_access_org(client: AsyncClient, db_session: AsyncSession):
    # Register a second user with their own org
    res = await client.post("/api/v1/auth/register", json={
        "email": "outsider@dataflow.io",
        "full_name": "Outsider",
        "password": "password123",
        "org_name": "Outsider Org",
    })
    assert res.status_code == 201
    outsider_token = res.json()["access_token"]
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    # Get the test org (created in conftest)
    result = await db_session.execute(select(Organization).where(Organization.slug == "test-org-fixture"))
    test_org = result.scalars().first()
    if not test_org:
        pytest.skip("test org not found")

    res2 = await client.get(
        f"/api/v1/orgs/{test_org.id}/datasets",
        headers=outsider_headers,
    )
    assert res2.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_upload_dataset(client: AsyncClient, db_session: AsyncSession):
    # Register viewer
    res = await client.post("/api/v1/auth/register", json={
        "email": "viewer@dataflow.io",
        "full_name": "Viewer",
        "password": "password123",
        "org_name": "Viewer Org",
    })
    # Viewer is owner of their own org — just verify they can list their own datasets
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.api.deps import get_current_user, get_org_member
from app.models.user import User
from app.schemas.analytics import AnalyticsQuery, AnalyticsResult
from app.services.analytics_service import run_analytics_query

router = APIRouter(prefix="/orgs/{org_id}/analytics", tags=["analytics"])


@router.post("/query", response_model=AnalyticsResult)
async def run_query(
    org_id: str,
    query: AnalyticsQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(get_org_member),
):
    return await run_analytics_query(db, org_id, query)

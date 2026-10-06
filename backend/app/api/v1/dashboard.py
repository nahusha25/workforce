"""
Phase 5 — Director Dashboard API Router (DSH-001).
All endpoints require Director role.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.dashboard.filters import get_dashboard_filters
from app.modules.dashboard.schemas import (
    DashboardFilters,
    DashboardMetricsResponse,
)
from app.modules.dashboard.service import DashboardService

router = APIRouter()


@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all 8 aggregated dashboard metrics (DSH-001)",
)
async def get_dashboard_metrics(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> DashboardMetricsResponse:
    """
    Returns all 8 high-level dashboard metrics for the filtered period and scope.
    All metrics are computed live from supervisor-approved records only.
    """
    return await DashboardService.get_metrics(session=db, f=filters)

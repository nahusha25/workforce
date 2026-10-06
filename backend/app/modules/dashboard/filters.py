"""
Phase 5 — Dashboard & Reports Query Filters Dependency.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException, Query, status

from app.modules.dashboard.schemas import DashboardFilters


def get_dashboard_filters(
    date_from: Optional[date] = Query(
        None,
        description="Start date (YYYY-MM-DD), inclusive. Defaults to 30 days ago.",
    ),
    date_to: Optional[date] = Query(
        None,
        description="End date (YYYY-MM-DD), inclusive. Defaults to today.",
    ),
    client_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter records scoped to client ID.",
    ),
    site_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter records scoped to site ID.",
    ),
    employee_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter records scoped to employee ID.",
    ),
    supervisor_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter records scoped to sites supervised by supervisor ID.",
    ),
) -> DashboardFilters:
    """FastAPI dependency for dashboard & reports query parameters."""
    today = date.today()
    d_from = date_from if date_from is not None else (today - timedelta(days=30))
    d_to = date_to if date_to is not None else today

    if d_from > d_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must not be greater than date_to",
        )

    if (d_to - d_from).days > 365:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date range cannot exceed 365 days",
        )

    return DashboardFilters(
        date_from=d_from,
        date_to=d_to,
        client_id=client_id,
        site_id=site_id,
        employee_id=employee_id,
        supervisor_id=supervisor_id,
    )

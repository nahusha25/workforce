"""
Phase 5 — Reports & Export API Router (DSH-002 through DSH-008).
All endpoints require Director role.
"""
from __future__ import annotations

import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.dashboard.export import export_report
from app.modules.dashboard.filters import get_dashboard_filters
from app.modules.dashboard.schemas import (
    AttendanceReportResponse,
    DashboardFilters,
    InvoiceSummaryResponse,
    MaterialsReportResponse,
    PaymentSummaryResponse,
    ProductivityReportResponse,
    WorkReportResponse,
)
from app.modules.dashboard.service import DashboardService

router = APIRouter()


# ---------------------------------------------------------------------------
# Report: DSH-002 Attendance
# ---------------------------------------------------------------------------

@router.get(
    "/attendance",
    response_model=AttendanceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Approved attendance history report (DSH-002)",
)
async def get_attendance_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    status: Optional[str] = Query("approved", description="Filter by status, default 'approved'"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> AttendanceReportResponse:
    return await DashboardService.get_attendance_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
        status_filter=status,
    )


# ---------------------------------------------------------------------------
# Report: DSH-003 Work entries
# ---------------------------------------------------------------------------

@router.get(
    "/work",
    response_model=WorkReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Approved daily work progress report (DSH-003)",
)
async def get_work_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    activity_id: Optional[uuid.UUID] = Query(None, description="Filter by activity ID"),
    work_order_id: Optional[uuid.UUID] = Query(None, description="Filter by work order ID"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> WorkReportResponse:
    return await DashboardService.get_work_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
        activity_id=activity_id,
        work_order_id=work_order_id,
    )


# ---------------------------------------------------------------------------
# Report: DSH-004 Materials
# ---------------------------------------------------------------------------

@router.get(
    "/materials",
    response_model=MaterialsReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Material transactions report (DSH-004)",
)
async def get_materials_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (purchased|consumed)"),
    is_high_value: Optional[bool] = Query(None, description="Filter by high value flag"),
    status: Optional[str] = Query(None, description="Filter by transaction status (approved|draft|rejected)"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> MaterialsReportResponse:
    return await DashboardService.get_materials_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        is_high_value=is_high_value,
        status=status,
    )


# ---------------------------------------------------------------------------
# Report: DSH-005 Productivity
# ---------------------------------------------------------------------------

@router.get(
    "/productivity",
    response_model=ProductivityReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Employee productivity report with category breakdown (DSH-005)",
)
async def get_productivity_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    sort_category: Optional[str] = Query(None, description="Sort employees by ratio in this category"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> ProductivityReportResponse:
    return await DashboardService.get_productivity_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
        sort_category=sort_category,
    )


# ---------------------------------------------------------------------------
# Report: DSH-006 Payment summary (estimated preview)
# ---------------------------------------------------------------------------

@router.get(
    "/payment-summary",
    response_model=PaymentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Weekly estimated payment preview using effective rates (DSH-006)",
)
@router.get(
    "/payment",
    response_model=PaymentSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_payment_summary_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> PaymentSummaryResponse:
    return await DashboardService.get_payment_summary_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Report: DSH-007 Invoice summary
# ---------------------------------------------------------------------------

@router.get(
    "/invoice-summary",
    response_model=InvoiceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Client & site aggregated invoice summary (DSH-007)",
)
async def get_invoice_summary_report(
    filters: DashboardFilters = Depends(get_dashboard_filters),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> InvoiceSummaryResponse:
    return await DashboardService.get_invoice_summary_report(
        session=db,
        f=filters,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Report: DSH-008 Export (Excel / PDF)
# ---------------------------------------------------------------------------

@router.get(
    "/{report_type}/export",
    summary="Export any report to Excel or PDF as streaming response (DSH-008)",
)
async def export_report_endpoint(
    report_type: str,
    format: str = Query(..., description="Export format: 'xlsx' or 'pdf'"),
    filters: DashboardFilters = Depends(get_dashboard_filters),
    # Optional report-specific query params passed along:
    status: Optional[str] = Query(None),
    activity_id: Optional[uuid.UUID] = Query(None),
    work_order_id: Optional[uuid.UUID] = Query(None),
    transaction_type: Optional[str] = Query(None),
    is_high_value: Optional[bool] = Query(None),
    sort_category: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["director", "administrator"])),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Streams an in-memory generated Excel (.xlsx) or PDF (.pdf) file.
    Does not write temporary files to disk.
    """
    buf, media_type, filename = await export_report(
        session=db,
        report_type=report_type,
        export_format=format,
        filters=filters,
        status=status,
        activity_id=activity_id,
        work_order_id=work_order_id,
        transaction_type=transaction_type,
        is_high_value=is_high_value,
        sort_category=sort_category,
    )

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.invoices.schemas import (
    CancelInvoiceRequest,
    GenerateInvoiceRequest,
    InvoiceDetailResponse,
    InvoicePreviewRequest,
    InvoicePreviewResponse,
    InvoiceResponse,
    IssueInvoiceRequest,
    UpdateDraftInvoiceRequest,
)
from app.modules.invoices.service import InvoiceService

router = APIRouter()


@router.get(
    "/preview",
    response_model=InvoicePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview unbilled invoice data via query parameters",
)
async def preview_invoice_get(
    client_id: uuid.UUID = Query(..., description="Client ID"),
    project_id: uuid.UUID = Query(..., description="Project ID"),
    site_id: uuid.UUID = Query(..., description="Site ID"),
    period_start: date = Query(..., description="Start date of billing period (inclusive)"),
    period_end: date = Query(..., description="End date of billing period (inclusive)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Previews eligible approved work and material records for a single site and billing period
    without committing any changes or reserving sequence numbers.
    """
    return await InvoiceService.preview_invoice(
        session=db,
        client_id=client_id,
        project_id=project_id,
        site_id=site_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.post(
    "/preview",
    response_model=InvoicePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview unbilled invoice data via request body",
)
async def preview_invoice_post(
    request: InvoicePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Previews eligible approved work and material records using a JSON request body.
    """
    return await InvoiceService.preview_invoice(
        session=db,
        client_id=request.client_id,
        project_id=request.project_id,
        site_id=request.site_id,
        period_start=request.period_start,
        period_end=request.period_end,
    )


@router.post(
    "/generate",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate draft invoice from unbilled records",
)
@router.post(
    "",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate draft invoice from unbilled records (root alias)",
    include_in_schema=False,
)
async def generate_invoice(
    request: GenerateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Generates a draft invoice from unbilled approved work and material records.
    Locks records using partial unique indexes and snapshots rates/dates.
    Guarantees idempotency via `idempotency_key`.
    """
    return await InvoiceService.generate_invoice(
        session=db,
        request=request,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=List[InvoiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List invoices with filters",
)
async def list_invoices(
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client ID"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    site_id: Optional[uuid.UUID] = Query(None, description="Filter by site ID"),
    invoice_status: Optional[str] = Query(None, alias="status", description="Filter by status (draft, issued, partially_paid, paid, cancelled)"),
    period_start: Optional[date] = Query(None, description="Filter by billing period start date"),
    period_end: Optional[date] = Query(None, description="Filter by billing period end date"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Lists invoices with filtering by client, project, site, status, and period dates.
    """
    return await InvoiceService.list_invoices(
        session=db,
        client_id=client_id,
        project_id=project_id,
        site_id=site_id,
        status_filter=invoice_status,
        period_start=period_start,
        period_end=period_end,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice details by ID with line items",
)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Fetches comprehensive invoice details including line items, snapshot rates, and metadata.
    """
    return await InvoiceService.get_invoice(
        session=db,
        invoice_id=invoice_id,
    )


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update draft invoice metadata, tax, or rate overrides",
)
@router.put(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update draft invoice (PUT alias)",
    include_in_schema=False,
)
async def update_draft_invoice(
    invoice_id: uuid.UUID,
    request: UpdateDraftInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Updates client PO number, notes, remarks, tax, due date, or Director rate overrides on a draft invoice.
    Recalculates subtotals and total. Only allowed while the invoice is in draft status.
    """
    return await InvoiceService.update_draft_invoice(
        session=db,
        invoice_id=invoice_id,
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{invoice_id}/issue",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue draft invoice and permanently freeze financial amounts",
)
async def issue_invoice(
    invoice_id: uuid.UUID,
    request: Optional[IssueInvoiceRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Transitions draft invoice to 'issued' status. Permanently freezes all line items, rates,
    and financial calculations.
    """
    return await InvoiceService.issue_invoice(
        session=db,
        invoice_id=invoice_id,
        current_user_id=current_user.id,
        request=request,
    )


@router.post(
    "/{invoice_id}/cancel",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel invoice and release source locks atomically",
)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    request: CancelInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Cancels a draft or unpaid issued invoice with a mandatory cancellation reason.
    Atomically releases active line item locks in the same database transaction so
    operational records become eligible for re-invoicing.
    Paid or partially paid invoices cannot be cancelled.
    """
    return await InvoiceService.cancel_invoice(
        session=db,
        invoice_id=invoice_id,
        request=request,
        current_user_id=current_user.id,
    )

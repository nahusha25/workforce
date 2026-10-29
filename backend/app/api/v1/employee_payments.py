from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.employee_payments.schemas import (
    CancelPaymentRequest,
    EmployeePaymentDetailResponse,
    EmployeePaymentPreviewResponse,
    EmployeePaymentResponse,
    GeneratePaymentRequest,
    PayPaymentRequest,
)
from app.modules.employee_payments.service import EmployeePaymentService

router = APIRouter()


@router.get(
    "/preview",
    response_model=EmployeePaymentPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview employee payment calculations without persisting records",
)
async def preview_employee_payments(
    period_start: date = Query(..., description="Start date of payment period (inclusive)"),
    period_end: date = Query(..., description="End date of payment period (inclusive)"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Optional specific employee ID to preview"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.preview_payments(
        session=db,
        period_start=period_start,
        period_end=period_end,
        employee_id=employee_id,
    )


@router.post(
    "/generate",
    response_model=List[EmployeePaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate draft employee payment records with source-locking and idempotency",
)
async def generate_employee_payments(
    request: GeneratePaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.generate_payments(
        session=db,
        request=request,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=List[EmployeePaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="List employee payment records with filters",
)
async def list_employee_payments(
    period_start: Optional[date] = Query(None, description="Filter by period start date"),
    period_end: Optional[date] = Query(None, description="Filter by period end date"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee"),
    payment_status: Optional[str] = Query(None, alias="status", description="Filter by status (draft, approved, paid, cancelled)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.list_payments(
        session=db,
        period_start=period_start,
        period_end=period_end,
        employee_id=employee_id,
        status_filter=payment_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{payment_id}",
    response_model=EmployeePaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single employee payment details with itemized lines and rate band summaries",
)
async def get_employee_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.get_payment(
        session=db,
        payment_id=payment_id,
    )


@router.post(
    "/{payment_id}/approve",
    response_model=EmployeePaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve draft employee payment",
)
async def approve_employee_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.approve_payment(
        session=db,
        payment_id=payment_id,
        current_user=current_user,
    )


@router.post(
    "/{payment_id}/pay",
    response_model=EmployeePaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark approved employee payment as paid",
)
async def mark_employee_payment_paid(
    payment_id: uuid.UUID,
    request: PayPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.mark_as_paid(
        session=db,
        payment_id=payment_id,
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{payment_id}/cancel",
    response_model=EmployeePaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel employee payment and release source locks",
)
async def cancel_employee_payment(
    payment_id: uuid.UUID,
    request: CancelPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    return await EmployeePaymentService.cancel_payment(
        session=db,
        payment_id=payment_id,
        request=request,
        current_user=current_user,
    )

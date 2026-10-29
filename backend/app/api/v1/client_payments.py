from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.client_payments.schemas import (
    ClientPaymentResponse,
    RecordPaymentRequest,
    VoidPaymentRequest,
)
from app.modules.client_payments.service import ClientPaymentService

router = APIRouter()


@router.post(
    "",
    response_model=ClientPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a client payment against an invoice",
)
async def record_payment(
    request: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Records a payment against an issued or partially paid invoice.
    Restricted to Director and Administrator roles only.
    Enforces atomic invoice row lock, overpayment rejection, date checks, and idempotent replay.
    """
    payment = await ClientPaymentService.record_payment(
        session=db,
        request=request,
        current_user=current_user,
    )
    return ClientPaymentResponse.model_validate(payment)


@router.get(
    "/invoice/{invoice_id}",
    response_model=List[ClientPaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all payments recorded for an invoice",
)
async def list_payments_for_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Lists all client payment transactions (active and voided) for the specified invoice,
    ordered by payment_date descending.
    """
    payments = await ClientPaymentService.list_payments_for_invoice(
        session=db,
        invoice_id=invoice_id,
    )
    return [ClientPaymentResponse.model_validate(p) for p in payments]


@router.get(
    "",
    response_model=List[ClientPaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="List payments with optional invoice filter",
)
async def list_payments_query(
    invoice_id: uuid.UUID = Query(..., description="Filter payments by invoice ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Query parameter variant for listing payments by invoice_id.
    """
    payments = await ClientPaymentService.list_payments_for_invoice(
        session=db,
        invoice_id=invoice_id,
    )
    return [ClientPaymentResponse.model_validate(p) for p in payments]


@router.get(
    "/{payment_id}",
    response_model=ClientPaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment details by ID",
)
async def get_payment_detail(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Retrieves full details for a single client payment record.
    """
    payment = await ClientPaymentService.get_payment_by_id(
        session=db,
        payment_id=payment_id,
    )
    return ClientPaymentResponse.model_validate(payment)


@router.post(
    "/{payment_id}/void",
    response_model=ClientPaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Void a recorded payment",
)
async def void_payment(
    payment_id: uuid.UUID,
    request: VoidPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Voids an active client payment.
    Requires mandatory void reason (>= 10 trimmed characters) and void idempotency key.
    Atomically recalculates the parent invoice's paid_amount cache and transitions invoice status.
    """
    payment = await ClientPaymentService.void_payment(
        session=db,
        payment_id=payment_id,
        request=request,
        current_user=current_user,
    )
    return ClientPaymentResponse.model_validate(payment)


@router.post(
    "/{payment_id}/receipt",
    response_model=ClientPaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload or replace receipt for a recorded client payment",
)
async def upload_payment_receipt(
    payment_id: uuid.UUID,
    file: UploadFile = File(..., description="Receipt document (PDF) or image (JPEG, PNG, WebP) up to 10MB"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Attaches or replaces a receipt attachment for an active recorded client payment.
    Restricted to Director and Administrator roles.
    Rejects uploads for voided payments.
    Safely unlinks existing receipt file upon replacement.
    """
    file_bytes = await file.read()
    payment = await ClientPaymentService.upload_receipt(
        session=db,
        payment_id=payment_id,
        file_bytes=file_bytes,
        filename=file.filename or "receipt",
        content_type=file.content_type,
        current_user=current_user,
    )
    return ClientPaymentResponse.model_validate(payment)


@router.get(
    "/{payment_id}/receipt",
    status_code=status.HTTP_200_OK,
    summary="Download or view receipt attachment for a client payment",
)
async def get_payment_receipt(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator"])),
):
    """
    Secure authenticated access to receipt attachment.
    Requires Director or Administrator authorization.
    Serves files from private storage; not exposed via static mounts.
    """
    result = await ClientPaymentService.get_receipt(
        session=db,
        payment_id=payment_id,
        current_user=current_user,
    )
    if result.file_path:
        return FileResponse(
            path=result.file_path,
            media_type=result.media_type,
            filename=result.filename,
            content_disposition_type="inline",
        )
    return Response(
        content=result.file_bytes,
        media_type=result.media_type,
        headers={"Content-Disposition": f'inline; filename="{result.filename}"'},
    )


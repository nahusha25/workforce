from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.client_payments import ClientPayment
from app.models.invoices import Invoice
from app.models.system import AuditLog
from app.modules.client_payments.schemas import (
    ALLOWED_PAYMENT_METHODS,
    ClientPaymentResponse,
    InvoicePaymentsSummaryResponse,
    RecordPaymentRequest,
    VoidPaymentRequest,
)
from app.shared.file_storage import (
    AmbiguousReceiptStorageError,
    FileSizeLimitExceededError,
    FileStorageError,
    FileStorageService,
    InvalidFileTypeError,
    LocalFileStorage,
    ReceiptFileResult,
    get_file_storage,
    get_receipt_file_path,
    save_receipt_file,
    validate_receipt_file,
)


class ClientPaymentService:
    @staticmethod
    def _round(val: Decimal | float | int) -> Decimal:
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _verify_authorization(cls, current_user: Optional[User], action_desc: str = "record/void client payments") -> None:
        """Enforces RBAC: Only director and administrator roles can record or void client payments."""
        if not current_user or current_user.role not in ("director", "administrator"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Only directors and administrators are permitted to {action_desc}.",
            )

    @staticmethod
    async def _generate_payment_number(session: AsyncSession) -> str:
        """
        Generates a forward-only unique client payment number using client_payment_number_seq.
        Format: CP-YYYYMMDD-XXXX (e.g. CP-20261008-0001).
        Concurrency safe; sequence gaps from rollback or concurrent failures are acceptable.
        """
        seq_val = (await session.execute(text("SELECT nextval('client_payment_number_seq')"))).scalar()
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"CP-{today_str}-{seq_val:04d}"

    @classmethod
    async def record_payment(
        cls,
        session: AsyncSession,
        request: RecordPaymentRequest,
        current_user: User,
    ) -> ClientPayment:
        """
        Records a funds transfer against an issued or partially paid invoice.
        Rules:
          - Only director or administrator
          - Idempotent replay: if idempotency_key matches an existing payment with identical parameters, return it.
          - If idempotency_key matches with conflicting parameters, return HTTP 409 Conflict.
          - Locks parent invoice row with FOR UPDATE first
          - Payments allowed only against 'issued' or 'partially_paid' invoices
          - Payment date cannot be in the future
          - Payment date cannot be before invoice issue_date
          - Overpayment rejected (cannot exceed invoice.total_amount - invoice.paid_amount)
          - Atomically updates invoices.paid_amount and transitions invoice status (partially_paid / paid).
        """
        cls._verify_authorization(current_user, "record client payments")

        amount = cls._round(request.amount)
        if amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Payment amount must be greater than zero.",
            )

        if request.payment_method not in ALLOWED_PAYMENT_METHODS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid payment method '{request.payment_method}'. Allowed: {', '.join(sorted(ALLOWED_PAYMENT_METHODS))}",
            )

        today = datetime.now(timezone.utc).date()
        if request.payment_date > today:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Payment date '{request.payment_date}' cannot be in the future.",
            )

        # 1. Check idempotency key before locking
        stmt_idem = select(ClientPayment).where(ClientPayment.idempotency_key == request.idempotency_key)
        existing = (await session.execute(stmt_idem)).scalar_one_or_none()
        if existing:
            # Check for replay match
            if (
                existing.invoice_id == request.invoice_id
                and existing.amount == amount
                and existing.payment_date == request.payment_date
                and existing.payment_method == request.payment_method
            ):
                return existing
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency conflict: idempotency_key '{request.idempotency_key}' already used with different payment parameters.",
            )

        # 2. Lock parent invoice FOR UPDATE
        stmt_inv = select(Invoice).where(Invoice.id == request.invoice_id).with_for_update()
        invoice = (await session.execute(stmt_inv)).scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found.",
            )

        # 3. Validate invoice eligibility
        if invoice.status == "draft":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Payments cannot be recorded against draft invoices. Issue the invoice first.",
            )
        if invoice.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Payments cannot be recorded against cancelled invoices.",
            )
        if invoice.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invoice is already fully paid. No further payments can be recorded.",
            )
        if invoice.status not in ("issued", "partially_paid"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Payments cannot be recorded against invoices with status '{invoice.status}'.",
            )

        if invoice.issue_date and request.payment_date < invoice.issue_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Payment date '{request.payment_date}' cannot precede invoice issue date '{invoice.issue_date}'.",
            )

        # 4. Calculate current active paid amount and check overpayment
        stmt_paid = (
            select(func.coalesce(func.sum(ClientPayment.amount), Decimal("0.00")))
            .where(ClientPayment.invoice_id == invoice.id, ClientPayment.status == "recorded")
        )
        current_paid = cls._round((await session.execute(stmt_paid)).scalar() or Decimal("0.00"))
        outstanding_balance = cls._round(invoice.total_amount - current_paid)

        if amount > outstanding_balance:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Payment amount (₹{amount:.2f}) exceeds outstanding balance (₹{outstanding_balance:.2f}). Overpayment is not permitted.",
            )

        # 5. Generate forward-only payment number
        payment_number = await cls._generate_payment_number(session)

        # 6. Create payment
        payment = ClientPayment(
            id=uuid.uuid4(),
            payment_number=payment_number,
            idempotency_key=request.idempotency_key,
            invoice_id=invoice.id,
            amount=amount,
            payment_date=request.payment_date,
            payment_method=request.payment_method,
            reference_number=request.reference_number.strip() if request.reference_number else None,
            notes=request.notes.strip() if request.notes else None,
            receipt_url=request.receipt_url.strip() if request.receipt_url else None,
            status="recorded",
            recorded_by=current_user.id,
        )
        session.add(payment)
        await session.flush()

        # 7. Update transactional cache on parent invoice
        new_paid = cls._round(current_paid + amount)
        invoice.paid_amount = new_paid
        if invoice.paid_amount == invoice.total_amount:
            invoice.status = "paid"
        else:
            invoice.status = "partially_paid"

        try:
            await session.commit()
            await session.refresh(payment)
        except IntegrityError as exc:
            await session.rollback()
            # Handle potential concurrent race on idempotency key
            stmt_recheck = select(ClientPayment).where(ClientPayment.idempotency_key == request.idempotency_key)
            existing_after_race = (await session.execute(stmt_recheck)).scalar_one_or_none()
            if existing_after_race:
                if (
                    existing_after_race.invoice_id == request.invoice_id
                    and existing_after_race.amount == amount
                    and existing_after_race.payment_date == request.payment_date
                    and existing_after_race.payment_method == request.payment_method
                ):
                    return existing_after_race
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency conflict: idempotency_key '{request.idempotency_key}' already used with different payment parameters.",
                )
            raise exc

        return payment

    @classmethod
    async def void_payment(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        request: VoidPaymentRequest,
        current_user: User,
    ) -> ClientPayment:
        """
        Voids an active client payment.
        Rules:
          - Only director or administrator
          - Mandatory void reason (min 10 trimmed characters)
          - Mandatory void_idempotency_key
          - Lock parent invoice FOR UPDATE first to prevent concurrency races
          - Replay idempotency: if payment is already voided with the exact same void_idempotency_key, return it.
          - If already voided with a different key, raise HTTP 409 Conflict.
          - If void_idempotency_key is already used on another payment, raise HTTP 409 Conflict.
          - Sets status='voided', voided_by, voided_at, void_reason, void_idempotency_key
          - Atomically recalculates parent invoice paid_amount and transitions status (paid -> partially_paid / issued).
        """
        cls._verify_authorization(current_user, "void client payments")

        cleaned_reason = request.void_reason.strip() if request.void_reason else ""
        if len(cleaned_reason) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Void reason must contain at least 10 non-whitespace characters.",
            )

        void_idem = request.void_idempotency_key.strip() if request.void_idempotency_key else ""
        if not void_idem:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="void_idempotency_key is required.",
            )

        # 1. Fetch payment to identify parent invoice
        payment = await session.get(ClientPayment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client payment not found.",
            )

        # 2. Strict lock order: Lock parent invoice FOR UPDATE first
        stmt_inv = select(Invoice).where(Invoice.id == payment.invoice_id).with_for_update()
        invoice = (await session.execute(stmt_inv)).scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent invoice not found.",
            )

        # 3. Lock payment FOR UPDATE
        payment = (
            await session.execute(
                select(ClientPayment).where(ClientPayment.id == payment_id).with_for_update()
            )
        ).scalar_one()

        # 4. Check if already voided
        if payment.status == "voided":
            if payment.void_idempotency_key == void_idem:
                # Idempotent replay: return already-voided record without re-adjusting balance
                return payment
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment '{payment.payment_number}' is already voided with a different void idempotency key.",
            )

        # 5. Check if void_idempotency_key is already used by another payment
        stmt_other = select(ClientPayment).where(ClientPayment.void_idempotency_key == void_idem)
        other_voided = (await session.execute(stmt_other)).scalar_one_or_none()
        if other_voided and other_voided.id != payment.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"void_idempotency_key '{void_idem}' is already used by payment '{other_voided.payment_number}'.",
            )

        # 6. Apply void metadata
        old_status = payment.status
        payment.status = "voided"
        payment.voided_by = current_user.id
        payment.voided_at = datetime.now(timezone.utc)
        payment.void_reason = cleaned_reason
        payment.void_idempotency_key = void_idem
        await session.flush()

        # 7. Recalculate parent invoice paid amount and status
        stmt_paid = (
            select(func.coalesce(func.sum(ClientPayment.amount), Decimal("0.00")))
            .where(ClientPayment.invoice_id == invoice.id, ClientPayment.status == "recorded")
        )
        new_paid = cls._round((await session.execute(stmt_paid)).scalar() or Decimal("0.00"))
        invoice.paid_amount = new_paid

        # Lifecycle transition on voiding:
        # paid -> partially_paid (if remaining balance > 0)
        # paid/partially_paid -> issued (if remaining paid_amount == 0)
        if invoice.paid_amount == Decimal("0.00"):
            invoice.status = "issued"
        elif Decimal("0.00") < invoice.paid_amount < invoice.total_amount:
            invoice.status = "partially_paid"
        else:
            invoice.status = "paid"

        # 8. Record centralized AuditLog entry in the same transaction
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="client_payment",
            entity_id=payment.id,
            action="client_payment_voided",
            changed_by=current_user.id,
            created_at=payment.voided_at,
            previous_values={
                "status": old_status,
                "amount": str(payment.amount),
                "invoice_id": str(payment.invoice_id),
                "payment_number": payment.payment_number,
            },
            new_values={
                "status": "voided",
                "void_reason": cleaned_reason,
                "void_idempotency_key": void_idem,
            },
        )
        session.add(audit_entry)

        await session.commit()
        await session.refresh(payment)
        return payment

    @classmethod
    async def get_payment_by_id(cls, session: AsyncSession, payment_id: uuid.UUID) -> ClientPayment:
        """Fetches a ClientPayment by ID, raising 404 if not found."""
        payment = await session.get(ClientPayment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client payment not found.",
            )
        return payment

    @classmethod
    async def list_payments_for_invoice(cls, session: AsyncSession, invoice_id: uuid.UUID) -> List[ClientPayment]:
        """Fetches all payments for an invoice ordered by payment_date DESC, created_at DESC."""
        invoice = await session.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found.",
            )

        stmt = (
            select(ClientPayment)
            .where(ClientPayment.invoice_id == invoice_id)
            .order_by(ClientPayment.payment_date.desc(), ClientPayment.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def recalculate_invoice_paid_amount(
        cls,
        session: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> Tuple[Decimal, str]:
        """
        Atomically reconciles parent invoice paid_amount cache from active recorded payments.
        Updates invoice.status accordingly.
        Returns (paid_amount, status).
        """
        stmt_inv = select(Invoice).where(Invoice.id == invoice_id).with_for_update()
        invoice = (await session.execute(stmt_inv)).scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found.",
            )

        stmt_paid = (
            select(func.coalesce(func.sum(ClientPayment.amount), Decimal("0.00")))
            .where(ClientPayment.invoice_id == invoice.id, ClientPayment.status == "recorded")
        )
        new_paid = cls._round((await session.execute(stmt_paid)).scalar() or Decimal("0.00"))
        invoice.paid_amount = new_paid

        if invoice.status not in ("draft", "cancelled"):
            if invoice.paid_amount == Decimal("0.00"):
                invoice.status = "issued"
            elif Decimal("0.00") < invoice.paid_amount < invoice.total_amount:
                invoice.status = "partially_paid"
            elif invoice.paid_amount == invoice.total_amount:
                invoice.status = "paid"

        await session.commit()
        return invoice.paid_amount, invoice.status

    @classmethod
    async def upload_receipt(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
        current_user: Optional[User] = None,
        storage: Optional[FileStorageService] = None,
        base_dir: Optional[Path] = None,
    ) -> ClientPayment:
        """
        Attaches or replaces a receipt document/image for an active recorded client payment.
        Rules:
          - Only director or administrator
          - Payment must exist
          - Rejects receipt attachment for voided payments (422)
          - Validates file format (PDF, JPG, PNG, WebP) and size (<= 10MB) before touching storage or DB
          - Safe replacement: Saves new receipt first without deleting existing file.
          - If DB update fails, rolls back DB, deletes newly uploaded candidate file, and preserves existing receipt.
          - Only after DB commit succeeds, cleans up old receipt file.
        """
        cls._verify_authorization(current_user, "upload client payment receipts")

        # 1. Acquire row lock on payment FOR UPDATE to prevent concurrent races
        stmt = select(ClientPayment).where(ClientPayment.id == payment_id).with_for_update()
        payment = (await session.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client payment not found.",
            )

        if payment.status == "voided":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot attach or replace receipt on a voided payment.",
            )

        # 2. Validate file format and size before touching storage or DB
        try:
            mime = validate_receipt_file(file_bytes, content_type=content_type)
        except (InvalidFileTypeError, FileSizeLimitExceededError, FileStorageError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        # 3. Storage provider resolution
        if storage is not None:
            storage_client = storage
        elif base_dir is not None:
            storage_client = LocalFileStorage(receipts_dir=base_dir)
        else:
            storage_client = get_file_storage()

        # 4. Check for existing receipt prior to new upload
        has_existing = bool(payment.receipt_url)
        old_storage_ref = payment.receipt_url

        # 5. Save new receipt candidate (existing receipt is NOT deleted yet)
        try:
            new_storage_ref, _ = await storage_client.upload_receipt(
                payment_id=payment.id,
                file_bytes=file_bytes,
                original_filename=filename,
                content_type=mime,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save receipt file: {str(exc)}",
            )

        # 6. Update payment metadata and insert audit log entry
        payment.receipt_url = new_storage_ref
        payment.updated_at = datetime.now(timezone.utc)

        if current_user and getattr(current_user, "id", None):
            action = "receipt_replacement" if has_existing else "receipt_upload"
            audit_entry = AuditLog(
                id=uuid.uuid4(),
                entity_type="client_payment",
                entity_id=payment.id,
                action=action,
                changed_by=current_user.id,
                created_at=datetime.now(timezone.utc),
                previous_values={
                    "receipt_url": f"/api/v1/client-payments/{payment.id}/receipt",
                    "storage_ref": old_storage_ref,
                } if has_existing else None,
                new_values={
                    "receipt_url": f"/api/v1/client-payments/{payment.id}/receipt",
                    "storage_ref": new_storage_ref,
                    "filename": filename,
                },
            )
            session.add(audit_entry)

        # 7. Database commit block ONLY
        try:
            await session.commit()
        except Exception as exc:
            # If DB commit fails, clean up the candidate file first so no orphan is left.
            try:
                await storage_client.delete_receipt(payment.id, storage_ref=new_storage_ref)
            except Exception:
                pass
            try:
                await session.rollback()
            except Exception:
                pass
            # Old receipt was untouched and remains intact!
            raise exc

        # 8. Decoupled post-commit refresh (never delete candidate on refresh failure)
        try:
            await session.refresh(payment)
        except Exception:
            pass

        # 9. Post-commit cleanup: only after DB commit succeeds, clean up old receipt files
        # Uses exact storage reference, not timestamp-based guesses!
        if has_existing and old_storage_ref and old_storage_ref != new_storage_ref:
            try:
                if not old_storage_ref.startswith("/api/"):
                    await storage_client.delete_receipt(payment.id, storage_ref=old_storage_ref)
                elif hasattr(storage_client, "delete_old_receipts"):
                    await storage_client.delete_old_receipts(payment.id, keep_ref=new_storage_ref)
            except Exception:
                pass

        return payment

    @classmethod
    async def get_receipt(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        current_user: Optional[User] = None,
        storage: Optional[FileStorageService] = None,
        base_dir: Optional[Path] = None,
    ) -> ReceiptFileResult:
        """
        Retrieves receipt file for a payment.
        Rules:
          - Only director or administrator
          - Payment must exist
          - Must have receipt_url attached
          - Returns ReceiptFileResult (can be unpacked as (file_path, media_type, filename))
          - Works on both active and voided payments (audit integrity)
        """
        cls._verify_authorization(current_user, "access client payment receipts")

        payment = await session.get(ClientPayment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client payment not found.",
            )

        if not payment.receipt_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No receipt attached to this payment.",
            )

        if storage is not None:
            storage_client = storage
        elif base_dir is not None:
            storage_client = LocalFileStorage(receipts_dir=base_dir)
        else:
            storage_client = get_file_storage()

        try:
            result = await storage_client.get_receipt(payment.id, storage_ref=payment.receipt_url)
        except AmbiguousReceiptStorageError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Receipt reference is ambiguous: multiple receipt files exist in storage for this payment. Manual reconciliation is required.",
            )

        if not result or (not result.file_path and not result.file_bytes):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt file not found in storage.",
            )

        return result


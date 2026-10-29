from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from app.models.auth import User
from app.shared.file_storage import LocalFileStorage, S3FileStorage
from app.models.client_payments import ClientPayment
from app.models.invoices import Invoice
from app.models.operations import Client, Project, Site
from app.models.system import AuditLog
from app.modules.client_payments.schemas import RecordPaymentRequest, VoidPaymentRequest
from app.modules.client_payments.service import ClientPaymentService
from app.modules.invoices.schemas import CancelInvoiceRequest
from app.modules.invoices.service import InvoiceService
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture
async def payment_service_db():
    """Sets up users (director, admin, supervisor, employee) and master data with an issued invoice."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        director = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="director")
        admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="administrator")
        supervisor = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        employee = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")
        session.add_all([director, admin, supervisor, employee])
        await session.flush()

        # 2. Master data
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        # 3. Issued invoice with total 50,000.00
        invoice = Invoice(
            id=_u(),
            invoice_number=f"INV-{sfx.upper()}",
            idempotency_key=f"inv_idem_{sfx}",
            client_id=client.id,
            project_id=project.id,
            site_id=site.id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            issue_date=date(2026, 10, 7),
            due_date=date(2026, 10, 21),
            status="issued",
            subtotal_work=Decimal("40000.00"),
            subtotal_material=Decimal("5000.00"),
            tax_amount=Decimal("5000.00"),
            total_amount=Decimal("50000.00"),
            paid_amount=Decimal("0.00"),
            created_by=director.id,
            issued_by=director.id,
        )
        session.add(invoice)
        await session.commit()

        return {
            "director": director,
            "admin": admin,
            "supervisor": supervisor,
            "employee": employee,
            "client": client,
            "project": project,
            "site": site,
            "invoice": invoice,
        }


@pytest.mark.asyncio
async def test_record_payment_normal_partial(payment_service_db):
    """Verifies recording a valid partial payment transitions invoice to 'partially_paid' and updates paid_amount."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    req = RecordPaymentRequest(
        idempotency_key=f"idem_norm_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("20000.00"),
        payment_date=date(2026, 10, 8),
        payment_method="neft",
        reference_number="NEFT999888",
        notes="First tranche",
    )

    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(session, req, current_user=data["director"])
        assert payment.amount == Decimal("20000.00")
        assert payment.status == "recorded"
        assert payment.payment_number.startswith("CP-")

    # Verify parent invoice updated
    async with TestingSessionLocal() as session:
        updated_inv = await session.get(Invoice, inv.id)
        assert updated_inv.paid_amount == Decimal("20000.00")
        assert updated_inv.status == "partially_paid"


@pytest.mark.asyncio
async def test_record_payment_full_payment(payment_service_db):
    """Verifies that paying the exact total balance sets invoice status to 'paid'."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    req = RecordPaymentRequest(
        idempotency_key=f"idem_full_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("50000.00"),
        payment_date=date(2026, 10, 8),
        payment_method="rtgs",
        reference_number="RTGS123456",
    )

    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(session, req, current_user=data["admin"])
        assert payment.amount == Decimal("50000.00")
        assert payment.status == "recorded"

    async with TestingSessionLocal() as session:
        updated_inv = await session.get(Invoice, inv.id)
        assert updated_inv.paid_amount == Decimal("50000.00")
        assert updated_inv.status == "paid"


@pytest.mark.asyncio
async def test_multiple_payments_and_exact_cache_synchronization(payment_service_db):
    """Verifies multi-tranche payments strictly maintain invoices.paid_amount == SUM(amount WHERE recorded)."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Tranche 1: 10,000
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_t1_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("10000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )

    # Tranche 2: 15,000
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_t2_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("15000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="upi",
            ),
            data["director"],
        )

    async with TestingSessionLocal() as session:
        recalc_paid, recalc_status = await ClientPaymentService.recalculate_invoice_paid_amount(session, inv.id)
        assert recalc_paid == Decimal("25000.00")
        assert recalc_status == "partially_paid"

    # Tranche 3: Remaining 25,000
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_t3_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("25000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="cheque",
            ),
            data["director"],
        )

    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("50000.00")
        assert inv_check.status == "paid"


@pytest.mark.asyncio
async def test_record_payment_invalid_invoice_statuses(payment_service_db):
    """Verifies payment rejection on draft, cancelled, or already paid invoices."""
    data = payment_service_db
    sfx = str(_u())[:8]

    # 1. Draft invoice
    async with TestingSessionLocal() as session:
        draft_inv = Invoice(
            id=_u(),
            invoice_number=f"INV-DRAFT-{sfx}",
            idempotency_key=f"idem_draft_{sfx}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="draft",
            total_amount=Decimal("10000.00"),
        )
        session.add(draft_inv)
        await session.commit()

        req = RecordPaymentRequest(
            idempotency_key=f"idem_p_draft_{sfx}",
            invoice_id=draft_inv.id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
        )
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "draft" in exc_info.value.detail

    # 2. Cancelled invoice
    async with TestingSessionLocal() as session:
        can_inv = Invoice(
            id=_u(),
            invoice_number=f"INV-CAN-{sfx}",
            idempotency_key=f"idem_can_{sfx}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="cancelled",
            total_amount=Decimal("10000.00"),
        )
        session.add(can_inv)
        await session.commit()

        req = RecordPaymentRequest(
            idempotency_key=f"idem_p_can_{sfx}",
            invoice_id=can_inv.id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
        )
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "cancelled" in exc_info.value.detail

    # 3. Already paid invoice
    async with TestingSessionLocal() as session:
        paid_inv = Invoice(
            id=_u(),
            invoice_number=f"INV-PAID-{sfx}",
            idempotency_key=f"idem_paid_{sfx}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            issue_date=date(2026, 10, 7),
            status="paid",
            total_amount=Decimal("10000.00"),
            paid_amount=Decimal("10000.00"),
        )
        session.add(paid_inv)
        await session.commit()

        req = RecordPaymentRequest(
            idempotency_key=f"idem_p_paid_{sfx}",
            invoice_id=paid_inv.id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
        )
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "already fully paid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_record_payment_overpayment_rejected(payment_service_db):
    """Verifies that paying even ₹0.01 more than outstanding balance is rejected."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Outstanding balance is 50,000.00
    req = RecordPaymentRequest(
        idempotency_key=f"idem_over_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("50000.01"),
        payment_date=date(2026, 10, 8),
        payment_method="neft",
    )

    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "exceeds outstanding balance" in exc_info.value.detail


@pytest.mark.asyncio
async def test_record_payment_future_date_rejected(payment_service_db):
    """Verifies that future payment dates are rejected."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)

    req = RecordPaymentRequest(
        idempotency_key=f"idem_fut_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("1000.00"),
        payment_date=tomorrow,
        payment_method="neft",
    )

    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "cannot be in the future" in exc_info.value.detail


@pytest.mark.asyncio
async def test_record_payment_pre_issue_date_rejected(payment_service_db):
    """Verifies that payment dates preceding invoice.issue_date are rejected."""
    data = payment_service_db
    inv = data["invoice"]  # issue_date is 2026-10-07
    sfx = str(_u())[:8]

    req = RecordPaymentRequest(
        idempotency_key=f"idem_pre_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("1000.00"),
        payment_date=date(2026, 10, 6),  # Before 2026-10-07
        payment_method="neft",
    )

    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["director"])
        assert exc_info.value.status_code == 422
        assert "cannot precede invoice issue date" in exc_info.value.detail


@pytest.mark.asyncio
async def test_record_payment_duplicate_idempotency_replay(payment_service_db):
    """Verifies that resubmitting the identical payment request returns existing payment without double counting."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    req = RecordPaymentRequest(
        idempotency_key=f"idem_replay_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("15000.00"),
        payment_date=date(2026, 10, 8),
        payment_method="neft",
    )

    # First call
    async with TestingSessionLocal() as session:
        p1 = await ClientPaymentService.record_payment(session, req, data["director"])
        assert p1.amount == Decimal("15000.00")

    # Second call (replay)
    async with TestingSessionLocal() as session:
        p2 = await ClientPaymentService.record_payment(session, req, data["director"])
        assert p2.id == p1.id
        assert p2.payment_number == p1.payment_number

    # Verify paid_amount is NOT doubled
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("15000.00")


@pytest.mark.asyncio
async def test_record_payment_conflicting_idempotency_key(payment_service_db):
    """Verifies that reusing the same idempotency key with conflicting parameters raises HTTP 409 Conflict."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    shared_key = f"idem_conflict_{sfx}"

    # First payment
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=shared_key,
                invoice_id=inv.id,
                amount=Decimal("5000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )

    # Conflicting payment (different amount)
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(
                session,
                RecordPaymentRequest(
                    idempotency_key=shared_key,
                    invoice_id=inv.id,
                    amount=Decimal("6000.00"),  # conflicting
                    payment_date=date(2026, 10, 8),
                    payment_method="neft",
                ),
                data["director"],
            )
        assert exc_info.value.status_code == 409
        assert "Idempotency conflict" in exc_info.value.detail


@pytest.mark.asyncio
async def test_void_payment_success_and_status_recalculation(payment_service_db):
    """Verifies voiding a full payment resets invoice status from 'paid' back to 'issued' and paid_amount to 0."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # 1. Full payment
    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_v_orig_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("50000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )
        pid = payment.id

    # Verify paid
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.status == "paid"
        assert inv_check.paid_amount == Decimal("50000.00")

    # 2. Void payment
    async with TestingSessionLocal() as session:
        voided_p = await ClientPaymentService.void_payment(
            session,
            pid,
            VoidPaymentRequest(
                void_idempotency_key=f"void_idem_{sfx}",
                void_reason="Deposit cheque bounced at clearing bank",
            ),
            current_user=data["director"],
        )
        assert voided_p.status == "voided"
        assert voided_p.void_reason == "Deposit cheque bounced at clearing bank"
        assert voided_p.voided_by == data["director"].id
        assert voided_p.voided_at is not None

    # Verify invoice reverted to issued with 0 paid_amount
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.status == "issued"
        assert inv_check.paid_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_void_payment_partial_reversion(payment_service_db):
    """Verifies voiding one payment transitions invoice from 'paid' to 'partially_paid'."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Two payments: 20k and 30k
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_vpr_1_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("20000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )
        p2 = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_vpr_2_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("30000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="rtgs",
            ),
            data["director"],
        )
        p2_id = p2.id

    # Void payment #2 (30,000)
    async with TestingSessionLocal() as session:
        await ClientPaymentService.void_payment(
            session,
            p2_id,
            VoidPaymentRequest(
                void_idempotency_key=f"void_idem_vpr_{sfx}",
                void_reason="Incorrect transaction reference provided by client",
            ),
            current_user=data["admin"],
        )

    # Verify remaining paid_amount is 20,000 and status is partially_paid
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("20000.00")
        assert inv_check.status == "partially_paid"


@pytest.mark.asyncio
async def test_void_payment_idempotency(payment_service_db):
    """Verifies that re-voiding a payment with the same void_idempotency_key returns the voided payment without re-adjusting balance."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_videm_rec_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("10000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )
        pid = p.id

    # Void 1
    async with TestingSessionLocal() as session:
        v1 = await ClientPaymentService.void_payment(
            session,
            pid,
            VoidPaymentRequest(
                void_idempotency_key=f"void_idem_replay_{sfx}",
                void_reason="Client issued stop-payment order",
            ),
            data["director"],
        )
        assert v1.status == "voided"

    # Void 2 (Replay with same void_idempotency_key)
    async with TestingSessionLocal() as session:
        v2 = await ClientPaymentService.void_payment(
            session,
            pid,
            VoidPaymentRequest(
                void_idempotency_key=f"void_idem_replay_{sfx}",
                void_reason="Client issued stop-payment order",
            ),
            data["director"],
        )
        assert v2.id == v1.id

    # Void 3 (Conflicting void_idempotency_key)
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.void_payment(
                session,
                pid,
                VoidPaymentRequest(
                    void_idempotency_key=f"diff_void_key_{sfx}",
                    void_reason="Attempting second void key",
                ),
                data["director"],
            )
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_void_payment_invalid_reason(payment_service_db):
    """Verifies that void_reason with fewer than 10 non-whitespace characters is rejected."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_short_rec_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("5000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )
        pid = p.id

    # Too short reason
    async with TestingSessionLocal() as session:
        with pytest.raises(Exception):  # Pydantic or HTTPException
            await ClientPaymentService.void_payment(
                session,
                pid,
                VoidPaymentRequest(
                    void_idempotency_key=f"void_short_{sfx}",
                    void_reason="error",  # < 10 chars
                ),
                data["director"],
            )


@pytest.mark.asyncio
async def test_paid_and_partially_paid_invoice_cancellation_blocked(payment_service_db):
    """Verifies that InvoiceService.cancel_invoice refuses to cancel invoices having active recorded payments."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Record partial payment
    async with TestingSessionLocal() as session:
        await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_cancel_block_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("15000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )

    # Attempt invoice cancellation
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.cancel_invoice(
                session,
                inv.id,
                CancelInvoiceRequest(cancellation_reason="Attempting to cancel partially paid invoice"),
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400
        assert "cannot be cancelled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_list_and_get_payments(payment_service_db):
    """Verifies get_payment_by_id and list_payments_for_invoice operations."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    dates = [date(2026, 10, 7), date(2026, 10, 8)]
    created_ids = []
    async with TestingSessionLocal() as session:
        for idx, dt in enumerate(dates):
            p = await ClientPaymentService.record_payment(
                session,
                RecordPaymentRequest(
                    idempotency_key=f"idem_list_{sfx}_{idx}",
                    invoice_id=inv.id,
                    amount=Decimal(f"{(idx + 1) * 5000}.00"),
                    payment_date=dt,
                    payment_method="neft",
                ),
                data["director"],
            )
            created_ids.append(p.id)

    async with TestingSessionLocal() as session:
        # Get by ID
        found = await ClientPaymentService.get_payment_by_id(session, created_ids[0])
        assert found.id == created_ids[0]

        # Non-existent ID raises 404
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.get_payment_by_id(session, _u())
        assert exc_info.value.status_code == 404

        # List for invoice
        payments = await ClientPaymentService.list_payments_for_invoice(session, inv.id)
        assert len(payments) == 2
        # Ordered by payment_date DESC: 2026-10-08, then 2026-10-07
        assert payments[0].payment_date == date(2026, 10, 8)
        assert payments[1].payment_date == date(2026, 10, 7)


@pytest.mark.asyncio
async def test_rbac_service_authorization(payment_service_db):
    """Verifies that only director and administrator can record and void payments."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    req = RecordPaymentRequest(
        idempotency_key=f"idem_rbac_{sfx}",
        invoice_id=inv.id,
        amount=Decimal("1000.00"),
        payment_date=date(2026, 10, 8),
        payment_method="neft",
    )

    # 1. Supervisor blocked
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["supervisor"])
        assert exc_info.value.status_code == 403

    # 2. Employee blocked
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.record_payment(session, req, data["employee"])
        assert exc_info.value.status_code == 403

    # 3. Director succeeds
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(session, req, data["director"])
        pid = p.id

    # 4. Supervisor cannot void
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.void_payment(
                session,
                pid,
                VoidPaymentRequest(
                    void_idempotency_key=f"void_rbac_{sfx}",
                    void_reason="Supervisor attempting unauthorized void",
                ),
                data["supervisor"],
            )
        assert exc_info.value.status_code == 403

    # 5. Administrator can void
    async with TestingSessionLocal() as session:
        voided = await ClientPaymentService.void_payment(
            session,
            pid,
            VoidPaymentRequest(
                void_idempotency_key=f"void_rbac_ok_{sfx}",
                void_reason="Administrator authorized void of test payment",
            ),
            data["admin"],
        )
        assert voided.status == "voided"


@pytest.mark.asyncio
async def test_concurrent_payment_locking(payment_service_db):
    """Critical Concurrency Test: Proves two concurrent payments cannot overdraw an invoice balance."""
    data = payment_service_db
    inv = data["invoice"]  # total_amount is 50,000.00
    sfx = str(_u())[:8]

    # Two concurrent payments of 30,000.00 each against a 50,000.00 invoice
    # Together they would be 60,000.00 (which exceeds 50,000.00).
    # Because Invoice row is locked FOR UPDATE first, one MUST succeed and the other MUST fail with 422 Overpayment.
    async def try_pay(amount: Decimal, key: str):
        async with TestingSessionLocal() as session:
            try:
                p = await ClientPaymentService.record_payment(
                    session,
                    RecordPaymentRequest(
                        idempotency_key=key,
                        invoice_id=inv.id,
                        amount=amount,
                        payment_date=date(2026, 10, 8),
                        payment_method="neft",
                    ),
                    data["director"],
                )
                return ("success", p.amount)
            except HTTPException as e:
                return ("error", e.status_code, e.detail)

    task1 = try_pay(Decimal("30000.00"), f"conc_p1_{sfx}")
    task2 = try_pay(Decimal("30000.00"), f"conc_p2_{sfx}")

    results = await asyncio.gather(task1, task2)

    statuses = [r[0] for r in results]
    assert "success" in statuses
    assert "error" in statuses

    # Find the error result
    err_res = next(r for r in results if r[0] == "error")
    assert err_res[1] == 422
    assert "exceeds outstanding balance" in err_res[2]

    # Check invoice paid_amount in DB is exactly 30,000.00 and status is partially_paid
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("30000.00")
        assert inv_check.status == "partially_paid"


@pytest.mark.asyncio
async def test_concurrent_void_and_payment_interaction(payment_service_db):
    """Proves concurrent void and payment operations keep invoice balance consistent without race conditions."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Setup: 20k payment on 50k invoice
    async with TestingSessionLocal() as session:
        orig_p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_conc_init_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("20000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            data["director"],
        )
        orig_pid = orig_p.id

    # Concurrently: Task A voids the 20k payment, Task B records a new 40k payment
    async def do_void():
        async with TestingSessionLocal() as session:
            return await ClientPaymentService.void_payment(
                session,
                orig_pid,
                VoidPaymentRequest(
                    void_idempotency_key=f"void_conc_key_{sfx}",
                    void_reason="Reversing initial transaction in concurrent flow",
                ),
                data["director"],
            )

    async def do_pay():
        async with TestingSessionLocal() as session:
            return await ClientPaymentService.record_payment(
                session,
                RecordPaymentRequest(
                    idempotency_key=f"idem_conc_new_{sfx}",
                    invoice_id=inv.id,
                    amount=Decimal("25000.00"),
                    payment_date=date(2026, 10, 8),
                    payment_method="rtgs",
                ),
                data["director"],
            )

    # Both lock parent invoice FOR UPDATE first, guaranteeing serialization
    await asyncio.gather(do_void(), do_pay())

    # Verify parent invoice paid_amount matches active recorded payments
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        active_sum = (
            await session.execute(
                select(ClientPayment.amount).where(
                    ClientPayment.invoice_id == inv.id, ClientPayment.status == "recorded"
                )
            )
        ).scalars().all()

        expected_paid = sum(active_sum, Decimal("0.00"))
        assert inv_check.paid_amount == expected_paid
        assert inv_check.status == "partially_paid"


# ---------------------------------------------------------------------------
# Receipt Service Level Tests
# ---------------------------------------------------------------------------

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"


@pytest.mark.asyncio
async def test_service_upload_receipt_success_and_replacement(payment_service_db, tmp_path):
    """Verifies service upload_receipt, get_receipt, and replacement behavior."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # 1. Record payment
    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_rcpt_srv_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("5000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=data["director"],
        )
        pid = payment.id

    # 2. Upload first receipt (PDF)
    async with TestingSessionLocal() as session:
        updated_p = await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="deposit.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            base_dir=tmp_path / "receipts",
        )
        assert updated_p.receipt_url.startswith(f"receipts/{pid}/")

    # 3. Retrieve receipt
    async with TestingSessionLocal() as session:
        file_path, mime, filename = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["admin"],
            base_dir=tmp_path / "receipts",
        )
        assert mime == "application/pdf"
        assert file_path.exists()
        assert file_path.read_bytes() == VALID_PDF_BYTES

    # 4. Replace receipt with PNG
    async with TestingSessionLocal() as session:
        replaced_p = await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PNG_BYTES,
            filename="deposit.png",
            content_type="image/png",
            current_user=data["director"],
            base_dir=tmp_path / "receipts",
        )
        assert replaced_p.receipt_url.startswith(f"receipts/{pid}/")
        assert replaced_p.receipt_url != updated_p.receipt_url

    # 5. Retrieve replaced receipt
    async with TestingSessionLocal() as session:
        new_path, new_mime, new_filename = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=tmp_path / "receipts",
        )
        assert new_mime == "image/png"
        assert new_path.exists()
        assert new_path.read_bytes() == VALID_PNG_BYTES
        # Old PDF must no longer exist
        assert not file_path.exists()


@pytest.mark.asyncio
async def test_service_upload_receipt_voided_rejection(payment_service_db, tmp_path):
    """Verifies that upload_receipt rejects attachment to a voided payment with 422."""
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Record and void
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_rcpt_void_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("3000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=data["director"],
        )
        await ClientPaymentService.void_payment(
            session,
            p.id,
            VoidPaymentRequest(
                void_idempotency_key=f"void_rcpt_srv_{sfx}",
                void_reason="Reversing payment for test purposes",
            ),
            current_user=data["director"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=p.id,
                file_bytes=VALID_PDF_BYTES,
                filename="receipt.pdf",
                content_type="application/pdf",
                current_user=data["director"],
                base_dir=tmp_path / "receipts",
            )
        assert exc_info.value.status_code == 422
        assert "voided" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_service_payment_succeeds_even_if_receipt_upload_fails_subsequently(payment_service_db, tmp_path):
    """
    Verifies the decoupled workflow:
    Payment is recorded first into the database.
    If a subsequent receipt upload fails (e.g. invalid file format or size limit exceeded),
    the payment record and invoice balances remain strictly intact and recorded.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    # Step 1: Payment records successfully
    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_decoupled_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("4000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="upi",
            ),
            current_user=data["director"],
        )
        pid = payment.id

    # Verify invoice has updated paid amount
    async with TestingSessionLocal() as session:
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("4000.00")

    # Step 2: Client attempts receipt upload with unsupported text file -> Fails with 400
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=b"This is not a PDF or supported image",
                filename="receipt.txt",
                content_type="text/plain",
                current_user=data["director"],
                base_dir=tmp_path / "receipts",
            )
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail

    # Step 3: Verify the payment record is still active and invoice balance is untouched
    async with TestingSessionLocal() as session:
        p_check = await session.get(ClientPayment, pid)
        assert p_check.status == "recorded"
        assert p_check.receipt_url is None
        inv_check = await session.get(Invoice, inv.id)
        assert inv_check.paid_amount == Decimal("4000.00")


@pytest.mark.asyncio
async def test_service_safe_replacement_preserves_old_receipt_when_db_commit_fails(payment_service_db, tmp_path):
    """
    Verifies Safe Replacement Failure-Path:
    1. A valid initial receipt (PDF) is uploaded and committed to DB.
    2. A replacement receipt (PNG) is uploaded, but database commit fails (simulated exception).
    3. The service cleans up the candidate PNG file and preserves the original PDF receipt.
    4. Subsequent get_receipt calls still retrieve the intact original PDF receipt.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "safe_replacement_test"

    # Step 1: Record payment and attach initial PDF receipt
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_safe_repl_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1500.00"),
                payment_date=date(2026, 10, 8),
                payment_method="cheque",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="original_receipt.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            base_dir=receipts_base,
        )

    # Verify initial receipt is accessible
    async with TestingSessionLocal() as session:
        initial_file, initial_mime, initial_name = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=receipts_base,
        )
        assert initial_mime == "application/pdf"
        assert initial_file.exists()
        assert initial_file.read_bytes() == VALID_PDF_BYTES

    # Step 2: Attempt replacement with PNG, but mock session.commit to fail
    async with TestingSessionLocal() as session:
        async def failing_commit():
            raise RuntimeError("Simulated Database Commit Failure")
        session.commit = failing_commit

        with pytest.raises(RuntimeError, match="Simulated Database Commit Failure"):
            await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=VALID_PNG_BYTES,
                filename="new_replacement.png",
                content_type="image/png",
                current_user=data["director"],
                base_dir=receipts_base,
            )

    # Step 3: Verify that the original PDF receipt is completely intact and accessible
    async with TestingSessionLocal() as session:
        file_check, mime_check, name_check = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=receipts_base,
        )
        assert mime_check == "application/pdf"
        assert file_check.exists()
        assert file_check.read_bytes() == VALID_PDF_BYTES

        # Verify no orphan PNG file exists in the payment directory
        p_dir = receipts_base / str(pid)
        files = list(p_dir.iterdir())
        assert len(files) == 1
        assert files[0] == file_check


@pytest.mark.asyncio
async def test_service_initial_upload_cleans_up_candidate_file_when_db_commit_fails(payment_service_db, tmp_path):
    """
    Verifies that on first upload, if DB commit fails, the candidate file is deleted
    and no orphan file remains in storage.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "initial_upload_fail_test"

    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_init_fail_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1200.00"),
                payment_date=date(2026, 10, 8),
                payment_method="upi",
            ),
            current_user=data["director"],
        )
        pid = p.id

        # Mock commit to fail
        async def failing_commit():
            raise RuntimeError("Database connection lost")
        session.commit = failing_commit

        with pytest.raises(RuntimeError, match="Database connection lost"):
            await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=VALID_PDF_BYTES,
                filename="candidate.pdf",
                content_type="application/pdf",
                current_user=data["director"],
                base_dir=receipts_base,
            )

    # Verify storage has no lingering files
    p_dir = receipts_base / str(pid)
    if p_dir.exists():
        assert len(list(p_dir.iterdir())) == 0

    # Verify get_receipt raises 404
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.get_receipt(
                session=session,
                payment_id=pid,
                current_user=data["director"],
                base_dir=receipts_base,
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_service_safe_replacement_preserves_old_receipt_when_storage_save_fails(payment_service_db, tmp_path):
    """
    Verifies that if saving the new receipt candidate to storage fails during replacement,
    the existing receipt is completely preserved and remains accessible.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "storage_save_fail_test"

    # Step 1: Record payment and upload initial valid PDF receipt
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_save_fail_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("2500.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="initial_receipt.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            base_dir=receipts_base,
        )

    # Verify initial receipt is accessible
    async with TestingSessionLocal() as session:
        init_file, init_mime, _ = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=receipts_base,
        )
        assert init_mime == "application/pdf"
        assert init_file.exists()
        assert init_file.read_bytes() == VALID_PDF_BYTES

    # Step 2: Attempt replacement with a mock storage provider whose upload_receipt fails
    from unittest.mock import AsyncMock
    mock_storage = AsyncMock()
    mock_storage.get_receipt.return_value = None
    mock_storage.upload_receipt.side_effect = RuntimeError("Disk quota exceeded / storage write failure")

    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=VALID_PNG_BYTES,
                filename="failed_replacement.png",
                content_type="image/png",
                current_user=data["director"],
                storage=mock_storage,
            )
        assert exc_info.value.status_code == 400
        assert "Failed to save receipt file" in exc_info.value.detail

    # Step 3: Verify original receipt remains completely intact and accessible
    async with TestingSessionLocal() as session:
        preserved_file, preserved_mime, _ = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=receipts_base,
        )
        assert preserved_mime == "application/pdf"
        assert preserved_file.exists()
        assert preserved_file.read_bytes() == VALID_PDF_BYTES


@pytest.mark.asyncio
async def test_service_old_file_deletion_failure_after_commit_succeeds(payment_service_db, tmp_path):
    """
    Verifies that if deleting old receipt files after a successful commit fails,
    the replacement request still succeeds and the newly committed receipt remains accessible.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "old_del_fail_test"

    # Step 1: Record payment and upload initial PDF receipt
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_del_fail_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1800.00"),
                payment_date=date(2026, 10, 8),
                payment_method="cheque",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="first_receipt.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            base_dir=receipts_base,
        )

    # Step 2: Replace receipt with a storage instance whose delete_old_receipts raises
    from app.shared.file_storage import LocalFileStorage
    custom_storage = LocalFileStorage(receipts_dir=receipts_base)

    async def failing_delete_old(payment_id, keep_ref):
        raise OSError("Permission denied: simulated unlink error on old receipt")

    custom_storage.delete_old_receipts = failing_delete_old

    # Upload replacement - must SUCCEED despite old file cleanup failure
    async with TestingSessionLocal() as session:
        updated_p = await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PNG_BYTES,
            filename="second_receipt.png",
            content_type="image/png",
            current_user=data["director"],
            storage=custom_storage,
        )
        assert updated_p.receipt_url.startswith(f"receipts/{pid}/")

    # Step 3: Verify the newly committed receipt is accessible
    async with TestingSessionLocal() as session:
        new_file, new_mime, _ = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            storage=custom_storage,
        )
        assert new_mime == "image/png"
        assert new_file.exists()
        assert new_file.read_bytes() == VALID_PNG_BYTES


@pytest.mark.asyncio
async def test_service_concurrent_receipt_replacements_leave_consistent_receipt(payment_service_db, tmp_path):
    """
    Verifies that concurrent replacements serialize cleanly under row lock,
    leaving the database referencing a consistent, existing, accessible receipt.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "concurrent_replacement_test"

    # Step 1: Initial payment & receipt
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_conc_rcpt_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("3500.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="initial.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            base_dir=receipts_base,
        )

    # Step 2: Launch two concurrent replacement requests with distinct payloads
    file_a = VALID_PNG_BYTES
    file_b = b"%PDF-1.4\n%Replacement-B-Content\ntrailer\n<<>>\n%%EOF"

    async def replace_worker(payload: bytes, name: str, mime: str):
        async with TestingSessionLocal() as session:
            return await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=payload,
                filename=name,
                content_type=mime,
                current_user=data["director"],
                base_dir=receipts_base,
            )

    results = await asyncio.gather(
        replace_worker(file_a, "replacement_a.png", "image/png"),
        replace_worker(file_b, "replacement_b.pdf", "application/pdf"),
        return_exceptions=True,
    )

    # Neither should crash with unhandled error
    for r in results:
        assert not isinstance(r, Exception), f"Concurrent replacement raised: {r}"

    # Step 3: Verify the database points to an accessible, consistent receipt
    async with TestingSessionLocal() as session:
        p_final = await session.get(ClientPayment, pid)
        assert p_final.receipt_url.startswith(f"receipts/{pid}/")

        final_file, final_mime, _ = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            base_dir=receipts_base,
        )
        assert final_file.exists()
        final_content = final_file.read_bytes()
        # Content must match either replacement A or replacement B
        assert final_content in (file_a, file_b)


@pytest.mark.asyncio
async def test_service_receipt_upload_and_replacement_creates_audit_entries(payment_service_db, tmp_path):
    """
    Verifies that every receipt upload and replacement creates an audit_logs entry
    with entity_type='client_payment', actor, payment ID, timestamp, and correct action.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "audit_test"
    director = data["director"]

    # 1. Record payment
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_audit_rcpt_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("2200.00"),
                payment_date=date(2026, 10, 8),
                payment_method="upi",
            ),
            current_user=director,
        )
        pid = p.id

    # 2. Upload initial receipt
    async with TestingSessionLocal() as session:
        uploaded_p1 = await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="audit_initial.pdf",
            content_type="application/pdf",
            current_user=director,
            base_dir=receipts_base,
        )
        ref_1 = uploaded_p1.receipt_url

    # Verify audit entry for initial upload
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid)
            .order_by(AuditLog.created_at.asc())
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        audit_1 = logs[0]
        assert audit_1.action == "receipt_upload"
        assert audit_1.changed_by == director.id
        assert audit_1.created_at is not None
        assert audit_1.previous_values is None
        assert audit_1.new_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert audit_1.new_values["storage_ref"] == ref_1
        assert audit_1.new_values["filename"] == "audit_initial.pdf"

    # 3. Replace receipt
    async with TestingSessionLocal() as session:
        uploaded_p2 = await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PNG_BYTES,
            filename="audit_replacement.png",
            content_type="image/png",
            current_user=director,
            base_dir=receipts_base,
        )
        ref_2 = uploaded_p2.receipt_url

    # Verify audit entry for replacement
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid)
            .order_by(AuditLog.created_at.asc())
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 2
        audit_2 = logs[1]
        assert audit_2.action == "receipt_replacement"
        assert audit_2.changed_by == director.id
        assert audit_2.created_at is not None
        assert audit_2.previous_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert audit_2.new_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert audit_2.previous_values["storage_ref"] == ref_1
        assert audit_2.new_values["storage_ref"] == ref_2
        assert audit_2.new_values["storage_ref"] != audit_2.previous_values["storage_ref"]
        assert audit_2.new_values["filename"] == "audit_replacement.png"


@pytest.mark.asyncio
async def test_service_concurrent_receipt_replacements_equal_timestamps_local(payment_service_db, tmp_path):
    """
    Verifies that when concurrent replacements occur and local files have equal/indistinguishable
    modification timestamps, exact reference resolution ensures the active receipt is never deleted
    and is correctly retrieved by get_receipt.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]
    receipts_base = tmp_path / "concurrent_equal_ts_local"
    storage = LocalFileStorage(receipts_dir=receipts_base)

    # 1. Initial payment and receipt
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_eq_ts_loc_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("4000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="initial.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            storage=storage,
        )

    # 2. Intercept save_receipt_sync to force equal mtime timestamps on all replacement files
    orig_save = storage._save_receipt_sync
    fixed_ts = 1710000000.0

    def patched_save(payment_id, file_bytes, original_filename, content_type=None):
        target_path, mime = orig_save(payment_id, file_bytes, original_filename, content_type)
        os.utime(target_path, (fixed_ts, fixed_ts))
        return target_path, mime

    storage._save_receipt_sync = patched_save

    # 3. Launch concurrent replacements with distinct payloads
    file_a = VALID_PNG_BYTES
    file_b = b"%PDF-1.4\n%Replacement-B-Equal-TS\ntrailer\n<<>>\n%%EOF"

    async def replace_worker(payload: bytes, name: str, mime: str):
        async with TestingSessionLocal() as session:
            return await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=payload,
                filename=name,
                content_type=mime,
                current_user=data["director"],
                storage=storage,
            )

    results = await asyncio.gather(
        replace_worker(file_a, "replacement_a.png", "image/png"),
        replace_worker(file_b, "replacement_b.pdf", "application/pdf"),
        return_exceptions=True,
    )
    for r in results:
        assert not isinstance(r, Exception), f"Concurrent replacement raised: {r}"

    # 4. Verify DB committed exact storage_ref and retrieved receipt matches exact reference
    async with TestingSessionLocal() as session:
        p_final = await session.get(ClientPayment, pid)
        assert p_final.receipt_url.startswith(f"receipts/{pid}/")

        final_res = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            storage=storage,
        )
        assert final_res.file_path.exists()
        # Verify timestamps are equal across remaining files in directory
        p_dir = storage._get_receipt_dir(pid)
        for f in p_dir.iterdir():
            if f.is_file():
                assert f.stat().st_mtime == fixed_ts

        # Content must match the exact committed file
        final_content = final_res.file_path.read_bytes()
        assert final_content in (file_a, file_b)
        if "replacement_a" in p_final.receipt_url:
            assert final_content == file_a
        else:
            assert final_content == file_b


@pytest.mark.asyncio
async def test_service_concurrent_receipt_replacements_equal_timestamps_mocked_s3(payment_service_db):
    """
    Verifies that when concurrent replacements occur on S3 with indistinguishable LastModified
    timestamps, exact reference resolution ensures the active object in S3 remains accessible
    and is not deleted by timestamp collision.
    """
    data = payment_service_db
    inv = data["invoice"]
    sfx = str(_u())[:8]

    s3_storage = S3FileStorage(bucket_name="workforce-receipts-s3")
    mock_s3 = MagicMock()
    s3_storage._client = mock_s3

    s3_objects = {}
    fixed_last_modified = "2026-10-09T12:00:00Z"

    def mock_put_object(Bucket, Key, Body, ContentType):
        s3_objects[Key] = {"Body": Body, "ContentType": ContentType, "LastModified": fixed_last_modified}
        return {}

    def mock_get_object(Bucket, Key):
        if Key not in s3_objects:
            raise Exception("NoSuchKey")
        body_mock = MagicMock()
        body_mock.read.return_value = s3_objects[Key]["Body"]
        return {"Body": body_mock, "ContentType": s3_objects[Key]["ContentType"], "LastModified": s3_objects[Key]["LastModified"]}

    def mock_delete_object(Bucket, Key):
        s3_objects.pop(Key, None)
        return {}

    def mock_list_objects_v2(Bucket, Prefix):
        contents = [
            {"Key": k, "LastModified": v["LastModified"]}
            for k, v in s3_objects.items()
            if k.startswith(Prefix)
        ]
        return {"Contents": contents}

    mock_s3.put_object.side_effect = mock_put_object
    mock_s3.get_object.side_effect = mock_get_object
    mock_s3.delete_object.side_effect = mock_delete_object
    mock_s3.list_objects_v2.side_effect = mock_list_objects_v2

    # 1. Initial payment and receipt in S3
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_eq_ts_s3_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("5000.00"),
                payment_date=date(2026, 10, 8),
                payment_method="rtgs",
            ),
            current_user=data["director"],
        )
        pid = p.id
        await ClientPaymentService.upload_receipt(
            session=session,
            payment_id=pid,
            file_bytes=VALID_PDF_BYTES,
            filename="initial_s3.pdf",
            content_type="application/pdf",
            current_user=data["director"],
            storage=s3_storage,
        )

    # 2. Launch concurrent replacements
    file_a = VALID_PNG_BYTES
    file_b = b"%PDF-1.4\n%Replacement-S3-Content\ntrailer\n<<>>\n%%EOF"

    async def replace_worker(payload: bytes, name: str, mime: str):
        async with TestingSessionLocal() as session:
            return await ClientPaymentService.upload_receipt(
                session=session,
                payment_id=pid,
                file_bytes=payload,
                filename=name,
                content_type=mime,
                current_user=data["director"],
                storage=s3_storage,
            )

    results = await asyncio.gather(
        replace_worker(file_a, "s3_rep_a.png", "image/png"),
        replace_worker(file_b, "s3_rep_b.pdf", "application/pdf"),
        return_exceptions=True,
    )
    for r in results:
        assert not isinstance(r, Exception), f"Concurrent replacement raised: {r}"

    # 3. Verify DB record identifies exact S3 key and get_receipt retrieves it
    async with TestingSessionLocal() as session:
        p_final = await session.get(ClientPayment, pid)
        assert p_final.receipt_url.startswith(f"receipts/{pid}/")
        assert p_final.receipt_url in s3_objects

        res = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            storage=s3_storage,
        )
        assert res.file_bytes in (file_a, file_b)
        if "s3_rep_a" in p_final.receipt_url:
            assert res.file_bytes == file_a
        else:
            assert res.file_bytes == file_b


@pytest.mark.asyncio
async def test_service_legacy_receipt_ambiguity_matrix(payment_service_db, tmp_path: Path):
    """
    Verifies service-level legacy fallback and ambiguity enforcement:
    - Legacy /api/ URL with 0 files -> 404 Not Found
    - Legacy /api/ URL with 1 file -> 200 OK (backward-compatible retrieval)
    - Legacy /api/ URL with >1 files -> 409 Conflict (manual reconciliation required)
    - Exact canonical reference with >1 files -> 200 OK (exact match)
    """
    data = payment_service_db
    storage = LocalFileStorage(receipts_dir=tmp_path / "service_legacy_matrix")
    sfx = str(_u())[:8]

    # Record payment without receipt
    req = RecordPaymentRequest(
        idempotency_key=f"idem_legacy_{sfx}",
        invoice_id=data["invoice"].id,
        amount=Decimal("1000.00"),
        payment_date=date.today(),
        payment_method="neft",
    )
    async with TestingSessionLocal() as session:
        payment = await ClientPaymentService.record_payment(session, req, data["director"])
        pid = payment.id

        # Point payment.receipt_url to legacy API endpoint
        payment.receipt_url = f"/api/v1/client-payments/{pid}/receipt"
        await session.commit()

    # 1. Zero files on disk: raises 404
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.get_receipt(
                session=session,
                payment_id=pid,
                current_user=data["director"],
                storage=storage,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Receipt file not found in storage."

    # 2. Add exactly 1 file: backward-compatible retrieval succeeds
    p_dir = storage._get_receipt_dir(pid)
    p_dir.mkdir(parents=True, exist_ok=True)
    file1 = p_dir / "11111111_single_receipt.pdf"
    file1.write_bytes(VALID_PDF_BYTES)

    async with TestingSessionLocal() as session:
        res_single = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            storage=storage,
        )
        assert res_single.filename == "11111111_single_receipt.pdf"

    # 3. Add second file to create ambiguity under legacy reference
    file2 = p_dir / "22222222_second_receipt.png"
    file2.write_bytes(VALID_PNG_BYTES)

    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.get_receipt(
                session=session,
                payment_id=pid,
                current_user=data["director"],
                storage=storage,
            )
        assert exc_info.value.status_code == 409
        assert "Receipt reference is ambiguous" in exc_info.value.detail
        assert "manual reconciliation" in exc_info.value.detail.lower()

    # 4. Set exact canonical reference in payment: succeeds despite multiple files present
    async with TestingSessionLocal() as session:
        p_db = await session.get(ClientPayment, pid)
        p_db.receipt_url = f"receipts/{pid}/{file1.name}"
        await session.commit()

        res_exact = await ClientPaymentService.get_receipt(
            session=session,
            payment_id=pid,
            current_user=data["director"],
            storage=storage,
        )
        assert res_exact.filename == "11111111_single_receipt.pdf"


@pytest.mark.asyncio
async def test_void_payment_creates_central_audit_log(payment_service_db):
    """Verifies voiding a payment creates a central AuditLog entry with client_payment_voided action,
    capturing entity ID, actor, timestamp, void reason, and state before/after."""
    data = payment_service_db
    inv = data["invoice"]
    director = data["director"]
    sfx = str(_u())[:8]

    # 1. Record payment
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_audit_void_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1500.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=director,
        )
        pid = p.id
        payment_num = p.payment_number

    # 2. Void payment
    void_reason = "Client requested stop-payment due to duplicate billing"
    void_key = f"void_audit_idem_{sfx}"
    async with TestingSessionLocal() as session:
        voided_p = await ClientPaymentService.void_payment(
            session=session,
            payment_id=pid,
            request=VoidPaymentRequest(
                void_idempotency_key=void_key,
                void_reason=void_reason,
            ),
            current_user=director,
        )
        assert voided_p.status == "voided"

    # 3. Verify central AuditLog entry
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid, AuditLog.action == "client_payment_voided")
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.action == "client_payment_voided"
        assert log.changed_by == director.id
        assert log.created_at is not None
        assert log.previous_values["status"] == "recorded"
        assert log.previous_values["amount"] == "1500.00"
        assert log.previous_values["payment_number"] == payment_num
        assert log.previous_values["invoice_id"] == str(inv.id)
        assert log.new_values["status"] == "voided"
        assert log.new_values["void_reason"] == void_reason
        assert log.new_values["void_idempotency_key"] == void_key


@pytest.mark.asyncio
async def test_void_payment_idempotent_retry_does_not_duplicate_audit_log(payment_service_db):
    """Verifies that re-submitting the exact same void_idempotency_key does not create duplicate AuditLog entries."""
    data = payment_service_db
    inv = data["invoice"]
    director = data["director"]
    sfx = str(_u())[:8]

    # Record payment
    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_audit_replay_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1200.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
            ),
            current_user=director,
        )
        pid = p.id

    void_key = f"void_replay_audit_{sfx}"
    void_reason = "Duplicate check detected by accounts department"

    # Void 1
    async with TestingSessionLocal() as session:
        v1 = await ClientPaymentService.void_payment(
            session=session,
            payment_id=pid,
            request=VoidPaymentRequest(
                void_idempotency_key=void_key,
                void_reason=void_reason,
            ),
            current_user=director,
        )
        assert v1.status == "voided"

    # Replay Void with same idempotency key
    async with TestingSessionLocal() as session:
        v2 = await ClientPaymentService.void_payment(
            session=session,
            payment_id=pid,
            request=VoidPaymentRequest(
                void_idempotency_key=void_key,
                void_reason=void_reason,
            ),
            current_user=director,
        )
        assert v2.status == "voided"

    # Assert exactly ONE audit log exists
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid, AuditLog.action == "client_payment_voided")
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1


@pytest.mark.asyncio
async def test_void_payment_invalid_or_blocked_creates_no_audit_log(payment_service_db):
    """Verifies that invalid or blocked void attempts (short reason, unauthorized role) create no audit logs."""
    data = payment_service_db
    inv = data["invoice"]
    director = data["director"]
    supervisor = data["supervisor"]
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_audit_block_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("900.00"),
                payment_date=date(2026, 10, 8),
                payment_method="cash",
            ),
            current_user=director,
        )
        pid = p.id

    # 1. Blocked: short void reason (< 10 chars)
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.void_payment(
                session=session,
                payment_id=pid,
                request=VoidPaymentRequest.model_construct(
                    void_idempotency_key=f"short_key_{sfx}",
                    void_reason="short",
                ),
                current_user=director,
            )
        assert exc_info.value.status_code == 422

    # 2. Blocked: unauthorized role (supervisor)
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await ClientPaymentService.void_payment(
                session=session,
                payment_id=pid,
                request=VoidPaymentRequest(
                    void_idempotency_key=f"unauth_key_{sfx}",
                    void_reason="Valid reason but supervisor has no permission",
                ),
                current_user=supervisor,
            )
        assert exc_info.value.status_code == 403

    # Assert zero audit logs exist
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid)
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 0


@pytest.mark.asyncio
async def test_void_payment_transaction_failure_rollback(payment_service_db, monkeypatch):
    """Verifies that if commit fails, both the payment status change and the audit log entry are rolled back."""
    data = payment_service_db
    inv = data["invoice"]
    director = data["director"]
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        p = await ClientPaymentService.record_payment(
            session,
            RecordPaymentRequest(
                idempotency_key=f"idem_audit_fail_{sfx}",
                invoice_id=inv.id,
                amount=Decimal("1100.00"),
                payment_date=date(2026, 10, 8),
                payment_method="cash",
            ),
            current_user=director,
        )
        pid = p.id

    async with TestingSessionLocal() as session:
        # Mock session.commit to fail
        async def mock_fail_commit():
            raise RuntimeError("Database connection interrupted during commit")

        monkeypatch.setattr(session, "commit", mock_fail_commit)

        with pytest.raises(RuntimeError):
            await ClientPaymentService.void_payment(
                session=session,
                payment_id=pid,
                request=VoidPaymentRequest(
                    void_idempotency_key=f"fail_key_{sfx}",
                    void_reason="Valid void reason testing rollback",
                ),
                current_user=director,
            )

    # In a fresh session, verify payment is still recorded and NO audit log exists
    async with TestingSessionLocal() as session:
        payment_check = await session.get(ClientPayment, pid)
        assert payment_check.status == "recorded"
        assert payment_check.voided_at is None

        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid)
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 0




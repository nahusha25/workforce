from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.client_payments import ClientPayment
from app.models.invoices import Invoice
from app.models.operations import Client, Project, Site
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def payment_db_setup():
    """Sets up user, client, project, site, and an issued invoice for payment testing."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        user = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="director")
        user2 = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="administrator")
        session.add_all([user, user2])
        await session.flush()

        # 2. Operations master data
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        # 3. Issued Invoice
        invoice = Invoice(
            id=_u(),
            invoice_number=f"INV-{sfx.upper()}",
            idempotency_key=f"inv_idem_{sfx}",
            client_id=client.id,
            project_id=project.id,
            site_id=site.id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="issued",
            subtotal_work=Decimal("50000.00"),
            subtotal_material=Decimal("10000.00"),
            tax_amount=Decimal("10800.00"),
            total_amount=Decimal("70800.00"),
            paid_amount=Decimal("0.00"),
            created_by=user.id,
        )
        session.add(invoice)
        await session.commit()

        return {
            "user": user,
            "user2": user2,
            "client": client,
            "project": project,
            "site": site,
            "invoice": invoice,
        }


@pytest.mark.asyncio
async def test_valid_payment_creation(payment_db_setup):
    """Verifies that a valid ClientPayment can be created and committed with all fields intact."""
    data = payment_db_setup
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        payment = ClientPayment(
            id=_u(),
            payment_number=f"CP-{sfx}",
            idempotency_key=f"idem_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("25000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            reference_number="NEFT987654321",
            notes="First instalment",
            receipt_url="https://example.com/receipts/cp-001.pdf",
            status="recorded",
            recorded_by=data["user"].id,
        )
        session.add(payment)
        await session.commit()

    async with TestingSessionLocal() as session:
        result = await session.execute(select(ClientPayment).where(ClientPayment.payment_number == f"CP-{sfx}"))
        saved = result.scalar_one()

        assert saved.amount == Decimal("25000.00")
        assert saved.payment_date == date(2026, 10, 8)
        assert saved.payment_method == "neft"
        assert saved.reference_number == "NEFT987654321"
        assert saved.notes == "First instalment"
        assert saved.receipt_url == "https://example.com/receipts/cp-001.pdf"
        assert saved.status == "recorded"
        assert saved.recorded_by == data["user"].id
        assert saved.voided_by is None
        assert saved.voided_at is None
        assert saved.void_reason is None
        assert saved.void_idempotency_key is None
        assert saved.created_at is not None
        assert saved.updated_at is not None


@pytest.mark.asyncio
async def test_payment_amount_constraint(payment_db_setup):
    """Verifies that DB CHECK constraint rejects amount <= 0."""
    data = payment_db_setup

    # 1. Zero amount
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p_zero = ClientPayment(
            id=_u(),
            payment_number=f"CP-ZERO-{sfx}",
            idempotency_key=f"idem_zero_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("0.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
        )
        session.add(p_zero)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. Negative amount
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p_neg = ClientPayment(
            id=_u(),
            payment_number=f"CP-NEG-{sfx}",
            idempotency_key=f"idem_neg_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("-100.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
        )
        session.add(p_neg)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_payment_method_constraint(payment_db_setup):
    """Verifies that DB CHECK constraint enforces valid payment methods (neft, rtgs, imps, upi, cheque, cash, other)."""
    data = payment_db_setup
    valid_methods = ["neft", "rtgs", "imps", "upi", "cheque", "cash", "other"]

    # All valid methods succeed
    for method in valid_methods:
        async with TestingSessionLocal() as session:
            sfx = str(_u())[:8]
            p = ClientPayment(
                id=_u(),
                payment_number=f"CP-{method[:3]}-{sfx}",
                idempotency_key=f"idem_{method}_{sfx}",
                invoice_id=data["invoice"].id,
                amount=Decimal("100.00"),
                payment_date=date(2026, 10, 8),
                payment_method=method,
                status="recorded",
            )
            session.add(p)
            await session.commit()

    # Invalid payment methods fail
    invalid_methods = ["bitcoin", "credit_card", "paypal", "wire", ""]
    for bad_method in invalid_methods:
        async with TestingSessionLocal() as session:
            sfx = str(_u())[:8]
            p_bad = ClientPayment(
                id=_u(),
                payment_number=f"CP-BAD-{sfx}",
                idempotency_key=f"idem_bad_{sfx}",
                invoice_id=data["invoice"].id,
                amount=Decimal("100.00"),
                payment_date=date(2026, 10, 8),
                payment_method=bad_method,
                status="recorded",
            )
            session.add(p_bad)
            with pytest.raises(IntegrityError):
                await session.commit()


@pytest.mark.asyncio
async def test_payment_status_constraint(payment_db_setup):
    """Verifies that DB CHECK constraint enforces status IN ('recorded', 'voided')."""
    data = payment_db_setup

    invalid_statuses = ["pending", "processing", "draft", "completed", "cancelled", "approved"]
    for bad_status in invalid_statuses:
        async with TestingSessionLocal() as session:
            sfx = str(_u())[:8]
            p_bad = ClientPayment(
                id=_u(),
                payment_number=f"CP-ST-{sfx}",
                idempotency_key=f"idem_st_{sfx}",
                invoice_id=data["invoice"].id,
                amount=Decimal("500.00"),
                payment_date=date(2026, 10, 8),
                payment_method="neft",
                status=bad_status,
            )
            session.add(p_bad)
            with pytest.raises(IntegrityError):
                await session.commit()


@pytest.mark.asyncio
async def test_recorded_state_void_fields_constraint(payment_db_setup):
    """Verifies that when status='recorded', all void fields must be NULL."""
    data = payment_db_setup

    # 1. status='recorded' with voided_by non-null
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-VBY-{sfx}",
            idempotency_key=f"idem_vby_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            voided_by=data["user"].id,
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. status='recorded' with voided_at non-null
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-VAT-{sfx}",
            idempotency_key=f"idem_vat_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            voided_at=_now(),
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 3. status='recorded' with void_reason non-null
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-VRS-{sfx}",
            idempotency_key=f"idem_vrs_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            void_reason="Mistake in cheque number",
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 4. status='recorded' with void_idempotency_key non-null
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-VIDEM-{sfx}",
            idempotency_key=f"idem_videm_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_voided_state_metadata_and_integrity(payment_db_setup):
    """Verifies that when status='voided', ALL void metadata fields must be NOT NULL."""
    data = payment_db_setup

    # 1. Missing voided_by
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-NO-VBY-{sfx}",
            idempotency_key=f"idem_novby_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=None,
            voided_at=_now(),
            void_reason="Incorrect amount",
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. Missing voided_at
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-NO-VAT-{sfx}",
            idempotency_key=f"idem_novat_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=data["user"].id,
            voided_at=None,
            void_reason="Incorrect amount",
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 3. Missing void_reason
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-NO-VRS-{sfx}",
            idempotency_key=f"idem_novrs_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason=None,
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 4. void_reason with fewer than 10 trimmed characters (< 10 chars)
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p_short = ClientPayment(
            id=_u(),
            payment_number=f"CP-SHORT-VRS-{sfx}",
            idempotency_key=f"idem_shortvrs_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="short",  # 5 characters
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p_short)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 5. void_reason with padding whitespace but < 10 trimmed characters
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p_padded_short = ClientPayment(
            id=_u(),
            payment_number=f"CP-PAD-VRS-{sfx}",
            idempotency_key=f"idem_padvrs_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="   error   ",  # 5 trimmed characters
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p_padded_short)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 6. Valid voided payment with all 4 void metadata fields and >= 10 trimmed chars succeeds
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p_valid_void = ClientPayment(
            id=_u(),
            payment_number=f"CP-VALID-VOID-{sfx}",
            idempotency_key=f"idem_valvoid_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="upi",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="Cheque bounced",  # 14 characters
            void_idempotency_key=f"void_idem_{sfx}",
        )
        session.add(p_valid_void)
        await session.commit()


@pytest.mark.asyncio
async def test_voided_payment_requires_void_idempotency_key(payment_db_setup):
    """Specifically verifies that status='voided' without void_idempotency_key raises IntegrityError."""
    data = payment_db_setup

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-NO-VIDEM-{sfx}",
            idempotency_key=f"idem_novidem_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("2000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="cheque",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="Duplicate payment entry",
            void_idempotency_key=None,
        )
        session.add(p)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_unique_idempotency_key(payment_db_setup):
    """Verifies that duplicate payment idempotency_key is rejected."""
    data = payment_db_setup
    sfx = str(_u())[:8]
    shared_key = f"shared_idem_{sfx}"

    # First payment succeeds
    async with TestingSessionLocal() as session:
        p1 = ClientPayment(
            id=_u(),
            payment_number=f"CP-1-{sfx}",
            idempotency_key=shared_key,
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
        )
        session.add(p1)
        await session.commit()

    # Second payment with same idempotency_key must fail
    async with TestingSessionLocal() as session:
        p2 = ClientPayment(
            id=_u(),
            payment_number=f"CP-2-{sfx}",
            idempotency_key=shared_key,
            invoice_id=data["invoice"].id,
            amount=Decimal("2000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="rtgs",
            status="recorded",
        )
        session.add(p2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_unique_void_idempotency_key(payment_db_setup):
    """Verifies that duplicate void_idempotency_key is rejected, while multiple NULLs are permitted."""
    data = payment_db_setup
    sfx = str(_u())[:8]
    shared_void_key = f"shared_void_idem_{sfx}"

    # First voided payment succeeds
    async with TestingSessionLocal() as session:
        p1 = ClientPayment(
            id=_u(),
            payment_number=f"CP-VOID1-{sfx}",
            idempotency_key=f"idem_v1_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="Reversal 1",
            void_idempotency_key=shared_void_key,
        )
        session.add(p1)
        await session.commit()

    # Second voided payment with same void_idempotency_key must fail
    async with TestingSessionLocal() as session:
        p2 = ClientPayment(
            id=_u(),
            payment_number=f"CP-VOID2-{sfx}",
            idempotency_key=f"idem_v2_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("1500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="voided",
            voided_by=data["user"].id,
            voided_at=_now(),
            void_reason="Reversal 2",
            void_idempotency_key=shared_void_key,
        )
        session.add(p2)
        with pytest.raises(IntegrityError):
            await session.commit()

    # Multiple recorded payments with void_idempotency_key=None must succeed
    async with TestingSessionLocal() as session:
        p3 = ClientPayment(
            id=_u(),
            payment_number=f"CP-NULL1-{sfx}",
            idempotency_key=f"idem_null1_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("500.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            void_idempotency_key=None,
        )
        p4 = ClientPayment(
            id=_u(),
            payment_number=f"CP-NULL2-{sfx}",
            idempotency_key=f"idem_null2_{sfx}",
            invoice_id=data["invoice"].id,
            amount=Decimal("600.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
            void_idempotency_key=None,
        )
        session.add_all([p3, p4])
        await session.commit()


@pytest.mark.asyncio
async def test_invoice_foreign_key_and_restrict(payment_db_setup):
    """Verifies that invoice_id FK is enforced and invoices with payments cannot be deleted (RESTRICT)."""
    data = payment_db_setup
    sfx = str(_u())[:8]

    # 1. Non-existent invoice_id fails
    async with TestingSessionLocal() as session:
        p_bad_fk = ClientPayment(
            id=_u(),
            payment_number=f"CP-FK-{sfx}",
            idempotency_key=f"idem_fk_{sfx}",
            invoice_id=_u(),  # random non-existent invoice id
            amount=Decimal("1000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="neft",
            status="recorded",
        )
        session.add(p_bad_fk)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. Deleting an invoice with payments is RESTRICTED
    async with TestingSessionLocal() as session:
        # Create a dedicated invoice and payment to test delete restriction
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-DEL-{sfx}",
            idempotency_key=f"idem_inv_del_{sfx}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="issued",
            total_amount=Decimal("5000.00"),
        )
        session.add(inv)
        await session.flush()

        p = ClientPayment(
            id=_u(),
            payment_number=f"CP-RESTRICT-{sfx}",
            idempotency_key=f"idem_restrict_{sfx}",
            invoice_id=inv.id,
            amount=Decimal("5000.00"),
            payment_date=date(2026, 10, 8),
            payment_method="imps",
            status="recorded",
        )
        session.add(p)
        await session.commit()

    # Now attempt to delete the invoice
    async with TestingSessionLocal() as session:
        inv_to_delete = await session.get(Invoice, inv.id)
        assert inv_to_delete is not None
        await session.delete(inv_to_delete)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_sequence_creation_and_increment():
    """Verifies that client_payment_number_seq exists and increments correctly."""
    async with TestingSessionLocal() as session:
        res1 = await session.execute(text("SELECT nextval('client_payment_number_seq')"))
        val1 = res1.scalar_one()

        res2 = await session.execute(text("SELECT nextval('client_payment_number_seq')"))
        val2 = res2.scalar_one()

        assert isinstance(val1, int)
        assert isinstance(val2, int)
        assert val2 == val1 + 1


@pytest.mark.asyncio
async def test_invoice_payments_relationship_ordering(payment_db_setup):
    """Verifies that Invoice.payments relationship is loaded and ordered by payment_date.desc()."""
    data = payment_db_setup
    sfx = str(_u())[:8]

    # Create 3 payments on different dates
    dates = [date(2026, 10, 2), date(2026, 10, 9), date(2026, 10, 5)]
    async with TestingSessionLocal() as session:
        for idx, p_date in enumerate(dates):
            p = ClientPayment(
                id=_u(),
                payment_number=f"CP-ORD-{sfx}-{idx}",
                idempotency_key=f"idem_ord_{sfx}_{idx}",
                invoice_id=data["invoice"].id,
                amount=Decimal(f"{(idx + 1) * 1000}.00"),
                payment_date=p_date,
                payment_method="neft",
                status="recorded",
            )
            session.add(p)
        await session.commit()

    # Query invoice and check relationship
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(Invoice)
            .where(Invoice.id == data["invoice"].id)
            .options(selectinload(Invoice.payments))
        )
        inv = result.scalar_one()

        assert len(inv.payments) == 3
        # Should be ordered descending: 2026-10-09, 2026-10-05, 2026-10-02
        loaded_dates = [p.payment_date for p in inv.payments]
        assert loaded_dates == [date(2026, 10, 9), date(2026, 10, 5), date(2026, 10, 2)]

        # Verify back_populates
        assert inv.payments[0].invoice.id == inv.id

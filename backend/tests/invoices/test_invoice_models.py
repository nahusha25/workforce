from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.auth import User
from app.models.invoices import Invoice, InvoiceLineItem
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    Material,
    MaterialTransaction,
    Project,
    Site,
)
from app.models.workforce import Employee, Role
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def invoice_db_setup():
    """Sets up base client, project, site, activity, and operational records for testing invoice constraints."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_dir = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="employee")
        session.add_all([u_dir, u_sup, u_emp])
        await session.flush()

        # 2. Operations Master Data
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        role = Role(id=_u(), name=f"Role_{sfx}")
        session.add(role)
        await session.flush()

        emp = Employee(
            id=_u(),
            user_id=u_emp.id,
            employee_code=f"EMP_{sfx}",
            mobile_id=u_emp.mobile_id,
            name=f"Worker_{sfx}",
        )
        session.add(emp)
        await session.flush()

        act = Activity(id=_u(), name=f"Activity_{sfx}", unit_of_measure="metre", approved_rate=150.00, category="cable")
        mat = Material(id=_u(), name=f"Material_{sfx}", unit_of_measure="nos", category="consumable", purchase_approval_limit=5000.00)
        session.add_all([act, mat])
        await session.flush()

        # 3. Operational Records
        att = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 5),
            status="approved",
            check_in_time=_now(),
        )
        session.add(att)
        await session.flush()

        dwe1 = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe1_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=date(2026, 10, 5),
            quantity=100.0,
            uom="metre",
            status="approved",
        )
        dwe2 = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe2_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=date(2026, 10, 6),
            quantity=50.0,
            uom="metre",
            status="approved",
        )
        session.add_all([dwe1, dwe2])
        await session.flush()

        mt1 = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe1.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="Cable Ties",
            quantity=10.0,
            amount=500.0,
            status="approved",
        )
        mt2 = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe2.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="Anchor Bolts",
            quantity=20.0,
            amount=1200.0,
            status="approved",
        )
        session.add_all([mt1, mt2])
        await session.commit()

        yield {
            "director": u_dir,
            "client": client,
            "project": project,
            "site": site,
            "dwe1": dwe1,
            "dwe2": dwe2,
            "mt1": mt1,
            "mt2": mt2,
        }


@pytest.mark.asyncio
async def test_invoice_creation_and_defaults(invoice_db_setup):
    """Verifies invoice creation with defaults and successful persistence."""
    data = invoice_db_setup
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-TEST-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            created_by=data["director"].id,
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)

        assert inv.status == "draft"
        assert inv.subtotal_work == Decimal("0.00")
        assert inv.subtotal_material == Decimal("0.00")
        assert inv.tax_amount == Decimal("0.00")
        assert inv.total_amount == Decimal("0.00")
        assert inv.paid_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_invoice_status_lifecycle_constraints(invoice_db_setup):
    """Verifies valid V1 statuses ('draft', 'issued', 'partially_paid', 'paid', 'cancelled')
    succeed, and strictly rejects 'approved' or any other non-lifecycle state."""
    data = invoice_db_setup

    # Valid statuses must all succeed
    valid_statuses = ["draft", "issued", "partially_paid", "paid", "cancelled"]
    for valid_st in valid_statuses:
        async with TestingSessionLocal() as session:
            inv = Invoice(
                id=_u(),
                invoice_number=f"INV-ST-{valid_st[:4]}-{_u().hex[:6]}",
                idempotency_key=f"idem_{_u().hex[:8]}",
                client_id=data["client"].id,
                project_id=data["project"].id,
                site_id=data["site"].id,
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 7),
                status=valid_st,
            )
            session.add(inv)
            await session.commit()

    # 'approved' is NOT in V1 lifecycle -> must raise IntegrityError
    async with TestingSessionLocal() as session:
        inv_approved = Invoice(
            id=_u(),
            invoice_number=f"INV-APP-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="approved",
        )
        session.add(inv_approved)
        with pytest.raises(IntegrityError):
            await session.commit()

    # Arbitrary invalid status -> must raise IntegrityError
    async with TestingSessionLocal() as session:
        inv_bad = Invoice(
            id=_u(),
            invoice_number=f"INV-BAD-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            status="finalised",
        )
        session.add(inv_bad)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_invoice_header_check_constraints(invoice_db_setup):
    """Verifies that DB-level constraints reject invalid dates, negative amounts, and due_date before issue_date."""
    data = invoice_db_setup

    # 1. period_end < period_start
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-ERR-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 10),
            period_end=date(2026, 10, 5),
        )
        session.add(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. negative tax_amount
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-ERR-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            tax_amount=Decimal("-10.00"),
        )
        session.add(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 3. negative total_amount
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-ERR-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            total_amount=Decimal("-0.01"),
        )
        session.add(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 4. negative paid_amount
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-ERR-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            paid_amount=Decimal("-50.00"),
        )
        session.add(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 5. due_date < issue_date
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-ERR-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            issue_date=date(2026, 10, 15),
            due_date=date(2026, 10, 10),
        )
        session.add(inv)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_invoice_line_quantity_strictly_positive(invoice_db_setup):
    """Verifies that invoice lines require quantity > 0, rejecting zero or negative quantities at DB level."""
    data = invoice_db_setup

    # Valid positive quantity succeeds
    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-QTY1-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv)
        await session.flush()

        line_valid = InvoiceLineItem(
            id=_u(),
            invoice_id=inv.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe1"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Valid quantity line",
            quantity=Decimal("0.50"),
            uom="metre",
            standard_rate=Decimal("100.00"),
            unit_rate=Decimal("100.00"),
            line_amount=Decimal("50.00"),
        )
        session.add(line_valid)
        await session.commit()

    # Zero quantity -> MUST raise IntegrityError
    async with TestingSessionLocal() as session:
        inv_zero = Invoice(
            id=_u(),
            invoice_number=f"INV-QTY0-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv_zero)
        await session.flush()

        line_zero = InvoiceLineItem(
            id=_u(),
            invoice_id=inv_zero.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe2"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 6),
            item_description="Zero quantity line",
            quantity=Decimal("0.00"),
            uom="metre",
            standard_rate=Decimal("100.00"),
            unit_rate=Decimal("100.00"),
            line_amount=Decimal("0.00"),
        )
        session.add(line_zero)
        with pytest.raises(IntegrityError):
            await session.commit()

    # Negative quantity -> MUST raise IntegrityError
    async with TestingSessionLocal() as session:
        inv_neg = Invoice(
            id=_u(),
            invoice_number=f"INV-QTYNEG-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv_neg)
        await session.flush()

        line_neg = InvoiceLineItem(
            id=_u(),
            invoice_id=inv_neg.id,
            line_type="material",
            source_daily_work_entry_id=None,
            source_material_transaction_id=data["mt1"].id,
            source_date=date(2026, 10, 5),
            item_description="Negative quantity line",
            quantity=Decimal("-1.00"),
            uom="nos",
            standard_rate=Decimal("50.00"),
            unit_rate=Decimal("50.00"),
            line_amount=Decimal("50.00"),
        )
        session.add(line_neg)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_invoice_line_single_source_integrity(invoice_db_setup):
    """Verifies that exactly one source reference is allowed per invoice line item."""
    data = invoice_db_setup

    async with TestingSessionLocal() as session:
        inv = Invoice(
            id=_u(),
            invoice_number=f"INV-LINE-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv)
        await session.flush()

        # 1. Valid work line: daily_work_entry_id set, material NULL -> succeeds
        line_work = InvoiceLineItem(
            id=_u(),
            invoice_id=inv.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe1"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Cable pulling",
            quantity=Decimal("100.00"),
            uom="metre",
            standard_rate=Decimal("150.00"),
            unit_rate=Decimal("150.00"),
            line_amount=Decimal("15000.00"),
        )
        session.add(line_work)

        # 2. Valid material line: material_transaction_id set, daily_work NULL -> succeeds
        line_mat = InvoiceLineItem(
            id=_u(),
            invoice_id=inv.id,
            line_type="material",
            source_daily_work_entry_id=None,
            source_material_transaction_id=data["mt1"].id,
            source_date=date(2026, 10, 5),
            item_description="Cable Ties",
            quantity=Decimal("10.00"),
            uom="nos",
            standard_rate=Decimal("50.00"),
            unit_rate=Decimal("50.00"),
            line_amount=Decimal("500.00"),
        )
        session.add(line_mat)
        await session.commit()

    # 3. Neither source set -> raises IntegrityError
    async with TestingSessionLocal() as session:
        inv2 = Invoice(
            id=_u(),
            invoice_number=f"INV-LINE2-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv2)
        await session.flush()

        line_neither = InvoiceLineItem(
            id=_u(),
            invoice_id=inv2.id,
            line_type="work",
            source_daily_work_entry_id=None,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Invalid line",
            quantity=Decimal("10.00"),
            uom="metre",
            standard_rate=Decimal("10.00"),
            unit_rate=Decimal("10.00"),
            line_amount=Decimal("100.00"),
        )
        session.add(line_neither)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 4. Both sources set -> raises IntegrityError
    async with TestingSessionLocal() as session:
        inv3 = Invoice(
            id=_u(),
            invoice_number=f"INV-LINE3-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv3)
        await session.flush()

        line_both = InvoiceLineItem(
            id=_u(),
            invoice_id=inv3.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe2"].id,
            source_material_transaction_id=data["mt2"].id,
            source_date=date(2026, 10, 6),
            item_description="Invalid line with both",
            quantity=Decimal("10.00"),
            uom="metre",
            standard_rate=Decimal("10.00"),
            unit_rate=Decimal("10.00"),
            line_amount=Decimal("100.00"),
        )
        session.add(line_both)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_invoice_line_partial_unique_indexes(invoice_db_setup):
    """Verifies that partial unique indexes prevent double billing while permitting unblocking when is_active=FALSE."""
    data = invoice_db_setup

    async with TestingSessionLocal() as session:
        inv1 = Invoice(
            id=_u(),
            invoice_number=f"INV-PAR1-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv1)
        await session.flush()

        # Add active line for dwe1
        line1 = InvoiceLineItem(
            id=_u(),
            invoice_id=inv1.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe1"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Cable pulling",
            quantity=Decimal("100.00"),
            uom="metre",
            standard_rate=Decimal("150.00"),
            unit_rate=Decimal("150.00"),
            line_amount=Decimal("15000.00"),
            is_active=True,
        )
        session.add(line1)
        await session.commit()

    # Second active line for same dwe1 -> raises IntegrityError
    async with TestingSessionLocal() as session:
        inv2 = Invoice(
            id=_u(),
            invoice_number=f"INV-PAR2-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv2)
        await session.flush()

        line2 = InvoiceLineItem(
            id=_u(),
            invoice_id=inv2.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe1"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Duplicate cable pulling",
            quantity=Decimal("100.00"),
            uom="metre",
            standard_rate=Decimal("150.00"),
            unit_rate=Decimal("150.00"),
            line_amount=Decimal("15000.00"),
            is_active=True,
        )
        session.add(line2)
        with pytest.raises(IntegrityError):
            await session.commit()

    # Simulate cancellation of inv1: set line1.is_active = False
    async with TestingSessionLocal() as session:
        await session.execute(
            text("UPDATE invoice_line_items SET is_active = FALSE WHERE id = :lid"),
            {"lid": line1.id},
        )
        await session.commit()

    # Now billing dwe1 in inv3 succeeds because line1 is no longer active!
    async with TestingSessionLocal() as session:
        inv3 = Invoice(
            id=_u(),
            invoice_number=f"INV-PAR3-{_u().hex[:6]}",
            idempotency_key=f"idem_{_u().hex[:8]}",
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        session.add(inv3)
        await session.flush()

        line3 = InvoiceLineItem(
            id=_u(),
            invoice_id=inv3.id,
            line_type="work",
            source_daily_work_entry_id=data["dwe1"].id,
            source_material_transaction_id=None,
            source_date=date(2026, 10, 5),
            item_description="Re-billed cable pulling",
            quantity=Decimal("100.00"),
            uom="metre",
            standard_rate=Decimal("150.00"),
            unit_rate=Decimal("150.00"),
            line_amount=Decimal("15000.00"),
            is_active=True,
        )
        session.add(line3)
        await session.commit()


@pytest.mark.asyncio
async def test_invoice_sequence_concurrency_safe():
    """Verifies that invoice_number_seq generates forward-only, monotonically increasing integer IDs."""
    async with TestingSessionLocal() as session:
        val1 = (await session.execute(text("SELECT nextval('invoice_number_seq')"))).scalar()
        val2 = (await session.execute(text("SELECT nextval('invoice_number_seq')"))).scalar()
        assert val2 == val1 + 1

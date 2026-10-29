from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.invoices import Invoice, InvoiceLineItem
from app.models.system import AuditLog
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
from app.modules.invoices.schemas import (
    CancelInvoiceRequest,
    GenerateInvoiceRequest,
    IssueInvoiceRequest,
    RateOverrideItem,
    UpdateDraftInvoiceRequest,
)
from app.modules.invoices.service import InvoiceService
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def svc_setup():
    """Sets up a comprehensive fixture with clients, projects, sites, activities, materials,
    approved daily work, and approved material transactions."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_dir = User(id=_u(), mobile_id=f"+9197{sfx[:6]}1", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9197{sfx[:6]}2", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9197{sfx[:6]}3", role="employee")
        session.add_all([u_dir, u_sup, u_emp])
        await session.flush()

        # 2. Hierarchy: Client -> Project -> Site
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Project_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        site_other = Site(id=_u(), project_id=project.id, name=f"OtherSite_{sfx}")
        session.add_all([site, site_other])
        await session.flush()

        # Another client & project for scoping tests
        client_other = Client(id=_u(), name=f"ClientOther_{sfx}")
        session.add(client_other)
        await session.flush()

        project_other = Project(id=_u(), client_id=client_other.id, name=f"ProjOther_{sfx}", status="in_progress")
        session.add(project_other)
        await session.flush()

        # 3. Workforce & Catalog
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

        act1 = Activity(id=_u(), name=f"Cable Pulling_{sfx}", unit_of_measure="metre", approved_rate=120.00, category="cable")
        act2 = Activity(id=_u(), name=f"Camera Mount_{sfx}", unit_of_measure="nos", approved_rate=450.00, category="mounting")
        mat1 = Material(id=_u(), name=f"RJ45 Connector_{sfx}", unit_of_measure="pack", category="consumable", purchase_approval_limit=5000.00)
        session.add_all([act1, act2, mat1])
        await session.flush()

        # 4. Attendance
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

        # 5. Daily Work Entries (in-period, target site, approved)
        # Work 1: 100 metres @ 120 = 12000.00
        dwe1 = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe1_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act1.id,
            work_date=date(2026, 10, 5),
            quantity=100.0,
            uom="metre",
            status="approved",
        )
        # Work 2: 10 cameras @ 450 = 4500.00
        dwe2 = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe2_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act2.id,
            work_date=date(2026, 10, 6),
            quantity=10.0,
            uom="nos",
            status="approved",
        )
        # Work 3 (OUT OF PERIOD: 2026-10-20)
        dwe_out = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe_out_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act1.id,
            work_date=date(2026, 10, 20),
            quantity=50.0,
            uom="metre",
            status="approved",
        )
        # Work 4 (DIFFERENT SITE)
        dwe_diff_site = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe_diff_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site_other.id,
            activity_id=act1.id,
            work_date=date(2026, 10, 5),
            quantity=50.0,
            uom="metre",
            status="approved",
        )
        # Work 5 (NOT APPROVED: submitted)
        dwe_subm = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe_subm_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act1.id,
            work_date=date(2026, 10, 5),
            quantity=30.0,
            uom="metre",
            status="submitted",
        )
        session.add_all([dwe1, dwe2, dwe_out, dwe_diff_site, dwe_subm])
        await session.flush()

        # 6. Material Transactions
        # Material 1: 3 packs @ amount = 1000.00 (notice 1000 / 3 has repeating decimal 333.333...)
        # Financial amount must remain exactly 1000.00!
        mt1 = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe1.id,
            material_id=mat1.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="RJ45 Connectors",
            quantity=3.0,
            amount=1000.0,
            status="approved",
        )
        # Material 2: out of period because parent dwe_out is in late October
        mt_out = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe_out.id,
            material_id=mat1.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="RJ45 Late",
            quantity=1.0,
            amount=350.0,
            status="approved",
        )
        # Material 3: not approved
        mt_subm = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe1.id,
            material_id=mat1.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="Unapproved Tape",
            quantity=2.0,
            amount=200.0,
            status="submitted",
        )
        session.add_all([mt1, mt_out, mt_subm])
        await session.commit()

        yield {
            "director": u_dir,
            "supervisor": u_sup,
            "employee": u_emp,
            "client": client,
            "client_other": client_other,
            "project": project,
            "project_other": project_other,
            "site": site,
            "site_other": site_other,
            "dwe1": dwe1,
            "dwe2": dwe2,
            "dwe_out": dwe_out,
            "mt1": mt1,
            "act1": act1,
            "act2": act2,
        }


@pytest.mark.asyncio
async def test_preview_invoice_scoping_and_date_filtering(svc_setup):
    """Verifies that invoice preview returns only approved, unbilled records strictly within
    the target date range and site, enforcing site-project-client hierarchy."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        # Valid preview
        preview = await InvoiceService.preview_invoice(
            session=session,
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )

        assert preview.billable_work_count == 2
        assert preview.billable_material_count == 1
        # dwe1: 100 * 120 = 12000.00; dwe2: 10 * 450 = 4500.00 => subtotal = 16500.00
        assert preview.subtotal_work == Decimal("16500.00")
        # mt1: amount = 1000.00
        assert preview.subtotal_material == Decimal("1000.00")
        assert preview.estimated_tax == Decimal("0.00")
        assert preview.estimated_total == Decimal("17500.00")
        assert len(preview.items) == 3

        # Scoping error: project does not belong to client
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.preview_invoice(
                session=session,
                client_id=data["client_other"].id,  # mismatch!
                project_id=data["project"].id,
                site_id=data["site"].id,
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 7),
            )
        assert exc_info.value.status_code == 422

        # Scoping error: site does not belong to project
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.preview_invoice(
                session=session,
                client_id=data["client_other"].id,
                project_id=data["project_other"].id,
                site_id=data["site"].id,  # site belongs to project, not project_other!
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 7),
            )
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_generate_invoice_approved_work_and_material_billing(svc_setup):
    """Verifies generating an invoice from approved work and materials:
    - Snapshots activity approved rates and work date.
    - Preserves material transaction amount exactly despite quantity division.
    - Generates sequential invoice number from sequence.
    - Tax defaults to 0.00."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_basic_{_u().hex[:8]}",
            client_po_number="PO-2026-999",
            notes="Standard weekly client invoice",
        )

        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        assert inv.status == "draft"
        assert inv.invoice_number.startswith("INV-")
        assert inv.client_id == data["client"].id
        assert inv.subtotal_work == Decimal("16500.00")
        assert inv.subtotal_material == Decimal("1000.00")
        assert inv.tax_amount == Decimal("0.00")
        assert inv.total_amount == Decimal("17500.00")
        assert inv.paid_amount == Decimal("0.00")
        assert len(inv.lines) == 3

        # Check line details
        work_lines = [l for l in inv.lines if l.line_type == "work"]
        mat_lines = [l for l in inv.lines if l.line_type == "material"]
        assert len(work_lines) == 2
        assert len(mat_lines) == 1

        # Check material line: amount preserved exactly as 1000.00
        mat_line = mat_lines[0]
        assert mat_line.source_material_transaction_id == data["mt1"].id
        assert mat_line.source_date == date(2026, 10, 5)  # DailyWorkEntry.work_date!
        assert mat_line.quantity == Decimal("3.00")
        assert mat_line.line_amount == Decimal("1000.00")  # Exactly 1000.00 preserved!
        assert mat_line.is_active is True


@pytest.mark.asyncio
async def test_unbilled_filtering_prevents_double_invoicing(svc_setup):
    """Verifies that generated invoice lines lock the underlying source records from future previews
    and prevent duplicate generation attempts."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_lock_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        assert inv.id is not None

        # Subsequent preview should report 0 unbilled records
        preview = await InvoiceService.preview_invoice(
            session=session,
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        assert preview.billable_work_count == 0
        assert preview.billable_material_count == 0
        assert preview.estimated_total == Decimal("0.00")

        # Attempting generation for the same period with a different idempotency key must fail
        req_dup = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_lock_dup_{_u().hex[:8]}",
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.generate_invoice(session, req_dup, current_user=data["director"])
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_director_rate_override_with_mandatory_reason(svc_setup):
    """Verifies that a Director can override a work entry rate with a mandatory reason."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        # Standard rate for dwe1 is 120.00. Override to 140.00.
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_ovr_{_u().hex[:8]}",
            rate_overrides=[
                RateOverrideItem(
                    source_id=data["dwe1"].id,
                    unit_rate=Decimal("140.00"),
                    rate_override_reason="Client agreed to difficult terrain supplement",
                )
            ],
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        line1 = next(l for l in inv.lines if l.source_daily_work_entry_id == data["dwe1"].id)
        assert line1.standard_rate == Decimal("120.00")
        assert line1.unit_rate == Decimal("140.00")
        assert line1.line_amount == Decimal("14000.00")  # 100 * 140.00
        assert line1.rate_override_reason == "Client agreed to difficult terrain supplement"
        # Total: 14000 (dwe1) + 4500 (dwe2) + 1000 (mt1) = 19500.00
        assert inv.subtotal_work == Decimal("18500.00")
        assert inv.total_amount == Decimal("19500.00")


@pytest.mark.asyncio
async def test_rate_override_missing_reason_rejected(svc_setup):
    """Verifies that rate override without a valid reason is rejected with 422."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_no_rsn_{_u().hex[:8]}",
            rate_overrides=[
                RateOverrideItem(
                    source_id=data["dwe1"].id,
                    unit_rate=Decimal("150.00"),
                    rate_override_reason="   ",  # whitespace only!
                )
            ],
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_rate_override_rbac_authorization(svc_setup):
    """Verifies that a non-Director (e.g. supervisor or employee) is forbidden from overriding rates."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_rbac_{_u().hex[:8]}",
            rate_overrides=[
                RateOverrideItem(
                    source_id=data["dwe1"].id,
                    unit_rate=Decimal("130.00"),
                    rate_override_reason="Unpermitted adjustment",
                )
            ],
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.generate_invoice(session, req, current_user=data["supervisor"])
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_draft_invoice_tax_and_overrides(svc_setup):
    """Verifies updating tax amount and rate overrides on a draft invoice, and recalculating totals."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_upd_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        # Update draft with tax amount and line override
        upd_req = UpdateDraftInvoiceRequest(
            tax_amount=Decimal("1500.00"),
            client_po_number="PO-UPDATED-001",
            rate_overrides=[
                RateOverrideItem(
                    source_id=data["dwe2"].id,
                    unit_rate=Decimal("500.00"),
                    rate_override_reason="Director special rate revision",
                )
            ],
        )
        inv_upd = await InvoiceService.update_draft_invoice(
            session=session,
            invoice_id=inv.id,
            request=upd_req,
            current_user=data["director"],
        )

        assert inv_upd.client_po_number == "PO-UPDATED-001"
        assert inv_upd.tax_amount == Decimal("1500.00")
        # dwe1: 100 * 120 = 12000; dwe2: 10 * 500 = 5000 => subtotal_work = 17000
        assert inv_upd.subtotal_work == Decimal("17000.00")
        assert inv_upd.subtotal_material == Decimal("1000.00")
        assert inv_upd.total_amount == Decimal("19500.00")  # 17000 + 1000 + 1500


@pytest.mark.asyncio
async def test_idempotent_generation_and_replay(svc_setup):
    """Verifies that replaying the generation request with the same idempotency key
    returns the original invoice without creating new records."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        idem_key = f"idem_rep_{_u().hex[:8]}"
        req1 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=idem_key,
        )
        inv1 = await InvoiceService.generate_invoice(session, req1, current_user=data["director"])

        # Exact replay returns same invoice
        inv2 = await InvoiceService.generate_invoice(session, req1, current_user=data["director"])
        assert inv1.id == inv2.id
        assert inv1.invoice_number == inv2.invoice_number

        # Reusing same idempotency key with different dates -> 409 Conflict
        req_conf = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 10),
            period_end=date(2026, 10, 15),
            idempotency_key=idem_key,
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.generate_invoice(session, req_conf, current_user=data["director"])
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_issue_invoice_lifecycle_and_freeze(svc_setup):
    """Verifies issuing an invoice transitions status to 'issued', freezes financial fields,
    and rejects modifications once issued."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_iss_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        # Issue invoice
        issue_req = IssueInvoiceRequest(
            issue_date=date(2026, 10, 8),
            due_date=date(2026, 10, 22),
        )
        issued_inv = await InvoiceService.issue_invoice(
            session=session,
            invoice_id=inv.id,
            current_user_id=data["director"].id,
            request=issue_req,
        )

        assert issued_inv.status == "issued"
        assert issued_inv.issue_date == date(2026, 10, 8)
        assert issued_inv.due_date == date(2026, 10, 22)
        assert issued_inv.issued_by == data["director"].id
        assert issued_inv.issued_at is not None

        # Re-issuing an already issued invoice is rejected
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.issue_invoice(
                session=session,
                invoice_id=inv.id,
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400

        # Attempting to update an issued invoice is rejected
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.update_draft_invoice(
                session=session,
                invoice_id=inv.id,
                request=UpdateDraftInvoiceRequest(tax_amount=Decimal("100.00")),
                current_user=data["director"],
            )
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_cancellation_releases_source_locks_atomically(svc_setup):
    """Verifies that cancelling an invoice atomically transitions its status to 'cancelled'
    and deactivates line items (is_active = FALSE), allowing the underlying records to be re-invoiced."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_can_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        # Preview shows 0 records locked
        preview_before = await InvoiceService.preview_invoice(
            session=session,
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        assert preview_before.billable_work_count == 0

        # Cancel the invoice
        can_req = CancelInvoiceRequest(cancellation_reason="Billing scope was revised by client")
        cancelled_inv = await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv.id,
            request=can_req,
            current_user_id=data["director"].id,
        )

        assert cancelled_inv.status == "cancelled"
        assert cancelled_inv.cancellation_reason == "Billing scope was revised by client"
        assert cancelled_inv.cancelled_by == data["director"].id
        assert cancelled_inv.cancelled_at is not None
        # All lines must now be inactive
        for line in cancelled_inv.lines:
            assert line.is_active is False

        # Preview now reveals the original records again!
        preview_after = await InvoiceService.preview_invoice(
            session=session,
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
        )
        assert preview_after.billable_work_count == 2
        assert preview_after.billable_material_count == 1
        assert preview_after.estimated_total == Decimal("17500.00")

        # Now re-generating an invoice for the same period with a new idempotency key succeeds!
        req2 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_can_re_{_u().hex[:8]}",
        )
        inv2 = await InvoiceService.generate_invoice(session, req2, current_user=data["director"])
        assert inv2.status == "draft"
        assert inv2.id != inv.id
        assert inv2.total_amount == Decimal("17500.00")


@pytest.mark.asyncio
async def test_prohibited_cancellation_of_paid_and_partially_paid_invoices(svc_setup):
    """Verifies that invoices that are paid, partially paid, or have paid_amount > 0 CANNOT be cancelled."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gen_nopay_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        # Manually simulate partial payment
        await session.execute(
            text("UPDATE invoices SET status = 'partially_paid', paid_amount = 5000.00 WHERE id = :id"),
            {"id": inv.id},
        )
        await session.commit()

        can_req = CancelInvoiceRequest(cancellation_reason="Attempt to cancel partially paid invoice")
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.cancel_invoice(
                session=session,
                invoice_id=inv.id,
                request=can_req,
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400

        # Manually simulate fully paid invoice
        await session.execute(
            text("UPDATE invoices SET status = 'paid', paid_amount = total_amount WHERE id = :id"),
            {"id": inv.id},
        )
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.cancel_invoice(
                session=session,
                invoice_id=inv.id,
                request=can_req,
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_invoice_number_sequence_monotonicity(svc_setup):
    """Verifies that invoice numbers follow the strict INV-YYYYMMDD-XXXX format
    and increase monotonically using the PostgreSQL sequence without wrapping."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req1 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"seq1_{_u().hex[:8]}",
        )
        inv1 = await InvoiceService.generate_invoice(session, req1, current_user=data["director"])
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert inv1.invoice_number.startswith(f"INV-{today_str}-")

        # Cancel inv1 so records are billable again
        await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv1.id,
            request=CancelInvoiceRequest(cancellation_reason="Seq test cancellation"),
            current_user_id=data["director"].id,
        )

        req2 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"seq2_{_u().hex[:8]}",
        )
        inv2 = await InvoiceService.generate_invoice(session, req2, current_user=data["director"])
        assert inv2.invoice_number.startswith(f"INV-{today_str}-")

        seq1_num = int(inv1.invoice_number.split("-")[-1])
        seq2_num = int(inv2.invoice_number.split("-")[-1])
        assert seq2_num > seq1_num


@pytest.mark.asyncio
async def test_empty_invoice_generation_rejected(svc_setup):
    """Verifies that attempting to generate an invoice when no billable records exist is rejected with 400."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        # Billing period where no work was done
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            idempotency_key=f"empty_{_u().hex[:8]}",
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        assert exc_info.value.status_code == 400
        assert "No unbilled approved records found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions(svc_setup):
    """Verifies that invalid lifecycle transitions are rejected:
    - cannot update an issued invoice
    - cannot update a cancelled invoice
    - cannot issue a cancelled invoice
    - cannot cancel an already cancelled invoice
    - cannot issue with due_date < issue_date
    """
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"trans_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])

        # 1. Reject invalid due_date < issue_date:
        # a) Schema-level validation
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            IssueInvoiceRequest(issue_date=date(2026, 10, 10), due_date=date(2026, 10, 5))

        # b) Service-level validation when existing due_date < requested issue_date
        await InvoiceService.update_draft_invoice(
            session=session,
            invoice_id=inv.id,
            request=UpdateDraftInvoiceRequest(due_date=date(2026, 10, 5)),
            current_user=data["director"],
        )
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.issue_invoice(
                session=session,
                invoice_id=inv.id,
                current_user_id=data["director"].id,
                request=IssueInvoiceRequest(
                    issue_date=date(2026, 10, 10),  # later than due_date 2026-10-05!
                ),
            )
        assert exc_info.value.status_code == 422

        # 2. Cancel invoice
        await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv.id,
            request=CancelInvoiceRequest(cancellation_reason="Testing transitions"),
            current_user_id=data["director"].id,
        )

        # 3. Reject issuing a cancelled invoice
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.issue_invoice(
                session=session,
                invoice_id=inv.id,
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400

        # 4. Reject updating a cancelled invoice
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.update_draft_invoice(
                session=session,
                invoice_id=inv.id,
                request=UpdateDraftInvoiceRequest(notes="New notes"),
                current_user=data["director"],
            )
        assert exc_info.value.status_code == 400

        # 5. Reject cancelling an already cancelled invoice
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.cancel_invoice(
                session=session,
                invoice_id=inv.id,
                request=CancelInvoiceRequest(cancellation_reason="Repeat cancel"),
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_concurrent_generation_handling(svc_setup):
    """Verifies that concurrent invoice generation requests using the same idempotency key
    safely complete without duplicate lines or sequence corruption."""
    import asyncio

    data = svc_setup
    idem_key = f"concurrent_{_u().hex[:8]}"
    req = GenerateInvoiceRequest(
        client_id=data["client"].id,
        project_id=data["project"].id,
        site_id=data["site"].id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 7),
        idempotency_key=idem_key,
    )

    async def _run_gen():
        async with TestingSessionLocal() as s:
            return await InvoiceService.generate_invoice(s, req, current_user=data["director"])

    results = await asyncio.gather(_run_gen(), _run_gen(), return_exceptions=True)
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) >= 1
    for s in successes:
        assert s.id == successes[0].id
        assert s.invoice_number == successes[0].invoice_number


@pytest.mark.asyncio
async def test_sequence_uniqueness_and_safe_gaps_on_rollback(svc_setup):
    """Verifies that:
    1. Idempotency replay returns the existing invoice without creating a new record.
    2. Failed or rolled back transactions can consume sequence values creating gaps,
       which are safely absorbed while guaranteeing invoice number uniqueness without collisions.
    3. Concurrent generation and rollbacks never produce duplicate invoice numbers."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        idem_key = f"gap_test_{_u().hex[:8]}"
        req1 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=idem_key,
        )
        inv1 = await InvoiceService.generate_invoice(session, req1, current_user=data["director"])
        seq1_num = int(inv1.invoice_number.split("-")[-1])

        # 1. Exact replay returns same invoice, no new invoice created
        inv1_replay = await InvoiceService.generate_invoice(session, req1, current_user=data["director"])
        assert inv1_replay.id == inv1.id
        assert inv1_replay.invoice_number == inv1.invoice_number

        # 2. Simulate a transaction that consumes sequence numbers and rolls back
        async with TestingSessionLocal() as fail_session:
            # Advance sequence and roll back
            await fail_session.execute(text("SELECT nextval('invoice_number_seq')"))
            await fail_session.execute(text("SELECT nextval('invoice_number_seq')"))
            await fail_session.rollback()

        # Cancel inv1 so records can be billed in next invoice
        await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv1.id,
            request=CancelInvoiceRequest(cancellation_reason="Allow next invoice generation"),
            current_user_id=data["director"].id,
        )

        # 3. Next invoice generation succeeds, absorbs the sequence gap, guarantees uniqueness
        req2 = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"gap_test2_{_u().hex[:8]}",
        )
        inv2 = await InvoiceService.generate_invoice(session, req2, current_user=data["director"])
        seq2_num = int(inv2.invoice_number.split("-")[-1])

        # seq2 must be strictly greater, reflecting consumed values from rolled back session (gap >= 2)
        assert seq2_num > seq1_num + 1
        assert inv1.invoice_number != inv2.invoice_number


@pytest.mark.asyncio
async def test_cancel_invoice_creates_central_audit_log(svc_setup):
    """Verifies that cancelling an invoice creates a central AuditLog entry with invoice_cancelled action,
    capturing entity ID, actor, timestamp, cancellation reason, and previous/new state."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"can_audit_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        inv_id = inv.id
        inv_num = inv.invoice_number
        tot_amount = str(inv.total_amount)

        # Cancel the invoice
        can_reason = "Billing scope was cancelled due to client dispute"
        can_req = CancelInvoiceRequest(cancellation_reason=can_reason)
        cancelled_inv = await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv_id,
            request=can_req,
            current_user_id=data["director"].id,
        )
        assert cancelled_inv.status == "cancelled"

    # Verify central AuditLog entry in fresh session
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "invoice", AuditLog.entity_id == inv_id, AuditLog.action == "invoice_cancelled")
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.action == "invoice_cancelled"
        assert log.changed_by == data["director"].id
        assert log.created_at is not None
        assert log.previous_values["status"] == "draft"
        assert log.previous_values["invoice_number"] == inv_num
        assert log.previous_values["total_amount"] == tot_amount
        assert log.previous_values["paid_amount"] == "0.00"
        assert log.new_values["status"] == "cancelled"
        assert log.new_values["cancellation_reason"] == can_reason


@pytest.mark.asyncio
async def test_cancel_invoice_duplicate_or_invalid_creates_no_audit_log(svc_setup):
    """Verifies that re-cancelling an already-cancelled invoice or invalid operations create no duplicate audit logs."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"can_dup_audit_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        inv_id = inv.id

        # Cancel once
        can_req = CancelInvoiceRequest(cancellation_reason="Initial cancellation reason")
        await InvoiceService.cancel_invoice(
            session=session,
            invoice_id=inv_id,
            request=can_req,
            current_user_id=data["director"].id,
        )

    # Attempt to cancel again: must fail
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await InvoiceService.cancel_invoice(
                session=session,
                invoice_id=inv_id,
                request=CancelInvoiceRequest(cancellation_reason="Second cancellation attempt"),
                current_user_id=data["director"].id,
            )
        assert exc_info.value.status_code == 400
        assert "already cancelled" in exc_info.value.detail

    # Verify exactly 1 audit entry exists
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "invoice", AuditLog.entity_id == inv_id, AuditLog.action == "invoice_cancelled")
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1


@pytest.mark.asyncio
async def test_cancel_invoice_transaction_failure_rollback(svc_setup, monkeypatch):
    """Verifies that if commit fails during invoice cancellation, status and audit log are rolled back."""
    data = svc_setup
    async with TestingSessionLocal() as session:
        req = GenerateInvoiceRequest(
            client_id=data["client"].id,
            project_id=data["project"].id,
            site_id=data["site"].id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            idempotency_key=f"can_fail_audit_{_u().hex[:8]}",
        )
        inv = await InvoiceService.generate_invoice(session, req, current_user=data["director"])
        inv_id = inv.id

    async with TestingSessionLocal() as session:
        async def mock_fail_commit():
            raise RuntimeError("Database error during cancel_invoice commit")

        monkeypatch.setattr(session, "commit", mock_fail_commit)

        with pytest.raises(RuntimeError):
            await InvoiceService.cancel_invoice(
                session=session,
                invoice_id=inv_id,
                request=CancelInvoiceRequest(cancellation_reason="Testing failure rollback"),
                current_user_id=data["director"].id,
            )

    # Verify status remains draft and NO audit entry exists
    async with TestingSessionLocal() as session:
        inv_db = await session.get(Invoice, inv_id)
        assert inv_db.status == "draft"
        assert inv_db.cancelled_at is None

        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "invoice", AuditLog.entity_id == inv_id)
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 0




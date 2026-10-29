from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.auth import User
from app.models.employee_payments import EmployeePayment, EmployeePaymentLine
from app.models.payroll_settings import PayrollOvertimeSettings
from app.models.system import AuditLog
from app.modules.employee_payments.schemas import CancelPaymentRequest, GeneratePaymentRequest
from app.modules.employee_payments.service import EmployeePaymentService
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Project,
    Site,
)
from app.models.workforce import Employee, EmployeeRateHistory, Role
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def ep_setup():
    """
    Sets up an environment with:
      - Admin and Director users
      - Supervisor and Employee users
      - 3 employees:
        - emp_daily: daily rate (500)
        - emp_weekly: weekly rate (3500)
        - emp_piece: piece rate (20 per unit)
      - 1 site and 1 activity
    """
    async with TestingSessionLocal() as session:
        await session.execute(delete(PayrollOvertimeSettings))
        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9199{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9199{sfx[:6]}2", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9199{sfx[:6]}3", role="supervisor")
        u_emp1 = User(id=_u(), mobile_id=f"+9199{sfx[:6]}4", role="employee")
        u_emp2 = User(id=_u(), mobile_id=f"+9199{sfx[:6]}5", role="employee")
        u_emp3 = User(id=_u(), mobile_id=f"+9199{sfx[:6]}6", role="employee")
        session.add_all([u_admin, u_dir, u_sup, u_emp1, u_emp2, u_emp3])
        await session.flush()

        # 2. Master Data
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        proj = Project(id=_u(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
        session.add(proj)
        await session.flush()

        site = Site(id=_u(), project_id=proj.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        act = Activity(id=_u(), name=f"Cable_{sfx}", unit_of_measure="metres", approved_rate=Decimal("150.00"), category="cable")
        session.add(act)
        await session.flush()

        # 3. Employees
        emp_daily = Employee(id=_u(), user_id=u_emp1.id, employee_code=f"EMP-D-{sfx}", mobile_id=u_emp1.mobile_id, name="Daily Worker")
        emp_weekly = Employee(id=_u(), user_id=u_emp2.id, employee_code=f"EMP-W-{sfx}", mobile_id=u_emp2.mobile_id, name="Weekly Worker")
        emp_piece = Employee(id=_u(), user_id=u_emp3.id, employee_code=f"EMP-P-{sfx}", mobile_id=u_emp3.mobile_id, name="Piece Worker")
        session.add_all([emp_daily, emp_weekly, emp_piece])
        await session.flush()

        # 4. Rate Histories
        r_daily = EmployeeRateHistory(
            id=_u(),
            employee_id=emp_daily.id,
            rate_type="daily",
            rate_amount=Decimal("500.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp_daily.id,
        )
        r_weekly = EmployeeRateHistory(
            id=_u(),
            employee_id=emp_weekly.id,
            rate_type="weekly",
            rate_amount=Decimal("3500.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp_weekly.id,
        )
        r_piece = EmployeeRateHistory(
            id=_u(),
            employee_id=emp_piece.id,
            rate_type="piece",
            rate_amount=Decimal("20.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp_piece.id,
        )
        session.add_all([r_daily, r_weekly, r_piece])
        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), u_admin.role),
            "director": create_access_token(str(u_dir.id), u_dir.role),
            "supervisor": create_access_token(str(u_sup.id), u_sup.role),
            "employee": create_access_token(str(u_emp1.id), u_emp1.role),
        }

        return {
            "users": {"admin": u_admin, "director": u_dir, "supervisor": u_sup, "emp1": u_emp1},
            "tokens": tokens,
            "employees": {"daily": emp_daily, "weekly": emp_weekly, "piece": emp_piece},
            "site": site,
            "activity": act,
        }


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. RBAC Tests
# ---------------------------------------------------------------------------

def test_employee_payments_rbac(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]

    # 1. No auth -> 401
    resp = client.get("/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07")
    assert resp.status_code == 401

    # 2. Employee role -> 403
    resp = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["employee"]),
    )
    assert resp.status_code == 403

    # 3. Supervisor role -> 403
    resp = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["supervisor"]),
    )
    assert resp.status_code == 403

    # 4. Director role -> 200
    resp = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["director"]),
    )
    assert resp.status_code == 200

    # 5. Administrator role -> 200
    resp = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["admin"]),
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. Preview Calculations: Daily, Weekly, Piece & Status Exclusion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_daily_weekly_and_piece_rates(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    act = ep_setup["activity"]

    async with TestingSessionLocal() as session:
        # 3 approved attendance days for daily worker (Oct 1, 2, 3)
        att_d1 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 1), status="approved")
        att_d2 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 2), status="approved")
        att_d3 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 3), status="approved")
        # 1 unapproved attendance (should be excluded)
        att_d_draft = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 4), status="pending_verification")

        # 5 approved attendance days for weekly worker (Oct 1 to Oct 5)
        # Weekly rate = 3500. Pro-rata: (5 / 7) * 3500 = 2500.00
        atts_w = [
            AttendanceRecord(id=_u(), employee_id=emps["weekly"].id, site_id=site.id, date=date(2026, 10, i), status="approved")
            for i in range(1, 6)
        ]

        # Attendance records for piece worker (required by DailyWorkEntry schema)
        att_p1 = AttendanceRecord(id=_u(), employee_id=emps["piece"].id, site_id=site.id, date=date(2026, 10, 1), status="approved")
        att_p2 = AttendanceRecord(id=_u(), employee_id=emps["piece"].id, site_id=site.id, date=date(2026, 10, 2), status="approved")
        att_p3 = AttendanceRecord(id=_u(), employee_id=emps["piece"].id, site_id=site.id, date=date(2026, 10, 3), status="approved")

        # 2 approved daily work entries for piece worker
        # Qty = 50 and 30 @ 20.00 = 1600.00
        # 1 rejected work entry (excluded)
        dwe_p1 = DailyWorkEntry(
            id=_u(), idempotency_key=str(_u()), attendance_record_id=att_p1.id, employee_id=emps["piece"].id, site_id=site.id,
            activity_id=act.id, work_date=date(2026, 10, 1), quantity=50, uom="metres", status="approved"
        )
        dwe_p2 = DailyWorkEntry(
            id=_u(), idempotency_key=str(_u()), attendance_record_id=att_p2.id, employee_id=emps["piece"].id, site_id=site.id,
            activity_id=act.id, work_date=date(2026, 10, 2), quantity=30, uom="metres", status="approved"
        )
        dwe_p_rej = DailyWorkEntry(
            id=_u(), idempotency_key=str(_u()), attendance_record_id=att_p3.id, employee_id=emps["piece"].id, site_id=site.id,
            activity_id=act.id, work_date=date(2026, 10, 3), quantity=100, uom="metres", status="rejected"
        )

        session.add_all([att_d1, att_d2, att_d3, att_d_draft, *atts_w, att_p1, att_p2, att_p3, dwe_p1, dwe_p2, dwe_p_rej])
        await session.commit()

    # Call Preview endpoint
    resp = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["director"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_employees"] == 3

    # Check daily worker
    d_item = next(i for i in data["items"] if i["employee_id"] == str(emps["daily"].id))
    assert Decimal(str(d_item["total_days"])) == Decimal("3.00")
    assert Decimal(str(d_item["total_amount"])) == Decimal("1500.00")
    assert d_item["eligible_attendance_count"] == 3

    # Check weekly worker: (5/7) * 3500 = 2500.00
    w_item = next(i for i in data["items"] if i["employee_id"] == str(emps["weekly"].id))
    assert Decimal(str(w_item["total_days"])) == Decimal("5.00")
    assert Decimal(str(w_item["total_amount"])) == Decimal("2500.00")
    assert w_item["eligible_attendance_count"] == 5

    # Check piece worker: (50 + 30) * 20 = 1600.00
    p_item = next(i for i in data["items"] if i["employee_id"] == str(emps["piece"].id))
    assert Decimal(str(p_item["total_quantity"])) == Decimal("80.00")
    assert Decimal(str(p_item["total_amount"])) == Decimal("1600.00")
    assert p_item["eligible_work_entry_count"] == 2

    # Grand total: 1500 + 2500 + 1600 = 5600.00
    assert Decimal(str(data["grand_total_amount"])) == Decimal("5600.00")


# ---------------------------------------------------------------------------
# 3. Generation, Full Lifecycle & Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_lifecycle_and_idempotency(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Create 2 approved attendance days for daily worker
        d1 = date(2026, 10, 10)
        d2 = date(2026, 10, 11)
        att1 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=d1, status="approved")
        att2 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=d2, status="approved")
        session.add_all([att1, att2])
        await session.commit()

    idemp_key = f"IDEMP-GEN-{str(_u())[:8]}"

    # Step 1: Generate payment (starts as draft)
    gen_payload = {
        "period_start": "2026-10-10",
        "period_end": "2026-10-15",
        "employee_id": str(emps["daily"].id),
        "idempotency_key": idemp_key,
    }
    resp = client.post("/api/v1/employee-payments/generate", json=gen_payload, headers=_auth(tokens["director"]))
    assert resp.status_code == 201
    gen_data = resp.json()
    assert len(gen_data) == 1
    payment_id = gen_data[0]["id"]
    assert gen_data[0]["status"] == "draft"
    assert Decimal(str(gen_data[0]["total_amount"])) == Decimal("1000.00")
    assert Decimal(str(gen_data[0]["total_days"])) == Decimal("2.00")

    # Step 2: Idempotency replay with same key
    resp_replay = client.post("/api/v1/employee-payments/generate", json=gen_payload, headers=_auth(tokens["director"]))
    assert resp_replay.status_code in (200, 201)
    replay_data = resp_replay.json()
    assert replay_data[0]["id"] == payment_id
    assert replay_data[0]["idempotency_key"] == idemp_key

    # Step 3: Fetch detail and verify line items
    resp_detail = client.get(f"/api/v1/employee-payments/{payment_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert len(detail_data["lines"]) == 2
    for line in detail_data["lines"]:
        assert line["rate_type"] == "daily"
        assert Decimal(str(line["rate_amount"])) == Decimal("500.00")
        assert Decimal(str(line["amount"])) == Decimal("500.00")
        assert line["is_active"] is True

    # Step 4: Invalid lifecycle transition — cannot pay while in draft
    resp_bad_pay = client.post(
        f"/api/v1/employee-payments/{payment_id}/pay",
        json={"payment_method": "bank_transfer"},
        headers=_auth(tokens["director"]),
    )
    assert resp_bad_pay.status_code == 400
    assert "approved before being marked as paid" in resp_bad_pay.json()["detail"]

    # Step 5: Approve payment (draft -> approved)
    resp_appr = client.post(f"/api/v1/employee-payments/{payment_id}/approve", headers=_auth(tokens["director"]))
    assert resp_appr.status_code == 200
    assert resp_appr.json()["status"] == "approved"
    assert resp_appr.json()["approved_by"] is not None

    # Step 6: Mark as paid (approved -> paid)
    pay_payload = {
        "payment_date": "2026-10-16",
        "payment_method": "bank_transfer",
        "reference_number": "UTR987654321",
        "remarks": "October first half payout",
    }
    resp_paid = client.post(f"/api/v1/employee-payments/{payment_id}/pay", json=pay_payload, headers=_auth(tokens["director"]))
    assert resp_paid.status_code == 200
    paid_data = resp_paid.json()
    assert paid_data["status"] == "paid"
    assert paid_data["payment_method"] == "bank_transfer"
    assert paid_data["reference_number"] == "UTR987654321"
    assert paid_data["remarks"] == "October first half payout"
    assert paid_data["paid_by"] is not None

    # Step 7: Cannot cancel an already paid payment
    resp_cancel_paid = client.post(
        f"/api/v1/employee-payments/{payment_id}/cancel",
        json={"cancellation_reason": "Attempting to cancel paid"},
        headers=_auth(tokens["director"]),
    )
    assert resp_cancel_paid.status_code == 400


# ---------------------------------------------------------------------------
# 4. Multi-Rate Band Payment Preservation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_rate_band_payment(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Create an employee with 2 consecutive rate bands:
        # Band 1: Oct 1 - Oct 3 @ daily 400.00
        # Band 2: Oct 4 - None @ daily 600.00
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9198{sfx[:6]}7", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(id=_u(), user_id=u.id, employee_code=f"EMP-M-{sfx}", mobile_id=u.mobile_id, name="Multi Rate Worker")
        session.add(emp)
        await session.flush()

        r1 = EmployeeRateHistory(
            id=_u(), employee_id=emp.id, rate_type="daily", rate_amount=Decimal("400.00"),
            effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 3), changed_by=emp.id
        )
        r2 = EmployeeRateHistory(
            id=_u(), employee_id=emp.id, rate_type="daily", rate_amount=Decimal("600.00"),
            effective_from=date(2026, 10, 4), effective_to=None, changed_by=emp.id
        )
        session.add_all([r1, r2])

        # 2 days in Band 1 (Oct 2, Oct 3)
        # 2 days in Band 2 (Oct 4, Oct 5)
        att1 = AttendanceRecord(id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 2), status="approved")
        att2 = AttendanceRecord(id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 3), status="approved")
        att3 = AttendanceRecord(id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 4), status="approved")
        att4 = AttendanceRecord(id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 5), status="approved")
        session.add_all([att1, att2, att3, att4])
        await session.commit()

    # Generate payment across the boundary (Oct 1 - Oct 10)
    gen_payload = {
        "period_start": "2026-10-01",
        "period_end": "2026-10-10",
        "employee_id": str(emp.id),
        "idempotency_key": f"IDEMP-MULTI-{sfx}",
    }
    resp = client.post("/api/v1/employee-payments/generate", json=gen_payload, headers=_auth(tokens["director"]))
    assert resp.status_code == 201
    payment_id = resp.json()[0]["id"]

    # Fetch detail
    resp_detail = client.get(f"/api/v1/employee-payments/{payment_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    data = resp_detail.json()

    # Total: 2 days @ 400 (800) + 2 days @ 600 (1200) = 2000.00
    assert Decimal(str(data["total_days"])) == Decimal("4.00")
    assert Decimal(str(data["total_amount"])) == Decimal("2000.00")

    # Verify both rate bands are preserved in summaries
    summaries = data["rate_band_summaries"]
    assert len(summaries) == 2
    b1 = next(s for s in summaries if Decimal(str(s["rate_amount"])) == Decimal("400.00"))
    b2 = next(s for s in summaries if Decimal(str(s["rate_amount"])) == Decimal("600.00"))
    assert Decimal(str(b1["approved_days"])) == Decimal("2.00")
    assert Decimal(str(b1["gross_amount"])) == Decimal("800.00")
    assert Decimal(str(b2["approved_days"])) == Decimal("2.00")
    assert Decimal(str(b2["gross_amount"])) == Decimal("1200.00")


# ---------------------------------------------------------------------------
# 5. Cancellation Releases Source Records for Re-invoicing / Re-payment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancellation_releases_source_records(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 20), status="approved")
        session.add(att)
        await session.commit()

    idemp1 = f"IDEMP-CANCEL-1-{str(_u())[:8]}"
    idemp2 = f"IDEMP-CANCEL-2-{str(_u())[:8]}"

    # Step 1: Generate payment 1
    resp1 = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-20", "period_end": "2026-10-25", "employee_id": str(emps["daily"].id), "idempotency_key": idemp1},
        headers=_auth(tokens["director"]),
    )
    assert resp1.status_code == 201
    pay1_id = resp1.json()[0]["id"]

    # Step 2: Attempting to generate a second payment with new idempotency key fails (0 eligible records)
    resp2_fail = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-20", "period_end": "2026-10-25", "employee_id": str(emps["daily"].id), "idempotency_key": idemp2},
        headers=_auth(tokens["director"]),
    )
    assert resp2_fail.status_code == 400

    # Step 3: Cancel payment 1
    resp_cancel = client.post(
        f"/api/v1/employee-payments/{pay1_id}/cancel",
        json={"cancellation_reason": "Rate adjustment required"},
        headers=_auth(tokens["director"]),
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"
    # Lines should be deactivated (is_active = False)
    for line in resp_cancel.json()["lines"]:
        assert line["is_active"] is False

    # Step 4: Now generate payment 2 with idemp2: should SUCCEED because records were released!
    resp2_ok = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-20", "period_end": "2026-10-25", "employee_id": str(emps["daily"].id), "idempotency_key": idemp2},
        headers=_auth(tokens["director"]),
    )
    assert resp2_ok.status_code == 201
    assert len(resp2_ok.json()) == 1
    pay2_id = resp2_ok.json()[0]["id"]
    assert pay2_id != pay1_id


# ---------------------------------------------------------------------------
# 6. Database Partial Unique Index Concurrency Protection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_database_partial_unique_index_concurrency_lock(ep_setup):
    """
    Directly tests that attempting to insert a second active line item for the same source attendance record
    is strictly rejected by PostgreSQL partial unique index `uq_active_payment_attendance`.
    """
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 28), status="approved")
        session.add(att)
        await session.flush()

        p1 = EmployeePayment(
            payment_number=f"PAY-DB-LOCK-1-{str(_u())[:6]}",
            idempotency_key=str(_u()),
            employee_id=emps["daily"].id,
            period_start=date(2026, 10, 28),
            period_end=date(2026, 10, 28),
            status="draft",
        )
        p2 = EmployeePayment(
            payment_number=f"PAY-DB-LOCK-2-{str(_u())[:6]}",
            idempotency_key=str(_u()),
            employee_id=emps["daily"].id,
            period_start=date(2026, 10, 28),
            period_end=date(2026, 10, 28),
            status="draft",
        )
        session.add_all([p1, p2])
        await session.flush()

        # Insert first active line item
        line1 = EmployeePaymentLine(
            payment_id=p1.id,
            source_attendance_id=att.id,
            source_date=att.date,
            rate_type="daily",
            rate_amount=Decimal("500.00"),
            rate_effective_from=date(2026, 10, 1),
            days=Decimal("1.00"),
            amount=Decimal("500.00"),
            is_active=True,
        )
        session.add(line1)
        await session.commit()

        # Insert second active line item pointing to the same attendance record
        line2 = EmployeePaymentLine(
            payment_id=p2.id,
            source_attendance_id=att.id,
            source_date=att.date,
            rate_type="daily",
            rate_amount=Decimal("500.00"),
            rate_effective_from=date(2026, 10, 1),
            days=Decimal("1.00"),
            amount=Decimal("500.00"),
            is_active=True,
        )
        session.add(line2)

        with pytest.raises(IntegrityError):
            await session.commit()


# ---------------------------------------------------------------------------
# 7. List Payments with Filters & Pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_payments_filters(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Create an attendance record for daily worker and generate payment
        d = date(2026, 11, 1)
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=d, status="approved")
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-LIST-{str(_u())[:8]}"
    client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-11-01", "period_end": "2026-11-05", "employee_id": str(emps["daily"].id), "idempotency_key": idemp},
        headers=_auth(tokens["director"]),
    )

    # 1. Filter by employee_id
    resp = client.get(f"/api/v1/employee-payments?employee_id={emps['daily'].id}", headers=_auth(tokens["director"]))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert all(p["employee_id"] == str(emps["daily"].id) for p in resp.json())

    # 2. Filter by status
    resp_draft = client.get("/api/v1/employee-payments?status=draft", headers=_auth(tokens["director"]))
    assert resp_draft.status_code == 200
    assert all(p["status"] == "draft" for p in resp_draft.json())

    # 3. Filter by date range
    resp_dates = client.get("/api/v1/employee-payments?period_start=2026-11-01&period_end=2026-11-05", headers=_auth(tokens["director"]))
    assert resp_dates.status_code == 200
    assert len(resp_dates.json()) >= 1


# ---------------------------------------------------------------------------
# 8. Batch Generation for All Eligible Employees
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_generate_payments(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Create approved attendance records for both daily and weekly worker in November
        att1 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 11, 10), status="approved")
        att2 = AttendanceRecord(id=_u(), employee_id=emps["weekly"].id, site_id=site.id, date=date(2026, 11, 10), status="approved")
        session.add_all([att1, att2])
        await session.commit()

    batch_idemp = f"IDEMP-BATCH-{str(_u())[:8]}"
    # Omit employee_id to generate batch for all employees
    resp = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-11-10", "period_end": "2026-11-15", "idempotency_key": batch_idemp},
        headers=_auth(tokens["director"]),
    )
    assert resp.status_code == 201
    payments = resp.json()
    assert len(payments) == 2
    emp_ids_in_batch = {p["employee_id"] for p in payments}
    assert str(emps["daily"].id) in emp_ids_in_batch
    assert str(emps["weekly"].id) in emp_ids_in_batch


# ---------------------------------------------------------------------------
# 9. Line Source Integrity DB Constraint (Exactly One Source Reference)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_line_source_integrity_db_constraints(ep_setup):
    """
    Tests that:
      - line with both attendance_id and work_entry_id violates check constraint
      - line with neither attendance_id nor work_entry_id violates check constraint
    """
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    act = ep_setup["activity"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 1), status="approved")
        session.add(att)
        await session.flush()

        dwe = DailyWorkEntry(
            id=_u(), idempotency_key=str(_u()), attendance_record_id=att.id, employee_id=emps["daily"].id, site_id=site.id,
            activity_id=act.id, work_date=date(2026, 12, 1), quantity=10, uom="metres", status="approved"
        )
        session.add(dwe)
        await session.flush()

        p = EmployeePayment(
            payment_number=f"PAY-SRC-INT-{str(_u())[:6]}",
            idempotency_key=str(_u()),
            employee_id=emps["daily"].id,
            period_start=date(2026, 12, 1),
            period_end=date(2026, 12, 1),
            status="draft",
        )
        session.add(p)
        await session.flush()

        # Case 1: Line with BOTH sources set -> violates check_payment_lines_exactly_one_source
        line_both = EmployeePaymentLine(
            payment_id=p.id,
            source_attendance_id=att.id,
            source_daily_work_entry_id=dwe.id,
            source_date=date(2026, 12, 1),
            rate_type="daily",
            rate_amount=Decimal("500.00"),
            rate_effective_from=date(2026, 10, 1),
            days=Decimal("1.00"),
            amount=Decimal("500.00"),
            is_active=True,
        )
        session.add(line_both)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async with TestingSessionLocal() as session:
        p2 = EmployeePayment(
            payment_number=f"PAY-SRC-INT2-{str(_u())[:6]}",
            idempotency_key=str(_u()),
            employee_id=emps["daily"].id,
            period_start=date(2026, 12, 1),
            period_end=date(2026, 12, 1),
            status="draft",
        )
        session.add(p2)
        await session.flush()

        # Case 2: Line with NEITHER source set -> violates check_payment_lines_exactly_one_source
        line_neither = EmployeePaymentLine(
            payment_id=p2.id,
            source_attendance_id=None,
            source_daily_work_entry_id=None,
            source_date=date(2026, 12, 1),
            rate_type="daily",
            rate_amount=Decimal("500.00"),
            rate_effective_from=date(2026, 10, 1),
            days=Decimal("1.00"),
            amount=Decimal("500.00"),
            is_active=True,
        )
        session.add(line_neither)
        with pytest.raises(IntegrityError):
            await session.commit()


# ---------------------------------------------------------------------------
# 10. Cancellation State Machine Locking & Atomic Line Deactivation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancellation_state_machine_transitions(client: TestClient, ep_setup):
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        att1 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 5), status="approved")
        att2 = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 6), status="approved")
        session.add_all([att1, att2])
        await session.commit()

    # 1. Draft -> Cancelled (allowed)
    idemp1 = f"IDEMP-DRAFT-CANCEL-{str(_u())[:8]}"
    resp1 = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-12-05", "period_end": "2026-12-05", "employee_id": str(emps["daily"].id), "idempotency_key": idemp1},
        headers=_auth(tokens["director"]),
    )
    assert resp1.status_code == 201
    pay1_id = resp1.json()[0]["id"]

    resp1_cancel = client.post(
        f"/api/v1/employee-payments/{pay1_id}/cancel",
        json={"cancellation_reason": "Draft cancelled by director"},
        headers=_auth(tokens["director"]),
    )
    assert resp1_cancel.status_code == 200
    assert resp1_cancel.json()["status"] == "cancelled"
    assert all(l["is_active"] is False for l in resp1_cancel.json()["lines"])

    # 2. Cancelled -> Approved (prohibited)
    resp_bad_appr = client.post(f"/api/v1/employee-payments/{pay1_id}/approve", headers=_auth(tokens["director"]))
    assert resp_bad_appr.status_code == 400

    # 3. Cancelled -> Paid (prohibited)
    resp_bad_pay = client.post(
        f"/api/v1/employee-payments/{pay1_id}/pay",
        json={"payment_method": "cash"},
        headers=_auth(tokens["director"]),
    )
    assert resp_bad_pay.status_code == 400

    # 4. Cancelled -> Cancelled (prohibited)
    resp_re_cancel = client.post(
        f"/api/v1/employee-payments/{pay1_id}/cancel",
        json={"cancellation_reason": "Trying to cancel again"},
        headers=_auth(tokens["director"]),
    )
    assert resp_re_cancel.status_code == 400

    # 5. Approved -> Cancelled (allowed and atomic)
    idemp2 = f"IDEMP-APPR-CANCEL-{str(_u())[:8]}"
    resp2 = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-12-06", "period_end": "2026-12-06", "employee_id": str(emps["daily"].id), "idempotency_key": idemp2},
        headers=_auth(tokens["director"]),
    )
    assert resp2.status_code == 201
    pay2_id = resp2.json()[0]["id"]

    # Transition draft -> approved
    client.post(f"/api/v1/employee-payments/{pay2_id}/approve", headers=_auth(tokens["director"]))

    # Transition approved -> cancelled
    resp2_cancel = client.post(
        f"/api/v1/employee-payments/{pay2_id}/cancel",
        json={"cancellation_reason": "Approved payment cancelled due to discrepancy"},
        headers=_auth(tokens["director"]),
    )
    assert resp2_cancel.status_code == 200
    assert resp2_cancel.json()["status"] == "cancelled"
    assert all(l["is_active"] is False for l in resp2_cancel.json()["lines"])


@pytest.mark.asyncio
async def test_cancel_employee_payment_creates_central_audit_log(client: TestClient, ep_setup):
    """Verifies that cancelling an employee payment creates a central AuditLog entry with
    employee_payment_cancelled action, capturing entity ID, actor, timestamp, reason, and state."""
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    director = ep_setup["users"]["director"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 10), status="approved")
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-AUDIT-EP-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-12-10", "period_end": "2026-12-10", "employee_id": str(emps["daily"].id), "idempotency_key": idemp},
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]
    pay_num = pay_data["payment_number"]
    tot_amt = str(pay_data["total_amount"])

    cancel_reason = "Payroll calculation disputed by employee"
    resp_cancel = client.post(
        f"/api/v1/employee-payments/{pay_id}/cancel",
        json={"cancellation_reason": cancel_reason},
        headers=_auth(tokens["director"]),
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"

    # Verify central AuditLog entry
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "employee_payment", AuditLog.entity_id == uuid.UUID(pay_id), AuditLog.action == "employee_payment_cancelled")
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.action == "employee_payment_cancelled"
        assert log.changed_by == director.id
        assert log.created_at is not None
        assert log.previous_values["status"] == "draft"
        assert log.previous_values["payment_number"] == pay_num
        assert Decimal(log.previous_values["total_amount"]) == Decimal(tot_amt)
        assert log.new_values["status"] == "cancelled"
        assert log.new_values["cancellation_reason"] == cancel_reason


@pytest.mark.asyncio
async def test_cancel_employee_payment_duplicate_or_invalid_creates_no_audit_log(client: TestClient, ep_setup):
    """Verifies that attempting duplicate cancellation or cancelling paid payment does not create extra audit entries."""
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 11), status="approved")
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-AUDIT-DUP-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-12-11", "period_end": "2026-12-11", "employee_id": str(emps["daily"].id), "idempotency_key": idemp},
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    # Cancel once
    resp1 = client.post(
        f"/api/v1/employee-payments/{pay_id}/cancel",
        json={"cancellation_reason": "First cancellation"},
        headers=_auth(tokens["director"]),
    )
    assert resp1.status_code == 200

    # Cancel second time: must fail
    resp2 = client.post(
        f"/api/v1/employee-payments/{pay_id}/cancel",
        json={"cancellation_reason": "Duplicate cancellation attempt"},
        headers=_auth(tokens["director"]),
    )
    assert resp2.status_code == 400
    assert "already cancelled" in resp2.json()["detail"].lower()

    # Verify exactly 1 audit entry
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "employee_payment", AuditLog.entity_id == uuid.UUID(pay_id))
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 1


@pytest.mark.asyncio
async def test_cancel_employee_payment_transaction_failure_rollback(ep_setup, monkeypatch):
    """Verifies that if commit fails during employee payment cancellation, status and audit entry roll back together."""
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    director = ep_setup["users"]["director"]

    async with TestingSessionLocal() as session:
        att = AttendanceRecord(id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 12, 12), status="approved")
        session.add(att)
        await session.commit()

    async with TestingSessionLocal() as session:
        gen_req = GeneratePaymentRequest(
            period_start=date(2026, 12, 12),
            period_end=date(2026, 12, 12),
            employee_id=emps["daily"].id,
            idempotency_key=f"IDEMP-FAIL-EP-{str(_u())[:8]}",
        )
        created_list = await EmployeePaymentService.generate_payments(session, gen_req, current_user=director)
        pay_id = created_list[0].id

    async with TestingSessionLocal() as session:
        async def mock_fail_commit():
            raise RuntimeError("Database error during cancel_payment commit")

        monkeypatch.setattr(session, "commit", mock_fail_commit)

        with pytest.raises(RuntimeError):
            await EmployeePaymentService.cancel_payment(
                session=session,
                payment_id=pay_id,
                request=CancelPaymentRequest(cancellation_reason="Testing failure rollback"),
                current_user=director,
            )

    # In fresh session, verify payment is still draft and NO audit entry exists
    async with TestingSessionLocal() as session:
        payment_check = await session.get(EmployeePayment, pay_id)
        assert payment_check.status == "draft"
        assert payment_check.cancelled_at is None

        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == "employee_payment", AuditLog.entity_id == pay_id)
        )
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) == 0


# ===========================================================================
# 11. BATCH 3 — PAYROLL OVERTIME CALCULATION ENGINE TESTS
# ===========================================================================

@pytest.mark.asyncio
async def test_overtime_daily_worker_calculation(client: TestClient, ep_setup):
    """
    Tests standard hours, overtime rate, daily rate single session calculation,
    field snapshots on line item, and header total reconciliation.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Seed overtime setting: 7.00h standard workday, 1.50x multiplier effective 2026-01-01
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 9 hours worked on Oct 1: 08:00 to 17:00 (2h overtime)
        d = date(2026, 10, 1)
        att = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=d,
            check_in_time=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    # 1. Preview
    resp_prev = client.get(
        "/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-01",
        headers=_auth(tokens["director"]),
    )
    assert resp_prev.status_code == 200
    prev_item = next(i for i in resp_prev.json()["items"] if i["employee_id"] == str(emps["daily"].id))
    assert Decimal(str(prev_item["total_days"])) == Decimal("1.00")
    assert Decimal(str(prev_item["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(prev_item["total_overtime_hours"])) == Decimal("2.00")
    # 500 / 7 = 71.43; 2.00 * 71.43 * 1.50 = 214.29
    assert Decimal(str(prev_item["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(prev_item["total_amount"])) == Decimal("714.29")

    # 2. Generate
    idemp = f"IDEMP-OT-DAILY-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-01",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(pay_data["total_amount"])) == Decimal("714.29")

    # 3. Verify detail line snapshots
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert len(detail["lines"]) == 1
    line = detail["lines"][0]
    assert line["rate_type"] == "daily"
    assert Decimal(str(line["rate_amount"])) == Decimal("500.00")
    assert Decimal(str(line["days"])) == Decimal("1.00")
    assert Decimal(str(line["regular_hours"])) == Decimal("7.00")
    assert Decimal(str(line["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(line["standard_day_hours"])) == Decimal("7.00")
    assert Decimal(str(line["hourly_equivalent_rate"])) == Decimal("71.43")
    assert Decimal(str(line["overtime_multiplier"])) == Decimal("1.50")
    assert Decimal(str(line["regular_amount"])) == Decimal("500.00")
    assert Decimal(str(line["overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(line["amount"])) == Decimal("714.29")


@pytest.mark.asyncio
async def test_overtime_weekly_worker_7_day_basis(client: TestClient, ep_setup):
    """
    Tests weekly worker 7-day proration basis, hourly equivalent rate ((weekly / 7) / std_hours),
    and overtime accumulation over multiple days.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # Weekly worker rate is 3500.00. (3500 / 7) = 500.00 daily equivalent.
        # Hourly equivalent = 500 / 7 = 71.43.
        # 3 approved days:
        # Day 1 (Oct 1): 7.00h (no OT)
        # Day 2 (Oct 2): 8.50h (1.50h OT) -> 1.50 * (500 / 7) * 1.50 = 160.71 (unrounded exact rate)
        # Day 3 (Oct 3): 9.00h (2.00h OT) -> 2.00 * (500 / 7) * 1.50 = 214.29
        att1 = AttendanceRecord(
            id=_u(), employee_id=emps["weekly"].id, site_id=site.id, date=date(2026, 10, 1),
            check_in_time=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),
            status="approved",
        )
        att2 = AttendanceRecord(
            id=_u(), employee_id=emps["weekly"].id, site_id=site.id, date=date(2026, 10, 2),
            check_in_time=datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 2, 16, 30, tzinfo=timezone.utc),
            status="approved",
        )
        att3 = AttendanceRecord(
            id=_u(), employee_id=emps["weekly"].id, site_id=site.id, date=date(2026, 10, 3),
            check_in_time=datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 3, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2, att3])
        await session.commit()

    idemp = f"IDEMP-OT-WEEKLY-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "employee_id": str(emps["weekly"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]

    # 3 days pro-rated on 7-day basis: (3 / 7) * 3500 = 1500.00
    assert Decimal(str(pay_data["total_days"])) == Decimal("3.00")
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("1500.00")
    # Total OT hours = 1.50 + 2.00 = 3.50
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("3.50")
    # Total OT amount = 160.71 + 214.29 = 375.00 (final-only rounding avoiding intermediate round error)
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("375.00")
    # Grand total = 1500.00 + 375.00 = 1875.00
    assert Decimal(str(pay_data["total_amount"])) == Decimal("1875.00")

    # Detail check
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 3

    assert Decimal(str(lines[0]["overtime_hours"])) == Decimal("0.00")
    assert Decimal(str(lines[0]["overtime_amount"])) == Decimal("0.00")

    # Line 2: 1.50 * (500 / 7) * 1.50 = 160.71 (unrounded rate basis)
    assert Decimal(str(lines[1]["overtime_hours"])) == Decimal("1.50")
    assert Decimal(str(lines[1]["hourly_equivalent_rate"])) == Decimal("71.43")
    assert Decimal(str(lines[1]["overtime_amount"])) == Decimal("160.71")

    # Line 3: 2.00 * (500 / 7) * 1.50 = 214.29
    assert Decimal(str(lines[2]["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(lines[2]["hourly_equivalent_rate"])) == Decimal("71.43")
    assert Decimal(str(lines[2]["overtime_amount"])) == Decimal("214.29")


@pytest.mark.asyncio
async def test_overtime_multiple_sessions_same_date_waterfall(client: TestClient, ep_setup):
    """
    Tests multiple sessions on the same date:
    - Daily rate regular pay paid ONCE on primary session (idx 0)
    - Subsequent session has days=0.00 and regular_amount=0.00
    - Chronological waterfall allocates regular hours up to standard threshold, then overtime hours
    - Distinct lines created per attendance record to satisfy database source constraints
    - Header totals reconcile exactly
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 2 sessions on Oct 5:
        # Session 1: 08:00 to 12:00 (4.00 hours)
        # Session 2: 13:00 to 18:00 (5.00 hours)
        # Total date hours = 9.00 hours. Std = 7.00h -> 2.00h OT
        d = date(2026, 10, 5)
        att1 = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=d, session_number=1,
            check_in_time=datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
            status="approved",
        )
        att2 = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=d, session_number=2,
            check_in_time=datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2])
        await session.commit()

    idemp = f"IDEMP-OT-MULTISESS-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-05",
            "period_end": "2026-10-05",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]

    # Header totals: exactly 1 day counted, regular pay paid once
    assert Decimal(str(pay_data["total_days"])) == Decimal("1.00")
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(pay_data["total_amount"])) == Decimal("714.29")

    # Itemized detail lines
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 2

    # Session 1: 4.00h regular, 0.00h OT, base day and pay allocated
    l1 = lines[0]
    assert l1["source_attendance_id"] == str(att1.id)
    assert Decimal(str(l1["days"])) == Decimal("1.00")
    assert Decimal(str(l1["regular_hours"])) == Decimal("4.00")
    assert Decimal(str(l1["overtime_hours"])) == Decimal("0.00")
    assert Decimal(str(l1["regular_amount"])) == Decimal("500.00")
    assert Decimal(str(l1["overtime_amount"])) == Decimal("0.00")
    assert Decimal(str(l1["amount"])) == Decimal("500.00")

    # Session 2: 3.00h regular (up to 7h std), 2.00h OT, 0 days, 0 regular pay
    l2 = lines[1]
    assert l2["source_attendance_id"] == str(att2.id)
    assert Decimal(str(l2["days"])) == Decimal("0.00")
    assert Decimal(str(l2["regular_hours"])) == Decimal("3.00")
    assert Decimal(str(l2["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(l2["regular_amount"])) == Decimal("0.00")
    assert Decimal(str(l2["overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(l2["amount"])) == Decimal("214.29")


@pytest.mark.asyncio
async def test_overtime_minute_rounding_round_half_up(client: TestClient, ep_setup):
    """
    Tests minute rounding with ROUND_HALF_UP:
    - 7 hours 0 min 30 sec -> rounds up to 7 hours 1 min (1 min OT = 0.02h)
    - 7 hours 0 min 29 sec -> rounds down to 7 hours 0 min (0 min OT = 0.00h)
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # Session 1: 08:00:00 to 15:00:30 (7h 0m 30s) -> 420.5 mins -> rounds UP to 421 mins -> 1 min OT (0.02h)
        att1 = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 6),
            check_in_time=datetime(2026, 10, 6, 8, 0, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 6, 15, 0, 30, tzinfo=timezone.utc),
            status="approved",
        )
        # Session 2: 08:00:00 to 15:00:29 (7h 0m 29s) -> 420.48 mins -> rounds DOWN to 420 mins -> 0 min OT (0.00h)
        att2 = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 7),
            check_in_time=datetime(2026, 10, 7, 8, 0, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 7, 15, 0, 29, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2])
        await session.commit()

    idemp = f"IDEMP-OT-ROUNDING-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-06",
            "period_end": "2026-10-07",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 2

    # Line 1: rounded up to 421 mins -> 0.02 OT hours
    assert Decimal(str(lines[0]["overtime_hours"])) == Decimal("0.02")
    assert Decimal(str(lines[0]["overtime_amount"])) > Decimal("0.00")

    # Line 2: rounded down to 420 mins -> 0.00 OT hours
    assert Decimal(str(lines[1]["overtime_hours"])) == Decimal("0.00")
    assert Decimal(str(lines[1]["overtime_amount"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_overtime_effective_date_boundaries(client: TestClient, ep_setup):
    """
    Tests that attendance records resolve overtime settings effective on their specific attendance date:
    - Setting 1 (Oct 1 - Oct 15): 7.00h, 1.50x
    - Setting 2 (Oct 16 - None): 8.00h, 2.00x
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        # Create a worker with 600 daily rate
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9197{sfx[:6]}1", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(id=_u(), user_id=u.id, employee_code=f"EMP-B-{sfx}", mobile_id=u.mobile_id, name="Boundary Worker")
        session.add(emp)
        await session.flush()

        rate = EmployeeRateHistory(
            id=_u(), employee_id=emp.id, rate_type="daily", rate_amount=Decimal("600.00"),
            effective_from=date(2026, 10, 1), effective_to=None, changed_by=emp.id,
        )
        session.add(rate)

        # 2 distinct overtime settings across boundary
        s1 = PayrollOvertimeSettings(
            id=_u(), standard_workday_hours=Decimal("7.00"), overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 15), description="Setting 1 (7h 1.5x)"
        )
        s2 = PayrollOvertimeSettings(
            id=_u(), standard_workday_hours=Decimal("8.00"), overtime_multiplier=Decimal("2.00"),
            effective_from=date(2026, 10, 16), effective_to=None, description="Setting 2 (8h 2.0x)"
        )
        session.add_all([s1, s2])

        # Date 1 (Oct 10): 9 hours worked -> Setting 1 applies: 2h OT @ (600/7 = 85.71) * 1.5x = 257.13
        att1 = AttendanceRecord(
            id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 10),
            check_in_time=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 10, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Date 2 (Oct 18): 9 hours worked -> Setting 2 applies: 1h OT @ (600/8 = 75.00) * 2.0x = 150.00
        att2 = AttendanceRecord(
            id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 18),
            check_in_time=datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2])
        await session.commit()

    idemp = f"IDEMP-OT-BOUND-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-10",
            "period_end": "2026-10-20",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 2

    # Oct 10: Setting 1 snapshot
    l1 = lines[0]
    assert l1["source_date"] == "2026-10-10"
    assert Decimal(str(l1["standard_day_hours"])) == Decimal("7.00")
    assert Decimal(str(l1["overtime_multiplier"])) == Decimal("1.50")
    assert Decimal(str(l1["hourly_equivalent_rate"])) == Decimal("85.71")
    assert Decimal(str(l1["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(l1["overtime_amount"])) == Decimal("257.14")

    # Oct 18: Setting 2 snapshot
    l2 = lines[1]
    assert l2["source_date"] == "2026-10-18"
    assert Decimal(str(l2["standard_day_hours"])) == Decimal("8.00")
    assert Decimal(str(l2["overtime_multiplier"])) == Decimal("2.00")
    assert Decimal(str(l2["hourly_equivalent_rate"])) == Decimal("75.00")
    assert Decimal(str(l2["overtime_hours"])) == Decimal("1.00")
    assert Decimal(str(l2["overtime_amount"])) == Decimal("150.00")


@pytest.mark.asyncio
async def test_overtime_missing_setting_no_retroactive_application(client: TestClient, ep_setup):
    """
    Tests requirement 13:
    If no overtime configuration applies to a date, do not apply a future setting retroactively;
    preserve regular-pay eligibility and calculate zero overtime.
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9197{sfx[:6]}2", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(id=_u(), user_id=u.id, employee_code=f"EMP-RETRO-{sfx}", mobile_id=u.mobile_id, name="Retro Worker")
        session.add(emp)
        await session.flush()

        rate = EmployeeRateHistory(
            id=_u(), employee_id=emp.id, rate_type="daily", rate_amount=Decimal("500.00"),
            effective_from=date(2026, 10, 1), effective_to=None, changed_by=emp.id,
        )
        session.add(rate)

        # Clear previous settings so no overtime setting exists for dates prior to 2026-10-25
        await session.execute(delete(PayrollOvertimeSettings))

        # Overtime setting is effective ONLY from 2026-10-25 onwards!
        ot_future = PayrollOvertimeSettings(
            id=_u(), standard_workday_hours=Decimal("7.00"), overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 10, 25), effective_to=None, description="Future setting only"
        )
        session.add(ot_future)

        # Attendance on 2026-10-05 with 9 hours worked (prior to any overtime setting)
        att_early = AttendanceRecord(
            id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 5),
            check_in_time=datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 5, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Attendance on 2026-10-26 with 9 hours worked (after setting effective)
        att_late = AttendanceRecord(
            id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 26),
            check_in_time=datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 26, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att_early, att_late])
        await session.commit()

    idemp = f"IDEMP-OT-MISSING-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-30",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 2

    # Date prior to overtime settings (Oct 5):
    # Future setting NOT applied retroactively! Zero overtime, regular pay preserved!
    l_early = lines[0]
    assert l_early["source_date"] == "2026-10-05"
    assert Decimal(str(l_early["days"])) == Decimal("1.00")
    assert Decimal(str(l_early["regular_amount"])) == Decimal("500.00")
    assert Decimal(str(l_early["overtime_hours"])) == Decimal("0.00")
    assert Decimal(str(l_early["overtime_amount"])) == Decimal("0.00")
    assert l_early["standard_day_hours"] is None
    assert l_early["hourly_equivalent_rate"] is None
    assert l_early["overtime_multiplier"] is None
    assert Decimal(str(l_early["amount"])) == Decimal("500.00")

    # Date with active setting (Oct 26):
    l_late = lines[1]
    assert l_late["source_date"] == "2026-10-26"
    assert Decimal(str(l_late["days"])) == Decimal("1.00")
    assert Decimal(str(l_late["regular_amount"])) == Decimal("500.00")
    assert Decimal(str(l_late["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(l_late["overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(l_late["standard_day_hours"])) == Decimal("7.00")
    assert Decimal(str(l_late["overtime_multiplier"])) == Decimal("1.50")
    assert Decimal(str(l_late["amount"])) == Decimal("714.29")


@pytest.mark.asyncio
async def test_piece_rate_exclusion_no_overtime(client: TestClient, ep_setup):
    """
    Tests requirement 9:
    Piece-rate calculation remains unchanged, with no overtime.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    act = ep_setup["activity"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # Piece worker attendance with 10 hours worked
        att_p = AttendanceRecord(
            id=_u(), employee_id=emps["piece"].id, site_id=site.id, date=date(2026, 10, 8),
            check_in_time=datetime(2026, 10, 8, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att_p)
        await session.flush()

        # Piece worker daily work entry: 50 units @ 20.00 = 1000.00
        dwe_p = DailyWorkEntry(
            id=_u(), idempotency_key=str(_u()), attendance_record_id=att_p.id,
            employee_id=emps["piece"].id, site_id=site.id, activity_id=act.id,
            work_date=date(2026, 10, 8), quantity=50, uom="metres", status="approved",
        )
        session.add(dwe_p)
        await session.commit()

    idemp = f"IDEMP-PIECE-NO-OT-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-08",
            "period_end": "2026-10-08",
            "employee_id": str(emps["piece"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]

    assert Decimal(str(pay_data["total_quantity"])) == Decimal("50.00")
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("1000.00")
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("0.00")
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("0.00")
    assert Decimal(str(pay_data["total_amount"])) == Decimal("1000.00")

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    line = resp_detail.json()["lines"][0]
    assert line["rate_type"] == "piece"
    assert Decimal(str(line["quantity"])) == Decimal("50.00")
    assert line["regular_hours"] is None
    assert Decimal(str(line["overtime_hours"])) == Decimal("0.00")
    assert line["standard_day_hours"] is None
    assert line["hourly_equivalent_rate"] is None
    assert line["overtime_multiplier"] is None
    assert Decimal(str(line["regular_amount"])) == Decimal("1000.00")
    assert Decimal(str(line["overtime_amount"])) == Decimal("0.00")
    assert Decimal(str(line["amount"])) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_overtime_unapproved_attendance_excluded(client: TestClient, ep_setup):
    """
    Tests requirement 1:
    Calculate overtime using approved attendance only.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 1 approved attendance with 9 hours (2h overtime)
        att_appr = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 11),
            check_in_time=datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 11, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # 1 pending attendance with 10 hours (should be excluded)
        att_pend = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 12),
            check_in_time=datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc),
            status="pending_verification",
        )
        session.add_all([att_appr, att_pend])
        await session.commit()

    idemp = f"IDEMP-OT-UNAPPR-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-11",
            "period_end": "2026-10-12",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]

    # Exactly 1 day, 2 hours overtime from the approved record only
    assert Decimal(str(pay_data["total_days"])) == Decimal("1.00")
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(pay_data["total_amount"])) == Decimal("714.29")


@pytest.mark.asyncio
async def test_overtime_idempotency_and_cancellation(client: TestClient, ep_setup):
    """
    Tests requirement 12:
    Preserve source locking, idempotency, cancellation behavior and historical payment snapshots.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        att = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 14),
            check_in_time=datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 14, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    idemp1 = f"IDEMP-OT-IDEMP-1-{str(_u())[:8]}"
    idemp2 = f"IDEMP-OT-IDEMP-2-{str(_u())[:8]}"

    # Step 1: Generate payment 1
    resp1 = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-14", "period_end": "2026-10-14", "employee_id": str(emps["daily"].id), "idempotency_key": idemp1},
        headers=_auth(tokens["director"]),
    )
    assert resp1.status_code == 201
    pay1_id = resp1.json()[0]["id"]
    assert Decimal(str(resp1.json()[0]["total_overtime_amount"])) == Decimal("214.29")

    # Step 2: Idempotent replay with same key
    resp_replay = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-14", "period_end": "2026-10-14", "employee_id": str(emps["daily"].id), "idempotency_key": idemp1},
        headers=_auth(tokens["director"]),
    )
    assert resp_replay.status_code in (200, 201)
    assert resp_replay.json()[0]["id"] == pay1_id

    # Step 3: Cancelling payment 1 deactivates lines and unlocks source record
    resp_cancel = client.post(
        f"/api/v1/employee-payments/{pay1_id}/cancel",
        json={"cancellation_reason": "Correction needed for overtime"},
        headers=_auth(tokens["director"]),
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"
    assert all(l["is_active"] is False for l in resp_cancel.json()["lines"])

    # Step 4: Re-generating with new idempotency key succeeds and relocks record
    resp2 = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-14", "period_end": "2026-10-14", "employee_id": str(emps["daily"].id), "idempotency_key": idemp2},
        headers=_auth(tokens["director"]),
    )
    assert resp2.status_code == 201
    pay2_id = resp2.json()[0]["id"]
    assert pay2_id != pay1_id
    assert Decimal(str(resp2.json()[0]["total_overtime_amount"])) == Decimal("214.29")


@pytest.mark.asyncio
async def test_overtime_historical_payment_snapshot_immutability(client: TestClient, ep_setup):
    """
    Tests historical payment immutability:
    Once payment is generated and paid, subsequent overtime configuration changes or rate history changes
    never alter historical snapshot values on lines or header totals.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        ot_initial = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 10, 15),
            description="Initial 7h 1.5x",
        )
        session.add(ot_initial)

        att = AttendanceRecord(
            id=_u(), employee_id=emps["daily"].id, site_id=site.id, date=date(2026, 10, 10),
            check_in_time=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 10, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-OT-IMMUTABLE-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={"period_start": "2026-10-10", "period_end": "2026-10-10", "employee_id": str(emps["daily"].id), "idempotency_key": idemp},
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    # Approve and Pay
    client.post(f"/api/v1/employee-payments/{pay_id}/approve", headers=_auth(tokens["director"]))
    client.post(
        f"/api/v1/employee-payments/{pay_id}/pay",
        json={"payment_method": "bank_transfer", "reference_number": "IMMUTABLE_REF"},
        headers=_auth(tokens["director"]),
    )

    # Now add a NEW overtime setting and employee rate history with different values
    async with TestingSessionLocal() as session:
        ot_new = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("8.00"),
            overtime_multiplier=Decimal("2.50"),
            effective_from=date(2026, 10, 16),
            effective_to=None,
            description="Updated 8h 2.5x",
        )
        rate_new = EmployeeRateHistory(
            id=_u(),
            employee_id=emps["daily"].id,
            rate_type="daily",
            rate_amount=Decimal("800.00"),
            effective_from=date(2026, 10, 16),
            effective_to=None,
            changed_by=emps["daily"].id,
        )
        session.add_all([ot_new, rate_new])
        await session.commit()

    # Query historical payment detail: MUST maintain exact snapshotted values
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    hist = resp_detail.json()
    assert Decimal(str(hist["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(hist["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(hist["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(hist["total_amount"])) == Decimal("714.29")

    line = hist["lines"][0]
    assert Decimal(str(line["rate_amount"])) == Decimal("500.00")
    assert Decimal(str(line["standard_day_hours"])) == Decimal("7.00")
    assert Decimal(str(line["overtime_multiplier"])) == Decimal("1.50")
    assert Decimal(str(line["hourly_equivalent_rate"])) == Decimal("71.43")
    assert Decimal(str(line["regular_amount"])) == Decimal("500.00")
    assert Decimal(str(line["overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(line["amount"])) == Decimal("714.29")


@pytest.mark.asyncio
async def test_overtime_monetary_precision_avoids_intermediate_rounding_daily(client: TestClient, ep_setup):
    """
    Demonstrates that daily overtime avoids premature intermediate rounding:
    - Daily rate = 500.00, standard workday = 7.00 hours, multiplier = 1.50.
    - Overtime hours = 1.50.
    - Premature intermediate rounding:
        hourly_rate = round(500 / 7, 2) = 71.43
        overtime_amount = round(1.50 * 71.43 * 1.50, 2) = round(160.7175, 2) = 160.72
    - Approved final-only rounding:
        exact_hourly_rate = 500 / 7 = 71.42857142857142857142857143...
        overtime_amount = round(1.50 * (500 / 7) * 1.50, 2) = round(160.7142857..., 2) = 160.71
    - Stored snapshot hourly_equivalent_rate = 71.43 (for 2-decimal display/audit)
    - Stored overtime_amount = 160.71 (exact calculation quantized at the end)
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        await session.execute(delete(PayrollOvertimeSettings))
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 8 hours 30 mins worked -> 1.50 hours overtime
        att = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 18),
            check_in_time=datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 18, 16, 30, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-PRECISION-DAILY-{str(_u())[:8]}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-18",
            "period_end": "2026-10-18",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    line = resp_detail.json()["lines"][0]

    # Stored display snapshot is 71.43
    assert Decimal(str(line["hourly_equivalent_rate"])) == Decimal("71.43")
    assert Decimal(str(line["overtime_hours"])) == Decimal("1.50")

    # Final-only rounding produces 160.71, NOT intermediate-rounded 160.72!
    assert Decimal(str(line["overtime_amount"])) == Decimal("160.71")
    assert Decimal(str(line["overtime_amount"])) != Decimal("160.72")
    assert Decimal(str(line["amount"])) == Decimal("660.71")


@pytest.mark.asyncio
async def test_overtime_monetary_precision_avoids_intermediate_rounding_weekly(client: TestClient, ep_setup):
    """
    Demonstrates that weekly overtime avoids premature intermediate rounding:
    - Weekly rate = 3000.00, standard workday = 7.00 hours, multiplier = 1.50.
    - Daily equivalent = 3000 / 7 = 428.57142857...
    - Overtime hours = 2.00.
    - Premature intermediate rounding:
        hourly_rate = round((3000 / 7) / 7, 2) = round(61.224489..., 2) = 61.22
        overtime_amount = round(2.00 * 61.22 * 1.50, 2) = 183.66
    - Approved final-only rounding:
        exact_hourly_rate = 3000 / 49 = 61.2244897959...
        overtime_amount = round(2.00 * (3000 / 49) * 1.50, 2) = round(183.673469..., 2) = 183.67
    - Stored snapshot hourly_equivalent_rate = 61.22 (for 2-decimal display/audit)
    - Stored overtime_amount = 183.67 (exact calculation quantized at the end)
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9197{sfx[:6]}3", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(id=_u(), user_id=u.id, employee_code=f"EMP-PREC-W-{sfx}", mobile_id=u.mobile_id, name="Weekly Prec Worker")
        session.add(emp)
        await session.flush()

        rate = EmployeeRateHistory(
            id=_u(), employee_id=emp.id, rate_type="weekly", rate_amount=Decimal("3000.00"),
            effective_from=date(2026, 10, 1), effective_to=None, changed_by=emp.id,
        )
        session.add(rate)

        await session.execute(delete(PayrollOvertimeSettings))
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 9 hours worked on Oct 19 (7h std, 2h overtime)
        att = AttendanceRecord(
            id=_u(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 19),
            check_in_time=datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-PRECISION-WEEKLY-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-19",
            "period_end": "2026-10-19",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_id = resp_gen.json()[0]["id"]

    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    line = resp_detail.json()["lines"][0]

    # Stored display snapshot is 61.22
    assert Decimal(str(line["hourly_equivalent_rate"])) == Decimal("61.22")
    assert Decimal(str(line["overtime_hours"])) == Decimal("2.00")

    # Final-only rounding produces 183.67, NOT intermediate-rounded 183.66!
    assert Decimal(str(line["overtime_amount"])) == Decimal("183.67")
    assert Decimal(str(line["overtime_amount"])) != Decimal("183.66")


@pytest.mark.asyncio
async def test_verified_attendance_included_in_preview_and_generation(client: TestClient, ep_setup):
    """
    Regression test proving:
    - 'verified' attendance (the approved state set by VerificationService) is included in payroll preview and generation.
    - 'draft' and 'flagged' attendance records are strictly excluded from both preview and generation.
    - The same verified source attendance cannot be paid twice (source locking and duplicate prevention).
    - Preview and generation produce identical calculated totals.
    """
    tokens = ep_setup["tokens"]
    emps = ep_setup["employees"]
    site = ep_setup["site"]
    sfx = str(_u())[:8]

    async with TestingSessionLocal() as session:
        ot_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description="Standard 7h 1.5x",
        )
        session.add(ot_setting)

        # 1. Verified attendance with 9 hours (7h regular, 2h overtime)
        att_verified = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 21),
            check_in_time=datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 21, 17, 0, tzinfo=timezone.utc),
            status="verified",
        )
        # 2. Draft attendance (must be excluded)
        att_draft = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 22),
            check_in_time=datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 22, 17, 0, tzinfo=timezone.utc),
            status="draft",
        )
        # 3. Flagged attendance (must be excluded)
        att_flagged = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 23),
            check_in_time=datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 23, 17, 0, tzinfo=timezone.utc),
            status="flagged",
        )
        # 4. Rejected attendance (must be excluded)
        att_rejected = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 23),
            check_in_time=datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 23, 17, 0, tzinfo=timezone.utc),
            status="rejected",
        )
        # 5. Correction required / unverified attendance (must be excluded)
        att_unverified = AttendanceRecord(
            id=_u(),
            employee_id=emps["daily"].id,
            site_id=site.id,
            date=date(2026, 10, 23),
            check_in_time=datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 23, 17, 0, tzinfo=timezone.utc),
            status="correction_required",
        )
        session.add_all([att_verified, att_draft, att_flagged, att_rejected, att_unverified])
        await session.commit()

    # Step A: Payroll Preview includes verified attendance and excludes draft, flagged, rejected, and unverified
    resp_prev = client.get(
        "/api/v1/employee-payments/preview",
        params={
            "period_start": "2026-10-21",
            "period_end": "2026-10-23",
            "employee_id": str(emps["daily"].id),
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    assert prev_data["total_employees"] == 1
    item = prev_data["items"][0]
    # Only 1 attendance record eligible: verified is included; draft and flagged are excluded
    assert item["eligible_attendance_count"] == 1
    assert Decimal(str(item["total_days"])) == Decimal("1.00")
    assert Decimal(str(item["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(item["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(item["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(item["total_amount"])) == Decimal("714.29")

    # Step B: Payroll Generation creates payment for the verified record matching preview
    idemp1 = f"IDEMP-VERIFIED-GEN1-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-21",
            "period_end": "2026-10-23",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp1,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    gen_data = resp_gen.json()[0]
    pay_id = gen_data["id"]

    assert Decimal(str(gen_data["total_days"])) == Decimal("1.00")
    assert Decimal(str(gen_data["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(gen_data["total_regular_amount"])) == Decimal("500.00")
    assert Decimal(str(gen_data["total_overtime_amount"])) == Decimal("214.29")
    assert Decimal(str(gen_data["total_amount"])) == Decimal("714.29")

    # Payment line itemized source points directly to the verified attendance record
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    lines = resp_detail.json()["lines"]
    assert len(lines) == 1
    assert lines[0]["source_attendance_id"] == str(att_verified.id)
    assert lines[0]["source_date"] == "2026-10-21"

    # Step C: Prove source attendance cannot be paid twice
    # 1. Preview shows 0 eligible records now that it is locked
    resp_prev_locked = client.get(
        "/api/v1/employee-payments/preview",
        params={
            "period_start": "2026-10-21",
            "period_end": "2026-10-23",
            "employee_id": str(emps["daily"].id),
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_prev_locked.status_code == 200
    assert resp_prev_locked.json()["total_employees"] == 0

    # 2. Subsequent generate with fresh idempotency key finds no eligible attendance
    idemp2 = f"IDEMP-VERIFIED-GEN2-{sfx}"
    resp_gen_locked = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-21",
            "period_end": "2026-10-23",
            "employee_id": str(emps["daily"].id),
            "idempotency_key": idemp2,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen_locked.status_code == 400
    assert "No eligible approved attendance" in resp_gen_locked.json()["detail"]


@pytest.mark.asyncio
async def test_monthly_payment_calculation_and_overtime(client: TestClient, ep_setup):
    """
    Tests:
    1. Monthly rate payment calculation: 30-day basis pro-rated per day.
    2. Standard working time is 8 hours per day.
    3. Overtime is paid at 1x the normal hourly-equivalent rate, with no additional multiplier.
    4. Detail line snapshots: rate_type="monthly", standard_day_hours=8.00, overtime_multiplier=1.00.
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(
            id=_u(),
            user_id=u.id,
            employee_code=f"EMP-MTH-{sfx}",
            mobile_id=u.mobile_id,
            name="Monthly Worker",
            classification="regular",
        )
        session.add(emp)
        await session.flush()

        rate = EmployeeRateHistory(
            id=_u(),
            employee_id=emp.id,
            rate_type="monthly",
            rate_amount=Decimal("30000.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp.id,
        )
        session.add(rate)

        # Day 1: 8 hours worked (08:00 to 16:00) -> 8.00 regular, 0.00 OT
        att1 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 10),
            check_in_time=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Day 2: 10 hours worked (08:00 to 18:00) -> 8.00 regular, 2.00 OT
        att2 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 11),
            check_in_time=datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Day 3: 8 hours worked (08:00 to 16:00) -> 8.00 regular, 0.00 OT
        att3 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 12),
            check_in_time=datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2, att3])
        await session.commit()

    # 1. Preview
    resp_prev = client.get(
        f"/api/v1/employee-payments/preview?period_start=2026-10-01&period_end=2026-10-31&employee_id={emp.id}",
        headers=_auth(tokens["director"]),
    )
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    item = prev_data["items"][0]
    assert Decimal(str(item["total_days"])) == Decimal("3.00")
    # 3 days @ (30000 / 30) = 3000.00 regular pay
    assert Decimal(str(item["total_regular_amount"])) == Decimal("3000.00")
    # 2.00 overtime hours on Day 2
    assert Decimal(str(item["total_overtime_hours"])) == Decimal("2.00")
    # Hourly equivalent rate = (30000 / 30) / 8 = 125.00
    # Overtime rate = 125.00 * 1.0 (no multiplier) = 125.00
    # Overtime amount = 2 * 125.00 = 250.00
    assert Decimal(str(item["total_overtime_amount"])) == Decimal("250.00")
    assert Decimal(str(item["total_amount"])) == Decimal("3250.00")

    # 2. Generate
    idemp = f"IDEMP-MTH-OT-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_data = resp_gen.json()[0]
    pay_id = pay_data["id"]
    assert Decimal(str(pay_data["total_regular_amount"])) == Decimal("3000.00")
    assert Decimal(str(pay_data["total_overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(pay_data["total_overtime_amount"])) == Decimal("250.00")
    assert Decimal(str(pay_data["total_amount"])) == Decimal("3250.00")

    # 3. Itemized lines
    resp_detail = client.get(f"/api/v1/employee-payments/{pay_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert len(detail["lines"]) == 3

    # Check Day 2 line (with OT)
    l2 = next(l for l in detail["lines"] if l["source_date"] == "2026-10-11")
    assert l2["rate_type"] == "monthly"
    assert Decimal(str(l2["rate_amount"])) == Decimal("30000.00")
    assert Decimal(str(l2["regular_hours"])) == Decimal("8.00")
    assert Decimal(str(l2["overtime_hours"])) == Decimal("2.00")
    assert Decimal(str(l2["standard_day_hours"])) == Decimal("8.00")
    assert Decimal(str(l2["hourly_equivalent_rate"])) == Decimal("125.00")
    assert Decimal(str(l2["overtime_multiplier"])) == Decimal("1.00")
    assert Decimal(str(l2["regular_amount"])) == Decimal("1000.00")
    assert Decimal(str(l2["overtime_amount"])) == Decimal("250.00")
    assert Decimal(str(l2["amount"])) == Decimal("1250.00")


@pytest.mark.asyncio
async def test_contract_employee_monthly_payment_workflow(client: TestClient, ep_setup):
    """
    Tests:
    1. Contract employee classification works with existing attendance and payment workflow.
    2. Retains existing monthly payment structure.
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(
            id=_u(),
            user_id=u.id,
            employee_code=f"EMP-CNT-PAY-{sfx}",
            mobile_id=u.mobile_id,
            name="Contract Specialist",
            classification="contract",
        )
        session.add(emp)
        await session.flush()

        # Link site assignment
        asgn = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            is_active=True,
        )
        session.add(asgn)

        rate = EmployeeRateHistory(
            id=_u(),
            employee_id=emp.id,
            rate_type="monthly",
            rate_amount=Decimal("45000.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp.id,
        )
        session.add(rate)

        # Attendance record on site
        att = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 15),
            check_in_time=datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add(att)
        await session.commit()

    idemp = f"IDEMP-CONTRACT-{sfx}"
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay = resp_gen.json()[0]
    assert Decimal(str(pay["total_days"])) == Decimal("1.00")
    # 45000 / 30 = 1500.00
    assert Decimal(str(pay["total_regular_amount"])) == Decimal("1500.00")
    assert Decimal(str(pay["total_amount"])) == Decimal("1500.00")


async def test_client_confirmed_salary_policy(client: TestClient, ep_setup):
    """
    Validates all rules of the client's confirmed salary policy:
    1. Monthly salary is paid on the 1st of every month (defaults to 1st of month following period_end).
    2. Regular salary calculated proportionally: (Monthly Salary / 30) * Actual Days Worked.
    3. Standard working hours: 8 hours per day.
    4. Overtime beyond 8 hours is paid at 1x the normal hourly rate: ((Monthly Salary / 30) / 8) * 1.0.
    5. Preserves calculation snapshots.
    """
    tokens = ep_setup["tokens"]
    site = ep_setup["site"]

    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        u = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="employee")
        session.add(u)
        await session.flush()

        emp = Employee(
            id=_u(),
            user_id=u.id,
            employee_code=f"EMP-POLICY-{sfx}",
            mobile_id=u.mobile_id,
            name="Policy Verified Employee",
            classification="regular",
        )
        session.add(emp)
        await session.flush()

        asgn = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            is_active=True,
        )
        session.add(asgn)

        # Monthly salary = 60,000.00
        # Daily equivalent = 60,000 / 30 = 2,000.00
        # Hourly equivalent = 2,000 / 8 = 250.00
        rate = EmployeeRateHistory(
            id=_u(),
            employee_id=emp.id,
            rate_type="monthly",
            rate_amount=Decimal("60000.00"),
            effective_from=date(2026, 10, 1),
            effective_to=None,
            changed_by=emp.id,
        )
        session.add(rate)

        # Day 1 (Oct 5): 8.00 hours -> 8h reg, 0h OT -> regular: 2,000.00, ot: 0.00
        att1 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 5),
            check_in_time=datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Day 2 (Oct 6): 10.00 hours -> 8h reg, 2h OT -> regular: 2,000.00, ot: 2h * 250 * 1.0 = 500.00
        att2 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 6),
            check_in_time=datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc),
            status="approved",
        )
        # Day 3 (Oct 7): 11.00 hours -> 8h reg, 3h OT -> regular: 2,000.00, ot: 3h * 250 * 1.0 = 750.00
        att3 = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 7),
            check_in_time=datetime(2026, 10, 7, 8, 0, tzinfo=timezone.utc),
            check_out_time=datetime(2026, 10, 7, 19, 0, tzinfo=timezone.utc),
            status="approved",
        )
        session.add_all([att1, att2, att3])
        await session.commit()

    idemp = f"IDEMP-POL-{sfx}"
    # Generate payment for October (period: 2026-10-01 to 2026-10-31)
    resp_gen = client.post(
        "/api/v1/employee-payments/generate",
        json={
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "employee_id": str(emp.id),
            "idempotency_key": idemp,
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_gen.status_code == 201
    pay_list = resp_gen.json()
    assert len(pay_list) == 1
    pay = pay_list[0]

    # Verify actual days worked = 3 days
    assert Decimal(str(pay["total_days"])) == Decimal("3.00")
    # Regular salary: (60,000 / 30) * 3 = 6,000.00
    assert Decimal(str(pay["total_regular_amount"])) == Decimal("6000.00")
    # Total OT hours = 2 + 3 = 5 hours
    assert Decimal(str(pay["total_overtime_hours"])) == Decimal("5.00")
    # Overtime: 5h * 250.00 * 1.0 = 1,250.00
    assert Decimal(str(pay["total_overtime_amount"])) == Decimal("1250.00")
    # Total Amount = 6,000.00 + 1,250.00 = 7,250.00
    assert Decimal(str(pay["total_amount"])) == Decimal("7250.00")

    # Fetch detail to verify line calculation snapshots
    pay_id = pay["id"]
    resp_detail = client.get(
        f"/api/v1/employee-payments/{pay_id}",
        headers=_auth(tokens["director"]),
    )
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    lines = detail["lines"]
    assert len(lines) == 3

    # Check snapshots on each line
    for line in lines:
        assert line["rate_type"] == "monthly"
        assert Decimal(str(line["rate_amount"])) == Decimal("60000.00")
        assert Decimal(str(line["standard_day_hours"])) == Decimal("8.00")
        assert Decimal(str(line["hourly_equivalent_rate"])) == Decimal("250.00")
        assert Decimal(str(line["overtime_multiplier"])) == Decimal("1.00")

    # Approve payment
    resp_app = client.post(
        f"/api/v1/employee-payments/{pay_id}/approve",
        headers=_auth(tokens["director"]),
    )
    assert resp_app.status_code == 200

    # Mark as paid without explicit payment_date -> defaults to 1st of month following period (2026-11-01)
    resp_pay = client.post(
        f"/api/v1/employee-payments/{pay_id}/pay",
        json={
            "payment_method": "bank_transfer",
            "reference_number": "UTR-SALARY-001",
        },
        headers=_auth(tokens["director"]),
    )
    assert resp_pay.status_code == 200
    paid_data = resp_pay.json()
    assert paid_data["status"] == "paid"
    assert paid_data["payment_date"] == "2026-11-01"







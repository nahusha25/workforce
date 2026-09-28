import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Project,
    Site,
    WorkOrder,
)
from app.models.workforce import Employee
from app.modules.daily_work.schemas import DailyWorkEntryCreate, DailyWorkEntryUpdate
from app.modules.daily_work.service import DailyWorkService
from tests.conftest import TestingSessionLocal


async def create_fixture_data(session: AsyncSession):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # 1. Users
    user_emp1 = User(id=uuid.uuid4(), mobile_id=f"M-EMP1-{suffix}", role="employee", is_active=True)
    user_emp2 = User(id=uuid.uuid4(), mobile_id=f"M-EMP2-{suffix}", role="employee", is_active=True)
    user_sup1 = User(id=uuid.uuid4(), mobile_id=f"M-SUP1-{suffix}", role="supervisor", is_active=True)
    user_sup2 = User(id=uuid.uuid4(), mobile_id=f"M-SUP2-{suffix}", role="supervisor", is_active=True)
    session.add_all([user_emp1, user_emp2, user_sup1, user_sup2])
    await session.commit()

    # 2. Employees:
    # supervisor 1
    sup1 = Employee(
        id=uuid.uuid4(),
        user_id=user_sup1.id,
        name=f"Supervisor One {suffix}",
        employee_code=f"SUP1-{suffix}",
        mobile_id=f"M-SUP1-{suffix}",
        is_active=True,
    )
    # supervisor 2
    sup2 = Employee(
        id=uuid.uuid4(),
        user_id=user_sup2.id,
        name=f"Supervisor Two {suffix}",
        employee_code=f"SUP2-{suffix}",
        mobile_id=f"M-SUP2-{suffix}",
        is_active=True,
    )
    session.add_all([sup1, sup2])
    await session.commit()

    # employee 1 (reports to sup1)
    emp1 = Employee(
        id=uuid.uuid4(),
        user_id=user_emp1.id,
        name=f"Employee One {suffix}",
        employee_code=f"EMP1-{suffix}",
        mobile_id=f"M-EMP1-{suffix}",
        supervisor_id=sup1.id,
        is_active=True,
    )
    # employee 2 (reports to sup2)
    emp2 = Employee(
        id=uuid.uuid4(),
        user_id=user_emp2.id,
        name=f"Employee Two {suffix}",
        employee_code=f"EMP2-{suffix}",
        mobile_id=f"M-EMP2-{suffix}",
        supervisor_id=sup2.id,
        is_active=True,
    )
    session.add_all([emp1, emp2])
    await session.commit()

    # 3. Client, Project, Sites
    client = Client(name=f"Client {suffix}", is_active=True)
    session.add(client)
    await session.commit()

    project = Project(client_id=client.id, name=f"Project {suffix}", status="active")
    session.add(project)
    await session.commit()

    # site 1: supervised by sup1
    site1 = Site(
        name=f"Site One {suffix}",
        project_id=project.id,
        supervisor_id=sup1.id,
        location="POINT(77.5946 12.9716)",
        permitted_radius_m=500.0,
    )
    # site 2: supervised by sup2
    site2 = Site(
        name=f"Site Two {suffix}",
        project_id=project.id,
        supervisor_id=sup2.id,
        location="POINT(77.6000 12.9800)",
        permitted_radius_m=500.0,
    )
    session.add_all([site1, site2])
    await session.commit()

    # Employee-Site Assignments
    assign1 = EmployeeSiteAssignment(employee_id=emp1.id, site_id=site1.id, is_active=True)
    assign2 = EmployeeSiteAssignment(employee_id=emp2.id, site_id=site2.id, is_active=True)
    session.add_all([assign1, assign2])
    await session.commit()

    # 4. Activity
    activity = Activity(
        name=f"Cable Pulling {suffix}",
        unit_of_measure="metre",
        approved_rate=12.50,
        category="cable",
        is_active=True,
    )
    session.add(activity)
    await session.commit()

    # 5. Work Order
    work_order = WorkOrder(
        order_number=f"WO-{suffix}",
        project_id=project.id,
        site_id=site1.id,
        status="open",
        is_active=True,
    )
    session.add(work_order)
    await session.commit()

    # 6. Active attendance record for emp1 today (check_out_time IS NULL)
    att_active = AttendanceRecord(
        employee_id=emp1.id,
        site_id=site1.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        check_out_time=None,
        status="draft",
        is_within_geofence=True,
    )
    session.add(att_active)
    await session.commit()

    return {
        "emp1": emp1,
        "emp2": emp2,
        "sup1": sup1,
        "sup2": sup2,
        "site1": site1,
        "site2": site2,
        "activity": activity,
        "work_order": work_order,
        "att_active": att_active,
        "today": today,
    }


def make_payload(activity_id, quantity=1.0, **kwargs):
    payload = {
        "idempotency_key": f"IDEMP-{uuid.uuid4()}",
        "activity_id": activity_id,
        "quantity": quantity,
    }
    payload.update(kwargs)
    return payload


# ==============================================================================
# 1. CREATE WORK ENTRY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_work_entry_success():
    """Valid active attendance today links attendance_record_id, auto-derives uom, and sets draft status."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]
        work_order = data["work_order"]
        att_active = data["att_active"]
        idemp_key = f"IDEMP-{uuid.uuid4()}"

        create_data = DailyWorkEntryCreate(
            idempotency_key=idemp_key,
            activity_id=activity.id,
            work_order_id=work_order.id,
            quantity=Decimal("45.5"),
            remarks="Initial run",
        )

        entry = await DailyWorkService.create_work_entry(session, emp1.id, create_data)

        assert entry.id is not None
        assert entry.idempotency_key == idemp_key
        assert entry.attendance_record_id == att_active.id
        assert entry.employee_id == emp1.id
        assert entry.site_id == att_active.site_id
        assert entry.activity_id == activity.id
        assert entry.work_order_id == work_order.id
        assert entry.work_date == data["today"]
        assert entry.date == data["today"]
        assert entry.status == "draft"
        assert float(entry.quantity) == 45.5
        assert entry.uom == activity.unit_of_measure
        assert entry.remarks == "Initial run"


@pytest.mark.asyncio
async def test_create_work_entry_duplicate_idempotency_key_rejected():
    """Rejects duplicate idempotency_key with 409 Conflict."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]
        dup_key = f"IDEMP-DUP-{uuid.uuid4()}"

        create_data1 = DailyWorkEntryCreate(
            idempotency_key=dup_key,
            activity_id=activity.id,
            quantity=Decimal("5.0"),
        )
        await DailyWorkService.create_work_entry(session, emp1.id, create_data1)

        create_data2 = DailyWorkEntryCreate(
            idempotency_key=dup_key,
            activity_id=activity.id,
            quantity=Decimal("10.0"),
        )
        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.create_work_entry(session, emp1.id, create_data2)
        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_work_entry_rejects_without_attendance():
    """Rejects if employee has no attendance records for today."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp2 = data["emp2"]  # emp2 has no attendance today
        activity = data["activity"]

        create_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=activity.id,
            quantity=Decimal("2.0"),
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.create_work_entry(session, emp2.id, create_data)
        assert exc_info.value.status_code == 400
        assert "active check-in" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_work_entry_rejects_when_checked_out():
    """Rejects if employee had checked in today but already checked out."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        att_active = data["att_active"]
        activity = data["activity"]

        # Simulate checkout
        att_active.check_out_time = datetime.now(timezone.utc)
        await session.commit()

        create_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=activity.id,
            quantity=Decimal("1.0"),
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.create_work_entry(session, emp1.id, create_data)
        assert exc_info.value.status_code == 400
        assert "active check-in" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_work_entry_allows_unclosed_yesterday_attendance():
    """An unclosed attendance record from yesterday (check_out_time is None) allows creating an entry today."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp2 = data["emp2"]
        site2 = data["site2"]
        activity = data["activity"]
        yesterday = data["today"] - timedelta(days=1)

        # Yesterday open session (check_out_time is None)
        att_yesterday = AttendanceRecord(
            employee_id=emp2.id,
            site_id=site2.id,
            date=yesterday,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(days=1),
            check_out_time=None,
            status="draft",
        )
        session.add(att_yesterday)
        await session.commit()

        create_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=activity.id,
            quantity=Decimal("1.0"),
        )

        entry = await DailyWorkService.create_work_entry(session, emp2.id, create_data)
        assert entry is not None
        assert entry.attendance_record_id == att_yesterday.id
        assert entry.site_id == site2.id
        assert entry.employee_id == emp2.id
        assert entry.quantity == Decimal("1.0")


@pytest.mark.asyncio
async def test_create_work_entry_rejects_closed_yesterday_attendance():
    """Rejects if attendance was checked in yesterday and already checked out, leaving no active session."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp2 = data["emp2"]
        site2 = data["site2"]
        activity = data["activity"]
        yesterday = data["today"] - timedelta(days=1)

        # Yesterday closed session
        att_yesterday_closed = AttendanceRecord(
            employee_id=emp2.id,
            site_id=site2.id,
            date=yesterday,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(days=1),
            check_out_time=datetime.now(timezone.utc) - timedelta(days=1, hours=-8),
            status="draft",
        )
        session.add(att_yesterday_closed)
        await session.commit()

        create_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=activity.id,
            quantity=Decimal("1.0"),
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.create_work_entry(session, emp2.id, create_data)
        assert exc_info.value.status_code == 400
        assert "active check-in" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_create_work_entry_invalid_activity_and_work_order():
    """Rejects non-existent activity_id or work_order_id with 404."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        fake_id = uuid.uuid4()

        # Invalid activity
        with pytest.raises(HTTPException) as exc1:
            await DailyWorkService.create_work_entry(
                session, emp1.id, make_payload(fake_id)
            )
        assert exc1.value.status_code == 404

        # Invalid work order
        with pytest.raises(HTTPException) as exc2:
            await DailyWorkService.create_work_entry(
                session,
                emp1.id,
                make_payload(activity.id, work_order_id=fake_id),
            )
        assert exc2.value.status_code == 404


@pytest.mark.asyncio
async def test_create_work_entry_negative_quantities_rejected():
    """Rejects negative quantities with 400."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.create_work_entry(
                session, emp1.id, make_payload(activity.id, quantity=-5.0)
            )
        assert exc_info.value.status_code == 400


# ==============================================================================
# 2. UPDATE WORK ENTRY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_update_work_entry_draft_and_correction_required():
    """Allows updating draft and correction_required entries."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        # 1. Update in draft status
        updated = await DailyWorkService.update_work_entry(
            session,
            entry.id,
            DailyWorkEntryUpdate(quantity=Decimal("150.0"), remarks="Updated draft"),
            employee_id=emp1.id,
        )
        assert float(updated.quantity) == 150.0
        assert updated.remarks == "Updated draft"

        # 2. Manually transition to correction_required
        updated.status = "correction_required"
        await session.commit()

        # Update in correction_required status
        updated2 = await DailyWorkService.update_work_entry(
            session,
            entry.id,
            {"quantity": 7.0},
            employee_id=emp1.id,
        )
        assert float(updated2.quantity) == 7.0


@pytest.mark.asyncio
async def test_update_work_entry_rejects_disallowed_statuses():
    """Rejects updating submitted, approved, or rejected entries."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        for blocked_status in ["submitted", "approved", "rejected"]:
            entry = await DailyWorkService.create_work_entry(
                session, emp1.id, make_payload(activity.id, quantity=1.0)
            )
            entry.status = blocked_status
            await session.commit()

            with pytest.raises(HTTPException) as exc_info:
                await DailyWorkService.update_work_entry(
                    session, entry.id, {"quantity": 20.0}, employee_id=emp1.id
                )
            assert exc_info.value.status_code == 400
            assert blocked_status in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_work_entry_rejects_unauthorized_employee():
    """Employee A cannot update Employee B's work entry."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=1.0)
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.update_work_entry(
                session, entry.id, {"quantity": 20.0}, employee_id=emp2.id
            )
        assert exc_info.value.status_code == 403


# ==============================================================================
# 3. SUBMIT WORK ENTRY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_submit_work_entry_success_from_draft():
    """Transitions draft to submitted when quantity is > 0."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=5.0)
        )
        assert entry.status == "draft"

        submitted = await DailyWorkService.submit_work_entry(
            session, entry.id, employee_id=emp1.id
        )
        assert submitted.status == "submitted"


@pytest.mark.asyncio
async def test_submit_work_entry_success_from_correction_required():
    """Transitions correction_required to submitted."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=20.0)
        )
        entry.status = "correction_required"
        await session.commit()

        submitted = await DailyWorkService.submit_work_entry(
            session, entry.id, employee_id=emp1.id
        )
        assert submitted.status == "submitted"


@pytest.mark.asyncio
async def test_submit_work_entry_rejects_all_zero_quantities():
    """Rejects submit when quantity is 0."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=0.0)
        )
        assert float(entry.quantity) == 0.0

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.submit_work_entry(session, entry.id, employee_id=emp1.id)
        assert exc_info.value.status_code == 400
        assert "greater than zero" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_submit_work_entry_rejects_already_submitted():
    """Rejects submit if status is already submitted, approved, or rejected."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )
        await DailyWorkService.submit_work_entry(session, entry.id, employee_id=emp1.id)

        # Attempt submitting again
        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.submit_work_entry(session, entry.id, employee_id=emp1.id)
        assert exc_info.value.status_code == 400
        assert "submitted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_submit_work_entry_rejects_unauthorized_employee():
    """Employee A cannot submit Employee B's work entry."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=1.0)
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.submit_work_entry(session, entry.id, employee_id=emp2.id)
        assert exc_info.value.status_code == 403


# ==============================================================================
# 4. GET WORK ENTRY TESTS (AUTHORIZATION RULES)
# ==============================================================================

@pytest.mark.asyncio
async def test_get_work_entry_self_access():
    """Employee can get their own work entry."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        retrieved = await DailyWorkService.get_work_entry(
            session, entry.id, user_role="employee", employee_id=emp1.id
        )
        assert retrieved.id == entry.id
        assert retrieved.employee_name == emp1.name
        assert retrieved.activity_name == activity.name
        assert retrieved.uom == activity.unit_of_measure


@pytest.mark.asyncio
async def test_get_work_entry_rejects_other_employee():
    """Employee A cannot view Employee B's entry."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.get_work_entry(
                session, entry.id, user_role="employee", employee_id=emp2.id
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_work_entry_supervisor_direct_report():
    """Supervisor can view work entry of direct report."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        sup1 = data["sup1"]  # emp1 reports to sup1
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        retrieved = await DailyWorkService.get_work_entry(
            session, entry.id, user_role="supervisor", employee_id=sup1.id
        )
        assert retrieved.id == entry.id


@pytest.mark.asyncio
async def test_get_work_entry_supervisor_site_assignment():
    """Supervisor can view work entry of employee assigned to their site."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp2 = data["emp2"]  # emp2 does not directly report to sup1
        sup1 = data["sup1"]
        site1 = data["site1"]  # site1 is supervised by sup1
        activity = data["activity"]
        today = data["today"]

        # Assign emp2 to site1 and create attendance there
        assign = EmployeeSiteAssignment(employee_id=emp2.id, site_id=site1.id, is_active=True)
        session.add(assign)
        att = AttendanceRecord(
            employee_id=emp2.id,
            site_id=site1.id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc),
            status="draft",
        )
        session.add(att)
        await session.commit()

        entry = await DailyWorkService.create_work_entry(
            session, emp2.id, make_payload(activity.id, quantity=4.0)
        )

        retrieved = await DailyWorkService.get_work_entry(
            session, entry.id, user_role="supervisor", employee_id=sup1.id
        )
        assert retrieved.id == entry.id


@pytest.mark.asyncio
async def test_get_work_entry_rejects_unauthorized_supervisor():
    """Supervisor 2 cannot view entry of Employee 1 (who reports to Supervisor 1)."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        sup2 = data["sup2"]  # sup2 does not supervise emp1 or site1
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.get_work_entry(
                session, entry.id, user_role="supervisor", employee_id=sup2.id
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_work_entry_admin_access():
    """Admin can view any work entry."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        retrieved = await DailyWorkService.get_work_entry(
            session, entry.id, is_admin=True
        )
        assert retrieved.id == entry.id


@pytest.mark.asyncio
async def test_get_work_entry_not_found():
    """Non-existent entry raises 404."""
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.get_work_entry(session, uuid.uuid4())
        assert exc_info.value.status_code == 404


# ==============================================================================
# 5. LIST WORK ENTRIES TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_list_work_entries_self():
    """Employee listing sees only their own entries."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=3.0)
        )

        items, total = await DailyWorkService.list_work_entries(
            session, employee_id=emp1.id
        )
        assert total >= 1
        assert any(item.id == entry.id for item in items)
        assert all(item.employee_id == emp1.id for item in items)


@pytest.mark.asyncio
async def test_list_work_entries_supervisor_team_scoping():
    """Supervisor listing sees only their assigned team's entries."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        sup1 = data["sup1"]
        sup2 = data["sup2"]
        site2 = data["site2"]
        activity = data["activity"]
        today = data["today"]

        # emp1 entry (supervised by sup1)
        entry1 = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=3.0)
        )

        # create active attendance & entry for emp2 (supervised by sup2)
        att2 = AttendanceRecord(
            employee_id=emp2.id,
            site_id=site2.id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc),
            status="draft",
        )
        session.add(att2)
        await session.commit()

        entry2 = await DailyWorkService.create_work_entry(
            session, emp2.id, make_payload(activity.id, quantity=7.0)
        )

        # Sup1 lists team entries
        items_sup1, _ = await DailyWorkService.list_work_entries(
            session, supervisor_emp_id=sup1.id
        )
        sup1_entry_ids = [item.id for item in items_sup1]
        assert entry1.id in sup1_entry_ids
        assert entry2.id not in sup1_entry_ids

        # Sup2 lists team entries
        items_sup2, _ = await DailyWorkService.list_work_entries(
            session, supervisor_emp_id=sup2.id
        )
        sup2_entry_ids = [item.id for item in items_sup2]
        assert entry2.id in sup2_entry_ids
        assert entry1.id not in sup2_entry_ids


@pytest.mark.asyncio
async def test_list_work_entries_supervisor_filters_by_authorized_employee():
    """Supervisor can filter by an authorized employee."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        sup1 = data["sup1"]
        activity = data["activity"]

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=5.0)
        )

        items, total = await DailyWorkService.list_work_entries(
            session, supervisor_emp_id=sup1.id, employee_id=emp1.id
        )
        assert total >= 1
        assert any(item.id == entry.id for item in items)


@pytest.mark.asyncio
async def test_list_work_entries_supervisor_filters_by_unauthorized_employee_rejected():
    """Supervisor filtering by an employee not in their team is rejected with 403."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp2 = data["emp2"]
        sup1 = data["sup1"]

        with pytest.raises(HTTPException) as exc_info:
            await DailyWorkService.list_work_entries(
                session, supervisor_emp_id=sup1.id, employee_id=emp2.id
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_list_work_entries_date_filter():
    """Filtering by date returns only entries for that date."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]
        today = data["today"]
        yesterday = today - timedelta(days=1)

        entry = await DailyWorkService.create_work_entry(
            session, emp1.id, make_payload(activity.id, quantity=2.0)
        )

        # Query for today
        items_today, total_today = await DailyWorkService.list_work_entries(
            session, employee_id=emp1.id, date=today
        )
        assert any(item.id == entry.id for item in items_today)

        # Query for yesterday
        items_yesterday, total_yesterday = await DailyWorkService.list_work_entries(
            session, employee_id=emp1.id, date=yesterday
        )
        assert not any(item.id == entry.id for item in items_yesterday)


@pytest.mark.asyncio
async def test_list_work_entries_pagination():
    """Test pagination skip and limit."""
    async with TestingSessionLocal() as session:
        data = await create_fixture_data(session)
        emp1 = data["emp1"]
        activity = data["activity"]

        # Create multiple entries for emp1
        for i in range(3):
            await DailyWorkService.create_work_entry(
                session, emp1.id, make_payload(activity.id, quantity=float(i + 1))
            )

        items_page1, total = await DailyWorkService.list_work_entries(
            session, employee_id=emp1.id, skip=0, limit=2
        )
        assert len(items_page1) == 2
        assert total >= 3

        items_page2, total2 = await DailyWorkService.list_work_entries(
            session, employee_id=emp1.id, skip=2, limit=2
        )
        assert len(items_page2) >= 1
        assert items_page1[0].id != items_page2[0].id

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    ExceptionFlag,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
from app.models.system import AuditLog
from app.models.workforce import Employee, Role
from app.modules.verification.exceptions import (
    InvalidVerificationStateError,
    MandatoryRemarksRequiredError,
    TargetNotFoundError,
    UnauthorizedSupervisorError,
)
from app.modules.verification.service import VerificationService
from tests.conftest import TestingSessionLocal


async def setup_test_environment(session: AsyncSession):
    suffix = str(uuid.uuid4())[:8]

    # Roles
    worker_role = Role(id=uuid.uuid4(), name=f"Worker-{suffix}")
    sup_role = Role(id=uuid.uuid4(), name=f"Supervisor-{suffix}")
    admin_role = Role(id=uuid.uuid4(), name=f"Admin-{suffix}")
    session.add_all([worker_role, sup_role, admin_role])

    # Users
    worker_user = User(id=uuid.uuid4(), mobile_id=f"W-{suffix}", role="employee", is_active=True)
    sup_user = User(id=uuid.uuid4(), mobile_id=f"S-{suffix}", role="supervisor", is_active=True)
    other_sup_user = User(id=uuid.uuid4(), mobile_id=f"OS-{suffix}", role="supervisor", is_active=True)
    admin_user = User(id=uuid.uuid4(), mobile_id=f"A-{suffix}", role="administrator", is_active=True)
    session.add_all([worker_user, sup_user, other_sup_user, admin_user])
    await session.flush()

    # Employees
    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        employee_code=f"SUP-{suffix}",
        mobile_id=sup_user.mobile_id,
        name="Assigned Supervisor",
        is_active=True,
    )
    other_sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=other_sup_user.id,
        employee_code=f"OSUP-{suffix}",
        mobile_id=other_sup_user.mobile_id,
        name="Other Supervisor",
        is_active=True,
    )
    worker_emp = Employee(
        id=uuid.uuid4(),
        user_id=worker_user.id,
        employee_code=f"EMP-{suffix}",
        mobile_id=worker_user.mobile_id,
        name="Field Worker One",
        supervisor_id=sup_emp.id,  # Assigned directly to sup_emp
        is_active=True,
    )
    session.add_all([sup_emp, other_sup_emp, worker_emp])
    await session.flush()

    # Project & Site
    client = Client(name=f"Client-{suffix}", is_active=True)
    session.add(client)
    await session.flush()

    project = Project(client_id=client.id, name=f"Project-{suffix}", status="active")
    session.add(project)
    await session.flush()

    site = Site(
        project_id=project.id,
        name=f"Site-{suffix}",
        supervisor_id=sup_emp.id,
        permitted_radius_m=500.0,
    )
    session.add(site)
    await session.flush()

    # Assignment
    assignment = EmployeeSiteAssignment(
        employee_id=worker_emp.id,
        site_id=site.id,
        is_active=True,
    )
    session.add(assignment)

    # Activity & Material
    activity = Activity(
        name="Cable Laying CAT6",
        unit_of_measure="metre",
        approved_rate=20.0,
        category="cable",
    )
    material = Material(
        material_code=f"MAT-{suffix}",
        name="CAT6 Box",
        unit_of_measure="box",
        category="cable",
        purchase_approval_limit=1000.0,
    )
    session.add_all([activity, material])
    await session.flush()

    # Work Order
    work_order = WorkOrder(
        order_number=f"WO-{suffix}",
        project_id=project.id,
        site_id=site.id,
        status="open",
        is_active=True,
    )
    session.add(work_order)

    # Attendance
    today = date.today()
    att = AttendanceRecord(
        employee_id=worker_emp.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
        check_in_distance_m=10.0,
        check_out_time=datetime.now(timezone.utc),
        check_out_distance_m=15.0,
        working_hours=8.0,
        is_within_geofence=True,
        status="draft",
    )
    session.add(att)
    await session.flush()

    # Work Entry
    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=att.id,
        employee_id=worker_emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=work_order.id,
        work_date=today,
        quantity=50.0,
        uom=activity.unit_of_measure,
        status="submitted",
    )
    session.add(dwe)
    await session.flush()

    # Photo
    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="/uploads/photos/test.jpg",
        thumbnail_url="/uploads/photos/test_thumb.jpg",
        file_size_bytes=1024,
    )
    session.add(photo)

    # Materials: one regular consumed, one high-value purchased
    mat_consumed = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="CAT6 Cable 50m",
        quantity=1.0,
        amount=500.0,
        is_high_value=False,
        status="submitted",
    )
    mat_purchased = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Heavy Duty Drill Bit",
        quantity=2.0,
        amount=3500.0,  # > 1000.0 limit
        is_high_value=True,
        bill_image_url="/uploads/bills/drill_receipt.jpg",
        status="submitted",
    )
    session.add_all([mat_consumed, mat_purchased])
    await session.commit()

    return {
        "worker_emp": worker_emp,
        "worker_user": worker_user,
        "sup_emp": sup_emp,
        "sup_user": sup_user,
        "other_sup_emp": other_sup_emp,
        "other_sup_user": other_sup_user,
        "admin_user": admin_user,
        "site": site,
        "activity": activity,
        "material": material,
        "work_order": work_order,
        "attendance": att,
        "daily_work_entry": dwe,
        "photo": photo,
        "mat_consumed": mat_consumed,
        "mat_purchased": mat_purchased,
        "today": today,
    }


@pytest.mark.asyncio
async def test_approve_attendance_transitions_to_verified():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        att = env["attendance"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks=None,
        )

        assert is_replay is False
        assert target_status == "verified"
        assert vr.id is not None
        assert vr.action == "approved"
        assert vr.attendance_record_id == att.id
        assert vr.daily_work_entry_id is None
        assert vr.material_transaction_id is None

        # Verify DB persistence of verified status
        stmt = select(AttendanceRecord).where(AttendanceRecord.id == att.id)
        res = await session.execute(stmt)
        updated_att = res.scalars().first()
        assert updated_att.status == "verified"

        # Verify audit log entry
        stmt_audit = select(AuditLog).where(
            AuditLog.entity_id == att.id, AuditLog.action == "verify_approved"
        )
        res_audit = await session.execute(stmt_audit)
        audit = res_audit.scalars().first()
        assert audit is not None
        assert audit.new_values["status"] == "verified"


@pytest.mark.asyncio
async def test_approve_daily_work_entry_transitions_to_approved():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Cabling verified and inspected",
        )

        assert is_replay is False
        assert target_status == "approved"
        assert vr.daily_work_entry_id == dwe.id
        assert vr.attendance_record_id is None
        assert vr.material_transaction_id is None

        # Verify DB persistence
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res = await session.execute(stmt)
        updated_dwe = res.scalars().first()
        assert updated_dwe.status == "approved"


@pytest.mark.asyncio
async def test_approve_material_transaction_independently():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        mat = env["mat_consumed"]
        dwe = env["daily_work_entry"]
        key = str(uuid.uuid4())

        # Verify material transaction independently
        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )

        assert is_replay is False
        assert target_status == "approved"
        assert vr.material_transaction_id == mat.id
        assert vr.daily_work_entry_id is None
        assert vr.attendance_record_id is None

        # Material status is approved
        stmt_m = select(MaterialTransaction).where(MaterialTransaction.id == mat.id)
        res_m = await session.execute(stmt_m)
        assert res_m.scalars().first().status == "approved"

        # Parent daily work entry status remains submitted (independent!)
        stmt_d = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res_d = await session.execute(stmt_d)
        assert res_d.scalars().first().status == "submitted"


@pytest.mark.asyncio
async def test_reject_material_transaction_with_mandatory_remarks():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        high_val_mat = env["mat_purchased"]
        dwe = env["daily_work_entry"]
        key = str(uuid.uuid4())

        # Supervisor rejects the high-value drill bit purchase due to illegible bill
        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=high_val_mat.id,
            action="rejected",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Drill bit receipt total does not match store invoice amount",  # >= 10 chars
        )

        assert is_replay is False
        assert target_status == "rejected"
        assert vr.material_transaction_id == high_val_mat.id

        # Material is rejected
        stmt_m = select(MaterialTransaction).where(MaterialTransaction.id == high_val_mat.id)
        res_m = await session.execute(stmt_m)
        assert res_m.scalars().first().status == "rejected"

        # Labor work entry is NOT affected!
        stmt_d = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res_d = await session.execute(stmt_d)
        assert res_d.scalars().first().status == "submitted"


@pytest.mark.asyncio
async def test_return_daily_work_entry_for_correction():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="correction_required",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Please attach missing end-of-cable termination photograph",  # >= 10 chars
        )

        assert is_replay is False
        assert target_status == "correction_required"
        assert vr.action == "correction_required"

        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "correction_required"


@pytest.mark.asyncio
async def test_mandatory_remarks_missing_or_short_raises_422():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]

        # Missing remarks on rejection
        with pytest.raises(MandatoryRemarksRequiredError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="rejected",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=env["sup_user"].id,
                supervisor_emp_id=env["sup_emp"].id,
                remarks=None,
            )
        assert exc_info.value.status_code == 422

        # Remarks shorter than 10 characters
        with pytest.raises(MandatoryRemarksRequiredError) as exc_info2:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="correction_required",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=env["sup_user"].id,
                supervisor_emp_id=env["sup_emp"].id,
                remarks="Too short",  # 9 chars
            )
        assert exc_info2.value.status_code == 422


@pytest.mark.asyncio
async def test_idempotency_replay_on_duplicate_key_returns_existing_record_with_200():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        key = f"IDEMP-{uuid.uuid4()}"

        # 1. Initial verification call
        vr1, status1, is_replay1 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay1 is False
        assert status1 == "approved"

        # 2. Retried verification call with identical idempotency_key (e.g. mobile reconnect)
        vr2, status2, is_replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay2 is True  # Replayed cleanly!
        assert status2 == "approved"
        assert vr2.id == vr1.id  # Same verification record


@pytest.mark.asyncio
async def test_concurrent_rapid_idempotency_key_verification():
    """Requirement 3: Two rapid/concurrent requests with the exact same idempotency_key
    must not create duplicate verification records in the database.
    """
    async with TestingSessionLocal() as session1, TestingSessionLocal() as session2:
        env = await setup_test_environment(session1)
        dwe = env["daily_work_entry"]
        key = f"CONCURRENT-KEY-{uuid.uuid4()}"

        # Run two verify_entity calls concurrently with the same idempotency_key
        # using separate database sessions (simulating two worker threads/processes)
        task1 = VerificationService.verify_entity(
            session=session1,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        task2 = VerificationService.verify_entity(
            session=session2,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )

        results = await asyncio.gather(task1, task2, return_exceptions=True)

        # Explicit assertion that neither concurrent task raised an unhandled exception
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert not exceptions, f"Concurrent task(s) raised unexpected exception(s): {exceptions}"
        assert len(results) == 2

        vr1, status1, is_replay1 = results[0]
        vr2, status2, is_replay2 = results[1]

        # Exactly one is original, one is replay
        assert (is_replay1, is_replay2) in ((False, True), (True, False))
        assert vr1.id == vr2.id

        # Verify at DB level that exactly ONE record exists with this idempotency key
        stmt = select(VerificationRecord).where(VerificationRecord.idempotency_key == key)
        db_records = (await session1.execute(stmt)).scalars().all()
        assert len(db_records) == 1


@pytest.mark.asyncio
async def test_state_machine_idempotency_when_already_approved():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        # Approve initially
        vr1, _, _ = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key1,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )

        # Another approve request arrives with different key (e.g. user double-clicked)
        vr2, status2, is_replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key2,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay2 is True
        assert status2 == "approved"
        assert vr2.id == vr1.id


@pytest.mark.asyncio
async def test_unassigned_supervisor_outside_team_scope_blocked():
    """Failure Mode A (SEC-004-A): A supervisor attempts to verify an employee/site outside their assigned scope.
    Must return 404 TargetNotFoundError (not 403) so existence and scope are indistinguishable from outside."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]

        # other_sup_emp is not assigned to worker_emp or the site
        with pytest.raises(TargetNotFoundError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="approved",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=env["other_sup_user"].id,
                supervisor_emp_id=env["other_sup_emp"].id,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Daily work record not found"


@pytest.mark.asyncio
async def test_regular_supervisor_cannot_reopen_approved_record():
    """Failure Mode B: An authorized supervisor attempts the admin-only Reopen action on an approved record."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]

        # 1. Assigned supervisor approves record
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )

        # 2. Regular supervisor attempts to reopen approved record -> 403 Forbidden
        with pytest.raises(UnauthorizedSupervisorError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="correction_required",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=env["sup_user"].id,
                supervisor_emp_id=env["sup_emp"].id,
                remarks="Attempting unauthorized supervisor reopen",
                is_admin=False,
            )
        assert exc_info.value.status_code == 403
        assert "Only administrators or directors can reopen" in exc_info.value.detail



@pytest.mark.asyncio
async def test_admin_reopen_approved_record_to_correction_required():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]

        # 1. Approve record
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )

        # 2. Regular supervisor attempts to reopen approved record -> 403
        with pytest.raises(UnauthorizedSupervisorError):
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="correction_required",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=env["sup_user"].id,
                supervisor_emp_id=env["sup_emp"].id,
                remarks="Trying to reopen without admin role",
                is_admin=False,
            )

        # 3. Admin reopens approved record with mandatory remarks -> Success!
        vr, new_status, _ = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="correction_required",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=env["admin_user"].id,
            supervisor_emp_id=None,
            remarks="Reopened per site audit discrepancy investigation",
            is_admin=True,
        )
        assert new_status == "correction_required"
        assert vr.action == "correction_required"

        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "correction_required"


@pytest.mark.asyncio
async def test_compute_exception_flags_detects_all_anomalies():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        today = env["today"]
        emp = env["worker_emp"]
        site = env["site"]

        # Create unclosed attendance with out of geofence
        bad_att = AttendanceRecord(
            employee_id=emp.id,
            site_id=site.id,
            date=today,
            session_number=2,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=5),
            check_out_time=None,  # missing checkout!
            is_within_geofence=False,  # out of location!
            status="flagged",
        )
        session.add(bad_att)
        await session.flush()

        # Create positive quantity work entry without photo
        no_photo_dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=bad_att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=env["activity"].id,
            work_date=today,
            quantity=100.0,
            uom="metre",
            status="submitted",
        )
        session.add(no_photo_dwe)
        await session.flush()

        flags = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=emp.id,
            work_date=today,
            attendance_record=bad_att,
            work_entries=[no_photo_dwe],
            material_transactions=[env["mat_purchased"]],  # is_high_value = True
        )

        assert "out_of_location" in flags
        assert "missing_checkout" in flags
        assert "no_photograph" in flags
        assert "high_value_material" in flags


@pytest.mark.asyncio
async def test_get_eod_summary_aggregates_team_and_pending_count():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        summary = await VerificationService.get_eod_summary(
            session=session,
            supervisor_emp_id=env["sup_emp"].id,
            review_date=env["today"],
        )

        assert summary.total_employees >= 1
        assert summary.pending_verification_count >= 1

        emp_item = next(i for i in summary.items if i.employee_id == env["worker_emp"].id)
        assert emp_item.employee_name == "Field Worker One"
        assert emp_item.work_entry_count == 1
        assert emp_item.photo_count == 1
        assert emp_item.material_count == 2
        assert emp_item.total_material_cost == Decimal("4000.00")
        assert "high_value_material" in emp_item.exception_flags
        assert emp_item.has_pending_verification is True


@pytest.mark.asyncio
async def test_get_employee_detail_combines_attendance_work_photos_materials():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=env["sup_emp"].id,
            employee_id=env["worker_emp"].id,
            review_date=env["today"],
        )

        assert detail.employee_name == "Field Worker One"
        assert detail.attendance is not None
        assert detail.attendance.working_hours == 8.0
        assert len(detail.work_entries) == 1
        we = detail.work_entries[0]
        assert we.activity_name == "Cable Laying CAT6"
        assert we.uom == "metre"
        assert len(we.photos) == 1
        assert len(we.materials) == 2

        # Check high-value material detail
        hv_mat = next(m for m in we.materials if m.is_high_value)
        assert hv_mat.item_name == "Heavy Duty Drill Bit"
        assert hv_mat.amount == Decimal("3500.00")
        assert hv_mat.bill_image_url == "/uploads/bills/drill_receipt.jpg"


@pytest.mark.asyncio
async def test_reject_attendance_with_mandatory_remarks():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        att = env["attendance"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="rejected",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Check-in GPS coordinates do not align with authorized site boundaries",
        )

        assert is_replay is False
        assert target_status == "rejected"
        assert vr.attendance_record_id == att.id
        assert vr.daily_work_entry_id is None
        assert vr.material_transaction_id is None
        assert vr.action == "rejected"

        stmt = select(AttendanceRecord).where(AttendanceRecord.id == att.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "rejected"


@pytest.mark.asyncio
async def test_return_attendance_for_correction():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        att = env["attendance"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="correction_required",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Please submit manual checkout explanation for partial shift",
        )

        assert is_replay is False
        assert target_status == "correction_required"
        assert vr.attendance_record_id == att.id

        stmt = select(AttendanceRecord).where(AttendanceRecord.id == att.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "correction_required"


@pytest.mark.asyncio
async def test_reject_daily_work_entry_with_remarks():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="rejected",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Work claimed was completed on previous shift by team B",
        )

        assert is_replay is False
        assert target_status == "rejected"
        assert vr.daily_work_entry_id == dwe.id

        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "rejected"


@pytest.mark.asyncio
async def test_return_material_transaction_for_correction():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        mat = env["mat_purchased"]
        key = str(uuid.uuid4())

        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat.id,
            action="correction_required",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
            remarks="Store receipt is blurred, please upload high-contrast scan",
        )

        assert is_replay is False
        assert target_status == "correction_required"
        assert vr.material_transaction_id == mat.id

        stmt = select(MaterialTransaction).where(MaterialTransaction.id == mat.id)
        res = await session.execute(stmt)
        assert res.scalars().first().status == "correction_required"


@pytest.mark.asyncio
async def test_idempotency_replay_on_duplicate_key_attendance():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        att = env["attendance"]
        key = f"IDEMP-ATT-{uuid.uuid4()}"

        # 1. Initial approval
        vr1, status1, is_replay1 = await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay1 is False
        assert status1 == "verified"

        # 2. Retried with identical key
        vr2, status2, is_replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay2 is True
        assert status2 == "verified"
        assert vr2.id == vr1.id


@pytest.mark.asyncio
async def test_idempotency_replay_on_duplicate_key_material():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        mat = env["mat_consumed"]
        key = f"IDEMP-MAT-{uuid.uuid4()}"

        # 1. Initial approval
        vr1, status1, is_replay1 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay1 is False
        assert status1 == "approved"

        # 2. Retried with identical key
        vr2, status2, is_replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat.id,
            action="approved",
            idempotency_key=key,
            supervisor_user_id=env["sup_user"].id,
            supervisor_emp_id=env["sup_emp"].id,
        )
        assert is_replay2 is True
        assert status2 == "approved"
        assert vr2.id == vr1.id


@pytest.mark.asyncio
async def test_eod_summary_three_way_pending_lifecycle():
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        today = env["today"]
        sup_emp = env["sup_emp"]
        sup_user = env["sup_user"]
        att = env["attendance"]
        dwe = env["daily_work_entry"]
        mat1 = env["mat_consumed"]
        mat2 = env["mat_purchased"]

        # Initially, all are submitted/draft -> pending is True
        s1 = await VerificationService.get_eod_summary(
            session=session, supervisor_emp_id=sup_emp.id, review_date=today
        )
        item1 = next(i for i in s1.items if i.employee_id == env["worker_emp"].id)
        assert item1.has_pending_verification is True

        # 1. Verify attendance
        await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        s2 = await VerificationService.get_eod_summary(
            session=session, supervisor_emp_id=sup_emp.id, review_date=today
        )
        item2 = next(i for i in s2.items if i.employee_id == env["worker_emp"].id)
        assert item2.attendance_status == "verified"
        # Still pending because daily_work_entry and materials are submitted!
        assert item2.has_pending_verification is True

        # 2. Verify daily work entry
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        s3 = await VerificationService.get_eod_summary(
            session=session, supervisor_emp_id=sup_emp.id, review_date=today
        )
        item3 = next(i for i in s3.items if i.employee_id == env["worker_emp"].id)
        # Still pending because materials are submitted!
        assert item3.has_pending_verification is True

        # 3. Verify material 1 and material 2
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat1.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=mat2.id,
            action="rejected",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks="Rejecting high value drill purchase receipt",
        )

        # Now all 3 categories (attendance, daily work, materials) are verified!
        s4 = await VerificationService.get_eod_summary(
            session=session, supervisor_emp_id=sup_emp.id, review_date=today
        )
        item4 = next(i for i in s4.items if i.employee_id == env["worker_emp"].id)
        assert item4.has_pending_verification is False


@pytest.mark.asyncio
async def test_draft_work_entry_and_material_do_not_count_as_pending_verification():
    """Verify that draft records not yet submitted by the worker do NOT show as pending supervisor verification."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        sup_emp = env["sup_emp"]
        att = env["attendance"]
        dwe = env["daily_work_entry"]
        mat1 = env["mat_consumed"]
        mat2 = env["mat_purchased"]

        # 1. Attendance is verified
        att.status = "verified"

        # 2. Daily work entry and materials are in 'draft' status (worker is still filling them out)
        dwe.status = "draft"
        mat1.status = "draft"
        mat2.status = "draft"
        await session.commit()

        # 3. Retrieve EOD summary for supervisor
        summary = await VerificationService.get_eod_summary(
            session=session,
            supervisor_emp_id=sup_emp.id,
            review_date=env["today"],
        )

        emp_item = next(i for i in summary.items if i.employee_id == env["worker_emp"].id)
        assert emp_item.work_entry_count == 1
        assert emp_item.material_count == 2
        # Crucial check: Draft items must NOT mark employee as pending verification!
        assert emp_item.has_pending_verification is False
        assert summary.pending_verification_count == 0

        # 4. Worker submits daily work entry
        dwe.status = "submitted"
        await session.commit()

        summary_after_sub = await VerificationService.get_eod_summary(
            session=session,
            supervisor_emp_id=sup_emp.id,
            review_date=env["today"],
        )
        emp_item_after = next(i for i in summary_after_sub.items if i.employee_id == env["worker_emp"].id)
        assert emp_item_after.has_pending_verification is True
        assert summary_after_sub.pending_verification_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# Batch 4B: Verification History in get_employee_detail
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_history_multi_step_chronological_order():
    """submitted → correction_required → resubmitted → approved yields 2 history
    events in chronological order with correct actions and remarks."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        worker_emp = env["worker_emp"]

        # Step 1: supervisor returns for correction
        key1 = str(uuid.uuid4())
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="correction_required",
            idempotency_key=key1,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks="Missing quantity breakdown for cable splices",
        )

        # Step 2: worker "resubmits" by setting status back to submitted
        stmt_dwe = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        res_dwe = await session.execute(stmt_dwe)
        dwe_obj = res_dwe.scalars().first()
        dwe_obj.status = "submitted"
        await session.commit()

        # Step 3: supervisor approves
        key2 = str(uuid.uuid4())
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=key2,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )

        # Fetch detail
        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=env["today"],
        )

        we = next(e for e in detail.work_entries if e.id == dwe.id)

        # Exactly 2 history events
        assert len(we.history) == 2

        # Oldest first (correction_required before approved)
        assert we.history[0].action == "correction_required"
        assert we.history[0].remarks == "Missing quantity breakdown for cable splices"
        assert we.history[1].action == "approved"
        assert we.history[1].remarks is None

        # Chronological ordering guaranteed
        assert we.history[0].verified_at <= we.history[1].verified_at

        # Current latest-action fields still reflect the final state
        assert we.verification_action == "approved"


@pytest.mark.asyncio
async def test_history_empty_when_no_verification_taken():
    """An item with no verification yet returns an empty history list."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        worker_emp = env["worker_emp"]
        sup_emp = env["sup_emp"]

        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=env["today"],
        )

        # Attendance history empty (no VR rows yet)
        if detail.attendance:
            assert detail.attendance.history == []

        # Work entry history empty
        for we in detail.work_entries:
            assert we.history == []
            for mat in we.materials:
                assert mat.history == []


@pytest.mark.asyncio
async def test_history_idempotency_replay_does_not_add_duplicate_event():
    """A replayed idempotency_key must not add a second history event."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        worker_emp = env["worker_emp"]

        shared_key = f"IDEMP-HIST-{uuid.uuid4()}"

        # First call — creates the VerificationRecord
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=shared_key,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )

        # Second call with the same key — must be a replay (no new DB row)
        _, _, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=shared_key,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )
        assert is_replay is True

        # History must contain exactly 1 event despite 2 calls
        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=env["today"],
        )
        we = next(e for e in detail.work_entries if e.id == dwe.id)
        assert len(we.history) == 1


@pytest.mark.asyncio
async def test_history_verifier_name_resolves_for_supervisor():
    """verified_by_name resolves to the supervisor's Employee name when an employee record exists."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        worker_emp = env["worker_emp"]
        today = env["today"]

        # Supervisor approves the work entry
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )

        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=today,
        )

        we = next(e for e in detail.work_entries if e.id == dwe.id)
        assert len(we.history) == 1
        assert we.history[0].verified_by == sup_user.id
        assert we.history[0].verified_by_name == "Assigned Supervisor"


@pytest.mark.asyncio
async def test_history_verifier_name_falls_back_to_role_label_for_admin_without_employee_record():
    """verified_by_name falls back to role label (Administrator) for an admin with no employee record,
    and raw mobile_id never leaks into verified_by_name."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        att = env["attendance"]
        sup_emp = env["sup_emp"]
        admin_user = env["admin_user"]  # no Employee row in setup_test_environment
        worker_emp = env["worker_emp"]
        today = env["today"]

        # Admin marks attendance as correction_required to get admin history event
        att_obj = (await session.execute(select(AttendanceRecord).where(AttendanceRecord.id == att.id))).scalars().first()
        att_obj.status = "submitted"
        await session.commit()

        await VerificationService.verify_entity(
            session=session,
            entity_type="attendance",
            entity_id=att.id,
            action="correction_required",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=admin_user.id,
            supervisor_emp_id=None,
            remarks="Admin override: geofence data requires review",
            is_admin=True,
        )

        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=today,
        )

        assert detail.attendance is not None
        assert len(detail.attendance.history) == 1
        admin_event = detail.attendance.history[0]
        assert admin_event.verified_by == admin_user.id
        # Role label from User.role = "administrator" -> "Administrator"
        assert admin_event.verified_by_name == "Administrator"
        # Raw mobile_id must NOT appear in verified_by_name
        assert admin_user.mobile_id not in admin_event.verified_by_name


@pytest.mark.asyncio
async def test_history_admin_reopen_chain_three_events_chronological():
    """Full lifecycle: submitted -> approved -> reopened by admin (correction_required)
    -> resubmitted -> approved yields 3 history events in chronological order.
    The reopen event carries mandatory remarks, verified_by_name is 'Administrator',
    and no mobile number appears anywhere in the serialized response."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        admin_user = env["admin_user"]
        worker_emp = env["worker_emp"]
        today = env["today"]

        # Step 1: Supervisor approves initial submission
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )

        # Step 2: Administrator reopens (correction_required) with mandatory remarks
        reopen_remarks = "Administrator audit: quality checklist and photo count mismatch"
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="correction_required",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=admin_user.id,
            supervisor_emp_id=None,
            remarks=reopen_remarks,
            is_admin=True,
        )

        # Step 3: Worker resubmits
        stmt_dwe = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
        dwe_obj = (await session.execute(stmt_dwe)).scalars().first()
        dwe_obj.status = "submitted"
        await session.commit()

        # Step 4: Supervisor approves resubmission
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks=None,
        )

        # Fetch consolidated detail
        detail = await VerificationService.get_employee_detail(
            session=session,
            supervisor_emp_id=sup_emp.id,
            employee_id=worker_emp.id,
            review_date=today,
        )

        we = next(e for e in detail.work_entries if e.id == dwe.id)

        # Exactly 3 history events
        assert len(we.history) == 3

        # Chronological ordering (oldest first)
        assert we.history[0].verified_at <= we.history[1].verified_at <= we.history[2].verified_at

        # Event 1: Initial approval by supervisor
        assert we.history[0].action == "approved"
        assert we.history[0].verified_by == sup_user.id
        assert we.history[0].verified_by_name == "Assigned Supervisor"
        assert we.history[0].remarks is None

        # Event 2: Admin reopen (correction_required) carrying mandatory remarks
        assert we.history[1].action == "correction_required"
        assert we.history[1].verified_by == admin_user.id
        assert we.history[1].verified_by_name == "Administrator"
        assert we.history[1].remarks == reopen_remarks

        # Event 3: Final approval by supervisor
        assert we.history[2].action == "approved"
        assert we.history[2].verified_by == sup_user.id
        assert we.history[2].verified_by_name == "Assigned Supervisor"
        assert we.history[2].remarks is None

        # Assert no mobile number anywhere in the serialized response
        serialized_json = detail.model_dump_json()
        assert admin_user.mobile_id not in serialized_json
        assert sup_user.mobile_id not in serialized_json
        assert env["worker_user"].mobile_id not in serialized_json


@pytest.mark.asyncio
async def test_history_unassigned_supervisor_gets_404_sec_004_a():
    """SEC-004-A: An unassigned supervisor gets 404 TargetNotFoundError (not 403) for get_employee_detail,
    returning the same 'Employee record not found' as a nonexistent employee."""
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        worker_emp = env["worker_emp"]
        other_sup_emp = env["other_sup_emp"]

        with pytest.raises(TargetNotFoundError) as exc_info:
            await VerificationService.get_employee_detail(
                session=session,
                supervisor_emp_id=other_sup_emp.id,
                employee_id=worker_emp.id,
                review_date=env["today"],
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Employee record not found"


@pytest.mark.asyncio
async def test_invalid_state_error_message_format_is_pinned():
    """Pin the exact exception detail string for InvalidVerificationStateError.

    The frontend relies on the exact template "Cannot {action} record with status '{current_status}'. Target must be submitted."
    (and specifically the STATE_CONFLICT_MARKER "Target must be submitted.") to distinguish state conflicts
    from other client errors without relying on fragile guessing.
    """
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        dwe = env["daily_work_entry"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        admin_user = env["admin_user"]

        # Case 1: Reject the record first so status becomes 'rejected'
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="rejected",
            idempotency_key=str(uuid.uuid4()),
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks="Rejecting item for invalid state pinning test",
        )
        await session.commit()

        # Attempt to approve the already-rejected item -> must raise InvalidVerificationStateError
        with pytest.raises(InvalidVerificationStateError) as exc_info_approve:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="approved",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=sup_user.id,
                supervisor_emp_id=sup_emp.id,
            )

        expected_msg_approve = "Cannot approved record with status 'rejected'. Target must be submitted."
        assert exc_info_approve.value.detail == expected_msg_approve
        assert exc_info_approve.value.status_code == 400
        assert "Target must be submitted." in exc_info_approve.value.detail

        # Case 2: Admin reopen of an item that is already in 'correction_required' status
        dwe.status = "correction_required"
        await session.commit()

        with pytest.raises(InvalidVerificationStateError) as exc_info_reopen:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="correction_required",
                idempotency_key=str(uuid.uuid4()),
                supervisor_user_id=admin_user.id,
                remarks="Attempting to reopen an already reopened item",
                is_admin=True,
            )

        expected_msg_reopen = "Cannot correction_required record with status 'correction_required'. Target must be submitted."
        assert exc_info_reopen.value.detail == expected_msg_reopen
        assert exc_info_reopen.value.status_code == 400
        assert "Target must be submitted." in exc_info_reopen.value.detail


# ── compute_exception_flags draft-scoping tests ──────────────────────────────

@pytest.mark.asyncio
async def test_no_photograph_flag_not_raised_for_draft_work_entry():
    """A draft work entry with positive quantity and no photo must NOT trigger
    the no_photograph exception. Only submitted entries are supervisor-relevant.
    The complementary case (submitted entry with no photo) must still fire.
    """
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        worker_emp = env["worker_emp"]
        site = env["site"]
        activity = env["activity"]
        att = env["attendance"]
        today = env["today"]

        # Draft entry: positive quantity, NO photo.
        draft_dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=activity.id,
            work_date=today,
            quantity=10.0,
            uom=activity.unit_of_measure,
            status="draft",
        )
        session.add(draft_dwe)
        await session.flush()

        flags = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=worker_emp.id,
            work_date=today,
            attendance_record=att,
            work_entries=[draft_dwe],
            material_transactions=[],
        )

        assert "no_photograph" not in flags, (
            "Draft entry without a photo must NOT raise no_photograph — "
            "the worker hasn't submitted it yet."
        )

        # Positive case: a submitted entry with no photo MUST fire.
        submitted_no_photo_dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=activity.id,
            work_date=today,
            quantity=5.0,
            uom=activity.unit_of_measure,
            status="submitted",
        )
        session.add(submitted_no_photo_dwe)
        await session.flush()

        flags_submitted = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=worker_emp.id,
            work_date=today,
            attendance_record=att,
            work_entries=[submitted_no_photo_dwe],
            material_transactions=[],
        )

        assert "no_photograph" in flags_submitted, (
            "Submitted entry without a photo MUST raise no_photograph."
        )


@pytest.mark.asyncio
async def test_high_value_material_flag_not_raised_for_draft_transaction():
    """A high-value material transaction with status='draft' must NOT trigger
    high_value_material. Only submitted transactions are supervisor-relevant.
    The complementary case (submitted high-value transaction) must still fire.
    """
    async with TestingSessionLocal() as session:
        env = await setup_test_environment(session)
        worker_emp = env["worker_emp"]
        site = env["site"]
        activity = env["activity"]
        material = env["material"]
        att = env["attendance"]
        today = env["today"]

        draft_dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=activity.id,
            work_date=today,
            quantity=1.0,
            uom=activity.unit_of_measure,
            status="draft",
        )
        session.add(draft_dwe)
        await session.flush()

        draft_mat = MaterialTransaction(
            daily_work_entry_id=draft_dwe.id,
            material_id=material.id,
            site_id=site.id,
            transaction_type="purchased",
            item_name="Expensive Bulk Cable",
            quantity=1.0,
            amount=9999.0,
            is_high_value=True,
            status="draft",
        )
        session.add(draft_mat)
        await session.flush()

        flags = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=worker_emp.id,
            work_date=today,
            attendance_record=att,
            work_entries=[draft_dwe],
            material_transactions=[draft_mat],
        )

        assert "high_value_material" not in flags, (
            "Draft material transaction (is_high_value=True, status='draft') must NOT "
            "raise high_value_material — the worker hasn't submitted it yet."
        )

        # Positive case: submitted high-value transaction MUST fire.
        submitted_mat = MaterialTransaction(
            daily_work_entry_id=draft_dwe.id,
            material_id=material.id,
            site_id=site.id,
            transaction_type="purchased",
            item_name="Expensive Bulk Cable (Submitted)",
            quantity=1.0,
            amount=9999.0,
            is_high_value=True,
            status="submitted",
        )
        session.add(submitted_mat)
        await session.flush()

        flags_submitted = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=worker_emp.id,
            work_date=today,
            attendance_record=att,
            work_entries=[draft_dwe],
            material_transactions=[submitted_mat],
        )

        assert "high_value_material" in flags_submitted, (
            "Submitted high-value material transaction MUST raise high_value_material."
        )



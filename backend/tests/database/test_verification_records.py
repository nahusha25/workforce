import uuid
from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
)
from app.models.workforce import Employee


def create_verification_dependencies(sync_db_session: Session):
    unique_suffix = str(uuid.uuid4())[:8]

    # Create worker user and supervisor user
    worker_user = User(mobile_id=f"W-{unique_suffix}", role="employee", is_active=True)
    supervisor_user = User(mobile_id=f"S-{unique_suffix}", role="supervisor", is_active=True)
    sync_db_session.add_all([worker_user, supervisor_user])
    sync_db_session.flush()

    client = Client(name=f"Client-{unique_suffix}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.flush()

    project = Project(client_id=client.id, name=f"Project-{unique_suffix}", status="active")
    sync_db_session.add(project)
    sync_db_session.flush()

    site = Site(project_id=project.id, name=f"Site-{unique_suffix}")
    emp = Employee(
        user_id=worker_user.id,
        employee_code=f"EMP-{unique_suffix}",
        mobile_id=worker_user.mobile_id,
        name="Field Worker",
        is_active=True,
    )
    activity = Activity(
        name=f"Activity-{unique_suffix}",
        unit_of_measure="metre",
        approved_rate=25.00,
        category="cable",
    )
    material = Material(
        material_code=f"MAT-{unique_suffix}",
        name="Cat6 Cable",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=1000.00,
    )
    sync_db_session.add_all([emp, site, activity, material])
    sync_db_session.flush()

    work_order = WorkOrder(
        order_number=f"WO-VR-{unique_suffix}",
        project_id=project.id,
        site_id=site.id,
        status="open",
        is_active=True,
    )
    attendance = AttendanceRecord(
        employee_id=emp.id,
        site_id=site.id,
        date=date.today(),
        status="present",
    )
    sync_db_session.add_all([work_order, attendance])
    sync_db_session.flush()

    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=work_order.id,
        work_date=date.today(),
        quantity=75.0,
        uom=activity.unit_of_measure,
        status="submitted",
    )
    sync_db_session.add(dwe)
    sync_db_session.flush()

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Conduit Pipes",
        quantity=10.0,
        amount=1500.0,
        is_high_value=True,
        status="submitted",
    )
    sync_db_session.add(tx)
    sync_db_session.flush()

    return {
        "supervisor_user": supervisor_user,
        "worker_user": worker_user,
        "attendance": attendance,
        "daily_work_entry": dwe,
        "material_transaction": tx,
    }


def test_valid_verification_record_daily_work_approve(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
        remarks=None,
    )
    sync_db_session.add(vr)
    sync_db_session.commit()

    assert vr.id is not None
    assert vr.daily_work_entry_id == deps["daily_work_entry"].id
    assert vr.attendance_record_id is None
    assert vr.material_transaction_id is None
    assert vr.action == "approved"
    assert vr.remarks is None
    assert vr.verified_at is not None
    assert vr.created_at is not None


def test_valid_verification_record_attendance_approve(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=deps["attendance"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
        remarks="Attendance verified with GPS log",
    )
    sync_db_session.add(vr)
    sync_db_session.commit()

    assert vr.id is not None
    assert vr.attendance_record_id == deps["attendance"].id
    assert vr.daily_work_entry_id is None
    assert vr.material_transaction_id is None
    assert vr.action == "approved"


def test_valid_verification_record_material_transaction_approve(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        material_transaction_id=deps["material_transaction"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
        remarks="Bill verified against site store register",
    )
    sync_db_session.add(vr)
    sync_db_session.commit()

    assert vr.id is not None
    assert vr.material_transaction_id == deps["material_transaction"].id
    assert vr.attendance_record_id is None
    assert vr.daily_work_entry_id is None
    assert vr.action == "approved"


def test_valid_verification_record_reject_with_mandatory_remarks(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        material_transaction_id=deps["material_transaction"].id,
        verified_by=deps["supervisor_user"].id,
        action="rejected",
        remarks="Bill receipt is illegible and unverified",  # >= 10 chars
    )
    sync_db_session.add(vr)
    sync_db_session.commit()

    assert vr.id is not None
    assert vr.action == "rejected"
    assert "illegible" in vr.remarks


def test_valid_verification_record_return_with_mandatory_remarks(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="correction_required",
        remarks="Please re-measure cabling quantity for corridor B",  # >= 10 chars
    )
    sync_db_session.add(vr)
    sync_db_session.commit()

    assert vr.id is not None
    assert vr.action == "correction_required"


def test_single_target_constraint_zero_targets_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=None,
        daily_work_entry_id=None,
        material_transaction_id=None,
        verified_by=deps["supervisor_user"].id,
        action="approved",
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_single_target" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_single_target_constraint_two_targets_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=deps["attendance"].id,
        daily_work_entry_id=deps["daily_work_entry"].id,
        material_transaction_id=None,
        verified_by=deps["supervisor_user"].id,
        action="approved",
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_single_target" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_single_target_constraint_all_three_targets_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=deps["attendance"].id,
        daily_work_entry_id=deps["daily_work_entry"].id,
        material_transaction_id=deps["material_transaction"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_single_target" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_mandatory_remarks_reject_without_remarks_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="rejected",
        remarks=None,
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_mandatory_remarks" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_mandatory_remarks_reject_with_short_remarks_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="rejected",
        remarks="rejected!",  # 9 chars (< 10)
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_mandatory_remarks" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_mandatory_remarks_reject_with_whitespace_padded_short_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="rejected",
        remarks="   short   ",  # trim is 5 chars (< 10)
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_mandatory_remarks" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_mandatory_remarks_return_without_remarks_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="correction_required",
        remarks=None,
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_mandatory_remarks" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_mandatory_remarks_return_with_short_remarks_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="correction_required",
        remarks="fix this",  # 8 chars (< 10)
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_mandatory_remarks" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_invalid_action_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="pending_review",  # Invalid action
        remarks="Invalid action testing",
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_verification_action" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_duplicate_idempotency_key_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)
    shared_key = str(uuid.uuid4())

    vr1 = VerificationRecord(
        idempotency_key=shared_key,
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
    )
    sync_db_session.add(vr1)
    sync_db_session.commit()

    vr2 = VerificationRecord(
        idempotency_key=shared_key,
        attendance_record_id=deps["attendance"].id,
        verified_by=deps["supervisor_user"].id,
        action="approved",
    )
    sync_db_session.add(vr2)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "idempotency_key" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()
    sync_db_session.rollback()


def test_foreign_key_invalid_verified_by_user_fails(sync_db_session: Session):
    deps = create_verification_dependencies(sync_db_session)

    vr = VerificationRecord(
        idempotency_key=str(uuid.uuid4()),
        daily_work_entry_id=deps["daily_work_entry"].id,
        verified_by=uuid.uuid4(),  # Non-existent user UUID
        action="approved",
    )
    sync_db_session.add(vr)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "foreign key" in str(exc_info.value).lower() or "verified_by" in str(exc_info.value).lower()
    sync_db_session.rollback()

import uuid
import pytest
from datetime import date, datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.operations import DailyWorkEntry, Site, Activity, WorkOrder, AttendanceRecord, Project, Client
from app.models.auth import User
from app.models.workforce import Employee

def create_dependencies(sync_db_session: Session):
    unique_suffix = str(uuid.uuid4())[:8]
    # User
    user = User(mobile_id=f"M-{unique_suffix}", role="employee", is_active=True)
    sync_db_session.add(user)
    sync_db_session.flush()

    # Client and Project for WorkOrder
    client = Client(name=f"DWE Client {unique_suffix}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.flush()

    project = Project(client_id=client.id, name=f"DWE Project {unique_suffix}", status="active")
    sync_db_session.add(project)
    sync_db_session.flush()

    # Employee
    emp = Employee(user_id=user.id, employee_code=f"E-{unique_suffix}", mobile_id=f"M-{unique_suffix}", name="John Doe", is_active=True)
    # Site
    site = Site(project_id=project.id, name=f"DWE Site {unique_suffix}")
    # Activity
    activity = Activity(name=f"DWE Activity {unique_suffix}", unit_of_measure="m", approved_rate=10.00, category="cable")
    
    sync_db_session.add_all([emp, site, activity])
    sync_db_session.flush()
    
    # WorkOrder
    work_order = WorkOrder(order_number=f"WO-DWE-{unique_suffix}", project_id=project.id, site_id=site.id, status="open", is_active=True)
    sync_db_session.add(work_order)
    sync_db_session.flush()
    
    # Attendance
    attendance = AttendanceRecord(employee_id=emp.id, site_id=site.id, date=date.today(), status="present")
    sync_db_session.add(attendance)
    sync_db_session.flush()
    
    return emp, site, activity, work_order, attendance

def test_valid_daily_work_entry(sync_db_session: Session):
    emp, site, activity, work_order, attendance = create_dependencies(sync_db_session)
    idemp_key = f"IDEMP-{uuid.uuid4()}"
    
    entry = DailyWorkEntry(
        idempotency_key=idemp_key,
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=work_order.id,
        work_date=date.today(),
        quantity=10.50,
        uom=activity.unit_of_measure,
        status="draft",
        remarks="Started work"
    )
    sync_db_session.add(entry)
    sync_db_session.commit()
    
    assert entry.id is not None
    assert isinstance(entry.id, uuid.UUID)
    assert entry.idempotency_key == idemp_key
    assert float(entry.quantity) == 10.50
    assert entry.uom == "m"
    assert entry.work_date == date.today()
    assert entry.status == "draft"

def test_zero_quantities_and_null_work_order(sync_db_session: Session):
    emp, site, activity, _, attendance = create_dependencies(sync_db_session)
    
    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=None,
        work_date=date.today(),
        quantity=0.00,
        uom=activity.unit_of_measure,
        status="submitted"
    )
    sync_db_session.add(entry)
    sync_db_session.commit()
    
    assert float(entry.quantity) == 0.0
    assert entry.work_order_id is None

@pytest.mark.parametrize("value", [-1, -10.5, -0.01])
def test_negative_quantities_rejected(sync_db_session: Session, value: float):
    emp, site, activity, _, attendance = create_dependencies(sync_db_session)
    
    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=value,
        uom=activity.unit_of_measure,
        status="draft"
    )
    sync_db_session.add(entry)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_duplicate_idempotency_key_rejected(sync_db_session: Session):
    emp, site, activity, _, attendance = create_dependencies(sync_db_session)
    dup_key = f"IDEMP-DUP-{uuid.uuid4()}"

    entry1 = DailyWorkEntry(
        idempotency_key=dup_key,
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=5.0,
        uom=activity.unit_of_measure,
        status="draft"
    )
    sync_db_session.add(entry1)
    sync_db_session.commit()

    entry2 = DailyWorkEntry(
        idempotency_key=dup_key,
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=10.0,
        uom=activity.unit_of_measure,
        status="draft"
    )
    sync_db_session.add(entry2)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

@pytest.mark.parametrize("status", [
    "draft",
    "submitted",
    "approved",
    "rejected",
    "correction_required"
])
def test_valid_statuses(sync_db_session: Session, status: str):
    emp, site, activity, _, attendance = create_dependencies(sync_db_session)
    
    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=1.0,
        uom=activity.unit_of_measure,
        status=status
    )
    sync_db_session.add(entry)
    sync_db_session.commit()
    assert entry.status == status

def test_invalid_status_rejected(sync_db_session: Session):
    emp, site, activity, _, attendance = create_dependencies(sync_db_session)
    
    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=1.0,
        uom=activity.unit_of_measure,
        status="invalid_status"
    )
    sync_db_session.add(entry)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_invalid_foreign_key_rejected(sync_db_session: Session):
    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        site_id=uuid.uuid4(),
        activity_id=uuid.uuid4(),
        work_date=date.today(),
        quantity=1.0,
        uom="nos",
        status="draft"
    )
    sync_db_session.add(entry)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

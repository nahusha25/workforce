import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.auth import User
from app.models.operations import Client, Project, Site, EmployeeSiteAssignment, AttendanceRecord, DailyWorkEntry, Activity
from app.models.workforce import Employee, Role


@pytest.fixture
def test_data(sync_db_session: Session):
    role = Role(id=uuid.uuid4(), name=f"Role-{uuid.uuid4().hex[:6]}", description="Worker")
    sync_db_session.add(role)

    client_obj = Client(id=uuid.uuid4(), name=f"Test Client {uuid.uuid4().hex[:6]}")
    sync_db_session.add(client_obj)

    project_obj = Project(id=uuid.uuid4(), client_id=client_obj.id, name="Test Project", status="Active")
    sync_db_session.add(project_obj)

    site_obj = Site(
        id=uuid.uuid4(), 
        project_id=project_obj.id, 
        name="Test Site", 
        location="POINT(2.3522 48.8566)", 
        permitted_radius_m=500.0
    )
    sync_db_session.add(site_obj)

    sync_db_session.commit()
    
    return {"site": site_obj, "role": role}

@pytest.fixture
def supervisor_user(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+188{str(uuid.uuid4().int)[:7]}",
        role="supervisor",
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()

    emp = Employee(
        id=uuid.uuid4(),
        user_id=user.id,
        employee_code=f"SUP-{str(uuid.uuid4().int)[:5]}",
        mobile_id=user.mobile_id,
        name="Sup Employee",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, emp, token

@pytest.fixture
def administrator_user(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+199{str(uuid.uuid4().int)[:7]}",
        role="administrator",
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, token


@pytest.fixture
def standard_employee(sync_db_session: Session, test_data):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+177{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()

    emp = Employee(
        id=uuid.uuid4(),
        user_id=user.id,
        employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
        mobile_id=user.mobile_id,
        name="Standard Employee",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()
    
    assignment = EmployeeSiteAssignment(
        employee_id=emp.id,
        site_id=test_data["site"].id,
        is_active=True
    )
    sync_db_session.add(assignment)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, emp, token

@pytest.fixture
def another_employee(sync_db_session: Session, test_data):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+166{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()

    emp = Employee(
        id=uuid.uuid4(),
        user_id=user.id,
        employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
        mobile_id=user.mobile_id,
        name="Another Employee",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()
    
    assignment = EmployeeSiteAssignment(
        employee_id=emp.id,
        site_id=test_data["site"].id,
        is_active=True
    )
    sync_db_session.add(assignment)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, emp, token


def test_authentication_required(client: TestClient):
    response = client.get("/api/v1/attendance")
    assert response.status_code in [401, 403] # HTTPBearer missing returns 403, but depending on custom logic 401


def test_check_in_success(client: TestClient, standard_employee):
    user, emp, token = standard_employee
    
    # 48.8567, 2.3523 is near the site's center
    response = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    assert "record_id" in response.json()


def test_check_in_geofence_violation(client: TestClient, another_employee):
    user, emp, token = another_employee
    
    # 51.5074, -0.1278 is London
    response = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 51.5074, "longitude": -0.1278}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "record_id" in data
    assert "warning" in data
    assert data["record"]["is_within_geofence"] is False
    assert data["record"]["status"] == "flagged"


def test_check_out_success(client: TestClient, standard_employee):
    user, emp, token = standard_employee
    
    # First check-in
    response = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    assert response.status_code == 201
    
    # Then check-out
    response_out = client.post(
        "/api/v1/attendance/check-out",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 48.8568, "longitude": 2.3524}
    )
    assert response_out.status_code == 200
    assert response_out.json()["status"] == "success"


def test_check_out_unclosed_session_from_prior_day(client: TestClient, standard_employee, test_data, sync_db_session: Session):
    """An unclosed attendance record from yesterday can be successfully checked out today."""
    from datetime import date, datetime, timezone, timedelta
    user, emp, token = standard_employee
    site = test_data["site"]
    yesterday = date.today() - timedelta(days=1)

    # Insert an unclosed attendance record from yesterday
    att_yesterday = AttendanceRecord(
        id=uuid.uuid4(),
        employee_id=emp.id,
        site_id=site.id,
        date=yesterday,
        session_number=1,
        check_in_time=datetime.now(timezone.utc) - timedelta(days=1),
        check_in_location="POINT(2.3522 48.8566)",
        check_out_time=None,
        status="draft",
        is_within_geofence=True,
    )
    sync_db_session.add(att_yesterday)
    sync_db_session.commit()

    # Check out today
    response_out = client.post(
        "/api/v1/attendance/check-out",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 48.8568, "longitude": 2.3524}
    )
    assert response_out.status_code == 200
    data = response_out.json()
    assert data["status"] == "success"
    assert data["record_id"] == str(att_yesterday.id)

    # Verify check_out_time and working_hours persisted
    sync_db_session.refresh(att_yesterday)
    assert att_yesterday.check_out_time is not None
    assert att_yesterday.working_hours is not None
    assert att_yesterday.working_hours > 0


def test_check_out_without_active_session_returns_404(client: TestClient, standard_employee):
    """Check-out when not checked in returns 404 with 'No active check-in session found'."""
    user, emp, token = standard_employee
    response_out = client.post(
        "/api/v1/attendance/check-out",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 48.8568, "longitude": 2.3524}
    )
    assert response_out.status_code == 404
    assert "No active check-in session found" in response_out.json()["detail"]


def test_list_attendance_self_scoping(client: TestClient, standard_employee, another_employee):
    user1, emp1, token1 = standard_employee
    user2, emp2, token2 = another_employee
    
    # emp1 checks in
    client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token1}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    
    # emp2 checks in
    client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token2}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    
    # emp1 lists attendance
    response = client.get(
        "/api/v1/attendance",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["employee_id"] == str(emp1.id)
    assert data["data"][0]["employee_name"] == "Standard Employee"
    assert data["data"][0]["site_name"] == "Test Site"


def test_supervisor_list_attendance_with_names(client: TestClient, standard_employee, supervisor_user, sync_db_session: Session):
    user1, emp1, token1 = standard_employee
    sup_user, sup_emp, sup_token = supervisor_user

    # Assign emp1 to supervisor
    from app.models.workforce import Employee
    e = sync_db_session.query(Employee).filter(Employee.id == emp1.id).first()
    e.supervisor_id = sup_emp.id
    sync_db_session.commit()

    # Employee checks in
    client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token1}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )

    # Supervisor lists attendance
    response = client.get(
        "/api/v1/attendance",
        headers={"Authorization": f"Bearer {sup_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    matching = [rec for rec in data["data"] if rec["employee_id"] == str(emp1.id)]
    assert len(matching) == 1
    assert matching[0]["employee_name"] == "Standard Employee"
    assert matching[0]["site_name"] == "Test Site"


def test_list_attendance_forbidden_access(client: TestClient, standard_employee, another_employee):
    user1, emp1, token1 = standard_employee
    user2, emp2, token2 = another_employee
    
    # emp1 tries to list attendance for emp2
    response = client.get(
        f"/api/v1/attendance?employee_id={emp2.id}",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert response.status_code == 403


def test_get_attendance_record_self_and_forbidden(client: TestClient, standard_employee, another_employee):
    user1, emp1, token1 = standard_employee
    user2, emp2, token2 = another_employee
    
    # emp1 checks in
    res = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token1}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    record_id = res.json()["record_id"]
    
    # emp1 can get their record
    res1 = client.get(
        f"/api/v1/attendance/{record_id}",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert res1.status_code == 200
    assert res1.json()["id"] == record_id
    
    # emp2 cannot get emp1's record
    res2 = client.get(
        f"/api/v1/attendance/{record_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert res2.status_code == 403


def test_supervisor_override(client: TestClient, standard_employee, supervisor_user, sync_db_session: Session):
    user1, emp1, token1 = standard_employee
    sup_user, sup_emp, sup_token = supervisor_user
    
    # employee gets geofence violation (creates draft? Actually in current logic, 422 doesn't save)
    # The requirement says "Supervisor overrides a geofence exception"
    # To override, there must be a record. Let's create one manually or via check-in.
    res = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token1}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    record_id = res.json()["record_id"]

    # employee tries to override (should be forbidden)
    res_emp = client.post(
        f"/api/v1/attendance/{record_id}/override",
        headers={"Authorization": f"Bearer {token1}"},
        json={"override_reason": "Approved by supervisor because of GPS drift"}
    )
    assert res_emp.status_code == 403

    # unauthorized supervisor overrides (should be forbidden)
    res_sup_unauth = client.post(
        f"/api/v1/attendance/{record_id}/override",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"override_reason": "Approved by supervisor because of GPS drift"}
    )
    assert res_sup_unauth.status_code == 403

    # Setup the authorization relationship
    from app.models.workforce import Employee
    e = sync_db_session.query(Employee).filter(Employee.id == emp1.id).first()
    e.supervisor_id = sup_emp.id
    sync_db_session.commit()

    # authorized supervisor overrides
    res_sup = client.post(
        f"/api/v1/attendance/{record_id}/override",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"override_reason": "Approved by supervisor because of GPS drift"}
    )
    assert res_sup.status_code == 200
    assert res_sup.json()["status"] == "success"

def test_administrator_override(client: TestClient, standard_employee, administrator_user, sync_db_session: Session):
    user1, emp1, token1 = standard_employee
    admin_user, admin_token = administrator_user

    # Employee creates check-in record
    res = client.post(
        "/api/v1/attendance/check-in",
        headers={"Authorization": f"Bearer {token1}"},
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    assert res.status_code == 201
    record_id = res.json()["record_id"]

    # Administrator overrides (bypasses supervisor assignment check)
    res_admin = client.post(
        f"/api/v1/attendance/{record_id}/override",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"override_reason": "Approved by administrator for exceptional maintenance"}
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"
    assert res_admin.json()["record_id"] == record_id

    # Verify override_by was recorded as admin user ID
    record = sync_db_session.query(AttendanceRecord).filter(AttendanceRecord.id == uuid.UUID(record_id)).first()
    assert record.override_by == admin_user.id


def test_not_found_behavior(client: TestClient, standard_employee):
    user, emp, token = standard_employee
    random_id = str(uuid.uuid4())
    res = client.get(
        f"/api/v1/attendance/{random_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 404


def test_multiple_sessions_per_day(client: TestClient, standard_employee, sync_db_session: Session):
    user, emp, token = standard_employee
    headers = {"Authorization": f"Bearer {token}"}

    # Session 1: check-in
    res1 = client.post("/api/v1/attendance/check-in", headers=headers, json={"latitude": 48.8567, "longitude": 2.3523})
    assert res1.status_code == 201
    rec1_id = res1.json()["record_id"]

    # Session 1 check-in again while still open -> 409
    res_conflict = client.post("/api/v1/attendance/check-in", headers=headers, json={"latitude": 48.8567, "longitude": 2.3523})
    assert res_conflict.status_code == 409

    # Session 1: check-out
    res_out1 = client.post("/api/v1/attendance/check-out", headers=headers, json={"latitude": 48.8568, "longitude": 2.3524})
    assert res_out1.status_code == 200

    # Session 2: check-in now permitted
    res2 = client.post("/api/v1/attendance/check-in", headers=headers, json={"latitude": 48.8567, "longitude": 2.3523})
    assert res2.status_code == 201
    rec2_id = res2.json()["record_id"]
    assert rec2_id != rec1_id

    # Verify session numbers in DB
    rec1 = sync_db_session.query(AttendanceRecord).filter(AttendanceRecord.id == rec1_id).first()
    rec2 = sync_db_session.query(AttendanceRecord).filter(AttendanceRecord.id == rec2_id).first()
    assert rec1.session_number == 1
    assert rec2.session_number == 2

    # Session 2: check-out
    res_out2 = client.post("/api/v1/attendance/check-out", headers=headers, json={"latitude": 48.8568, "longitude": 2.3524})
    assert res_out2.status_code == 200

    # Session 3: check-in
    res3 = client.post("/api/v1/attendance/check-in", headers=headers, json={"latitude": 48.8567, "longitude": 2.3523})
    assert res3.status_code == 201
    rec3_id = res3.json()["record_id"]
    rec3 = sync_db_session.query(AttendanceRecord).filter(AttendanceRecord.id == rec3_id).first()
    assert rec3.session_number == 3


def test_check_out_pre_validation_soft_check(client: TestClient, standard_employee, test_data, sync_db_session: Session):
    user, emp, token = standard_employee
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check-in
    res_in = client.post(
        "/api/v1/attendance/check-in",
        headers=headers,
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    assert res_in.status_code == 201
    record_id = uuid.UUID(res_in.json()["record_id"])

    # 2. Check-out with NO daily work entries -> soft warning returned
    res_out = client.post(
        "/api/v1/attendance/check-out",
        headers=headers,
        json={"latitude": 48.8568, "longitude": 2.3524}
    )
    assert res_out.status_code == 200
    assert res_out.json()["status"] == "success"
    assert res_out.json()["requires_confirmation"] is True
    assert "No daily work entries submitted" in res_out.json()["warning"]

    # 3. Check-in for a new session
    res_in2 = client.post(
        "/api/v1/attendance/check-in",
        headers=headers,
        json={"latitude": 48.8567, "longitude": 2.3523}
    )
    assert res_in2.status_code == 201
    record_id2 = uuid.UUID(res_in2.json()["record_id"])

    # Create an activity
    activity = Activity(
        id=uuid.uuid4(),
        name=f"CCTV-{uuid.uuid4().hex[:4]}",
        unit_of_measure="devices",
        approved_rate=150.0,
        category="device",
        is_active=True
    )
    sync_db_session.add(activity)
    sync_db_session.commit()

    # Create a draft daily work entry
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    draft_entry = DailyWorkEntry(
        id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=record_id2,
        employee_id=emp.id,
        site_id=test_data["site"].id,
        activity_id=activity.id,
        work_date=today,
        quantity=5.0,
        uom=activity.unit_of_measure,
        status="draft",
    )
    sync_db_session.add(draft_entry)
    sync_db_session.commit()

    # Check-out with draft entries -> warning returned
    res_out2 = client.post(
        "/api/v1/attendance/check-out",
        headers=headers,
        json={"latitude": 48.8568, "longitude": 2.3524}
    )
    assert res_out2.status_code == 200
    assert res_out2.json()["requires_confirmation"] is True
    assert "draft" in res_out2.json()["warning"]



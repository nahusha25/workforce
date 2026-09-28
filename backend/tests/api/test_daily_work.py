import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Material,
    MaterialTransaction,
    Project,
    Site,
    WorkOrder,
    WorkPhoto,
)
from app.models.system import AuditLog
from app.models.workforce import Employee, Role

VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"A" * 100)


@pytest.fixture
def daily_work_setup(sync_db_session: Session):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # Roles
    role = Role(id=uuid.uuid4(), name=f"Role-{suffix}", description="Worker")
    sync_db_session.add(role)

    # Master Data: Client, Project, Site
    client_obj = Client(id=uuid.uuid4(), name=f"Client-{suffix}")
    sync_db_session.add(client_obj)

    project_obj = Project(id=uuid.uuid4(), client_id=client_obj.id, name=f"Project-{suffix}", status="Active")
    sync_db_session.add(project_obj)

    site_obj = Site(
        id=uuid.uuid4(),
        project_id=project_obj.id,
        name=f"Site-{suffix}",
        location="POINT(2.3522 48.8566)",
        permitted_radius_m=500.0,
    )
    sync_db_session.add(site_obj)

    # Activities
    act_cable = Activity(
        id=uuid.uuid4(),
        name=f"Cable Laying {suffix}",
        unit_of_measure="metres",
        approved_rate=15.50,
        category="cable",
        is_active=True,
    )
    sync_db_session.add(act_cable)

    # Materials
    mat_cat6 = Material(
        id=uuid.uuid4(),
        material_code=f"MAT-C6-{suffix}",
        name=f"Cat6 Cable {suffix}",
        description="High grade Cat6 cable",
        unit_of_measure="box",
        category="cable",
        purchase_approval_limit=1000.00,
        is_active=True,
    )
    sync_db_session.add(mat_cat6)

    # Work Order
    wo = WorkOrder(
        id=uuid.uuid4(),
        order_number=f"WO-{suffix}",
        project_id=project_obj.id,
        site_id=site_obj.id,
        description="Daily Work Order",
        status="open",
        is_active=True,
    )
    sync_db_session.add(wo)
    sync_db_session.commit()

    # Supervisor User & Employee
    sup_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+188{str(uuid.uuid4().int)[:7]}",
        role="supervisor",
        is_active=True,
    )
    sync_db_session.add(sup_user)
    sync_db_session.commit()

    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        employee_code=f"SUP-{suffix}",
        mobile_id=sup_user.mobile_id,
        name="Supervisor User",
        is_active=True,
    )
    sync_db_session.add(sup_emp)
    sync_db_session.commit()

    # Another Supervisor (Unassigned)
    other_sup_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+189{str(uuid.uuid4().int)[:7]}",
        role="supervisor",
        is_active=True,
    )
    sync_db_session.add(other_sup_user)
    sync_db_session.commit()

    other_sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=other_sup_user.id,
        employee_code=f"SUP2-{suffix}",
        mobile_id=other_sup_user.mobile_id,
        name="Other Supervisor",
        is_active=True,
    )
    sync_db_session.add(other_sup_emp)
    sync_db_session.commit()

    # Employee 1 (Assigned to supervisor)
    emp1_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+177{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=True,
    )
    sync_db_session.add(emp1_user)
    sync_db_session.commit()

    emp1 = Employee(
        id=uuid.uuid4(),
        user_id=emp1_user.id,
        employee_code=f"EMP1-{suffix}",
        mobile_id=emp1_user.mobile_id,
        name="Primary Worker",
        supervisor_id=sup_emp.id,
        is_active=True,
    )
    sync_db_session.add(emp1)
    sync_db_session.commit()

    assign1 = EmployeeSiteAssignment(
        employee_id=emp1.id,
        site_id=site_obj.id,
        is_active=True,
    )
    sync_db_session.add(assign1)
    sync_db_session.commit()

    # Employee 2 (Assigned to another supervisor)
    emp2_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+166{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=True,
    )
    sync_db_session.add(emp2_user)
    sync_db_session.commit()

    emp2 = Employee(
        id=uuid.uuid4(),
        user_id=emp2_user.id,
        employee_code=f"EMP2-{suffix}",
        mobile_id=emp2_user.mobile_id,
        name="Secondary Worker",
        supervisor_id=other_sup_emp.id,
        is_active=True,
    )
    sync_db_session.add(emp2)
    sync_db_session.commit()

    assign2 = EmployeeSiteAssignment(
        employee_id=emp2.id,
        site_id=site_obj.id,
        is_active=True,
    )
    sync_db_session.add(assign2)
    sync_db_session.commit()

    # Active Attendance Check-In for Employee 1
    att1 = AttendanceRecord(
        id=uuid.uuid4(),
        employee_id=emp1.id,
        site_id=site_obj.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        check_in_location="POINT(2.3522 48.8566)",
        status="verified",
        is_within_geofence=True,
    )
    sync_db_session.add(att1)
    sync_db_session.commit()

    emp1_token = create_access_token(str(emp1_user.id), emp1_user.role)
    emp2_token = create_access_token(str(emp2_user.id), emp2_user.role)
    sup_token = create_access_token(str(sup_user.id), sup_user.role)
    other_sup_token = create_access_token(str(other_sup_user.id), other_sup_user.role)

    return {
        "site": site_obj,
        "activity": act_cable,
        "material": mat_cat6,
        "work_order": wo,
        "emp1": emp1,
        "emp1_token": emp1_token,
        "emp2": emp2,
        "emp2_token": emp2_token,
        "sup": sup_emp,
        "sup_token": sup_token,
        "other_sup": other_sup_emp,
        "other_sup_token": other_sup_token,
        "att1": att1,
    }


# ==============================================================================
# WRK-001: POST /api/v1/daily-work
# ==============================================================================

def test_wrk_001_create_valid_work_entry(client: TestClient, daily_work_setup):
    """TC-1: Valid work entry creation."""
    token = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    wo = daily_work_setup["work_order"]

    idem_key = str(uuid.uuid4())
    payload = {
        "idempotency_key": idem_key,
        "activity_id": str(act.id),
        "work_order_id": str(wo.id),
        "quantity": 120.5,
        "remarks": "Morning shift cables",
    }
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["idempotency_key"] == idem_key
    assert float(data["quantity"]) == 120.5
    assert data["uom"] == act.unit_of_measure
    assert data["activity_id"] == str(act.id)
    assert data["work_order_id"] == str(wo.id)
    assert data["employee_id"] == str(daily_work_setup["emp1"].id)
    assert data["work_date"] == str(date.today())
    assert data["photos"] == []
    assert data["materials"] == []

    # Duplicate idempotency_key returns 409 Conflict
    dup_resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert dup_resp.status_code == 409


def test_wrk_001_no_active_attendance_returns_422(client: TestClient, daily_work_setup):
    """TC-2: No active attendance returns 422 Unprocessable Entity."""
    token = daily_work_setup["emp2_token"]  # emp2 has no active check-in today
    act = daily_work_setup["activity"]

    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "activity_id": str(act.id),
        "quantity": 2.0,
    }
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422, resp.text
    assert "checked in" in resp.json()["detail"].lower()


def test_wrk_001_unclosed_yesterday_attendance_allows_entry(client: TestClient, daily_work_setup, sync_db_session):
    """An unclosed attendance record from yesterday (check_out_time is None) allows creating an entry via POST."""
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)
    emp2 = daily_work_setup["emp2"]
    token = daily_work_setup["emp2_token"]
    site = daily_work_setup["site"]
    act = daily_work_setup["activity"]

    att_yesterday = AttendanceRecord(
        id=uuid.uuid4(),
        employee_id=emp2.id,
        site_id=site.id,
        date=yesterday,
        session_number=1,
        check_in_time=datetime.now(timezone.utc) - timedelta(days=1),
        check_out_time=None,
        status="verified",
        is_within_geofence=True,
    )
    sync_db_session.add(att_yesterday)
    sync_db_session.commit()

    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "activity_id": str(act.id),
        "quantity": 15.0,
    }
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert float(data["quantity"]) == 15.0
    assert data["status"] == "draft"


def test_wrk_001_invalid_activity_id(client: TestClient, daily_work_setup):
    """TC-3: Invalid activity_id returns 404."""
    token = daily_work_setup["emp1_token"]
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "activity_id": str(uuid.uuid4()),
        "quantity": 1.0,
    }
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404, resp.text
    assert "activity not found" in resp.json()["detail"].lower()


def test_wrk_001_negative_quantities_validation(client: TestClient, daily_work_setup):
    """TC-4: Negative quantities return 422."""
    token = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "activity_id": str(act.id),
        "quantity": -1.0,
    }
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


def test_wrk_001_missing_required_activity_id(client: TestClient, daily_work_setup):
    """TC-5: Missing activity_id returns 422."""
    token = daily_work_setup["emp1_token"]
    payload = {"idempotency_key": str(uuid.uuid4()), "quantity": 5.0}
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422

    # Missing idempotency_key also returns 422
    payload_no_key = {"activity_id": str(daily_work_setup["activity"].id), "quantity": 5.0}
    resp_no_key = client.post("/api/v1/daily-work", json=payload_no_key, headers={"Authorization": f"Bearer {token}"})
    assert resp_no_key.status_code == 422


def test_wrk_001_no_auth(client: TestClient):
    """TC-6: No auth header returns 401/403."""
    resp = client.post("/api/v1/daily-work", json={})
    assert resp.status_code in [401, 403]


def test_wrk_001_non_employee_role(client: TestClient, daily_work_setup):
    """TC-7: Supervisor token rejected with 403 Forbidden."""
    sup_token = daily_work_setup["sup_token"]
    act = daily_work_setup["activity"]
    payload = {"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 1.0}
    resp = client.post("/api/v1/daily-work", json=payload, headers={"Authorization": f"Bearer {sup_token}"})
    assert resp.status_code == 403


# ==============================================================================
# WRK-002: GET /api/v1/daily-work
# ==============================================================================

def test_wrk_002_list_work_entries_employee_sees_own(client: TestClient, daily_work_setup):
    """TC-1: Employee only sees own entries."""
    token1 = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]

    # Create entry for emp1
    client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )

    resp = client.get("/api/v1/daily-work", headers={"Authorization": f"Bearer {token1}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert data["total"] >= 1
    for item in data["data"]:
        assert item["employee_id"] == str(daily_work_setup["emp1"].id)


def test_wrk_002_supervisor_sees_assigned_employee(client: TestClient, daily_work_setup):
    """TC-2: Supervisor sees assigned employee entries."""
    token1 = daily_work_setup["emp1_token"]
    sup_token = daily_work_setup["sup_token"]
    act = daily_work_setup["activity"]
    emp1_id = daily_work_setup["emp1"].id

    client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 4.0},
        headers={"Authorization": f"Bearer {token1}"},
    )

    resp = client.get(f"/api/v1/daily-work?employee_id={emp1_id}", headers={"Authorization": f"Bearer {sup_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_wrk_002_supervisor_unassigned_employee_rejected(client: TestClient, daily_work_setup):
    """TC-3: Supervisor accessing unassigned employee returns 403."""
    other_sup_token = daily_work_setup["other_sup_token"]
    emp1_id = daily_work_setup["emp1"].id

    resp = client.get(
        f"/api/v1/daily-work?employee_id={emp1_id}",
        headers={"Authorization": f"Bearer {other_sup_token}"},
    )
    assert resp.status_code == 403


def test_wrk_002_filter_by_status_and_pagination(client: TestClient, daily_work_setup):
    """TC-4 & TC-5: Filter by status and pagination."""
    token = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]

    client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 1.0},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get("/api/v1/daily-work?status=draft&page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "draft" for item in data["data"])
    assert len(data["data"]) <= 5


def test_wrk_002_list_includes_photos_and_materials(client: TestClient, daily_work_setup, sync_db_session: Session):
    """List endpoint populates photos and materials on returned entries."""
    token = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    site = daily_work_setup["site"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    entry_id = uuid.UUID(create_res.json()["id"])

    photo = WorkPhoto(
        daily_work_entry_id=entry_id,
        image_url="http://test.com/photo.jpg",
        thumbnail_url="http://test.com/thumb.jpg",
        file_size_bytes=1024,
    )
    mat = MaterialTransaction(
        daily_work_entry_id=entry_id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="PVC Pipe 2m",
        quantity=5.0,
        amount=15.0,
        status="draft",
    )
    sync_db_session.add(photo)
    sync_db_session.add(mat)
    sync_db_session.commit()

    resp = client.get("/api/v1/daily-work", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    target = next((e for e in data if e["id"] == str(entry_id)), None)
    assert target is not None
    assert len(target["photos"]) == 1
    assert target["photos"][0]["image_url"] == "http://test.com/photo.jpg"
    assert len(target["materials"]) == 1
    assert target["materials"][0]["item_name"] == "PVC Pipe 2m"


# ==============================================================================
# WRK-003: GET /api/v1/daily-work/{id}
# ==============================================================================

def test_wrk_003_get_detail_and_access_control(client: TestClient, daily_work_setup):
    """TC-1, TC-2, TC-3: Get work entry detail with nested photos and materials."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 3.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert create_res.status_code == 201
    entry_id = create_res.json()["id"]

    # 1. Own entry -> 200
    resp = client.get(f"/api/v1/daily-work/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert resp.status_code == 200
    entry_data = resp.json()
    assert entry_data["id"] == entry_id
    assert "photos" in entry_data
    assert "materials" in entry_data

    # 2. Other employee -> 403
    resp_other = client.get(f"/api/v1/daily-work/{entry_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp_other.status_code == 403

    # 3. Non existent -> 404
    resp_none = client.get(f"/api/v1/daily-work/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token1}"})
    assert resp_none.status_code == 404


# ==============================================================================
# WRK-004: PUT /api/v1/daily-work/{id}
# ==============================================================================

def test_wrk_004_update_work_entry(client: TestClient, daily_work_setup):
    """TC-1 to TC-5: Update work entry, status restrictions, validation."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 3.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # 1. Valid update on draft -> 200
    update_res = client.put(
        f"/api/v1/daily-work/{entry_id}",
        json={"quantity": 10.0, "remarks": "Updated afternoon"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert update_res.status_code == 200
    assert float(update_res.json()["quantity"]) == 10.0
    assert update_res.json()["remarks"] == "Updated afternoon"

    # 2. Negative quantity -> 422
    neg_res = client.put(
        f"/api/v1/daily-work/{entry_id}",
        json={"quantity": -5.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert neg_res.status_code == 422

    # 3. Other employee cannot update -> 403
    other_res = client.put(
        f"/api/v1/daily-work/{entry_id}",
        json={"quantity": 8.0},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert other_res.status_code == 403


# ==============================================================================
# WRK-005: POST /api/v1/daily-work/{id}/submit
# ==============================================================================

def test_wrk_005_submit_work_entry_and_conflict(client: TestClient, daily_work_setup, sync_db_session: Session):
    """TC-1 to TC-4: Submit work entry, conflict when already submitted, audit log."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 5.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # 1. Other employee cannot submit -> 403
    other_res = client.post(f"/api/v1/daily-work/{entry_id}/submit", headers={"Authorization": f"Bearer {token2}"})
    assert other_res.status_code == 403

    # 2. Valid submit -> 200
    submit_res = client.post(f"/api/v1/daily-work/{entry_id}/submit", headers={"Authorization": f"Bearer {token1}"})
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "submitted"

    # 3. Already submitted -> 409 Conflict
    re_submit = client.post(f"/api/v1/daily-work/{entry_id}/submit", headers={"Authorization": f"Bearer {token1}"})
    assert re_submit.status_code == 409

    # 4. WRK-004 on submitted entry -> 409 Conflict
    edit_submitted = client.put(
        f"/api/v1/daily-work/{entry_id}",
        json={"quantity": 12.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert edit_submitted.status_code == 409

    # 4b. Submitting an entry with quantity <= 0 returns 400 Bad Request
    zero_entry = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 0.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert zero_entry.status_code == 201
    zero_id = zero_entry.json()["id"]
    zero_submit = client.post(f"/api/v1/daily-work/{zero_id}/submit", headers={"Authorization": f"Bearer {token1}"})
    assert zero_submit.status_code == 400
    assert "greater than zero" in zero_submit.json()["detail"].lower()

    # 5. Check audit log
    audit = sync_db_session.query(AuditLog).filter(
        AuditLog.entity_id == uuid.UUID(entry_id),
        AuditLog.action == "submit",
    ).first()
    assert audit is not None


# ==============================================================================
# WRK-006: POST /api/v1/daily-work/{id}/photos
# ==============================================================================

def test_wrk_006_upload_photo(client: TestClient, daily_work_setup):
    """TC-1 to TC-5: Upload work photo, file validation, status restrictions, RBAC."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # 1. Valid JPEG -> 201
    photo_file = io.BytesIO(VALID_JPEG_BYTES)
    res_upload = client.post(
        f"/api/v1/daily-work/{entry_id}/photos",
        files={"file": ("photo.jpg", photo_file, "image/jpeg")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res_upload.status_code == 201, res_upload.text
    photo_data = res_upload.json()
    assert "image_url" in photo_data
    photo_id = photo_data["id"]

    # 2. List photos -> 200
    res_list = client.get(f"/api/v1/daily-work/{entry_id}/photos", headers={"Authorization": f"Bearer {token1}"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. Invalid file type (PDF/text) -> 422
    bad_file = io.BytesIO(b"%PDF-1.4 fake pdf data")
    res_bad = client.post(
        f"/api/v1/daily-work/{entry_id}/photos",
        files={"file": ("doc.pdf", bad_file, "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res_bad.status_code == 422

    # 4. Other employee upload -> 403
    photo_file2 = io.BytesIO(VALID_JPEG_BYTES)
    res_other = client.post(
        f"/api/v1/daily-work/{entry_id}/photos",
        files={"file": ("photo2.jpg", photo_file2, "image/jpeg")},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res_other.status_code == 403

    # 5. Delete photo -> 200
    del_res = client.delete(f"/api/v1/daily-work/photos/{photo_id}", headers={"Authorization": f"Bearer {token1}"})
    assert del_res.status_code == 200


# ==============================================================================
# WRK-007: POST /api/v1/daily-work/{id}/materials
# ==============================================================================

def test_wrk_007_create_material_transaction(client: TestClient, daily_work_setup):
    """TC-1 to TC-7: Create material transaction, high-value calculation, validation."""
    token1 = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]  # limit is 1000.00

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # 1. Normal purchase (amount <= limit) -> is_high_value = False
    norm_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": 2,
            "amount": 500.0,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert norm_res.status_code == 201, norm_res.text
    assert norm_res.json()["is_high_value"] is False

    # 2. High-value purchase (amount > limit) -> is_high_value = True
    high_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": 5,
            "amount": 2500.0,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert high_res.status_code == 201
    assert high_res.json()["is_high_value"] is True

    # 3. Zero/negative quantity -> 422
    zero_qty = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={"item_name": "Test", "transaction_type": "purchased", "quantity": 0, "amount": 10},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert zero_qty.status_code == 422

    # 4. Negative amount -> 422
    neg_amt = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={"item_name": "Test", "transaction_type": "purchased", "quantity": 1, "amount": -10},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert neg_amt.status_code == 422

    # 5. Invalid transaction_type -> 422
    bad_type = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={"item_name": "Test", "transaction_type": "returned", "quantity": 1, "amount": 10},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert bad_type.status_code == 422


# ==============================================================================
# WRK-008: PUT /api/v1/daily-work/{id}/materials/{mid}
# ==============================================================================

def test_wrk_008_update_material_transaction(client: TestClient, daily_work_setup):
    """WRK-008: Update material transaction and recompute is_high_value."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]  # limit is 1000.00

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # Create low value
    mat_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": 1,
            "amount": 200.0,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    mid = mat_res.json()["id"]
    assert mat_res.json()["is_high_value"] is False

    # 1. Update amount to exceed limit -> recomputes is_high_value = True
    upd_res = client.put(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}",
        json={"amount": 1500.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["is_high_value"] is True
    assert float(upd_res.json()["amount"]) == 1500.0

    # 2. Other employee cannot edit -> 403
    other_res = client.put(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}",
        json={"amount": 300.0},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert other_res.status_code == 403

    # 3. Non-existent material id -> 404
    non_res = client.put(
        f"/api/v1/daily-work/{entry_id}/materials/{uuid.uuid4()}",
        json={"amount": 300.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert non_res.status_code == 404


# ==============================================================================
# WRK-009: POST /api/v1/daily-work/{id}/materials/{mid}/bill
# ==============================================================================

def test_wrk_009_upload_bill_image(client: TestClient, daily_work_setup):
    """WRK-009: Upload bill image for material purchase."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    mat_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": 1,
            "amount": 500.0,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    mid = mat_res.json()["id"]

    # 1. Valid bill upload -> 200
    bill_file = io.BytesIO(VALID_JPEG_BYTES)
    bill_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}/bill",
        files={"file": ("receipt.jpg", bill_file, "image/jpeg")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert bill_res.status_code == 200, bill_res.text
    assert bill_res.json()["id"] == mid
    assert "bill_image_url" in bill_res.json()

    # 2. Invalid file type (PDF/text) -> 422
    bad_bill = io.BytesIO(b"not an image text content")
    bad_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}/bill",
        files={"file": ("invoice.txt", bad_bill, "text/plain")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert bad_res.status_code == 422

    # 3. Other employee upload -> 403
    bill_file2 = io.BytesIO(VALID_JPEG_BYTES)
    other_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}/bill",
        files={"file": ("receipt2.jpg", bill_file2, "image/jpeg")},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert other_res.status_code == 403

    # 4. Add/upload to submitted entry -> 409
    submit_res = client.post(f"/api/v1/daily-work/{entry_id}/submit", headers={"Authorization": f"Bearer {token1}"})
    assert submit_res.status_code == 200

    locked_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={"item_name": "Extra", "transaction_type": "purchased", "quantity": 1, "amount": 10},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert locked_res.status_code == 409

    locked_bill = client.post(
        f"/api/v1/daily-work/{entry_id}/materials/{mid}/bill",
        files={"file": ("receipt3.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert locked_bill.status_code == 409


# ==============================================================================
# WRK-008 & WRK-011: DELETE Endpoints (Photos & Material Transactions)
# ==============================================================================

def test_wrk_delete_photo_and_material_endpoints(client: TestClient, daily_work_setup):
    """Test WRK-008 (DELETE /daily-work/photos/{id}) & WRK-011 (DELETE /daily-work/materials/{id})."""
    token1 = daily_work_setup["emp1_token"]
    token2 = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 2.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # 1. Upload photo and delete it
    photo_file = io.BytesIO(VALID_JPEG_BYTES)
    photo_res = client.post(
        f"/api/v1/daily-work/{entry_id}/photos",
        files={"file": ("test.jpg", photo_file, "image/jpeg")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    photo_id = photo_res.json()["id"]

    # Other employee cannot delete photo -> 403
    del_other_photo = client.delete(
        f"/api/v1/daily-work/photos/{photo_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert del_other_photo.status_code == 403

    # Delete non-existent photo -> 404
    del_non_photo = client.delete(
        f"/api/v1/daily-work/photos/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert del_non_photo.status_code == 404

    # Owning employee deletes photo -> 200
    del_photo = client.delete(
        f"/api/v1/daily-work/photos/{photo_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert del_photo.status_code == 200
    assert del_photo.json()["status"] == "success"

    # Photo is no longer in entry detail
    detail_res = client.get(f"/api/v1/daily-work/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert len(detail_res.json()["photos"]) == 0

    # 2. Create material transaction and delete it
    mat_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "consumed",
            "item_name": mat.name,
            "quantity": 10,
            "amount": 0.0,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    mat_id = mat_res.json()["id"]

    # Other employee cannot delete material transaction -> 403
    del_other_mat = client.delete(
        f"/api/v1/daily-work/materials/{mat_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert del_other_mat.status_code == 403

    # Delete non-existent material transaction -> 404
    del_non_mat = client.delete(
        f"/api/v1/daily-work/materials/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert del_non_mat.status_code == 404

    # Owning employee deletes material transaction -> 200
    del_mat = client.delete(
        f"/api/v1/daily-work/materials/{mat_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert del_mat.status_code == 200
    assert del_mat.json()["status"] == "success"

    # Material is no longer in entry detail
    detail_res2 = client.get(f"/api/v1/daily-work/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert len(detail_res2.json()["materials"]) == 0


# ==============================================================================
# Additional Tests: Decimal Precision & Purchased Transaction Without Bill
# ==============================================================================

def test_material_decimal_precision_roundtrip(client: TestClient, daily_work_setup):
    """Confirm exact Decimal precision round-trip (e.g. amount=1234.56 surviving API response)."""
    token1 = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 1.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # Send amount=1234.56 and quantity=15.75
    post_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": 15.75,
            "amount": 1234.56,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert post_res.status_code == 201, post_res.text
    tx_data = post_res.json()

    # Exact Decimal precision checks on creation response
    assert Decimal(str(tx_data["amount"])) == Decimal("1234.56")
    assert Decimal(str(tx_data["quantity"])) == Decimal("15.75")

    # Exact Decimal precision checks on entry detail GET
    detail_res = client.get(f"/api/v1/daily-work/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert detail_res.status_code == 200
    mats = detail_res.json()["materials"]
    assert len(mats) == 1
    assert Decimal(str(mats[0]["amount"])) == Decimal("1234.56")
    assert Decimal(str(mats[0]["quantity"])) == Decimal("15.75")

    # Exact Decimal precision checks on materials list GET
    list_res = client.get(f"/api/v1/daily-work/{entry_id}/materials", headers={"Authorization": f"Bearer {token1}"})
    assert list_res.status_code == 200
    list_mats = list_res.json()
    assert len(list_mats) == 1
    assert Decimal(str(list_mats[0]["amount"])) == Decimal("1234.56")


def test_purchased_transaction_without_bill_file(client: TestClient, daily_work_setup):
    """Confirm purchased material transaction without a bill file defaults correctly."""
    token1 = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 1.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # Purchased uncataloged item without bill file
    post_res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        json={
            "transaction_type": "purchased",
            "item_name": "Uncataloged Safety Harness",
            "quantity": 1,
            "amount": 150.00,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert post_res.status_code == 201, post_res.text
    tx_data = post_res.json()

    # Confirm bill_image_url is None
    assert tx_data["bill_image_url"] is None
    # Confirm uncataloged purchase defaults to is_high_value = True
    assert tx_data["is_high_value"] is True
    # Confirm status is draft
    assert tx_data["status"] == "draft"


def test_material_combined_multipart_with_bill_upload(client: TestClient, daily_work_setup):
    """Test the single combined multipart endpoint matching BE-019's create_material_transaction."""
    token1 = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]

    create_res = client.post(
        "/api/v1/daily-work",
        json={"idempotency_key": str(uuid.uuid4()), "activity_id": str(act.id), "quantity": 1.0},
        headers={"Authorization": f"Bearer {token1}"},
    )
    entry_id = create_res.json()["id"]

    # Send multipart form data with both metadata and bill_file
    bill_bytes = io.BytesIO(VALID_JPEG_BYTES)
    res = client.post(
        f"/api/v1/daily-work/{entry_id}/materials",
        data={
            "material_id": str(mat.id),
            "transaction_type": "purchased",
            "item_name": mat.name,
            "quantity": "2",
            "amount": "250.00",
        },
        files={"bill_file": ("invoice.jpg", bill_bytes, "image/jpeg")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["item_name"] == mat.name
    assert Decimal(str(data["amount"])) == Decimal("250.00")
    assert data["bill_image_url"] is not None
    assert "materials/" in data["bill_image_url"]


# ==============================================================================
# Daily Work Reference Data Endpoints: Activities & Work Orders
# ==============================================================================

def test_employee_can_list_activities_and_work_orders(client: TestClient, daily_work_setup):
    """Confirm an employee-role token gets 200 from both reference endpoints (not 403)."""
    token = daily_work_setup["emp1_token"]
    act = daily_work_setup["activity"]
    wo = daily_work_setup["work_order"]

    # 1. Activities
    resp_act = client.get("/api/v1/daily-work/activities", headers={"Authorization": f"Bearer {token}"})
    assert resp_act.status_code == 200, resp_act.text
    activities = resp_act.json()
    assert isinstance(activities, list)
    act_ids = [a["id"] for a in activities]
    assert str(act.id) in act_ids

    # 2. Work Orders
    resp_wo = client.get("/api/v1/daily-work/work-orders", headers={"Authorization": f"Bearer {token}"})
    assert resp_wo.status_code == 200, resp_wo.text
    work_orders = resp_wo.json()
    assert isinstance(work_orders, list)
    wo_ids = [w["id"] for w in work_orders]
    assert str(wo.id) in wo_ids


def test_reference_endpoints_only_return_active_records(client: TestClient, daily_work_setup, sync_db_session: Session):
    """Confirm both endpoints only return is_active=true records."""
    token = daily_work_setup["emp1_token"]
    suffix = uuid.uuid4().hex[:8]

    # Create an inactive activity and an active activity
    inactive_act = Activity(
        id=uuid.uuid4(),
        name=f"Deactivated Activity {suffix}",
        unit_of_measure="metres",
        approved_rate=10.0,
        category="cable",
        is_active=False,
    )
    active_act = Activity(
        id=uuid.uuid4(),
        name=f"Active Activity {suffix}",
        unit_of_measure="metres",
        approved_rate=20.0,
        category="cable",
        is_active=True,
    )
    sync_db_session.add(inactive_act)
    sync_db_session.add(active_act)

    # Create an inactive work order and an active work order
    site = daily_work_setup["site"]
    inactive_wo = WorkOrder(
        id=uuid.uuid4(),
        order_number=f"WO-INACT-{suffix}",
        project_id=site.project_id,
        site_id=site.id,
        description="Deactivated WO",
        status="closed",
        is_active=False,
    )
    active_wo = WorkOrder(
        id=uuid.uuid4(),
        order_number=f"WO-ACT-{suffix}",
        project_id=site.project_id,
        site_id=site.id,
        description="Active WO",
        status="open",
        is_active=True,
    )
    sync_db_session.add(inactive_wo)
    sync_db_session.add(active_wo)
    sync_db_session.commit()

    # Query activities
    resp_act = client.get("/api/v1/daily-work/activities", headers={"Authorization": f"Bearer {token}"})
    assert resp_act.status_code == 200
    activities = resp_act.json()
    act_ids = [a["id"] for a in activities]
    assert str(active_act.id) in act_ids
    assert str(inactive_act.id) not in act_ids
    assert all(a["is_active"] is True for a in activities)

    # Query work orders
    resp_wo = client.get("/api/v1/daily-work/work-orders", headers={"Authorization": f"Bearer {token}"})
    assert resp_wo.status_code == 200
    work_orders = resp_wo.json()
    wo_ids = [w["id"] for w in work_orders]
    assert str(active_wo.id) in wo_ids
    assert str(inactive_wo.id) not in wo_ids
    assert all(w["is_active"] is True for w in work_orders)


def test_reference_endpoints_unauthenticated_returns_401(client: TestClient):
    """Confirm unauthenticated requests get 401 Unauthorized."""
    resp_act = client.get("/api/v1/daily-work/activities")
    assert resp_act.status_code == 401

    resp_wo = client.get("/api/v1/daily-work/work-orders")
    assert resp_wo.status_code == 401


def test_access_control_idor_cross_employee_photo_and_material_returns_403(
    client: TestClient,
    daily_work_setup: dict,
):
    """SEC-003 Verification: Prove that Employee B cannot access or delete

    Employee A's uploaded photos or material transactions via IDOR / URL manipulation.
    """
    emp1_token = daily_work_setup["emp1_token"]
    emp2_token = daily_work_setup["emp2_token"]
    act = daily_work_setup["activity"]
    mat = daily_work_setup["material"]

    # 1. Employee A creates their own daily work entry
    res_entry = client.post(
        "/api/v1/daily-work",
        headers={"Authorization": f"Bearer {emp1_token}"},
        json={
            "activity_id": str(act.id),
            "quantity": 25.0,
            "uom": act.unit_of_measure,
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Employee A work entry",
        },
    )
    assert res_entry.status_code == 201
    entry_a_id = res_entry.json()["id"]

    # 2. Employee A uploads a photo to their own entry
    res_photo = client.post(
        f"/api/v1/daily-work/{entry_a_id}/photos",
        headers={"Authorization": f"Bearer {emp1_token}"},
        files={"file": ("site_photo.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
    )
    assert res_photo.status_code == 201
    photo_a_id = res_photo.json()["id"]

    # 3. Employee B attempts to GET photo list for Employee A's entry -> 403 Forbidden
    res_get_photos = client.get(
        f"/api/v1/daily-work/{entry_a_id}/photos",
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert res_get_photos.status_code == 403
    assert "Cannot access photos for another employee's work entry" in res_get_photos.json()["detail"]

    # 4. Employee B attempts to DELETE Employee A's photo by ID -> 403 Forbidden
    res_del_photo = client.delete(
        f"/api/v1/daily-work/photos/{photo_a_id}",
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert res_del_photo.status_code == 403
    assert "Cannot delete photo uploaded by another employee" in res_del_photo.json()["detail"]

    # 5. Employee A creates a material transaction on their own entry
    res_mat = client.post(
        f"/api/v1/daily-work/{entry_a_id}/materials",
        headers={"Authorization": f"Bearer {emp1_token}"},
        json={
            "material_id": str(mat.id),
            "transaction_type": "consumed",
            "item_name": "Cat6 Cable Box",
            "quantity": 3.0,
            "amount": 150.0,
        },
    )
    assert res_mat.status_code == 201
    tx_a_id = res_mat.json()["id"]

    # 6. Employee B attempts to GET materials list for Employee A's entry -> 403 Forbidden
    res_get_mats = client.get(
        f"/api/v1/daily-work/{entry_a_id}/materials",
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert res_get_mats.status_code == 403
    assert "Cannot access material transactions for another employee's work entry" in res_get_mats.json()["detail"]

    # 7. Employee B attempts to DELETE Employee A's material transaction by ID -> 403 Forbidden
    res_del_mat = client.delete(
        f"/api/v1/daily-work/materials/{tx_a_id}",
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert res_del_mat.status_code == 403
    assert "Cannot delete material transaction recorded by another employee" in res_del_mat.json()["detail"]

    # 8. Employee B attempts to POST a photo into Employee A's entry -> 403 Forbidden
    res_cross_upload = client.post(
        f"/api/v1/daily-work/{entry_a_id}/photos",
        headers={"Authorization": f"Bearer {emp2_token}"},
        files={"file": ("injected.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
    )
    assert res_cross_upload.status_code == 403
    assert "Cannot upload photo for another employee's work entry" in res_cross_upload.json()["detail"]

    # 9. Employee B attempts to POST a material transaction into Employee A's entry -> 403 Forbidden
    res_cross_mat = client.post(
        f"/api/v1/daily-work/{entry_a_id}/materials",
        headers={"Authorization": f"Bearer {emp2_token}"},
        json={
            "transaction_type": "consumed",
            "item_name": "Injected Consumable",
            "quantity": 1.0,
            "amount": 10.0,
        },
    )
    assert res_cross_mat.status_code == 403
    assert "Cannot add material to another employee's work entry" in res_cross_mat.json()["detail"]




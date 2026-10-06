from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

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
    ExceptionFlag,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
from app.models.workforce import Employee, Role


@pytest.fixture
def verification_setup(sync_db_session: Session):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # Roles
    worker_role = Role(id=uuid.uuid4(), name=f"Worker-{suffix}")
    sup_role = Role(id=uuid.uuid4(), name=f"Supervisor-{suffix}")
    sync_db_session.add_all([worker_role, sup_role])

    # Users
    worker_user = User(id=uuid.uuid4(), mobile_id=f"W-{suffix}", role="employee", is_active=True)
    sup_user = User(id=uuid.uuid4(), mobile_id=f"S-{suffix}", role="supervisor", is_active=True)
    other_sup_user = User(id=uuid.uuid4(), mobile_id=f"OS-{suffix}", role="supervisor", is_active=True)
    admin_user = User(id=uuid.uuid4(), mobile_id=f"A-{suffix}", role="administrator", is_active=True)
    sync_db_session.add_all([worker_user, sup_user, other_sup_user, admin_user])
    sync_db_session.commit()

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
        name="Field Worker",
        supervisor_id=sup_emp.id,
        is_active=True,
    )
    sync_db_session.add_all([sup_emp, other_sup_emp, worker_emp])
    sync_db_session.commit()

    # Client, Project, Site
    client = Client(name=f"Client-{suffix}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.commit()

    project = Project(client_id=client.id, name=f"Project-{suffix}", status="active")
    sync_db_session.add(project)
    sync_db_session.commit()

    site = Site(
        project_id=project.id,
        name=f"Site-{suffix}",
        supervisor_id=sup_emp.id,
        permitted_radius_m=500.0,
        location="POINT(2.3522 48.8566)",
    )
    sync_db_session.add(site)
    sync_db_session.commit()

    assignment = EmployeeSiteAssignment(
        employee_id=worker_emp.id,
        site_id=site.id,
        is_active=True,
    )
    sync_db_session.add(assignment)

    activity = Activity(
        name=f"Fiber Splicing {suffix}",
        unit_of_measure="joint",
        approved_rate=50.0,
        category="cable",
    )
    material = Material(
        material_code=f"MAT-{suffix}",
        name=f"Fiber Splice Tray {suffix}",
        unit_of_measure="piece",
        category="cable",
        purchase_approval_limit=500.0,
    )
    sync_db_session.add_all([activity, material])
    sync_db_session.commit()

    work_order = WorkOrder(
        order_number=f"WO-{suffix}",
        project_id=project.id,
        site_id=site.id,
        status="open",
        is_active=True,
    )
    sync_db_session.add(work_order)
    sync_db_session.commit()

    # Attendance
    att = AttendanceRecord(
        employee_id=worker_emp.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
        check_out_time=datetime.now(timezone.utc),
        working_hours=8.0,
        is_within_geofence=True,
        status="draft",
    )
    sync_db_session.add(att)
    sync_db_session.commit()

    # Daily Work Entry
    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=att.id,
        employee_id=worker_emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=work_order.id,
        work_date=today,
        quantity=10.0,
        uom=activity.unit_of_measure,
        status="submitted",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()

    # Photo
    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="/uploads/photos/fiber.jpg",
        thumbnail_url="/uploads/photos/fiber_thumb.jpg",
        file_size_bytes=2048,
    )
    sync_db_session.add(photo)

    # Material Transactions
    mat_cons = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Fiber Tray",
        quantity=2.0,
        amount=200.0,
        is_high_value=False,
        status="submitted",
    )
    mat_purch = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Precision Cleaver",
        quantity=1.0,
        amount=1500.0,  # > 500 limit
        is_high_value=True,
        bill_image_url="/uploads/bills/cleaver.jpg",
        status="submitted",
    )
    sync_db_session.add_all([mat_cons, mat_purch])
    sync_db_session.commit()

    # JWT Tokens
    worker_token = create_access_token(str(worker_user.id), worker_user.role)
    sup_token = create_access_token(str(sup_user.id), sup_user.role)
    other_sup_token = create_access_token(str(other_sup_user.id), other_sup_user.role)
    admin_token = create_access_token(str(admin_user.id), admin_user.role)

    return {
        "today": today,
        "worker_user": worker_user,
        "worker_emp": worker_emp,
        "sup_user": sup_user,
        "sup_emp": sup_emp,
        "other_sup_user": other_sup_user,
        "other_sup_emp": other_sup_emp,
        "admin_user": admin_user,
        "site": site,
        "attendance": att,
        "dwe": dwe,
        "mat_cons": mat_cons,
        "mat_purch": mat_purch,
        "worker_token": worker_token,
        "sup_token": sup_token,
        "other_sup_token": other_sup_token,
        "admin_token": admin_token,
    }


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------------------------
# RBAC Tests
# -------------------------------------------------------------------------

def test_unauthenticated_request_returns_401(client: TestClient, verification_setup):
    res = client.get("/api/v1/verification/summary?date=2026-09-26")
    assert res.status_code == 401


def test_worker_role_blocked_with_403(client: TestClient, verification_setup):
    env = verification_setup
    res = client.get(
        f"/api/v1/verification/summary?date={env['today'].isoformat()}",
        headers=auth_header(env["worker_token"]),
    )
    assert res.status_code == 403


def test_cross_supervisor_unassigned_blocked_with_404_sec_004_a(client: TestClient, verification_setup):
    """SEC-004-A: VER-002 returns 404 with generic 'Employee record not found'
    both when an employee is outside the supervisor's scope and when nonexistent,
    preventing valid employee ID enumeration.
    """
    env = verification_setup

    # 1. Existing employee outside supervisor's scope -> 404
    res_scope = client.get(
        f"/api/v1/verification/summary/{env['worker_emp'].id}?date={env['today'].isoformat()}",
        headers=auth_header(env["other_sup_token"]),
    )
    assert res_scope.status_code == 404
    assert res_scope.json()["detail"] == "Employee record not found"

    # 2. Non-existent employee UUID -> 404 with identical message
    res_nonexistent = client.get(
        f"/api/v1/verification/summary/{uuid.uuid4()}?date={env['today'].isoformat()}",
        headers=auth_header(env["other_sup_token"]),
    )
    assert res_nonexistent.status_code == 404
    assert res_nonexistent.json()["detail"] == "Employee record not found"

    # 3. Indistinguishable responses
    assert res_scope.status_code == res_nonexistent.status_code
    assert res_scope.json() == res_nonexistent.json()


# -------------------------------------------------------------------------
# VER-001: EOD Verification Summary
# -------------------------------------------------------------------------

def test_ver_001_get_verification_summary_success(client: TestClient, verification_setup):
    env = verification_setup
    res = client.get(
        f"/api/v1/verification/summary?date={env['today'].isoformat()}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date"] == env["today"].isoformat()
    assert data["total_employees"] >= 1
    assert data["pending_verification_count"] >= 1

    item = next(i for i in data["items"] if i["employee_id"] == str(env["worker_emp"].id))
    assert item["employee_name"] == "Field Worker"
    assert item["work_entry_count"] == 1
    assert item["photo_count"] == 1
    assert item["material_count"] == 2
    assert "high_value_material" in item["exception_flags"]
    assert item["has_pending_verification"] is True


def test_ver_001_get_summary_with_site_filter(client: TestClient, verification_setup):
    env = verification_setup
    res = client.get(
        f"/api/v1/verification/summary?date={env['today'].isoformat()}&site_id={env['site'].id}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["site_id"] == str(env["site"].id)


# -------------------------------------------------------------------------
# VER-002: Employee Day Detail
# -------------------------------------------------------------------------

def test_ver_002_get_employee_detail_success(client: TestClient, verification_setup):
    env = verification_setup
    res = client.get(
        f"/api/v1/verification/summary/{env['worker_emp'].id}?date={env['today'].isoformat()}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == str(env["worker_emp"].id)
    assert data["employee_name"] == "Field Worker"
    assert data["attendance"]["working_hours"] == 8.0
    assert len(data["work_entries"]) == 1

    we = data["work_entries"][0]
    assert we["id"] == str(env["dwe"].id)
    assert len(we["photos"]) == 1
    assert len(we["materials"]) == 2

    hv_mat = next(m for m in we["materials"] if m["is_high_value"])
    assert hv_mat["item_name"] == "Precision Cleaver"
    assert float(hv_mat["amount"]) == 1500.0


def test_ver_002_get_detail_non_existent_employee_returns_404(client: TestClient, verification_setup):
    env = verification_setup
    res = client.get(
        f"/api/v1/verification/summary/{uuid.uuid4()}?date={env['today'].isoformat()}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 404


# -------------------------------------------------------------------------
# VER-003: Approve
# -------------------------------------------------------------------------

def test_ver_003_approve_attendance_returns_verified_status(client: TestClient, verification_setup):
    env = verification_setup
    att = env["attendance"]
    key = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/verification/{att.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "attendance",
            "idempotency_key": key,
            "remarks": "Attendance confirmed",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_id"] == str(att.id)
    assert data["action"] == "approved"
    assert data["status"] == "verified"
    assert data["target_status"] == "verified"
    assert data["is_replay"] is False
    assert data["verification_record_id"] is not None


def test_ver_003_approve_daily_work_entry_success(client: TestClient, verification_setup):
    env = verification_setup
    dwe = env["dwe"]
    key = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": key,
            "remarks": "Joints verified and OTDR tested",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["is_replay"] is False


def test_ver_003_approve_material_transaction_independently(client: TestClient, verification_setup):
    env = verification_setup
    mat = env["mat_cons"]
    key = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/verification/{mat.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "material",
            "idempotency_key": key,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["is_replay"] is False


def test_ver_003_idempotency_replay_on_duplicate_key_returns_200_with_is_replay(client: TestClient, verification_setup):
    env = verification_setup
    dwe = env["dwe"]
    key = f"IDEMP-API-{uuid.uuid4()}"

    # First attempt
    res1 = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": key,
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_replay"] is False

    # Second attempt (exact same key)
    res2 = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": key,
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_replay"] is True
    assert data2["id"] == data1["id"]
    assert data2["status"] == "approved"


# -------------------------------------------------------------------------
# VER-004: Reject
# -------------------------------------------------------------------------

def test_ver_004_reject_material_with_mandatory_remarks_success(client: TestClient, verification_setup):
    env = verification_setup
    mat = env["mat_purch"]
    key = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/verification/{mat.id}/reject",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "material",
            "idempotency_key": key,
            "remarks": "Tool price exceeds local retail market benchmarks",  # >= 10 chars
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"
    assert data["is_replay"] is False


def test_ver_004_reject_missing_or_short_remarks_returns_422(client: TestClient, verification_setup):
    env = verification_setup
    mat = env["mat_purch"]

    # Missing remarks
    res1 = client.post(
        f"/api/v1/verification/{mat.id}/reject",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "material",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert res1.status_code == 422

    # Remarks < 10 characters
    res2 = client.post(
        f"/api/v1/verification/{mat.id}/reject",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "material",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Too short",
        },
    )
    assert res2.status_code == 422


# -------------------------------------------------------------------------
# VER-005: Return for Correction & Admin Reopen
# -------------------------------------------------------------------------

def test_ver_005_return_daily_work_entry_success(client: TestClient, verification_setup):
    env = verification_setup
    dwe = env["dwe"]
    key = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": key,
            "remarks": "Please provide spliced strand loss measurement readings",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "correction_required"


def test_ver_005_admin_can_reopen_approved_record(client: TestClient, verification_setup):
    env = verification_setup
    dwe = env["dwe"]

    # 1. Supervisor approves
    client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
        },
    )

    # 2. Regular supervisor attempts to reopen approved record -> 403 Forbidden
    res_sup = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Supervisor trying to reopen approved record",
        },
    )
    assert res_sup.status_code == 403

    # 3. Administrator reopens approved record -> 200 OK
    res_admin = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(env["admin_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Authorized admin reopen following site discrepancy report",
        },
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "correction_required"


# -------------------------------------------------------------------------
# Batch 4B: VER-002 history field in API response
# -------------------------------------------------------------------------

def test_ver_002_history_field_present_and_populated_after_approve(client: TestClient, verification_setup):
    """VER-002 returns a populated history list on work_entries after an approve action."""
    env = verification_setup
    dwe = env["dwe"]

    # Approve the daily work entry
    client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
        },
    )

    # Fetch VER-002
    res = client.get(
        f"/api/v1/verification/summary/{env['worker_emp'].id}?date={env['today'].isoformat()}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 200
    data = res.json()

    we = next(e for e in data["work_entries"] if e["id"] == str(dwe.id))

    # history list present and has exactly one event
    assert "history" in we
    assert len(we["history"]) == 1

    event = we["history"][0]
    assert event["action"] == "approved"
    assert event["remarks"] is None
    # verified_by_name resolves to supervisor's employee name
    assert event["verified_by_name"] == "Assigned Supervisor"
    # verified_by is the user UUID (not the mobile_id)
    assert event["verified_by"] == str(env["sup_user"].id)
    # verified_at is a valid ISO datetime
    assert "verified_at" in event
    assert "id" in event

    # Existing fields preserved unchanged
    assert we["verification_action"] == "approved"
    assert we["verification_record_id"] is not None


def test_ver_002_history_empty_before_any_verification(client: TestClient, verification_setup):
    """VER-002 returns empty history lists when no verification has been performed."""
    env = verification_setup

    res = client.get(
        f"/api/v1/verification/summary/{env['worker_emp'].id}?date={env['today'].isoformat()}",
        headers=auth_header(env["sup_token"]),
    )
    assert res.status_code == 200
    data = res.json()

    # Attendance history
    if data.get("attendance"):
        assert data["attendance"]["history"] == []

    # All work entries and their materials have empty history
    for we in data["work_entries"]:
        assert we["history"] == []
        for mat in we["materials"]:
            assert mat["history"] == []


# =========================================================================
# SEC-004: Security Audit on Verification Endpoints (IDOR & Role Checks)
# =========================================================================

def test_sec_004_idor_cross_supervisor_view_and_actions_return_unified_404(
    client: TestClient, verification_setup
):
    """SEC-004 / SEC-004-A: Cross-supervisor access to another supervisor's team/site.
    All view and action endpoints (approve/reject/return) must return a unified 404
    with identical generic error messages for out-of-scope targets and nonexistent targets,
    eliminating any existence or scope enumeration oracle.
    """
    env = verification_setup
    other_sup_token = env["other_sup_token"]
    worker_emp = env["worker_emp"]
    dwe = env["dwe"]
    att = env["attendance"]
    mat = env["mat_cons"]
    nonexistent_id = uuid.uuid4()

    # 1. VER-002: View employee summary detail
    # Out-of-scope supervisor -> 404
    res_view_scope = client.get(
        f"/api/v1/verification/summary/{worker_emp.id}?date={env['today'].isoformat()}",
        headers=auth_header(other_sup_token),
    )
    assert res_view_scope.status_code == 404
    assert res_view_scope.json()["detail"] == "Employee record not found"

    # Nonexistent employee -> identical 404
    res_view_nonexistent = client.get(
        f"/api/v1/verification/summary/{nonexistent_id}?date={env['today'].isoformat()}",
        headers=auth_header(other_sup_token),
    )
    assert res_view_nonexistent.status_code == 404
    assert res_view_nonexistent.json()["detail"] == "Employee record not found"
    assert res_view_scope.json() == res_view_nonexistent.json()

    # 2. VER-003: Approve daily work
    # Out of scope -> 404
    res_app_scope = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "daily_work", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_app_scope.status_code == 404
    assert res_app_scope.json()["detail"] == "Daily work record not found"

    # Nonexistent -> identical 404
    res_app_nonexistent = client.post(
        f"/api/v1/verification/{nonexistent_id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "daily_work", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_app_nonexistent.status_code == 404
    assert res_app_nonexistent.json()["detail"] == "Daily work record not found"
    assert res_app_scope.json() == res_app_nonexistent.json()

    # 3. VER-004: Reject daily work
    res_rej_scope = client.post(
        f"/api/v1/verification/{dwe.id}/reject",
        headers=auth_header(other_sup_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Out-of-scope supervisor rejection attempt",
        },
    )
    assert res_rej_scope.status_code == 404
    assert res_rej_scope.json()["detail"] == "Daily work record not found"

    res_rej_nonexistent = client.post(
        f"/api/v1/verification/{nonexistent_id}/reject",
        headers=auth_header(other_sup_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Nonexistent entity rejection attempt",
        },
    )
    assert res_rej_nonexistent.status_code == 404
    assert res_rej_nonexistent.json()["detail"] == "Daily work record not found"
    assert res_rej_scope.json() == res_rej_nonexistent.json()

    # 4. VER-005: Return daily work
    res_ret_scope = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(other_sup_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Out-of-scope supervisor return attempt",
        },
    )
    assert res_ret_scope.status_code == 404
    assert res_ret_scope.json()["detail"] == "Daily work record not found"

    res_ret_nonexistent = client.post(
        f"/api/v1/verification/{nonexistent_id}/return",
        headers=auth_header(other_sup_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Nonexistent entity return attempt",
        },
    )
    assert res_ret_nonexistent.status_code == 404
    assert res_ret_nonexistent.json()["detail"] == "Daily work record not found"
    assert res_ret_scope.json() == res_ret_nonexistent.json()

    # 5. Out-of-scope attendance & material actions
    res_att_scope = client.post(
        f"/api/v1/verification/{att.id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "attendance", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_att_scope.status_code == 404
    assert res_att_scope.json()["detail"] == "Attendance record not found"

    res_att_nonexistent = client.post(
        f"/api/v1/verification/{nonexistent_id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "attendance", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_att_nonexistent.status_code == 404
    assert res_att_nonexistent.json()["detail"] == "Attendance record not found"
    assert res_att_scope.json() == res_att_nonexistent.json()

    res_mat_scope = client.post(
        f"/api/v1/verification/{mat.id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "material", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_mat_scope.status_code == 404
    assert res_mat_scope.json()["detail"] == "Material record not found"

    res_mat_nonexistent = client.post(
        f"/api/v1/verification/{nonexistent_id}/approve",
        headers=auth_header(other_sup_token),
        json={"entity_type": "material", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_mat_nonexistent.status_code == 404
    assert res_mat_nonexistent.json()["detail"] == "Material record not found"
    assert res_mat_scope.json() == res_mat_nonexistent.json()


def test_sec_004_idor_regular_supervisor_cannot_reopen_approved_record_returns_403(
    client: TestClient, verification_setup
):
    """SEC-004: Role distinction check.
    While scope & existence checks return unified 404, role authorization checks
    for privileged actions (e.g. reopening an approved record) must strictly return 403 Forbidden.
    """
    env = verification_setup
    sup_token = env["sup_token"]
    admin_token = env["admin_token"]
    dwe = env["dwe"]

    # 1. Assigned supervisor approves the daily work entry
    res_app = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(sup_token),
        json={"entity_type": "daily_work", "idempotency_key": str(uuid.uuid4())},
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    # 2. Regular supervisor attempts to call the Reopen action -> 403 Forbidden
    res_reopen_sup = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(sup_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Supervisor attempting unauthorized reopen on approved record",
        },
    )
    assert res_reopen_sup.status_code == 403
    assert "Only administrators or directors can reopen an approved record" in res_reopen_sup.json()["detail"]

    # 3. Administrator successfully reopens the record -> 200 OK
    res_reopen_admin = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=auth_header(admin_token),
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Admin reopening approved record for required corrections",
        },
    )
    assert res_reopen_admin.status_code == 200
    assert res_reopen_admin.json()["status"] == "correction_required"


def test_sec_004_role_spoofing_tampered_role_blocked_across_all_verification_endpoints(
    client: TestClient, verification_setup
):
    """SEC-004: Role spoofing verification.
    A JWT with a tampered role claim (e.g., an employee forging role='supervisor' or 'administrator'
    in the JWT payload) is blocked with 403 Forbidden because backend verifies identity and DB role.
    """
    env = verification_setup
    dwe = env["dwe"]
    worker_emp = env["worker_emp"]
    worker_user = env["worker_user"]

    for fake_role in ["supervisor", "administrator", "director", "superadmin"]:
        tampered_token = create_access_token(str(worker_user.id), fake_role)
        headers = auth_header(tampered_token)

        # 1. VER-001 Summary Queue
        res1 = client.get(
            f"/api/v1/verification/summary?date={env['today'].isoformat()}",
            headers=headers,
        )
        assert res1.status_code == 403, f"Endpoint 1 allowed role {fake_role}"

        # 2. VER-002 Employee Detail
        res2 = client.get(
            f"/api/v1/verification/summary/{worker_emp.id}?date={env['today'].isoformat()}",
            headers=headers,
        )
        assert res2.status_code == 403, f"Endpoint 2 allowed role {fake_role}"

        # 3. VER-003 Approve
        res3 = client.post(
            f"/api/v1/verification/{dwe.id}/approve",
            headers=headers,
            json={"entity_type": "daily_work", "idempotency_key": str(uuid.uuid4())},
        )
        assert res3.status_code == 403, f"Endpoint 3 allowed role {fake_role}"

        # 4. VER-004 Reject
        res4 = client.post(
            f"/api/v1/verification/{dwe.id}/reject",
            headers=headers,
            json={
                "entity_type": "daily_work",
                "idempotency_key": str(uuid.uuid4()),
                "remarks": "Spoofed reject attempt",
            },
        )
        assert res4.status_code == 403, f"Endpoint 4 allowed role {fake_role}"

        # 5. VER-005 Return
        res5 = client.post(
            f"/api/v1/verification/{dwe.id}/return",
            headers=headers,
            json={
                "entity_type": "daily_work",
                "idempotency_key": str(uuid.uuid4()),
                "remarks": "Spoofed return attempt",
            },
        )
        assert res5.status_code == 403, f"Endpoint 5 allowed role {fake_role}"


def test_sec_004_employee_role_blocked_from_all_verification_endpoints(
    client: TestClient, verification_setup
):
    """SEC-004: Standard employee role (field worker) must be completely blocked
    with 403 Forbidden from accessing any verification endpoint.
    """
    env = verification_setup
    worker_headers = auth_header(env["worker_token"])
    dwe = env["dwe"]
    worker_emp = env["worker_emp"]

    # 1. VER-001 Summary Queue
    res1 = client.get(
        f"/api/v1/verification/summary?date={env['today'].isoformat()}",
        headers=worker_headers,
    )
    assert res1.status_code == 403

    # 2. VER-002 Employee Detail (even for their own employee_id!)
    res2 = client.get(
        f"/api/v1/verification/summary/{worker_emp.id}?date={env['today'].isoformat()}",
        headers=worker_headers,
    )
    assert res2.status_code == 403

    # 3. VER-003 Approve (even for their own work entry!)
    res3 = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=worker_headers,
        json={"entity_type": "daily_work", "idempotency_key": str(uuid.uuid4())},
    )
    assert res3.status_code == 403

    # 4. VER-004 Reject
    res4 = client.post(
        f"/api/v1/verification/{dwe.id}/reject",
        headers=worker_headers,
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Worker attempting self-rejection",
        },
    )
    assert res4.status_code == 403

    # 5. VER-005 Return
    res5 = client.post(
        f"/api/v1/verification/{dwe.id}/return",
        headers=worker_headers,
        json={
            "entity_type": "daily_work",
            "idempotency_key": str(uuid.uuid4()),
            "remarks": "Worker attempting return",
        },
    )
    assert res5.status_code == 403


def test_sec_004_idempotency_key_uniqueness_under_rapid_retry(
    client: TestClient, verification_setup, sync_db_session: Session
):
    """SEC-004: Idempotency uniqueness enforcement under rapid retry.
    Two rapid requests with the exact same idempotency_key must create exactly
    ONE verification_record at the DB level, with the second request safely returning
    the winner's record with is_replay=True.
    """
    env = verification_setup
    dwe = env["dwe"]
    key = f"SEC004-IDEMP-{uuid.uuid4()}"

    payload = {
        "entity_type": "daily_work",
        "idempotency_key": key,
        "remarks": "First submission",
    }

    # First request
    res1 = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json=payload,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_replay"] is False

    # Rapid retry with identical idempotency key
    res2 = client.post(
        f"/api/v1/verification/{dwe.id}/approve",
        headers=auth_header(env["sup_token"]),
        json=payload,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_replay"] is True

    # Same verification record returned
    assert data1["verification_record_id"] == data2["verification_record_id"]

    # Verify at the database level: exactly ONE record exists for this key
    db_records = (
        sync_db_session.query(VerificationRecord)
        .filter(VerificationRecord.idempotency_key == key)
        .all()
    )
    assert len(db_records) == 1
    assert str(db_records[0].id) == data1["verification_record_id"]


def test_sec_004_idempotency_key_uniqueness_under_concurrent_api_retry(
    client: TestClient, verification_setup, sync_db_session: Session
):
    """SEC-004: Concurrent API retry with the same idempotency_key.
    Simulating two threads hitting the endpoint concurrently with the same idempotency key.
    Both return 200, one original and one replay, with exactly ONE DB record created.
    """
    import concurrent.futures

    env = verification_setup
    mat_id = str(env["mat_purch"].id)
    key = f"SEC004-CONCUR-{uuid.uuid4()}"

    def send_approve():
        return client.post(
            f"/api/v1/verification/{mat_id}/approve",
            headers=auth_header(env["sup_token"]),
            json={
                "entity_type": "material",
                "idempotency_key": key,
                "remarks": "Concurrent approval",
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_approve)
        f2 = executor.submit(send_approve)
        r1 = f1.result()
        r2 = f2.result()

    responses = [r1, r2]
    assert all(r.status_code == 200 for r in responses), f"Unexpected status: {[r.status_code for r in responses]}"
    replays = [r.json()["is_replay"] for r in responses]
    assert False in replays
    assert True in replays

    # IDs match
    ids = [r.json()["verification_record_id"] for r in responses]
    assert ids[0] == ids[1]

    # Verify DB level
    sync_db_session.rollback()
    db_records = (
        sync_db_session.query(VerificationRecord)
        .filter(VerificationRecord.idempotency_key == key)
        .all()
    )
    assert len(db_records) == 1


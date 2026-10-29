import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.auth import User
from app.models.operations import Client, Project, Site
from app.models.workforce import Employee, Role


@pytest.fixture
def setup_master_data(sync_db_session: Session):
    r1_name = f"Mason-{uuid.uuid4().hex[:6]}"
    r2_name = f"Electrician-{uuid.uuid4().hex[:6]}"
    role1 = Role(id=uuid.uuid4(), name=r1_name, description="Masonry worker")
    role2 = Role(id=uuid.uuid4(), name=r2_name, description="Electrical worker")
    sync_db_session.add(role1)
    sync_db_session.add(role2)

    client_obj = Client(id=uuid.uuid4(), name=f"Test Client Corp {uuid.uuid4().hex[:6]}")
    sync_db_session.add(client_obj)

    project_obj = Project(id=uuid.uuid4(), client_id=client_obj.id, name="Test Construction Project", status="Active")
    sync_db_session.add(project_obj)

    site_obj1 = Site(id=uuid.uuid4(), project_id=project_obj.id, name="Site Alpha")
    site_obj2 = Site(id=uuid.uuid4(), project_id=project_obj.id, name="Site Beta")
    sync_db_session.add(site_obj1)
    sync_db_session.add(site_obj2)

    sync_db_session.commit()

    return {
        "role1_id": role1.id,
        "role1_name": r1_name,
        "role2_id": role2.id,
        "role2_name": r2_name,
        "site1_id": site_obj1.id,
        "site2_id": site_obj2.id,
    }


@pytest.fixture
def admin_user(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+199{str(uuid.uuid4().int)[:7]}",
        role="administrator",
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()

    emp = Employee(
        id=uuid.uuid4(),
        user_id=user.id,
        employee_code=f"ADM-{str(uuid.uuid4().int)[:5]}",
        mobile_id=user.mobile_id,
        name="Admin Employee",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, token


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
        name="Chief Supervisor",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, emp, token


@pytest.fixture
def employee_user(sync_db_session: Session):
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
        name="Standard Worker",
        is_active=True,
    )
    sync_db_session.add(emp)
    sync_db_session.commit()

    token = create_access_token(str(user.id), user.role)
    return user, emp, token


def test_onboard_employee_success(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "John Builder",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }

    response = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Builder"
    assert data["mobile_id"] == payload["mobile_number"]
    assert data["employee_code"] == payload["employee_code"]
    assert data["system_role"] == "employee"
    assert len(data["trade_roles"]) == 1
    assert data["trade_roles"][0]["name"] == master["role1_name"]
    assert data["current_rate"]["rate_amount"] == 500.0
    assert len(data["active_sites"]) == 1
    assert data["active_sites"][0]["name"] == "Site Alpha"


def test_onboard_employee_duplicate_mobile_or_code(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data
    mobile = f"+155{str(uuid.uuid4().int)[:7]}"
    code = f"EMP-{str(uuid.uuid4().int)[:5]}"

    payload = {
        "name": "First Worker",
        "mobile_number": mobile,
        "employee_code": code,
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201

    # Duplicate mobile
    payload_dup_mobile = dict(payload)
    payload_dup_mobile["employee_code"] = f"EMP-{str(uuid.uuid4().int)[:5]}"
    resp_dup1 = client.post(
        "/api/v1/employees",
        json=payload_dup_mobile,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_dup1.status_code == 409
    assert resp_dup1.json()["error"]["code"] == "CONFLICT"

    # Duplicate code
    payload_dup_code = dict(payload)
    payload_dup_code["mobile_number"] = f"+155{str(uuid.uuid4().int)[:7]}"
    resp_dup2 = client.post(
        "/api/v1/employees",
        json=payload_dup_code,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_dup2.status_code == 409
    assert resp_dup2.json()["error"]["code"] == "CONFLICT"


def test_onboard_employee_invalid_fk(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data

    # Invalid site
    payload = {
        "name": "Invalid Site Worker",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 400.0,
        "site_ids": [str(uuid.uuid4())],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_list_and_get_employees_supervisor_scoping(
    client: TestClient, admin_user, supervisor_user, employee_user, setup_master_data
):
    _, admin_token = admin_user
    _, sup_emp, sup_token = supervisor_user
    master = setup_master_data

    # Admin creates employee assigned to supervisor
    payload = {
        "name": "Supervised Worker",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "supervisor_id": str(sup_emp.id),
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 600.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    subordinate_id = resp.json()["id"]

    # Admin creates employee NOT assigned to supervisor
    payload_other = {
        "name": "Other Worker",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 600.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp_other = client.post(
        "/api/v1/employees",
        json=payload_other,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_other.status_code == 201
    other_emp_id = resp_other.json()["id"]

    # Supervisor lists employees: should only see subordinate
    sup_list_resp = client.get(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {sup_token}"},
    )
    assert sup_list_resp.status_code == 200
    sup_list_ids = [e["id"] for e in sup_list_resp.json()]
    assert subordinate_id in sup_list_ids
    assert other_emp_id not in sup_list_ids

    # Supervisor gets subordinate details -> 200
    sub_get_resp = client.get(
        f"/api/v1/employees/{subordinate_id}",
        headers={"Authorization": f"Bearer {sup_token}"},
    )
    assert sub_get_resp.status_code == 200

    # Supervisor gets unassigned employee details -> 403 Forbidden
    other_get_resp = client.get(
        f"/api/v1/employees/{other_emp_id}",
        headers={"Authorization": f"Bearer {sup_token}"},
    )
    assert other_get_resp.status_code == 403


def test_get_my_profile(client: TestClient, employee_user):
    _, emp_obj, emp_token = employee_user

    resp = client.get(
        "/api/v1/employees/me",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(emp_obj.id)
    assert data["name"] == emp_obj.name


def test_update_employee_and_rate_change(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee
    payload = {
        "name": "Rate Change Worker",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    emp_id = create_resp.json()["id"]

    # Update rate
    update_payload = {
        "rate_amount": 650.0,
        "name": "Rate Change Worker Updated",
    }
    update_resp = client.put(
        f"/api/v1/employees/{emp_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["name"] == "Rate Change Worker Updated"
    assert updated_data["current_rate"]["rate_amount"] == 650.0


def test_assign_site_endpoint(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with site1
    payload = {
        "name": "Multi Site Worker",
        "mobile_number": f"+155{str(uuid.uuid4().int)[:7]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    emp_id = create_resp.json()["id"]

    # Assign site2 via EMP-006
    assign_resp = client.post(
        f"/api/v1/employees/{emp_id}/site-assignments",
        json={"site_id": str(master["site2_id"])},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_resp.status_code == 200
    active_sites = assign_resp.json()["active_sites"]
    site_ids = [s["id"] for s in active_sites]
    assert str(master["site1_id"]) in site_ids
    assert str(master["site2_id"]) in site_ids


def test_employee_rbac_protections(client: TestClient, employee_user, setup_master_data):
    _, _, emp_token = employee_user
    master = setup_master_data

    # Standard employee attempts admin operations -> 403
    resp_create = client.post(
        "/api/v1/employees",
        json={},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp_create.status_code == 403

    resp_update = client.put(
        f"/api/v1/employees/{uuid.uuid4()}",
        json={},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp_update.status_code == 403

    resp_assign = client.post(
        f"/api/v1/employees/{uuid.uuid4()}/site-assignments",
        json={"site_id": str(master["site1_id"])},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp_assign.status_code == 403


def test_unauthenticated_requests(client: TestClient):
    assert client.post("/api/v1/employees", json={}).status_code == 401
    assert client.get("/api/v1/employees").status_code == 401
    assert client.get("/api/v1/employees/me").status_code == 401
    assert client.delete(f"/api/v1/employees/{uuid.uuid4()}").status_code == 401


def test_delete_employee_success(client: TestClient, admin_user, setup_master_data):
    admin_user_obj, admin_token = admin_user
    master = setup_master_data

    # 1. Create employee
    mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    create_payload = {
        "employee_code": f"EMP-DEL-{str(uuid.uuid4().int)[:4]}",
        "mobile_number": mobile,
        "name": "Delete Me Worker",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 750.00,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = resp.json()["id"]

    # 2. Delete employee
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # 3. Confirm 404
    get_resp = client.get(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


def test_delete_employee_rbac(client: TestClient, employee_user, admin_user, setup_master_data):
    admin_user_obj, admin_token = admin_user
    _, _, emp_token = employee_user
    master = setup_master_data

    # Create employee
    mobile = f"+9197{str(uuid.uuid4().int)[:8]}"
    create_payload = {
        "employee_code": f"EMP-DEL-RBAC-{str(uuid.uuid4().int)[:4]}",
        "mobile_number": mobile,
        "name": "RBAC Worker",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 600.00,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    emp_id = resp.json()["id"]

    # Employee tries to delete -> 403
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert del_resp.status_code == 403


def test_delete_employee_cannot_delete_self(client: TestClient, admin_user, sync_db_session: Session):
    admin_user_obj, admin_token = admin_user
    admin_emp = sync_db_session.query(Employee).filter(Employee.user_id == admin_user_obj.id).first()

    del_resp = client.delete(
        f"/api/v1/employees/{admin_emp.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code in [400, 422]
    assert "Cannot delete your own administrator account" in del_resp.text


def test_delete_employee_not_found(client: TestClient, admin_user):
    admin_user_obj, admin_token = admin_user

    del_resp = client.delete(
        f"/api/v1/employees/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 404


def test_update_employee_full_fields(client: TestClient, admin_user, setup_master_data):
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with site1, role1
    orig_mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    create_payload = {
        "employee_code": f"EMP-UPD-{str(uuid.uuid4().int)[:4]}",
        "mobile_number": orig_mobile,
        "name": "Original Worker",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["id"]

    new_mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    update_payload = {
        "name": "Updated Worker Name",
        "mobile_number": new_mobile,
        "system_role": "supervisor",
        "trade_role_ids": [str(master["role2_id"])],
        "site_ids": [str(master["site2_id"])],
        "rate_type": "monthly",
        "rate_amount": 25000.0,
        "is_active": False,
    }
    update_resp = client.put(
        f"/api/v1/employees/{emp_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Updated Worker Name"
    assert data["mobile_id"] == new_mobile
    assert data["system_role"] == "supervisor"
    assert data["is_active"] is False
    assert len(data["trade_roles"]) == 1
    assert data["trade_roles"][0]["name"] == master["role2_name"]
    assert len(data["active_sites"]) == 1
    assert data["active_sites"][0]["name"] == "Site Beta"
    assert data["current_rate"]["rate_type"] == "monthly"
    assert data["current_rate"]["rate_amount"] == 25000.0


def test_onboard_employee_without_trade_role_rejected(client: TestClient, admin_user, setup_master_data):
    """Employee (Field Worker): Trade / Job Role is mandatory. Omitting or empty list is rejected."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Empty list
    payload_empty = {
        "name": "No Trade Worker",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload_empty,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 422

    # 2. Omitted key (defaults to empty list, must be rejected for employee)
    payload_omitted = {
        "name": "Omitted Trade Worker",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp2 = client.post(
        "/api/v1/employees",
        json=payload_omitted,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 422


def test_onboard_employee_with_trade_role_success(client: TestClient, admin_user, setup_master_data):
    """Employee (Field Worker): Trade / Job Role provided is accepted."""
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "Technician Worker",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 600.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_role"] == "employee"
    assert len(data["trade_roles"]) == 1
    assert data["trade_roles"][0]["id"] == str(master["role1_id"])


def test_onboard_supervisor_without_trade_role_success(client: TestClient, admin_user, setup_master_data):
    """Supervisor: Trade / Job Role is optional. Can be onboarded without one."""
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "Site Supervisor",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"SUP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "supervisor",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 1000.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_role"] == "supervisor"
    assert data["trade_roles"] == []


def test_onboard_director_without_trade_role_success(client: TestClient, admin_user, setup_master_data):
    """Director: Trade / Job Role is optional. Can be onboarded without one."""
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "Operations Director",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"DIR-{str(uuid.uuid4().int)[:5]}",
        "system_role": "director",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2000.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_role"] == "director"
    assert data["trade_roles"] == []


def test_onboard_administrator_without_trade_role_success(client: TestClient, admin_user, setup_master_data):
    """Administrator: Trade / Job Role is optional. Can be onboarded without one."""
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "System Administrator",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"ADM-{str(uuid.uuid4().int)[:5]}",
        "system_role": "administrator",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 1500.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_role"] == "administrator"
    assert data["trade_roles"] == []


def test_onboard_non_employee_with_optional_trade_role_success(client: TestClient, admin_user, setup_master_data):
    """Non-employee role (e.g. Supervisor): Trade / Job Role can be optionally selected."""
    _, admin_token = admin_user
    master = setup_master_data

    payload = {
        "name": "Technical Supervisor",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"SUP-T-{str(uuid.uuid4().int)[:4]}",
        "system_role": "supervisor",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 1200.0,
        "site_ids": [str(master["site1_id"])],
    }
    resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_role"] == "supervisor"
    assert len(data["trade_roles"]) == 1
    assert data["trade_roles"][0]["id"] == str(master["role1_id"])


def test_update_employee_trade_role_validation(client: TestClient, admin_user, setup_master_data):
    """Updating trade roles enforces the same rules: employee must have >= 1 trade role, supervisor can have none."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with trade role
    create_payload = {
        "name": "Worker For Update",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["id"]

    # Attempt to clear trade roles for employee role -> 422
    update_fail = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"trade_role_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_fail.status_code == 422

    # Promote to supervisor and clear trade roles -> 200
    update_ok = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "supervisor", "trade_role_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_ok.status_code == 200
    assert update_ok.json()["system_role"] == "supervisor"
    assert update_ok.json()["trade_roles"] == []


def test_onboard_employee_without_site_rejected(client: TestClient, admin_user, setup_master_data):
    """Employee (Field Worker): At least one client site is mandatory. Empty list or omitted is rejected."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Empty list
    payload_empty = {
        "name": "No Site Employee",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
        "site_ids": [],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload_empty,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 422

    # 2. Omitted key (defaults to empty list, rejected for employee)
    payload_omitted = {
        "name": "Omitted Site Employee",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 500.0,
    }
    resp2 = client.post(
        "/api/v1/employees",
        json=payload_omitted,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 422


def test_onboard_supervisor_without_site_rejected(client: TestClient, admin_user, setup_master_data):
    """Supervisor: At least one client site is mandatory. Empty list or omitted is rejected."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Empty list
    payload_empty = {
        "name": "No Site Supervisor",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"SUP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "supervisor",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 900.0,
        "site_ids": [],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload_empty,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 422

    # 2. Omitted key
    payload_omitted = {
        "name": "Omitted Site Supervisor",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"SUP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "supervisor",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 900.0,
    }
    resp2 = client.post(
        "/api/v1/employees",
        json=payload_omitted,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 422


def test_onboard_director_without_site_success(client: TestClient, admin_user, setup_master_data):
    """Director: Client site assignment is optional. Can be created with empty list or omitted site_ids."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Empty list
    payload_empty = {
        "name": "Site Optional Director",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"DIR-{str(uuid.uuid4().int)[:5]}",
        "system_role": "director",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2500.0,
        "site_ids": [],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload_empty,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["system_role"] == "director"
    assert data1["active_sites"] == []

    # 2. Omitted key
    payload_omitted = {
        "name": "Omitted Site Director",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"DIR-{str(uuid.uuid4().int)[:5]}",
        "system_role": "director",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2500.0,
    }
    resp2 = client.post(
        "/api/v1/employees",
        json=payload_omitted,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["system_role"] == "director"
    assert data2["active_sites"] == []


def test_onboard_administrator_without_site_success(client: TestClient, admin_user, setup_master_data):
    """Administrator: Client site assignment is optional. Can be created with empty list or omitted site_ids."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Empty list
    payload_empty = {
        "name": "Site Optional Admin",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"ADM-{str(uuid.uuid4().int)[:5]}",
        "system_role": "administrator",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2000.0,
        "site_ids": [],
    }
    resp1 = client.post(
        "/api/v1/employees",
        json=payload_empty,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["system_role"] == "administrator"
    assert data1["active_sites"] == []

    # 2. Omitted key
    payload_omitted = {
        "name": "Omitted Site Admin",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"ADM-{str(uuid.uuid4().int)[:5]}",
        "system_role": "administrator",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2000.0,
    }
    resp2 = client.post(
        "/api/v1/employees",
        json=payload_omitted,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["system_role"] == "administrator"
    assert data2["active_sites"] == []


def test_update_employee_site_validation(client: TestClient, admin_user, setup_master_data):
    """Employee site update: cannot clear sites; omitting site_ids preserves existing assignments."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with site1
    payload = {
        "name": "Site Check Employee",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"EMP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "employee",
        "trade_role_ids": [str(master["role1_id"])],
        "rate_type": "monthly",
        "rate_amount": 550.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["id"]

    # 1. Clearing site_ids for employee must fail (422)
    resp_clear = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_clear.status_code == 422

    # 2. Updating another field without specifying site_ids must PRESERVE existing site assignments
    resp_update_name = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"name": "Site Check Employee Renamed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_update_name.status_code == 200
    data_name = resp_update_name.json()
    assert data_name["name"] == "Site Check Employee Renamed"
    assert len(data_name["active_sites"]) == 1
    assert data_name["active_sites"][0]["id"] == str(master["site1_id"])

    # 3. Explicitly changing site_ids replaces the site assignment
    resp_replace = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": [str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_replace.status_code == 200
    data_replace = resp_replace.json()
    assert len(data_replace["active_sites"]) == 1
    assert data_replace["active_sites"][0]["id"] == str(master["site2_id"])


def test_update_supervisor_site_validation(client: TestClient, admin_user, setup_master_data):
    """Supervisor site update: cannot clear sites; omitting site_ids preserves existing assignments."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create supervisor with site1
    payload = {
        "name": "Site Check Supervisor",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"SUP-{str(uuid.uuid4().int)[:5]}",
        "system_role": "supervisor",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 1100.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    sup_id = create_resp.json()["id"]

    # 1. Clearing site_ids for supervisor must fail (422)
    resp_clear = client.put(
        f"/api/v1/employees/{sup_id}",
        json={"site_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_clear.status_code == 422

    # 2. Updating name preserves existing sites
    resp_update = client.put(
        f"/api/v1/employees/{sup_id}",
        json={"name": "Site Check Supervisor Renamed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_update.status_code == 200
    assert len(resp_update.json()["active_sites"]) == 1
    assert resp_update.json()["active_sites"][0]["id"] == str(master["site1_id"])


def test_update_director_and_administrator_empty_sites(client: TestClient, admin_user, setup_master_data):
    """Director / Administrator: can clear sites or update with empty site list."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create director with site1
    payload = {
        "name": "Site Clearing Director",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"DIR-{str(uuid.uuid4().int)[:5]}",
        "system_role": "director",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2500.0,
        "site_ids": [str(master["site1_id"])],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    dir_id = create_resp.json()["id"]
    assert len(create_resp.json()["active_sites"]) == 1

    # Clear sites for Director -> 200
    clear_resp = client.put(
        f"/api/v1/employees/{dir_id}",
        json={"site_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["active_sites"] == []

    # Create administrator without sites
    admin_payload = {
        "name": "Site Assigned Admin",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"ADM-{str(uuid.uuid4().int)[:5]}",
        "system_role": "administrator",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 1800.0,
        "site_ids": [],
    }
    create_admin_resp = client.post(
        "/api/v1/employees",
        json=admin_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_admin_resp.status_code == 201
    admin_emp_id = create_admin_resp.json()["id"]
    assert create_admin_resp.json()["active_sites"] == []

    # Assign a site to administrator -> 200
    assign_resp = client.put(
        f"/api/v1/employees/{admin_emp_id}",
        json={"site_ids": [str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_resp.status_code == 200
    assert len(assign_resp.json()["active_sites"]) == 1
    assert assign_resp.json()["active_sites"][0]["id"] == str(master["site2_id"])


def test_update_role_change_site_safety(client: TestClient, admin_user, setup_master_data):
    """Role change safety: changing a role without sites to employee or supervisor requires at least one site."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create director with no sites
    payload = {
        "name": "Transition Director",
        "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
        "employee_code": f"DIR-{str(uuid.uuid4().int)[:5]}",
        "system_role": "director",
        "trade_role_ids": [],
        "rate_type": "monthly",
        "rate_amount": 2500.0,
        "site_ids": [],
    }
    create_resp = client.post(
        "/api/v1/employees",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["id"]
    assert create_resp.json()["active_sites"] == []

    # 1. Changing role to supervisor WITHOUT passing site_ids -> rejected (has 0 active sites)
    resp_change_no_sites = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "supervisor"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_change_no_sites.status_code in (400, 422)

    # 2. Changing role to supervisor WITH empty site_ids -> rejected
    resp_change_empty_sites = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "supervisor", "site_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_change_empty_sites.status_code == 422

    # 3. Changing role to supervisor WITH a site -> 200 OK
    resp_change_valid = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "supervisor", "site_ids": [str(master["site1_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_change_valid.status_code == 200
    data_valid = resp_change_valid.json()
    assert data_valid["system_role"] == "supervisor"
    assert len(data_valid["active_sites"]) == 1

    # 4. Now transition supervisor to employee without trade roles -> rejected
    resp_emp_no_trade = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "employee", "trade_role_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_emp_no_trade.status_code == 422

    # 5. Transition supervisor to employee with trade role, keeping existing site -> 200 OK
    resp_emp_valid = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"system_role": "employee", "trade_role_ids": [str(master["role1_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_emp_valid.status_code == 200
    data_emp = resp_emp_valid.json()
    assert data_emp["system_role"] == "employee"
    assert len(data_emp["active_sites"]) == 1


def _get_or_create_test_role_and_site(sync_db_session: Session):
    role = sync_db_session.query(Role).first()
    if not role:
        role = Role(id=uuid.uuid4(), name=f"Role-{uuid.uuid4().hex[:6]}")
        sync_db_session.add(role)
        sync_db_session.flush()

    site = sync_db_session.query(Site).first()
    if not site:
        client = Client(id=uuid.uuid4(), name=f"Client-{uuid.uuid4().hex[:6]}")
        sync_db_session.add(client)
        sync_db_session.flush()
        project = Project(id=uuid.uuid4(), client_id=client.id, name=f"Proj-{uuid.uuid4().hex[:6]}", status="Active")
        sync_db_session.add(project)
        sync_db_session.flush()
        site = Site(id=uuid.uuid4(), project_id=project.id, name=f"Site-{uuid.uuid4().hex[:6]}")
        sync_db_session.add(site)
        sync_db_session.flush()

    sync_db_session.commit()
    return role.id, site.id


def test_delete_employee_with_attendance_deactivates(
    client: TestClient, admin_user, sync_db_session: Session
):
    admin_user_obj, admin_token = admin_user
    role_id, site_id = _get_or_create_test_role_and_site(sync_db_session)

    # 1. Onboard employee
    mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    resp = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-ATT-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": mobile,
            "name": "Historical Attendance Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 750.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = uuid.UUID(resp.json()["id"])

    # 2. Add historical attendance record
    from datetime import date, datetime, timezone
    from app.models.operations import AttendanceRecord, EmployeeSiteAssignment

    att = AttendanceRecord(
        id=uuid.uuid4(),
        employee_id=emp_id,
        site_id=site_id,
        date=date.today(),
        check_in_time=datetime.now(timezone.utc),
        status="approved",
    )
    sync_db_session.add(att)
    sync_db_session.commit()

    # 3. Call delete endpoint
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "success"
    assert del_data["action"] == "deactivated"
    assert "deactivated successfully" in del_data["message"]

    # 4. Verify employee is preserved and marked inactive
    emp_db = sync_db_session.query(Employee).filter(Employee.id == emp_id).first()
    assert emp_db is not None
    assert emp_db.is_active is False

    # 5. Verify user is marked inactive
    user_db = sync_db_session.query(User).filter(User.id == emp_db.user_id).first()
    assert user_db is not None
    assert user_db.is_active is False

    # 6. Verify site assignments are deactivated
    assignments = sync_db_session.query(EmployeeSiteAssignment).filter(EmployeeSiteAssignment.employee_id == emp_id).all()
    assert len(assignments) > 0
    assert all(not a.is_active for a in assignments)

    # 7. Verify attendance record is intact
    att_db = sync_db_session.query(AttendanceRecord).filter(AttendanceRecord.id == att.id).first()
    assert att_db is not None

    # 8. Deleting again when already inactive is idempotent
    del_again_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_again_resp.status_code == 200
    del_again_data = del_again_resp.json()
    assert del_again_data["status"] == "success"
    assert del_again_data["action"] == "deactivated"
    assert "already deactivated" in del_again_data["message"]


def test_delete_employee_with_daily_work_deactivates(
    client: TestClient, admin_user, sync_db_session: Session
):
    admin_user_obj, admin_token = admin_user
    role_id, site_id = _get_or_create_test_role_and_site(sync_db_session)

    # Onboard employee
    mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    resp = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-DWE-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": mobile,
            "name": "Historical DWE Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 750.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = uuid.UUID(resp.json()["id"])

    # Setup attendance, activity & DWE
    from datetime import date, datetime, timezone
    from decimal import Decimal
    from app.models.operations import Activity, AttendanceRecord, DailyWorkEntry

    att = AttendanceRecord(
        id=uuid.uuid4(),
        employee_id=emp_id,
        site_id=site_id,
        date=date.today(),
        check_in_time=datetime.now(timezone.utc),
        status="approved",
    )
    sync_db_session.add(att)
    sync_db_session.flush()

    act = Activity(
        id=uuid.uuid4(),
        name=f"Test Work Activity {uuid.uuid4().hex[:4]}",
        unit_of_measure="pcs",
        approved_rate=100.0,
        category="mounting",
        is_active=True,
    )
    sync_db_session.add(act)
    sync_db_session.flush()

    dwe = DailyWorkEntry(
        id=uuid.uuid4(),
        idempotency_key=f"IDEM-DWE-{uuid.uuid4().hex[:8]}",
        attendance_record_id=att.id,
        employee_id=emp_id,
        site_id=site_id,
        activity_id=act.id,
        work_date=date.today(),
        quantity=Decimal("10.00"),
        uom="pcs",
        status="approved",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()

    # Call delete endpoint
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["action"] == "deactivated"

    # Verify DWE preserved & employee inactive
    dwe_db = sync_db_session.query(DailyWorkEntry).filter(DailyWorkEntry.id == dwe.id).first()
    assert dwe_db is not None
    emp_db = sync_db_session.query(Employee).filter(Employee.id == emp_id).first()
    assert emp_db.is_active is False


def test_delete_employee_with_asset_custody_deactivates(
    client: TestClient, admin_user, sync_db_session: Session
):
    admin_user_obj, admin_token = admin_user
    role_id, site_id = _get_or_create_test_role_and_site(sync_db_session)

    # Onboard employee
    mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    resp = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-AST-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": mobile,
            "name": "Asset Custodian Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 750.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = uuid.UUID(resp.json()["id"])

    # Create asset in their custody
    from app.models.assets import Asset

    asset = Asset(
        id=uuid.uuid4(),
        asset_tag=f"AST-{str(uuid.uuid4().int)[:6]}",
        name="Field Hammer Drill",
        category="Power Tools",
        condition="good",
        status="issued_employee",
        location_type="site",
        current_site_id=site_id,
        current_custodian_id=emp_id,
        is_active=True,
    )
    sync_db_session.add(asset)
    sync_db_session.commit()

    # Call delete endpoint
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["action"] == "deactivated"

    # Asset is preserved and custodian unchanged
    asset_db = sync_db_session.query(Asset).filter(Asset.id == asset.id).first()
    assert asset_db is not None
    assert asset_db.current_custodian_id == emp_id

    # Employee is deactivated
    emp_db = sync_db_session.query(Employee).filter(Employee.id == emp_id).first()
    assert emp_db.is_active is False


def test_delete_employee_with_payment_deactivates(
    client: TestClient, admin_user, sync_db_session: Session
):
    admin_user_obj, admin_token = admin_user
    role_id, site_id = _get_or_create_test_role_and_site(sync_db_session)

    # Onboard employee
    mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
    resp = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-PAY-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": mobile,
            "name": "Paid Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 750.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = uuid.UUID(resp.json()["id"])

    # Create employee payment
    from datetime import date
    from decimal import Decimal
    from app.models.employee_payments import EmployeePayment

    pay = EmployeePayment(
        id=uuid.uuid4(),
        payment_number=f"PAY-{uuid.uuid4().hex[:8]}",
        idempotency_key=f"IDEM-{uuid.uuid4().hex[:8]}",
        employee_id=emp_id,
        period_start=date.today(),
        period_end=date.today(),
        status="paid",
        total_amount=Decimal("1500.00"),
    )
    sync_db_session.add(pay)
    sync_db_session.commit()

    # Call delete endpoint
    del_resp = client.delete(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["action"] == "deactivated"

    # Verify payment preserved and employee inactive
    pay_db = sync_db_session.query(EmployeePayment).filter(EmployeePayment.id == pay.id).first()
    assert pay_db is not None
    emp_db = sync_db_session.query(Employee).filter(Employee.id == emp_id).first()
    assert emp_db.is_active is False


def test_list_employees_filter_by_is_active(client: TestClient, admin_user, sync_db_session: Session):
    _, admin_token = admin_user
    role_id, site_id = _get_or_create_test_role_and_site(sync_db_session)

    # 1. Onboard an active employee
    resp_act = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-ACT-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "name": "Active Filter Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 500.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_act.status_code == 201
    act_id = resp_act.json()["id"]

    # 2. Onboard another employee and deactivate them
    resp_inact = client.post(
        "/api/v1/employees",
        json={
            "employee_code": f"EMP-INA-{str(uuid.uuid4().int)[:4]}",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "name": "Inactive Filter Worker",
            "system_role": "employee",
            "trade_role_ids": [str(role_id)],
            "rate_type": "monthly",
            "rate_amount": 500.00,
            "site_ids": [str(site_id)],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_inact.status_code == 201
    inact_id = resp_inact.json()["id"]

    # Deactivate second employee via PUT is_active=False
    resp_deact = client.put(
        f"/api/v1/employees/{inact_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["is_active"] is False

    # 3. Query with is_active=true
    resp_active_only = client.get(
        "/api/v1/employees?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_active_only.status_code == 200
    active_data = resp_active_only.json()
    assert all(e["is_active"] is True for e in active_data)
    active_ids = [e["id"] for e in active_data]
    assert act_id in active_ids
    assert inact_id not in active_ids

    # 4. Query with is_active=false
    resp_inactive_only = client.get(
        "/api/v1/employees?is_active=false",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_inactive_only.status_code == 200
    inactive_data = resp_inactive_only.json()
    assert all(e["is_active"] is False for e in inactive_data)
    inactive_ids = [e["id"] for e in inactive_data]
    assert inact_id in inactive_ids
    assert act_id not in inactive_ids

    # 5. Query without is_active returns all
    resp_all = client.get(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_all.status_code == 200
    all_ids = [e["id"] for e in resp_all.json()]
    assert act_id in all_ids
    assert inact_id in all_ids


def test_onboard_employee_rejects_non_monthly_rate_type(client: TestClient, admin_user, setup_master_data):
    """Rejects daily and weekly rate types; monthly is the only supported pay frequency."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Daily rate rejected
    resp_daily = client.post(
        "/api/v1/employees",
        json={
            "name": "Daily Pay Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-DAILY-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "daily",
            "rate_amount": 500.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_daily.status_code == 422

    # 2. Weekly rate rejected
    resp_weekly = client.post(
        "/api/v1/employees",
        json={
            "name": "Weekly Pay Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-WEEK-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "weekly",
            "rate_amount": 3500.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_weekly.status_code == 422


def test_contract_employee_classification_and_site_requirement(client: TestClient, admin_user, setup_master_data):
    """Tests contract-basis employee classification, site requirement, and directory filter."""
    _, admin_token = admin_user
    master = setup_master_data

    # 1. Contract employee without site is rejected
    resp_no_site = client.post(
        "/api/v1/employees",
        json={
            "name": "Contract Worker No Site",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-CNT-NOSITE-{str(uuid.uuid4().int)[:4]}",
            "system_role": "director",
            "classification": "contract",
            "rate_type": "monthly",
            "rate_amount": 30000.0,
            "site_ids": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_no_site.status_code == 422

    # 2. Contract employee with site succeeds
    resp_contract = client.post(
        "/api/v1/employees",
        json={
            "name": "Contract Site Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-CNT-OK-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "classification": "contract",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 25000.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_contract.status_code == 201
    contract_data = resp_contract.json()
    assert contract_data["classification"] == "contract"
    assert len(contract_data["active_sites"]) == 1
    assert contract_data["active_sites"][0]["id"] == str(master["site1_id"])
    assert contract_data["active_sites"][0]["name"] == "Site Alpha"

    # 3. Regular employee default classification
    resp_regular = client.post(
        "/api/v1/employees",
        json={
            "name": "Regular Staff Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-REG-OK-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 22000.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_regular.status_code == 201
    reg_data = resp_regular.json()
    assert reg_data["classification"] == "regular"

    # 4. Filter by classification=contract
    resp_filter_contract = client.get(
        "/api/v1/employees?classification=contract",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_filter_contract.status_code == 200
    contract_list = resp_filter_contract.json()
    assert all(e["classification"] == "contract" for e in contract_list)
    assert any(e["id"] == contract_data["id"] for e in contract_list)
    assert not any(e["id"] == reg_data["id"] for e in contract_list)

    # 5. Filter by classification=regular
    resp_filter_reg = client.get(
        "/api/v1/employees?classification=regular",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_filter_reg.status_code == 200
    reg_list = resp_filter_reg.json()
    assert all(e["classification"] == "regular" for e in reg_list)
    assert any(e["id"] == reg_data["id"] for e in reg_list)
    assert not any(e["id"] == contract_data["id"] for e in reg_list)


def test_multiple_sites_assignment_and_reassignment_flow(
    client: TestClient, admin_user, setup_master_data, sync_db_session: Session
):
    """Regression test for assigning multiple sites, removing sites, and re-assigning previously unassigned sites without duplicate records or unique constraint errors."""
    from app.models.operations import EmployeeSiteAssignment

    _, admin_token = admin_user
    master = setup_master_data

    # 1. Create Employee A with site1
    resp_a = client.post(
        "/api/v1/employees",
        json={
            "name": "Employee A Multi-Site",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-A-{str(uuid.uuid4().int)[:4]}",
            "system_role": "supervisor",
            "trade_role_ids": [],
            "rate_type": "monthly",
            "rate_amount": 35000.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_a.status_code == 201
    emp_a_id = resp_a.json()["id"]

    # 2. Create unrelated Employee B with site2
    resp_b = client.post(
        "/api/v1/employees",
        json={
            "name": "Employee B Unrelated",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-B-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 20000.0,
            "site_ids": [str(master["site2_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_b.status_code == 201
    emp_b_id = resp_b.json()["id"]

    # 3. Update Employee A to have BOTH site1 and site2
    resp_a_multi = client.put(
        f"/api/v1/employees/{emp_a_id}",
        json={"site_ids": [str(master["site1_id"]), str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_a_multi.status_code == 200
    active_sites_a = resp_a_multi.json()["active_sites"]
    assert len(active_sites_a) == 2
    active_ids_a = {s["id"] for s in active_sites_a}
    assert str(master["site1_id"]) in active_ids_a
    assert str(master["site2_id"]) in active_ids_a

    # Verify Employee B's assignments were NOT affected
    db_b_assigns = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=emp_b_id).all()
    assert len(db_b_assigns) == 1
    assert db_b_assigns[0].site_id == master["site2_id"]
    assert db_b_assigns[0].is_active is True

    # Verify Employee A has exactly 2 records in DB, both active
    db_a_assigns = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=emp_a_id).all()
    assert len(db_a_assigns) == 2
    assert all(a.is_active is True for a in db_a_assigns)

    # 4. Remove site1 by updating Employee A to [site2] only
    resp_a_remove = client.put(
        f"/api/v1/employees/{emp_a_id}",
        json={"site_ids": [str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_a_remove.status_code == 200
    active_sites_after_remove = resp_a_remove.json()["active_sites"]
    assert len(active_sites_after_remove) == 1
    assert active_sites_after_remove[0]["id"] == str(master["site2_id"])

    # In DB: site1 is inactive, site2 is active, still exactly 2 records
    sync_db_session.expire_all()
    db_a_assigns_2 = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=emp_a_id).all()
    assert len(db_a_assigns_2) == 2
    a1_rec = next(a for a in db_a_assigns_2 if a.site_id == master["site1_id"])
    a2_rec = next(a for a in db_a_assigns_2 if a.site_id == master["site2_id"])
    assert a1_rec.is_active is False
    assert a1_rec.unassigned_at is not None
    assert a2_rec.is_active is True

    # 5. Re-add site1 alongside site2 (exact reproduction scenario for Michel EMP-2)
    resp_a_readd = client.put(
        f"/api/v1/employees/{emp_a_id}",
        json={"site_ids": [str(master["site1_id"]), str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_a_readd.status_code == 200
    readded_sites = resp_a_readd.json()["active_sites"]
    assert len(readded_sites) == 2
    readded_ids = {s["id"] for s in readded_sites}
    assert str(master["site1_id"]) in readded_ids
    assert str(master["site2_id"]) in readded_ids

    # Verify no duplicate records created in DB: STILL exactly 2 records, both active
    sync_db_session.expire_all()
    db_a_assigns_3 = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=emp_a_id).all()
    assert len(db_a_assigns_3) == 2
    assert all(a.is_active is True for a in db_a_assigns_3)
    assert all(a.unassigned_at is None for a in db_a_assigns_3)


def test_assign_site_endpoint_reactivates_inactive_assignment(
    client: TestClient, admin_user, setup_master_data, sync_db_session: Session
):
    """assign_site endpoint must reactivate previously unassigned site assignment without unique constraint violation."""
    from app.models.operations import EmployeeSiteAssignment

    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with site1
    resp = client.post(
        "/api/v1/employees",
        json={
            "name": "Reactivate Site Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-REACT-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 16000.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = resp.json()["id"]

    # Switch to site2, making site1 inactive
    resp_site2 = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": [str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_site2.status_code == 200

    # Call POST /api/v1/employees/{emp_id}/site-assignments with site1
    resp_assign = client.post(
        f"/api/v1/employees/{emp_id}/site-assignments",
        json={"site_id": str(master["site1_id"])},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_assign.status_code == 200
    active_sites = resp_assign.json()["active_sites"]
    active_ids = {s["id"] for s in active_sites}
    assert str(master["site1_id"]) in active_ids
    assert str(master["site2_id"]) in active_ids

    # Calling it again should be idempotent
    resp_assign_dup = client.post(
        f"/api/v1/employees/{emp_id}/site-assignments",
        json={"site_id": str(master["site1_id"])},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_assign_dup.status_code == 200

    # Verify DB has exactly 2 records, both active
    sync_db_session.expire_all()
    assigns = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=emp_id).all()
    assert len(assigns) == 2
    assert all(a.is_active is True for a in assigns)


def test_invalid_site_assignment_rejected(client: TestClient, admin_user, setup_master_data):
    """Updating with invalid/non-existent site IDs returns 404 and preserves existing assignments."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create employee with site1
    resp = client.post(
        "/api/v1/employees",
        json={
            "name": "Invalid Site Test Employee",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-INV-{str(uuid.uuid4().int)[:4]}",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 17000.0,
            "site_ids": [str(master["site1_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = resp.json()["id"]

    # Attempt to update with a non-existent site ID alongside site1
    fake_site_id = str(uuid.uuid4())
    resp_invalid = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": [str(master["site1_id"]), fake_site_id]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_invalid.status_code == 404
    err_body = resp_invalid.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "sites do not exist" in err_msg

    # Verify existing site assignments remain intact
    resp_get = client.get(
        f"/api/v1/employees/{emp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_get.status_code == 200
    active_sites = resp_get.json()["active_sites"]
    assert len(active_sites) == 1
    assert active_sites[0]["id"] == str(master["site1_id"])


def test_contract_employee_multiple_sites_and_clearing_validation(
    client: TestClient, admin_user, setup_master_data
):
    """Contract employee can have multiple sites, but clearing sites is rejected with 422."""
    _, admin_token = admin_user
    master = setup_master_data

    # Create contract employee with 2 sites
    resp = client.post(
        "/api/v1/employees",
        json={
            "name": "Contract Multi Site Worker",
            "mobile_number": f"+9198{str(uuid.uuid4().int)[:8]}",
            "employee_code": f"EMP-CON-M-{str(uuid.uuid4().int)[:4]}",
            "classification": "contract",
            "system_role": "employee",
            "trade_role_ids": [str(master["role1_id"])],
            "rate_type": "monthly",
            "rate_amount": 19000.0,
            "site_ids": [str(master["site1_id"]), str(master["site2_id"])],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    emp_id = resp.json()["id"]
    assert len(resp.json()["active_sites"]) == 2

    # Attempt to clear sites for contract employee -> 422
    resp_clear = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_clear.status_code == 422

    # Update to 1 site -> 200
    resp_one = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"site_ids": [str(master["site2_id"])]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_one.status_code == 200
    assert len(resp_one.json()["active_sites"]) == 1
    assert resp_one.json()["active_sites"][0]["id"] == str(master["site2_id"])

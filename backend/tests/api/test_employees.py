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
        "rate_type": "daily",
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
        "rate_type": "daily",
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
        "rate_type": "daily",
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
        "rate_type": "daily",
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
        "rate_type": "daily",
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
        "rate_type": "daily",
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
        "rate_type": "daily",
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

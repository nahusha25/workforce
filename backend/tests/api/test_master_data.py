import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.auth import User
from app.models.workforce import Role


@pytest.fixture
def admin_token(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+123{str(uuid.uuid4().int)[:7]}",
        role="administrator",
        is_active=True
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    return create_access_token(str(user.id), user.role)

@pytest.fixture
def employee_token(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+123{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=True
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    return create_access_token(str(user.id), user.role)

@pytest.fixture
def director_token(sync_db_session: Session):
    user = User(
        id=uuid.uuid4(),
        mobile_id=f"+123{str(uuid.uuid4().int)[:7]}",
        role="director",
        is_active=True
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    return create_access_token(str(user.id), user.role)

def test_clients_crud(client: TestClient, admin_token: str):
    # 1. Create client
    response = client.post(
        "/api/v1/admin/clients",
        json={"name": "Test Client", "contact_person": "John Doe", "is_active": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    client_id = response.json()["id"]
    
    # 2. List clients
    response = client.get(
        "/api/v1/admin/clients",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert any(c["id"] == client_id for c in response.json())

def test_projects_crud(client: TestClient, admin_token: str):
    # 1. Create a client first
    resp = client.post(
        "/api/v1/admin/clients",
        json={"name": "Client for Project"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client_id = resp.json()["id"]

    # 2. Create project
    response = client.post(
        "/api/v1/admin/projects",
        json={
            "name": "Test Project",
            "status": "Active",
            "client_id": client_id
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    # 3. List projects
    response = client.get(
        "/api/v1/admin/projects",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert any(p["id"] == project_id for p in response.json())

def test_projects_invalid_client(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/admin/projects",
        json={
            "name": "Invalid Project",
            "status": "Active",
            "client_id": str(uuid.uuid4())
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

def test_sites_crud(client: TestClient, admin_token: str):
    # Create client
    resp = client.post(
        "/api/v1/admin/clients",
        json={"name": "Client for Site"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client_id = resp.json()["id"]
    
    # Create project
    resp = client.post(
        "/api/v1/admin/projects",
        json={"name": "Project for Site", "status": "Active", "client_id": client_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    project_id = resp.json()["id"]

    # Create Site
    response = client.post(
        "/api/v1/admin/sites",
        json={
            "name": "Test Site",
            "project_id": project_id,
            "permitted_radius_m": 50.0
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    site_id = response.json()["id"]

    # List Sites
    response = client.get(
        "/api/v1/admin/sites",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert any(s["id"] == site_id for s in response.json())

def test_sites_invalid_project(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/admin/sites",
        json={
            "name": "Invalid Site",
            "project_id": str(uuid.uuid4())
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

def test_roles_list(client: TestClient, admin_token: str, sync_db_session: Session):
    role = Role(id=uuid.uuid4(), name="new_test_role")
    sync_db_session.add(role)
    sync_db_session.commit()

    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert any(r["name"] == "new_test_role" for r in response.json())

def test_unauthorized_access(client: TestClient, employee_token: str):
    endpoints = [
        ("GET", "/api/v1/admin/clients"),
        ("POST", "/api/v1/admin/clients"),
        ("GET", "/api/v1/admin/projects"),
        ("POST", "/api/v1/admin/projects"),
        ("GET", "/api/v1/admin/sites"),
        ("POST", "/api/v1/admin/sites"),
        ("GET", "/api/v1/admin/roles"),
        ("GET", "/api/v1/admin/work-orders"),
        ("POST", "/api/v1/admin/work-orders"),
        ("GET", "/api/v1/admin/activities"),
        ("POST", "/api/v1/admin/activities"),
        ("GET", "/api/v1/admin/materials"),
        ("POST", "/api/v1/admin/materials"),
    ]

    for method, url in endpoints:
        if method == "GET":
            resp = client.get(url, headers={"Authorization": f"Bearer {employee_token}"})
        else:
            resp = client.post(url, json={}, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

def test_unauthenticated_access(client: TestClient):
    response = client.get("/api/v1/admin/clients")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Work Orders, Activities, and Materials Admin Tests (BE-021)
# ---------------------------------------------------------------------------

def test_work_orders_crud(client: TestClient, admin_token: str, director_token: str):
    # 1. Create prerequisite client, project, site
    suffix = uuid.uuid4().hex[:6]
    c_res = client.post(
        "/api/v1/admin/clients",
        json={"name": f"Client WO {suffix}"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client_id = c_res.json()["id"]

    p_res = client.post(
        "/api/v1/admin/projects",
        json={"name": f"Project WO {suffix}", "status": "active", "client_id": client_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    project_id = p_res.json()["id"]

    s_res = client.post(
        "/api/v1/admin/sites",
        json={"name": f"Site WO {suffix}", "project_id": project_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    site_id = s_res.json()["id"]

    # 2. Create work order with director_token
    order_no = f"WO-{suffix}"
    wo_res = client.post(
        "/api/v1/admin/work-orders",
        json={
            "order_number": order_no,
            "project_id": project_id,
            "site_id": site_id,
            "description": "Main installation",
            "billing_basis": "per_metre",
            "status": "draft",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {director_token}"}
    )
    assert wo_res.status_code == 201, wo_res.text
    wo_data = wo_res.json()
    wo_id = wo_data["id"]
    assert wo_data["order_number"] == order_no
    assert wo_data["status"] == "draft"
    assert wo_data["is_active"] is True

    # 3. List work orders
    list_res = client.get("/api/v1/admin/work-orders", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert any(w["id"] == wo_id for w in list_res.json())

    # 4. Get single work order
    get_res = client.get(f"/api/v1/admin/work-orders/{wo_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == wo_id
    assert get_res.json()["order_number"] == order_no

    # 5. Update work order (including deactivation / soft delete is_active=False)
    upd_res = client.put(
        f"/api/v1/admin/work-orders/{wo_id}",
        json={"status": "open", "description": "Updated desc", "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["status"] == "open"
    assert upd_res.json()["description"] == "Updated desc"
    assert upd_res.json()["is_active"] is False

    # 6. Duplicate order_number -> 409 Conflict
    dup_res = client.post(
        "/api/v1/admin/work-orders",
        json={
            "order_number": order_no,
            "project_id": project_id,
            "site_id": site_id,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert dup_res.status_code == 409

    # 7. Invalid project_id -> 404
    bad_proj = client.post(
        "/api/v1/admin/work-orders",
        json={
            "order_number": f"WO-BAD-{suffix}",
            "project_id": str(uuid.uuid4()),
            "site_id": site_id,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_proj.status_code == 404

    # 8. Non-existent id -> 404
    non_get = client.get(f"/api/v1/admin/work-orders/{uuid.uuid4()}", headers={"Authorization": f"Bearer {admin_token}"})
    assert non_get.status_code == 404


def test_activities_crud(client: TestClient, admin_token: str, director_token: str):
    suffix = uuid.uuid4().hex[:6]
    name = f"Cable Pulling {suffix}"

    # 1. Create activity (test director role authorization)
    create_res = client.post(
        "/api/v1/admin/activities",
        json={
            "name": name,
            "unit_of_measure": "metre",
            "approved_rate": "12.50",
            "category": "cable",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {director_token}"}
    )
    assert create_res.status_code == 201, create_res.text
    act_data = create_res.json()
    act_id = act_data["id"]
    assert act_data["name"] == name
    assert float(act_data["approved_rate"]) == 12.50
    assert act_data["category"] == "cable"
    assert act_data["is_active"] is True

    # 2. List activities
    list_res = client.get("/api/v1/admin/activities", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert any(a["id"] == act_id for a in list_res.json())

    # 3. Get single activity
    get_res = client.get(f"/api/v1/admin/activities/{act_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == act_id

    # 4. Update activity (update rate and deactivate is_active=False)
    upd_res = client.put(
        f"/api/v1/admin/activities/{act_id}",
        json={"approved_rate": "15.00", "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upd_res.status_code == 200
    assert float(upd_res.json()["approved_rate"]) == 15.00
    assert upd_res.json()["is_active"] is False

    # 5. Invalid category -> 422
    bad_cat = client.post(
        "/api/v1/admin/activities",
        json={
            "name": "Bad Category",
            "unit_of_measure": "m",
            "approved_rate": "10.00",
            "category": "invalid_cat",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_cat.status_code == 422

    # 6. Negative approved_rate -> 422
    bad_rate = client.post(
        "/api/v1/admin/activities",
        json={
            "name": "Negative Rate",
            "unit_of_measure": "m",
            "approved_rate": "-5.00",
            "category": "cable",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_rate.status_code == 422

    # 7. Non-existent id -> 404
    non_get = client.get(f"/api/v1/admin/activities/{uuid.uuid4()}", headers={"Authorization": f"Bearer {admin_token}"})
    assert non_get.status_code == 404


def test_materials_crud(client: TestClient, admin_token: str, director_token: str):
    suffix = uuid.uuid4().hex[:6]
    name = f"Cat6 Reel {suffix}"

    # 1. Create material
    create_res = client.post(
        "/api/v1/admin/materials",
        json={
            "name": name,
            "material_code": f"MAT-{suffix}",
            "description": "305m Cat6 box",
            "unit_of_measure": "box",
            "category": "cable",
            "purchase_approval_limit": "2500.00",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {director_token}"}
    )
    assert create_res.status_code == 201, create_res.text
    mat_data = create_res.json()
    mat_id = mat_data["id"]
    assert mat_data["name"] == name
    assert float(mat_data["purchase_approval_limit"]) == 2500.00
    assert mat_data["category"] == "cable"
    assert mat_data["is_active"] is True

    # 2. List materials
    list_res = client.get("/api/v1/admin/materials", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert any(m["id"] == mat_id for m in list_res.json())

    # 3. Get single material
    get_res = client.get(f"/api/v1/admin/materials/{mat_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == mat_id

    # 4. Update material (update limit and deactivate is_active=False)
    upd_res = client.put(
        f"/api/v1/admin/materials/{mat_id}",
        json={"purchase_approval_limit": "3000.00", "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upd_res.status_code == 200
    assert float(upd_res.json()["purchase_approval_limit"]) == 3000.00
    assert upd_res.json()["is_active"] is False

    # 5. Invalid category -> 422
    bad_cat = client.post(
        "/api/v1/admin/materials",
        json={
            "name": "Bad Category Mat",
            "unit_of_measure": "pcs",
            "category": "software",
            "purchase_approval_limit": "100.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_cat.status_code == 422

    # 6. Negative purchase_approval_limit -> 422
    bad_limit = client.post(
        "/api/v1/admin/materials",
        json={
            "name": "Negative Limit",
            "unit_of_measure": "pcs",
            "category": "tool",
            "purchase_approval_limit": "-10.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert bad_limit.status_code == 422

    # 7. Non-existent id -> 404
    non_get = client.get(f"/api/v1/admin/materials/{uuid.uuid4()}", headers={"Authorization": f"Bearer {admin_token}"})
    assert non_get.status_code == 404


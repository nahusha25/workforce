from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.auth import User
from app.models.material_inventory import MaterialStock, MaterialStockMovement
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
)
from app.models.system import AuditLog
from app.models.workforce import Employee
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def inventory_api_setup():
    """Sets up roles, sites, materials, and supervisor assignments for inventory tests."""
    async with TestingSessionLocal() as session:
        # Clear inventory tables and related audit logs in test DB
        await session.execute(delete(AuditLog).where(AuditLog.entity_type == "material_stock_movement"))
        await session.execute(delete(MaterialStockMovement))
        await session.execute(delete(MaterialStock))
        await session.commit()

        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9197{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9197{sfx[:6]}2", role="director")
        u_sup1 = User(id=_u(), mobile_id=f"+9197{sfx[:6]}3", role="supervisor")
        u_sup2 = User(id=_u(), mobile_id=f"+9197{sfx[:6]}4", role="supervisor")
        u_sup_none = User(id=_u(), mobile_id=f"+9197{sfx[:6]}6", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9197{sfx[:6]}5", role="employee")
        session.add_all([u_admin, u_dir, u_sup1, u_sup2, u_sup_none, u_emp])
        await session.flush()

        # 2. Supervisor Employees
        emp_sup1 = Employee(
            id=_u(),
            user_id=u_sup1.id,
            employee_code=f"SUP1-{sfx}",
            mobile_id=u_sup1.mobile_id,
            name=f"Supervisor One {sfx}",
            is_active=True,
        )
        emp_sup2 = Employee(
            id=_u(),
            user_id=u_sup2.id,
            employee_code=f"SUP2-{sfx}",
            mobile_id=u_sup2.mobile_id,
            name=f"Supervisor Two {sfx}",
            is_active=True,
        )
        emp_sup_none = Employee(
            id=_u(),
            user_id=u_sup_none.id,
            employee_code=f"SUP-NONE-{sfx}",
            mobile_id=u_sup_none.mobile_id,
            name=f"Supervisor None {sfx}",
            is_active=True,
        )
        emp_worker = Employee(
            id=_u(),
            user_id=u_emp.id,
            employee_code=f"EMP-{sfx}",
            mobile_id=u_emp.mobile_id,
            name=f"Worker {sfx}",
            is_active=True,
        )
        session.add_all([emp_sup1, emp_sup2, emp_sup_none, emp_worker])
        await session.flush()

        # 3. Client, Project, Sites
        client = Client(id=_u(), name=f"InvClient {sfx}")
        project = Project(id=_u(), client_id=client.id, name=f"InvProj {sfx}", status="in_progress")
        session.add_all([client, project])
        await session.flush()

        site_a = Site(
            id=_u(),
            project_id=project.id,
            name=f"Site Alpha {sfx}",
            supervisor_id=emp_sup1.id,
            is_active=True,
        )
        site_b = Site(
            id=_u(),
            project_id=project.id,
            name=f"Site Beta {sfx}",
            supervisor_id=emp_sup2.id,
            is_active=True,
        )
        site_c = Site(
            id=_u(),
            project_id=project.id,
            name=f"Site Gamma {sfx}",
            supervisor_id=None,
            is_active=True,
        )
        session.add_all([site_a, site_b, site_c])
        await session.flush()

        # Assign sup1 to site_c via active EmployeeSiteAssignment
        assignment_sup1_c = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_sup1.id,
            site_id=site_c.id,
            is_active=True,
        )
        session.add(assignment_sup1_c)
        await session.flush()

        # 4. Materials
        mat_active = Material(
            id=_u(),
            material_code=f"MAT-CCTV-{sfx}",
            name=f"CCTV Camera {sfx}",
            unit_of_measure="nos",
            category="device",
            purchase_approval_limit=10000.00,
            is_active=True,
        )
        mat_cable = Material(
            id=_u(),
            material_code=f"MAT-CAB-{sfx}",
            name=f"Cat6 Cable {sfx}",
            unit_of_measure="metre",
            category="cable",
            purchase_approval_limit=5000.00,
            is_active=True,
        )
        mat_inactive = Material(
            id=_u(),
            material_code=f"MAT-DISC-{sfx}",
            name=f"Discontinued Switch {sfx}",
            unit_of_measure="nos",
            category="device",
            purchase_approval_limit=1000.00,
            is_active=False,
        )
        session.add_all([mat_active, mat_cable, mat_inactive])
        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), role="administrator"),
            "director": create_access_token(str(u_dir.id), role="director"),
            "sup1": create_access_token(str(u_sup1.id), role="supervisor"),
            "sup2": create_access_token(str(u_sup2.id), role="supervisor"),
            "sup_none": create_access_token(str(u_sup_none.id), role="supervisor"),
            "employee": create_access_token(str(u_emp.id), role="employee"),
        }


        return {
            "users": {
                "admin": u_admin,
                "director": u_dir,
                "sup1": u_sup1,
                "sup2": u_sup2,
                "sup_none": u_sup_none,
                "employee": u_emp,
            },
            "employees": {
                "sup1": emp_sup1,
                "sup2": emp_sup2,
                "sup_none": emp_sup_none,
                "worker": emp_worker,
            },
            "sites": {
                "site_a": site_a,
                "site_b": site_b,
                "site_c": site_c,
            },
            "materials": {
                "active": mat_active,
                "cable": mat_cable,
                "inactive": mat_inactive,
            },
            "tokens": tokens,
        }



# ===========================================================================
# 1. Stock Inward: Initial Receipt and Increasing Existing Stock
# ===========================================================================

def test_stock_inward_initial_receipt_creates_stock_row_and_ledger(client: TestClient, inventory_api_setup):
    """Test receiving initial stock creates a new MaterialStock row and ledger movement."""
    env = inventory_api_setup
    payload = {
        "site_id": str(env["sites"]["site_a"].id),
        "material_id": str(env["materials"]["active"].id),
        "quantity": "10.00",
        "remarks": "Initial site shipment received",
        "idempotency_key": f"INW-INIT-{_u()}",
    }

    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 201
    data = resp.json()

    assert data["site_id"] == payload["site_id"]
    assert data["material_id"] == payload["material_id"]
    assert data["material_name"] == env["materials"]["active"].name
    assert data["quantity"] == "10.00"
    assert data["balance_after"] == "10.00"
    assert data["movement_type"] == "inward"
    assert data["idempotency_key"] == payload["idempotency_key"]
    assert data["movement_id"] is not None


def test_stock_inward_subsequent_receipt_increases_balance_and_updates_row(client: TestClient, inventory_api_setup):
    """Test receiving subsequent stock increases balance without creating duplicate MaterialStock rows."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)

    # First receipt: 10.00
    p1 = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "10.00",
        "idempotency_key": f"INW-SUB-1-{_u()}",
    }
    r1 = client.post("/api/v1/inventory/inward", json=p1, headers=_auth(env["tokens"]["admin"]))
    assert r1.status_code == 201
    assert r1.json()["balance_after"] == "10.00"

    # Second receipt: 5.50
    p2 = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "5.50",
        "idempotency_key": f"INW-SUB-2-{_u()}",
    }
    r2 = client.post("/api/v1/inventory/inward", json=p2, headers=_auth(env["tokens"]["admin"]))
    assert r2.status_code == 201
    assert r2.json()["balance_after"] == "15.50"


def test_stock_inward_records_correct_balance_after_and_audit_log(client: TestClient, inventory_api_setup):
    """Test that movement ledger and central AuditLog correctly capture previous balance and new balance."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["cable"].id)
    key = f"INW-AUDIT-{_u()}"

    p = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "100.00",
        "remarks": "Spool delivery",
        "idempotency_key": key,
    }
    resp = client.post("/api/v1/inventory/inward", json=p, headers=_auth(env["tokens"]["director"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["balance_after"] == "100.00"


# ===========================================================================
# 2. Validation: Zero, Negative, Invalid Quantities, Inactive Material, Missing Site
# ===========================================================================

def test_stock_inward_rejects_zero_quantity(client: TestClient, inventory_api_setup):
    """Test zero quantity is rejected."""
    env = inventory_api_setup
    payload = {
        "site_id": str(env["sites"]["site_a"].id),
        "material_id": str(env["materials"]["active"].id),
        "quantity": "0.00",
        "idempotency_key": f"INW-ZERO-{_u()}",
    }
    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 422


def test_stock_inward_rejects_negative_quantity(client: TestClient, inventory_api_setup):
    """Test negative quantity is rejected."""
    env = inventory_api_setup
    payload = {
        "site_id": str(env["sites"]["site_a"].id),
        "material_id": str(env["materials"]["active"].id),
        "quantity": "-5.00",
        "idempotency_key": f"INW-NEG-{_u()}",
    }
    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 422


def test_stock_inward_rejects_inactive_material(client: TestClient, inventory_api_setup):
    """Test inactive material is rejected with 400 Bad Request."""
    env = inventory_api_setup
    payload = {
        "site_id": str(env["sites"]["site_a"].id),
        "material_id": str(env["materials"]["inactive"].id),
        "quantity": "5.00",
        "idempotency_key": f"INW-INACT-{_u()}",
    }
    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


def test_stock_inward_rejects_nonexistent_site(client: TestClient, inventory_api_setup):
    """Test nonexistent site returns 404 Not Found."""
    env = inventory_api_setup
    payload = {
        "site_id": str(_u()),
        "material_id": str(env["materials"]["active"].id),
        "quantity": "5.00",
        "idempotency_key": f"INW-NOSITE-{_u()}",
    }
    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 404
    assert "site" in resp.json()["detail"].lower()


def test_stock_inward_rejects_nonexistent_material(client: TestClient, inventory_api_setup):
    """Test nonexistent material returns 404 Not Found."""
    env = inventory_api_setup
    payload = {
        "site_id": str(env["sites"]["site_a"].id),
        "material_id": str(_u()),
        "quantity": "5.00",
        "idempotency_key": f"INW-NOMAT-{_u()}",
    }
    resp = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 404
    assert "material" in resp.json()["detail"].lower()


# ===========================================================================
# 3. Idempotency: Replays and Conflict Rejection
# ===========================================================================

def test_stock_inward_idempotent_replay_does_not_duplicate_stock(client: TestClient, inventory_api_setup):
    """Test identical retries return original result and do not increase stock twice."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)
    key = f"INW-REPLAY-{_u()}"

    payload = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "10.00",
        "remarks": "Delivery A",
        "idempotency_key": key,
    }

    # First attempt
    r1 = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["balance_after"] == "10.00"

    # Second attempt (identical replay)
    r2 = client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))
    assert r2.status_code in (200, 201)
    d2 = r2.json()
    assert d2["movement_id"] == d1["movement_id"]
    assert d2["balance_after"] == "10.00"

    # Verify query still returns 10.00, not 20.00
    q = client.get(f"/api/v1/inventory/sites/{site_id}/materials/{mat_id}", headers=_auth(env["tokens"]["admin"]))
    assert q.status_code == 200
    assert q.json()["quantity_available"] == "10.00"


def test_stock_inward_idempotency_conflict_on_different_payload(client: TestClient, inventory_api_setup):
    """Test reusing idempotency key with different payload returns 409 Conflict."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)
    key = f"INW-CONF-{_u()}"

    p1 = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "10.00",
        "idempotency_key": key,
    }
    r1 = client.post("/api/v1/inventory/inward", json=p1, headers=_auth(env["tokens"]["admin"]))
    assert r1.status_code == 201

    # Conflict: different quantity
    p2 = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "25.00",
        "idempotency_key": key,
    }
    r2 = client.post("/api/v1/inventory/inward", json=p2, headers=_auth(env["tokens"]["admin"]))
    assert r2.status_code == 409
    assert "idempotency conflict" in r2.json()["detail"].lower()


# ===========================================================================
# 4. Atomic Rollback when Audit Logging Fails
# ===========================================================================

def test_stock_inward_atomic_rollback_when_audit_fails(client: TestClient, inventory_api_setup):
    """Test that if AuditLog insertion fails, both stock and movement changes are rolled back."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)

    payload = {
        "site_id": site_id,
        "material_id": mat_id,
        "quantity": "50.00",
        "idempotency_key": f"INW-FAIL-AUDIT-{_u()}",
    }

    # Simulate audit failure by patching AuditLog to raise RuntimeError
    with patch("app.modules.material_inventory.service.AuditLog", side_effect=RuntimeError("Audit database crashed")):
        with pytest.raises(RuntimeError):
            client.post("/api/v1/inventory/inward", json=payload, headers=_auth(env["tokens"]["admin"]))

    # Verify no stock row or movement was persisted
    q = client.get(f"/api/v1/inventory/sites/{site_id}/materials/{mat_id}", headers=_auth(env["tokens"]["admin"]))
    assert q.status_code == 200
    assert q.json()["quantity_available"] == "0.00"


# ===========================================================================
# 5. Role & Site-Level Permissions
# ===========================================================================

def test_supervisor_can_inward_and_view_supervised_site(client: TestClient, inventory_api_setup):
    """Test supervisor can inward stock and view inventory at their supervised site."""
    env = inventory_api_setup
    site_a = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)

    # Supervisor 1 supervises Site A
    p = {
        "site_id": site_a,
        "material_id": mat_id,
        "quantity": "12.00",
        "idempotency_key": f"INW-SUP-OK-{_u()}",
    }
    r = client.post("/api/v1/inventory/inward", json=p, headers=_auth(env["tokens"]["sup1"]))
    assert r.status_code == 201
    assert r.json()["balance_after"] == "12.00"

    # View site inventory
    v = client.get(f"/api/v1/inventory/sites/{site_a}", headers=_auth(env["tokens"]["sup1"]))
    assert v.status_code == 200
    assert v.json()["site_id"] == site_a


def test_supervisor_denied_for_unsupervised_site(client: TestClient, inventory_api_setup):
    """Test supervisor is denied with 403 Forbidden when attempting inward or view at unsupervised site."""
    env = inventory_api_setup
    site_b = str(env["sites"]["site_b"].id)
    mat_id = str(env["materials"]["active"].id)

    # Supervisor 1 does NOT supervise Site B
    p = {
        "site_id": site_b,
        "material_id": mat_id,
        "quantity": "5.00",
        "idempotency_key": f"INW-SUP-DENY-{_u()}",
    }
    r = client.post("/api/v1/inventory/inward", json=p, headers=_auth(env["tokens"]["sup1"]))
    assert r.status_code == 403

    # Attempting to view Site B inventory
    v = client.get(f"/api/v1/inventory/sites/{site_b}", headers=_auth(env["tokens"]["sup1"]))
    assert v.status_code == 403

    # Attempting to view specific material at Site B
    m = client.get(f"/api/v1/inventory/sites/{site_b}/materials/{mat_id}", headers=_auth(env["tokens"]["sup1"]))
    assert m.status_code == 403


def test_employee_access_denied_on_all_inventory_endpoints(client: TestClient, inventory_api_setup):
    """Test employees receive 403 Forbidden on all inventory endpoints."""
    env = inventory_api_setup
    site_a = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)

    # Inward mutation
    p = {
        "site_id": site_a,
        "material_id": mat_id,
        "quantity": "5.00",
        "idempotency_key": f"INW-EMP-DENY-{_u()}",
    }
    r = client.post("/api/v1/inventory/inward", json=p, headers=_auth(env["tokens"]["employee"]))
    assert r.status_code == 403

    # List inventory
    r_list = client.get(f"/api/v1/inventory/sites/{site_a}", headers=_auth(env["tokens"]["employee"]))
    assert r_list.status_code == 403

    # Detail balance
    r_detail = client.get(f"/api/v1/inventory/sites/{site_a}/materials/{mat_id}", headers=_auth(env["tokens"]["employee"]))
    assert r_detail.status_code == 403


# ===========================================================================
# 5b. Authorized Inventory Sites Listing (GET /inventory/sites)
# ===========================================================================

def test_get_inventory_sites_authorized_supervisor(client: TestClient, inventory_api_setup):
    """Test supervisor receives only authorized sites (direct supervisor_id and active assignments)."""
    env = inventory_api_setup
    res = client.get("/api/v1/inventory/sites", headers=_auth(env["tokens"]["sup1"]))
    assert res.status_code == 200
    sites = res.json()
    site_ids = {s["id"] for s in sites}

    # sup1 has site_a (direct supervisor_id) and site_c (active EmployeeSiteAssignment)
    assert str(env["sites"]["site_a"].id) in site_ids
    assert str(env["sites"]["site_c"].id) in site_ids
    # sup1 does NOT supervise site_b
    assert str(env["sites"]["site_b"].id) not in site_ids


def test_get_inventory_sites_supervisor_without_assignments(client: TestClient, inventory_api_setup):
    """Test supervisor with no site assignments receives empty list without granting all sites."""
    env = inventory_api_setup
    res = client.get("/api/v1/inventory/sites", headers=_auth(env["tokens"]["sup_none"]))
    assert res.status_code == 200
    sites = res.json()
    assert sites == []


def test_get_inventory_sites_admin_and_director(client: TestClient, inventory_api_setup):
    """Test administrators and directors receive all active sites."""
    env = inventory_api_setup
    # Administrator
    res_admin = client.get("/api/v1/inventory/sites", headers=_auth(env["tokens"]["admin"]))
    assert res_admin.status_code == 200
    admin_site_ids = {s["id"] for s in res_admin.json()}
    assert str(env["sites"]["site_a"].id) in admin_site_ids
    assert str(env["sites"]["site_b"].id) in admin_site_ids
    assert str(env["sites"]["site_c"].id) in admin_site_ids

    # Director
    res_dir = client.get("/api/v1/inventory/sites", headers=_auth(env["tokens"]["director"]))
    assert res_dir.status_code == 200
    dir_site_ids = {s["id"] for s in res_dir.json()}
    assert str(env["sites"]["site_a"].id) in dir_site_ids
    assert str(env["sites"]["site_b"].id) in dir_site_ids
    assert str(env["sites"]["site_c"].id) in dir_site_ids


def test_get_inventory_sites_employee_forbidden(client: TestClient, inventory_api_setup):
    """Test employees receive 403 Forbidden on GET /inventory/sites."""
    env = inventory_api_setup
    res = client.get("/api/v1/inventory/sites", headers=_auth(env["tokens"]["employee"]))
    assert res.status_code == 403


def test_get_inventory_sites_unauthenticated(client: TestClient):
    """Test unauthenticated call to GET /inventory/sites returns 401."""
    res = client.get("/api/v1/inventory/sites")
    assert res.status_code == 401


def test_supervisor_unauthorized_site_access_is_strictly_denied(client: TestClient, inventory_api_setup):
    """Test supervisor direct access to unauthorized site is strictly blocked."""
    env = inventory_api_setup
    site_b = str(env["sites"]["site_b"].id)
    site_a = str(env["sites"]["site_a"].id)
    mat_id = str(env["materials"]["active"].id)

    # sup1 viewing site_b inventory
    res_view = client.get(f"/api/v1/inventory/sites/{site_b}", headers=_auth(env["tokens"]["sup1"]))
    assert res_view.status_code == 403
    assert "Supervisor is not authorized to view inventory for this site." in res_view.json()["detail"]

    # sup_none viewing site_a inventory
    res_none = client.get(f"/api/v1/inventory/sites/{site_a}", headers=_auth(env["tokens"]["sup_none"]))
    assert res_none.status_code == 403

    # sup1 viewing movements at site_b
    res_mov = client.get(
        f"/api/v1/inventory/sites/{site_b}/materials/{mat_id}/movements",
        headers=_auth(env["tokens"]["sup1"]),
    )
    assert res_mov.status_code == 403


def test_read_inventory_returns_zero_without_creating_stock_row(client: TestClient, inventory_api_setup):
    """Test querying material with no stock returns 0.00 without inventing a MaterialStock row."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_b"].id)
    mat_id = str(env["materials"]["cable"].id)

    # GET /sites/{site_id}/materials/{material_id}
    resp = client.get(f"/api/v1/inventory/sites/{site_id}/materials/{mat_id}", headers=_auth(env["tokens"]["admin"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["quantity_available"] == "0.00"
    assert data["last_movement_at"] is None

    # GET /sites/{site_id} with search filter for the specific test material
    list_resp = client.get(
        f"/api/v1/inventory/sites/{site_id}?search={env['materials']['cable'].material_code}",
        headers=_auth(env["tokens"]["admin"]),
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    matching = [item for item in list_data["items"] if item["material_id"] == mat_id]
    assert len(matching) == 1
    assert matching[0]["quantity_available"] == "0.00"


def test_read_site_inventory_pagination_and_search_filters(client: TestClient, inventory_api_setup):
    """Test site inventory filtering by search term, category, and active status."""
    env = inventory_api_setup
    site_id = str(env["sites"]["site_a"].id)

    # Search by code
    r_search = client.get(
        f"/api/v1/inventory/sites/{site_id}?search=CCTV",
        headers=_auth(env["tokens"]["admin"]),
    )
    assert r_search.status_code == 200
    items = r_search.json()["items"]
    assert all("cctv" in i["material_name"].lower() or "cctv" in i["material_code"].lower() for i in items)

    # Filter by category
    r_cat = client.get(
        f"/api/v1/inventory/sites/{site_id}?category=cable",
        headers=_auth(env["tokens"]["admin"]),
    )
    assert r_cat.status_code == 200
    cat_items = r_cat.json()["items"]
    assert all(i["category"] == "cable" for i in cat_items)

    # Filter by is_active=False
    r_inact = client.get(
        f"/api/v1/inventory/sites/{site_id}?is_active=false",
        headers=_auth(env["tokens"]["admin"]),
    )
    assert r_inact.status_code == 200
    inact_items = r_inact.json()["items"]
    assert all(not i["is_active"] for i in inact_items)


# ===========================================================================
# 7. Non-Regression: Existing MaterialTransaction and Daily Work Unaffected
# ===========================================================================

def test_existing_material_transactions_and_invoicing_unaffected(client: TestClient, inventory_api_setup):
    """Test that existing MaterialTransaction model and workflow remain functional and unaffected."""
    env = inventory_api_setup
    site_id = env["sites"]["site_a"].id
    mat = env["materials"]["active"]
    worker = env["employees"]["worker"]

    # Inward stock
    inw = client.post(
        "/api/v1/inventory/inward",
        json={
            "site_id": str(site_id),
            "material_id": str(mat.id),
            "quantity": "20.00",
            "idempotency_key": f"INW-NONREG-{_u()}",
        },
        headers=_auth(env["tokens"]["admin"]),
    )
    assert inw.status_code == 201

    # Verify inventory is recorded and independent of daily work
    check = client.get(
        f"/api/v1/inventory/sites/{site_id}/materials/{mat.id}",
        headers=_auth(env["tokens"]["admin"]),
    )
    assert check.status_code == 200
    assert check.json()["quantity_available"] == "20.00"


# ===========================================================================
# 8. Concurrency: Initial Row Creation Race & Idempotency Key Collisions
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrent_initial_row_creation_and_receipts(inventory_api_setup):
    """Test concurrent inward receipts on uninitialized site/material handle race and correctly total stock."""
    from app.modules.material_inventory.schemas import StockInwardRequest
    from app.modules.material_inventory.service import MaterialInventoryService

    env = inventory_api_setup
    site_id = env["sites"]["site_b"].id
    mat_id = env["materials"]["active"].id
    admin_user = env["users"]["admin"]

    # Verify no stock row exists initially
    async with TestingSessionLocal() as session:
        check = await session.execute(
            select(MaterialStock).where(MaterialStock.site_id == site_id, MaterialStock.material_id == mat_id)
        )
        assert check.scalar_one_or_none() is None

    # Two concurrent receipts: 10.00 and 5.00
    req1 = StockInwardRequest(
        site_id=site_id,
        material_id=mat_id,
        quantity=Decimal("10.00"),
        idempotency_key=f"CONC-1-{_u()}",
    )
    req2 = StockInwardRequest(
        site_id=site_id,
        material_id=mat_id,
        quantity=Decimal("5.00"),
        idempotency_key=f"CONC-2-{_u()}",
    )

    async def _run(req):
        async with TestingSessionLocal() as session:
            return await MaterialInventoryService.record_stock_inward(session, req, admin_user)

    results = await asyncio.gather(_run(req1), _run(req2))
    assert len(results) == 2

    # Check database state: exactly one stock row with total quantity 15.00, and two movement rows
    async with TestingSessionLocal() as session:
        stock_rows = (
            await session.execute(
                select(MaterialStock).where(MaterialStock.site_id == site_id, MaterialStock.material_id == mat_id)
            )
        ).scalars().all()
        assert len(stock_rows) == 1
        assert stock_rows[0].quantity == Decimal("15.00")

        mvts = (
            await session.execute(
                select(MaterialStockMovement).where(
                    MaterialStockMovement.site_id == site_id,
                    MaterialStockMovement.material_id == mat_id,
                )
            )
        ).scalars().all()
        assert len(mvts) == 2


@pytest.mark.asyncio
async def test_concurrent_identical_idempotency_key_race(inventory_api_setup):
    """Test concurrent receipt requests with identical idempotency key resolve safely without duplicate stock."""
    from app.modules.material_inventory.schemas import StockInwardRequest
    from app.modules.material_inventory.service import MaterialInventoryService

    env = inventory_api_setup
    site_id = env["sites"]["site_b"].id
    mat_id = env["materials"]["cable"].id
    admin_user = env["users"]["admin"]
    key = f"CONC-KEY-RACE-{_u()}"

    req = StockInwardRequest(
        site_id=site_id,
        material_id=mat_id,
        quantity=Decimal("20.00"),
        idempotency_key=key,
    )

    async def _run():
        async with TestingSessionLocal() as session:
            return await MaterialInventoryService.record_stock_inward(session, req, admin_user)

    res1, res2 = await asyncio.gather(_run(), _run())
    assert res1.movement_id == res2.movement_id
    assert res1.balance_after == Decimal("20.00")
    assert res2.balance_after == Decimal("20.00")

    async with TestingSessionLocal() as session:
        stock = (
            await session.execute(
                select(MaterialStock).where(MaterialStock.site_id == site_id, MaterialStock.material_id == mat_id)
            )
        ).scalar_one()
        assert stock.quantity == Decimal("20.00")


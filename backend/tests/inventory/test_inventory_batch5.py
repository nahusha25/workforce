from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.auth import User
from app.models.material_inventory import MaterialStock, MaterialStockMovement
from app.models.operations import Client, EmployeeSiteAssignment, Material, Project, Site
from app.models.system import AuditLog
from app.models.workforce import Employee
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_inventory_batch5_endpoints(client: TestClient):
    """Test stock movement history and daily work availability endpoints with RBAC enforcement."""
    async with TestingSessionLocal() as session:
        # Clean test inventory
        await session.execute(delete(AuditLog).where(AuditLog.entity_type == "material_stock_movement"))
        await session.execute(delete(MaterialStockMovement))
        await session.execute(delete(MaterialStock))
        await session.commit()

        sfx = str(_u())[:8]

        # 1. Users & Roles
        u_admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="administrator")
        u_sup = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="supervisor")
        u_sup_other = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        u_emp_assigned = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")
        u_emp_unassigned = User(id=_u(), mobile_id=f"+9198{sfx[:6]}5", role="employee")
        session.add_all([u_admin, u_sup, u_sup_other, u_emp_assigned, u_emp_unassigned])
        await session.flush()

        # 2. Employees
        emp_sup = Employee(
            id=_u(),
            user_id=u_sup.id,
            employee_code=f"SUP-{sfx}",
            mobile_id=u_sup.mobile_id,
            name=f"Supervisor {sfx}",
            is_active=True,
        )
        emp_assigned = Employee(
            id=_u(),
            user_id=u_emp_assigned.id,
            employee_code=f"EMPA-{sfx}",
            mobile_id=u_emp_assigned.mobile_id,
            name=f"Assigned Worker {sfx}",
            is_active=True,
        )
        emp_unassigned = Employee(
            id=_u(),
            user_id=u_emp_unassigned.id,
            employee_code=f"EMPU-{sfx}",
            mobile_id=u_emp_unassigned.mobile_id,
            name=f"Unassigned Worker {sfx}",
            is_active=True,
        )
        session.add_all([emp_sup, emp_assigned, emp_unassigned])
        await session.flush()

        # 3. Client, Project, Sites
        client_obj = Client(id=_u(), name=f"Batch5 Client {sfx}")
        project = Project(id=_u(), client_id=client_obj.id, name=f"Batch5 Project {sfx}", status="active")
        session.add_all([client_obj, project])
        await session.flush()

        site = Site(
            id=_u(),
            project_id=project.id,
            name=f"Batch5 Site {sfx}",
            supervisor_id=emp_sup.id,
            permitted_radius_m=1000.0,
        )
        session.add(site)
        await session.flush()

        # 4. Active Assignment for emp_assigned to site
        asgn = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_assigned.id,
            site_id=site.id,
            is_active=True,
        )
        session.add(asgn)

        # 5. Material & Initial Stock + Movement
        material = Material(
            id=_u(),
            material_code=f"MAT5-{sfx}",
            name=f"Cat6 Cable Roll {sfx}",
            unit_of_measure="roll",
            category="cable",
            purchase_approval_limit=5000.0,
            is_active=True,
        )
        session.add(material)
        await session.flush()

        stock = MaterialStock(
            site_id=site.id,
            material_id=material.id,
            quantity=Decimal("15.00"),
        )
        mvt1 = MaterialStockMovement(
            site_id=site.id,
            material_id=material.id,
            movement_type="inward",
            quantity=Decimal("20.00"),
            balance_after=Decimal("20.00"),
            idempotency_key=f"INW-TEST-{_u()}",
            remarks="Initial shipment",
            created_by=u_admin.id,
        )
        mvt2 = MaterialStockMovement(
            site_id=site.id,
            material_id=material.id,
            movement_type="consumed",
            quantity=Decimal("5.00"),
            balance_after=Decimal("15.00"),
            idempotency_key=f"CON-TEST-{_u()}",
            remarks="Daily consumption",
            created_by=u_sup.id,
        )
        session.add_all([stock, mvt1, mvt2])
        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), role="administrator"),
            "sup": create_access_token(str(u_sup.id), role="supervisor"),
            "sup_other": create_access_token(str(u_sup_other.id), role="supervisor"),
            "emp_assigned": create_access_token(str(u_emp_assigned.id), role="employee"),
            "emp_unassigned": create_access_token(str(u_emp_unassigned.id), role="employee"),
        }

    site_str = str(site.id)
    mat_str = str(material.id)

    # 1. Stock Movement History Endpoint
    # Admin access -> 200 OK with 2 movements
    r = client.get(
        f"/api/v1/inventory/sites/{site_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["admin"]),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["movement_type"] == "consumed"
    assert data["items"][0]["quantity"] == "5.00"
    assert data["items"][0]["balance_after"] == "15.00"
    assert data["items"][1]["movement_type"] == "inward"
    assert data["items"][1]["quantity"] == "20.00"
    assert data["items"][1]["balance_after"] == "20.00"

    # Authorized Supervisor access -> 200 OK
    r = client.get(
        f"/api/v1/inventory/sites/{site_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["sup"]),
    )
    assert r.status_code == 200

    # Unauthorized Supervisor access -> 403 Forbidden
    r = client.get(
        f"/api/v1/inventory/sites/{site_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["sup_other"]),
    )
    assert r.status_code == 403

    # Employee access to inventory movements -> 403 Forbidden
    r = client.get(
        f"/api/v1/inventory/sites/{site_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["emp_assigned"]),
    )
    assert r.status_code == 403

    # 2. Daily Work Stock Availability Endpoint
    # Assigned employee access -> 200 OK with available quantity 15.00
    r_avail = client.get(
        f"/api/v1/daily-work/sites/{site_str}/materials/{mat_str}/availability",
        headers=_auth(tokens["emp_assigned"]),
    )
    assert r_avail.status_code == 200
    avail_data = r_avail.json()
    assert avail_data["quantity_available"] == "15.00"
    assert avail_data["material_id"] == mat_str
    assert avail_data["unit_of_measure"] == "roll"

    # Unassigned employee access -> 403 Forbidden
    r_unassigned = client.get(
        f"/api/v1/daily-work/sites/{site_str}/materials/{mat_str}/availability",
        headers=_auth(tokens["emp_unassigned"]),
    )
    assert r_unassigned.status_code == 403

    # Admin access to availability -> 200 OK
    r_admin_avail = client.get(
        f"/api/v1/daily-work/sites/{site_str}/materials/{mat_str}/availability",
        headers=_auth(tokens["admin"]),
    )
    assert r_admin_avail.status_code == 200

    # Querying unstocked material -> returns 0.00 without error
    fake_mat = str(_u())
    r_not_found = client.get(
        f"/api/v1/daily-work/sites/{site_str}/materials/{fake_mat}/availability",
        headers=_auth(tokens["emp_assigned"]),
    )
    assert r_not_found.status_code == 404

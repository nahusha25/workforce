from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
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
async def test_material_inventory_end_to_end_verification(client: TestClient):
    """Full end-to-end controlled verification for Material Inventory Batches 1–5."""

    async with TestingSessionLocal() as session:
        # Pre-flight check: Verify we are strictly running against the isolated test database
        res_db = await session.execute(text("SELECT current_database()"))
        current_db = res_db.scalar()
        assert current_db == "workforce_test_test", (
            f"SAFETY ABORT: Test attempted against non-isolated database: {current_db}"
        )

        sfx = str(_u())[:8]

        # 1. Setup Users & Roles
        u_admin = User(id=_u(), mobile_id=f"+9188{sfx[:6]}1", role="administrator")
        u_sup_a = User(id=_u(), mobile_id=f"+9188{sfx[:6]}2", role="supervisor")
        u_sup_b = User(id=_u(), mobile_id=f"+9188{sfx[:6]}3", role="supervisor")
        u_emp_assigned = User(id=_u(), mobile_id=f"+9188{sfx[:6]}4", role="employee")
        u_emp_unassigned = User(id=_u(), mobile_id=f"+9188{sfx[:6]}5", role="employee")
        session.add_all([u_admin, u_sup_a, u_sup_b, u_emp_assigned, u_emp_unassigned])
        await session.flush()

        # 2. Setup Employees
        emp_sup_a = Employee(
            id=_u(),
            user_id=u_sup_a.id,
            employee_code=f"SUPA-{sfx}",
            mobile_id=u_sup_a.mobile_id,
            name=f"Supervisor A {sfx}",
            is_active=True,
        )
        emp_sup_b = Employee(
            id=_u(),
            user_id=u_sup_b.id,
            employee_code=f"SUPB-{sfx}",
            mobile_id=u_sup_b.mobile_id,
            name=f"Supervisor B {sfx}",
            is_active=True,
        )
        emp_assigned = Employee(
            id=_u(),
            user_id=u_emp_assigned.id,
            employee_code=f"EMPA-{sfx}",
            mobile_id=u_emp_assigned.mobile_id,
            name=f"Worker Assigned {sfx}",
            supervisor_id=emp_sup_a.id,
            is_active=True,
        )
        emp_unassigned = Employee(
            id=_u(),
            user_id=u_emp_unassigned.id,
            employee_code=f"EMPU-{sfx}",
            mobile_id=u_emp_unassigned.mobile_id,
            name=f"Worker Unassigned {sfx}",
            is_active=True,
        )
        session.add_all([emp_sup_a, emp_sup_b, emp_assigned, emp_unassigned])
        await session.flush()

        # 3. Setup Client, Project, Sites
        client_obj = Client(id=_u(), name=f"E2E Client {sfx}")
        project = Project(id=_u(), client_id=client_obj.id, name=f"E2E Project {sfx}", status="active")
        session.add_all([client_obj, project])
        await session.flush()

        site_a = Site(
            id=_u(),
            project_id=project.id,
            name=f"Site A {sfx}",
            supervisor_id=emp_sup_a.id,
            permitted_radius_m=1000.0,
        )
        site_b = Site(
            id=_u(),
            project_id=project.id,
            name=f"Site B {sfx}",
            supervisor_id=emp_sup_b.id,
            permitted_radius_m=1000.0,
        )
        session.add_all([site_a, site_b])
        await session.flush()

        # 4. Active Assignment: emp_assigned -> site_a
        assignment = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_assigned.id,
            site_id=site_a.id,
            is_active=True,
        )
        session.add(assignment)

        # 5. Catalogue Material
        material = Material(
            id=_u(),
            material_code=f"E2E-MAT-{sfx}",
            name=f"Cat6 Cable Roll {sfx}",
            unit_of_measure="roll",
            category="cable",
            purchase_approval_limit=5000.0,
            is_active=True,
        )
        session.add(material)
        await session.flush()

        # 6. Activity, Attendance, Daily Work Entry
        activity = Activity(
            id=_u(),
            name=f"Cabling-{sfx}",
            unit_of_measure="roll",
            approved_rate=50.0,
            category="cable",
        )
        session.add(activity)
        await session.flush()

        att = AttendanceRecord(
            id=_u(),
            employee_id=emp_assigned.id,
            site_id=site_a.id,
            date=date.today(),
            session_number=1,
            check_in_time=datetime.now(timezone.utc),
            working_hours=8.0,
            is_within_geofence=True,
            status="verified",
        )
        session.add(att)
        await session.flush()

        dwe = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"DWE-{sfx}-{_u()}",
            attendance_record_id=att.id,
            employee_id=emp_assigned.id,
            site_id=site_a.id,
            activity_id=activity.id,
            work_date=date.today(),
            quantity=5.0,
            uom="roll",
            status="submitted",
        )
        session.add(dwe)
        await session.commit()

        # Auth Tokens
        tokens = {
            "admin": create_access_token(str(u_admin.id), role="administrator"),
            "sup_a": create_access_token(str(u_sup_a.id), role="supervisor"),
            "sup_b": create_access_token(str(u_sup_b.id), role="supervisor"),
            "emp_assigned": create_access_token(str(u_emp_assigned.id), role="employee"),
            "emp_unassigned": create_access_token(str(u_emp_unassigned.id), role="employee"),
        }

    site_a_str = str(site_a.id)
    site_b_str = str(site_b.id)
    mat_str = str(material.id)

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 1: Stock Inward (Receive 10 units at Site A)
    # -------------------------------------------------------------------------
    inward_idemp = f"INW-E2E-{_u()}"
    inward_payload = {
        "site_id": site_a_str,
        "material_id": mat_str,
        "quantity": 10.0,
        "idempotency_key": inward_idemp,
        "remarks": "E2E delivery shipment of 10 rolls",
    }
    r_inw = client.post(
        "/api/v1/inventory/inward",
        json=inward_payload,
        headers=_auth(tokens["sup_a"]),
    )
    assert r_inw.status_code == 201, f"Stock inward failed: {r_inw.text}"
    inw_data = r_inw.json()
    assert inw_data["quantity"] == "10.00"
    assert inw_data["balance_after"] == "10.00"
    assert inw_data["movement_type"] == "inward"
    inward_movement_id = inw_data["movement_id"]

    # Confirm balance via Site Inventory API is 10.00 (filter by test material code)
    r_inv = client.get(
        f"/api/v1/inventory/sites/{site_a_str}?search={material.material_code}",
        headers=_auth(tokens["sup_a"]),
    )
    assert r_inv.status_code == 200
    inv_items = r_inv.json()["items"]
    mat_inv = next(item for item in inv_items if item["material_id"] == mat_str)
    assert mat_inv["quantity_available"] == "10.00"

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 2: Consumption (2 units consumed, submitted, approved)
    # -------------------------------------------------------------------------
    async with TestingSessionLocal() as session:
        tx_consumed = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe.id,
            material_id=material.id,
            site_id=site_a.id,
            transaction_type="consumed",
            item_name=material.name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx_consumed)
        await session.commit()
        tx_id_str = str(tx_consumed.id)

    approve_idemp = f"APP-E2E-{_u()}"
    approve_payload = {
        "entity_type": "material",
        "idempotency_key": approve_idemp,
        "remarks": "Approved 2 rolls consumed",
    }
    r_app = client.post(
        f"/api/v1/verification/{tx_id_str}/approve",
        json=approve_payload,
        headers=_auth(tokens["sup_a"]),
    )
    assert r_app.status_code == 200, f"Approval failed: {r_app.text}"
    app_data = r_app.json()
    assert app_data["status"] == "approved"
    assert app_data["is_replay"] is False

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 3: Balance (Confirm available quantity is exactly 8)
    # -------------------------------------------------------------------------
    # 3a: Check via site inventory API (filter by test material code)
    r_inv_post = client.get(
        f"/api/v1/inventory/sites/{site_a_str}?search={material.material_code}",
        headers=_auth(tokens["sup_a"]),
    )
    assert r_inv_post.status_code == 200
    mat_post = next(item for item in r_inv_post.json()["items"] if item["material_id"] == mat_str)
    assert mat_post["quantity_available"] == "8.00"

    # 3b: Check via daily work stock availability API (assigned employee)
    r_avail = client.get(
        f"/api/v1/daily-work/sites/{site_a_str}/materials/{mat_str}/availability",
        headers=_auth(tokens["emp_assigned"]),
    )
    assert r_avail.status_code == 200
    assert r_avail.json()["quantity_available"] == "8.00"

    # 3c: Check direct database row
    async with TestingSessionLocal() as session:
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == site_a.id,
            MaterialStock.material_id == material.id,
        )
        stock_row = (await session.execute(stmt_stock)).scalars().first()
        assert stock_row is not None
        assert stock_row.quantity == Decimal("8.00")

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 4: Ledger (Inward & Consumption movements)
    # -------------------------------------------------------------------------
    r_mvt = client.get(
        f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["sup_a"]),
    )
    assert r_mvt.status_code == 200
    mvt_data = r_mvt.json()
    assert mvt_data["total"] == 2
    items = mvt_data["items"]

    # Ordered descending by created_at:
    # 1st item: consumption
    mvt_consumed = items[0]
    assert mvt_consumed["movement_type"] == "consumed"
    assert mvt_consumed["quantity"] == "2.00"
    assert mvt_consumed["balance_after"] == "8.00"
    assert mvt_consumed["material_transaction_id"] == tx_id_str
    assert mvt_consumed["created_by"] == str(u_sup_a.id)
    assert mvt_consumed["actor_name"] == f"Supervisor A {sfx}"
    assert mvt_consumed["created_at"] is not None

    # 2nd item: inward
    mvt_inw = items[1]
    assert mvt_inw["movement_type"] == "inward"
    assert mvt_inw["movement_id"] == inward_movement_id
    assert mvt_inw["quantity"] == "10.00"
    assert mvt_inw["balance_after"] == "10.00"
    assert mvt_inw["created_by"] == str(u_sup_a.id)
    assert mvt_inw["actor_name"] == f"Supervisor A {sfx}"
    assert mvt_inw["remarks"] == "E2E delivery shipment of 10 rolls"
    assert mvt_inw["created_at"] is not None

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 5: Idempotency (Repeat approval request)
    # -------------------------------------------------------------------------
    r_app_replay = client.post(
        f"/api/v1/verification/{tx_id_str}/approve",
        json=approve_payload,
        headers=_auth(tokens["sup_a"]),
    )
    assert r_app_replay.status_code == 200
    replay_data = r_app_replay.json()
    assert replay_data["is_replay"] is True
    assert replay_data["status"] == "approved"

    # Confirm stock remains exactly 8.00 and no new movement was appended
    async with TestingSessionLocal() as session:
        stock_db_replay = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db_replay.quantity == Decimal("8.00")

    r_mvt_replay = client.get(
        f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["sup_a"]),
    )
    assert r_mvt_replay.status_code == 200
    assert r_mvt_replay.json()["total"] == 2

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 6: Insufficient Stock (Attempt approval for 10 units)
    # -------------------------------------------------------------------------
    async with TestingSessionLocal() as session:
        tx_excess = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe.id,
            material_id=material.id,
            site_id=site_a.id,
            transaction_type="consumed",
            item_name=material.name,
            quantity=10.0,  # 10 > remaining 8
            amount=0.0,
            status="submitted",
        )
        session.add(tx_excess)
        await session.commit()
        tx_excess_id = str(tx_excess.id)

    excess_idemp = f"APP-EXCESS-{_u()}"
    r_app_excess = client.post(
        f"/api/v1/verification/{tx_excess_id}/approve",
        json={
            "entity_type": "material",
            "idempotency_key": excess_idemp,
            "remarks": "Excess quantity approval test",
        },
        headers=_auth(tokens["sup_a"]),
    )
    # Must fail with 400 Bad Request
    assert r_app_excess.status_code == 400
    assert "Insufficient stock" in r_app_excess.json()["detail"]

    # Confirm stock is unchanged and still exactly 8.00
    async with TestingSessionLocal() as session:
        stock_excess_check = (await session.execute(stmt_stock)).scalars().first()
        assert stock_excess_check.quantity == Decimal("8.00")

        # Confirm tx status was not approved
        stmt_excess_tx = select(MaterialTransaction).where(MaterialTransaction.id == tx_excess.id)
        excess_tx_db = (await session.execute(stmt_excess_tx)).scalars().first()
        assert excess_tx_db.status == "submitted"

    # Confirm no new movement recorded
    r_mvt_excess = client.get(
        f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements",
        headers=_auth(tokens["sup_a"]),
    )
    assert r_mvt_excess.status_code == 200
    assert r_mvt_excess.json()["total"] == 2

    # -------------------------------------------------------------------------
    # VERIFICATION STEP 7: Authorization Checks
    # -------------------------------------------------------------------------
    # 7a: Administrator has global access
    r_admin_inv = client.get(f"/api/v1/inventory/sites/{site_a_str}", headers=_auth(tokens["admin"]))
    assert r_admin_inv.status_code == 200
    r_admin_mvt = client.get(f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements", headers=_auth(tokens["admin"]))
    assert r_admin_mvt.status_code == 200

    # 7b: Supervisor A is restricted to Site A:
    # Allowed at Site A:
    assert client.get(f"/api/v1/inventory/sites/{site_a_str}", headers=_auth(tokens["sup_a"])).status_code == 200
    # Forbidden at Site B:
    assert client.get(f"/api/v1/inventory/sites/{site_b_str}", headers=_auth(tokens["sup_a"])).status_code == 403
    assert client.post("/api/v1/inventory/inward", json={"site_id": site_b_str, "material_id": mat_str, "quantity": 1.0, "idempotency_key": f"INW-{_u()}"}, headers=_auth(tokens["sup_a"])).status_code == 403
    assert client.get(f"/api/v1/inventory/sites/{site_b_str}/materials/{mat_str}/movements", headers=_auth(tokens["sup_a"])).status_code == 403

    # 7c: Supervisor B is forbidden at Site A:
    assert client.get(f"/api/v1/inventory/sites/{site_a_str}", headers=_auth(tokens["sup_b"])).status_code == 403
    assert client.post("/api/v1/inventory/inward", json={"site_id": site_a_str, "material_id": mat_str, "quantity": 1.0, "idempotency_key": f"INW-{_u()}"}, headers=_auth(tokens["sup_b"])).status_code == 403
    assert client.get(f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements", headers=_auth(tokens["sup_b"])).status_code == 403

    # 7d: Employee is denied management inventory endpoints:
    assert client.get(f"/api/v1/inventory/sites/{site_a_str}", headers=_auth(tokens["emp_assigned"])).status_code == 403
    assert client.post("/api/v1/inventory/inward", json={"site_id": site_a_str, "material_id": mat_str, "quantity": 1.0, "idempotency_key": f"INW-{_u()}"}, headers=_auth(tokens["emp_assigned"])).status_code == 403
    assert client.get(f"/api/v1/inventory/sites/{site_a_str}/materials/{mat_str}/movements", headers=_auth(tokens["emp_assigned"])).status_code == 403

    # 7e: Employee stock availability lookup:
    # Assigned employee can query actively assigned Site A -> 200 OK
    assert client.get(f"/api/v1/daily-work/sites/{site_a_str}/materials/{mat_str}/availability", headers=_auth(tokens["emp_assigned"])).status_code == 200
    # Assigned employee forbidden on unassigned Site B -> 403
    assert client.get(f"/api/v1/daily-work/sites/{site_b_str}/materials/{mat_str}/availability", headers=_auth(tokens["emp_assigned"])).status_code == 403
    # Unassigned employee forbidden on Site A -> 403
    assert client.get(f"/api/v1/daily-work/sites/{site_a_str}/materials/{mat_str}/availability", headers=_auth(tokens["emp_unassigned"])).status_code == 403

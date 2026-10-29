from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.main import app
from app.models.assets import Asset, AssetTransaction
from app.models.auth import User
from app.models.operations import Client, EmployeeSiteAssignment, Project, Site
from app.models.system import AuditLog
from app.models.workforce import Employee
from app.modules.assets.schemas import AssetIssueRequest
from app.modules.assets.service import AssetService
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def batch2_setup():
    """
    Sets up users, supervisor profiles, employees, sites, and assignments for Batch 2 testing.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9197{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9197{sfx[:6]}2", role="director")
        u_sup_a = User(id=_u(), mobile_id=f"+9197{sfx[:6]}3", role="supervisor")
        u_sup_b = User(id=_u(), mobile_id=f"+9197{sfx[:6]}4", role="supervisor")
        u_emp_1 = User(id=_u(), mobile_id=f"+9197{sfx[:6]}5", role="employee")
        u_emp_2 = User(id=_u(), mobile_id=f"+9197{sfx[:6]}6", role="employee")
        u_emp_inact = User(id=_u(), mobile_id=f"+9197{sfx[:6]}7", role="employee")
        session.add_all([u_admin, u_dir, u_sup_a, u_sup_b, u_emp_1, u_emp_2, u_emp_inact])
        await session.flush()

        # 2. Supervisor Employee profiles
        emp_sup_a = Employee(
            id=_u(),
            user_id=u_sup_a.id,
            employee_code=f"SUP_A_{sfx}",
            mobile_id=u_sup_a.mobile_id,
            name=f"Supervisor_Alpha_{sfx}",
            is_active=True,
        )
        emp_sup_b = Employee(
            id=_u(),
            user_id=u_sup_b.id,
            employee_code=f"SUP_B_{sfx}",
            mobile_id=u_sup_b.mobile_id,
            name=f"Supervisor_Beta_{sfx}",
            is_active=True,
        )
        session.add_all([emp_sup_a, emp_sup_b])
        await session.flush()

        # 3. Master Data: Client, Project, Sites
        client = Client(id=_u(), name=f"Batch2Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Batch2Proj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        # Site A and Site C are supervised by emp_sup_a; Site B is supervised by emp_sup_b
        site_a = Site(id=_u(), project_id=project.id, name=f"Site_Alpha_{sfx}", supervisor_id=emp_sup_a.id)
        site_b = Site(id=_u(), project_id=project.id, name=f"Site_Beta_{sfx}", supervisor_id=emp_sup_b.id)
        site_c = Site(id=_u(), project_id=project.id, name=f"Site_Gamma_{sfx}", supervisor_id=emp_sup_a.id)
        session.add_all([site_a, site_b, site_c])
        await session.flush()

        # Unrelated client and site (to verify cross-client transfer rejection)
        client_other = Client(id=_u(), name=f"OtherClient_{sfx}")
        session.add(client_other)
        await session.flush()
        project_other = Project(id=_u(), client_id=client_other.id, name=f"OtherProj_{sfx}", status="in_progress")
        session.add(project_other)
        await session.flush()
        site_other = Site(id=_u(), project_id=project_other.id, name=f"Site_OtherClient_{sfx}")
        session.add(site_other)
        await session.flush()

        # 4. Standard Employee profiles
        emp_1 = Employee(
            id=_u(),
            user_id=u_emp_1.id,
            employee_code=f"EMP_1_{sfx}",
            mobile_id=u_emp_1.mobile_id,
            name=f"Worker_One_{sfx}",
            is_active=True,
        )
        emp_2 = Employee(
            id=_u(),
            user_id=u_emp_2.id,
            employee_code=f"EMP_2_{sfx}",
            mobile_id=u_emp_2.mobile_id,
            name=f"Worker_Two_{sfx}",
            is_active=True,
        )
        emp_inactive = Employee(
            id=_u(),
            user_id=u_emp_inact.id,
            employee_code=f"EMP_INACT_{sfx}",
            mobile_id=u_emp_inact.mobile_id,
            name=f"Worker_Inactive_{sfx}",
            is_active=False,
        )
        session.add_all([emp_1, emp_2, emp_inactive])
        await session.flush()

        # 5. Site assignments:
        # emp_1 active on Site A
        # emp_2 active on Site B
        # emp_inactive active on Site A (but employee record itself is inactive)
        asgn_1 = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_1.id,
            site_id=site_a.id,
            is_active=True,
        )
        asgn_2 = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_2.id,
            site_id=site_b.id,
            is_active=True,
        )
        asgn_inact = EmployeeSiteAssignment(
            id=_u(),
            employee_id=emp_inactive.id,
            site_id=site_a.id,
            is_active=True,
        )
        session.add_all([asgn_1, asgn_2, asgn_inact])
        await session.flush()

        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), u_admin.role),
            "director": create_access_token(str(u_dir.id), u_dir.role),
            "supervisor_a": create_access_token(str(u_sup_a.id), u_sup_a.role),
            "supervisor_b": create_access_token(str(u_sup_b.id), u_sup_b.role),
            "employee": create_access_token(str(u_emp_1.id), u_emp_1.role),
        }

        return {
            "tokens": tokens,
            "client": client,
            "project": project,
            "site_a": site_a,
            "site_b": site_b,
            "site_c": site_c,
            "site_other": site_other,
            "client_other": client_other,
            "emp_1": emp_1,
            "emp_2": emp_2,
            "emp_inactive": emp_inactive,
            "users": {
                "admin": u_admin,
                "director": u_dir,
                "supervisor_a": u_sup_a,
                "supervisor_b": u_sup_b,
                "employee_1": u_emp_1,
            },
        }


# =========================================================================
# 1. SCOPE A: ASSET ISSUE TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_issue_asset_to_assigned_employee_success(client: TestClient, batch2_setup):
    """
    Test issuing an available asset to an employee actively assigned to the asset's current site.
    Verifies:
      - 200 OK
      - status updated to 'issued_employee'
      - current_custodian_id updated to employee id
      - current_site_id remains unchanged
      - AssetTransaction ledger written with transaction_type='issued'
      - Central AuditLog record created
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]

    # Register asset at Site A
    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Laser Distance Meter",
            "category": "survey_tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["id"]

    # Issue asset to emp_1 (actively assigned to Site A)
    issue_payload = {
        "employee_id": str(emp_1.id),
        "remarks": "Issued for room measurement work",
    }
    issue_res = client.post(f"/api/v1/assets/{asset_id}/issue", json=issue_payload, headers=_auth(admin_token))
    assert issue_res.status_code == 200, issue_res.text
    issued_data = issue_res.json()

    assert issued_data["id"] == asset_id
    assert issued_data["status"] == "issued_employee"
    assert issued_data["current_custodian_id"] == str(emp_1.id)
    assert issued_data["current_custodian_name"] == emp_1.name
    assert issued_data["current_site_id"] == str(site_a.id)
    assert issued_data["location_type"] == "site"

    # Verify transaction ledger
    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=_auth(admin_token))
    assert detail_res.status_code == 200
    transactions = detail_res.json()["transactions"]
    assert len(transactions) == 2  # registration + issue
    latest_tx = transactions[0]  # sorted descending
    assert latest_tx["transaction_type"] == "issued"
    assert latest_tx["to_employee_id"] == str(emp_1.id)
    assert latest_tx["to_employee_name"] == emp_1.name
    assert latest_tx["to_site_id"] == str(site_a.id)
    assert latest_tx["remarks"] == "Issued for room measurement work"

    # Verify central audit log
    async with TestingSessionLocal() as session:
        audit_stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id == uuid.UUID(asset_id), AuditLog.action == "issue")
            .order_by(AuditLog.created_at.desc())
        )
        audit_log = (await session.execute(audit_stmt)).scalars().first()
        assert audit_log is not None
        assert audit_log.new_values["status"] == "issued_employee"
        assert audit_log.new_values["current_custodian_id"] == str(emp_1.id)


@pytest.mark.asyncio
async def test_issue_asset_employee_not_assigned_to_site_rejected(client: TestClient, batch2_setup):
    """
    Reject issue if employee is not assigned to the asset's current site.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_2 = batch2_setup["emp_2"]  # emp_2 is assigned to Site B, not Site A

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Rotary Hammer Drill",
            "category": "power_tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["id"]

    issue_res = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_2.id)},
        headers=_auth(admin_token),
    )
    assert issue_res.status_code == 400
    assert "Employee does not have an active assignment to the asset's current site" in issue_res.text


@pytest.mark.asyncio
async def test_issue_asset_warehouse_asset_rejected(client: TestClient, batch2_setup):
    """
    Reject issue if asset is stored in the Central Warehouse.
    Warehouse assets cannot be issued directly to employees; they must first be assigned to a site.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    emp_1 = batch2_setup["emp_1"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Warehouse Generator",
            "category": "machinery",
            "location_type": "warehouse",
        },
        headers=_auth(admin_token),
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["id"]

    issue_res = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )
    assert issue_res.status_code == 400
    assert "Warehouse assets cannot be issued directly" in issue_res.text


@pytest.mark.asyncio
async def test_issue_asset_already_issued_or_unavailable_rejected(client: TestClient, batch2_setup):
    """
    Reject issue if the asset is already issued (409 Conflict) or not in 'available' status (400 Bad Request).
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]

    # 1. Damaged asset registration
    reg_damaged = client.post(
        "/api/v1/assets",
        json={
            "name": "Damaged Angle Grinder",
            "category": "power_tools",
            "status": "damaged",
            "condition": "damaged",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert reg_damaged.status_code == 201
    damaged_id = reg_damaged.json()["id"]

    res_damaged_issue = client.post(
        f"/api/v1/assets/{damaged_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )
    assert res_damaged_issue.status_code == 400
    assert "Only 'available' assets can be issued" in res_damaged_issue.text

    # 2. Available asset, issued once
    reg_ok = client.post(
        "/api/v1/assets",
        json={
            "name": "Vibrating Plate Compactor",
            "category": "heavy_machinery",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert reg_ok.status_code == 201
    compactor_id = reg_ok.json()["id"]

    res_first_issue = client.post(
        f"/api/v1/assets/{compactor_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )
    assert res_first_issue.status_code == 200

    # Double issue attempt (conflict)
    res_second_issue = client.post(
        f"/api/v1/assets/{compactor_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )
    assert res_second_issue.status_code == 409
    assert "already issued to an employee" in res_second_issue.text


@pytest.mark.asyncio
async def test_issue_asset_inactive_employee_or_nonexistent_rejected(client: TestClient, batch2_setup):
    """
    Reject issue if employee is inactive or does not exist.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_inactive = batch2_setup["emp_inactive"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Bench Grinder",
            "category": "workshop_equipment",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["id"]

    # Inactive employee
    inact_res = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_inactive.id)},
        headers=_auth(admin_token),
    )
    assert inact_res.status_code == 400
    assert "Cannot issue asset to an inactive employee" in inact_res.text

    # Non-existent employee
    fake_emp_id = _u()
    fake_res = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(fake_emp_id)},
        headers=_auth(admin_token),
    )
    assert fake_res.status_code == 404
    assert f"Employee {fake_emp_id} not found" in fake_res.text


# =========================================================================
# 2. SCOPE A: ASSET RETURN TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_return_asset_success_custodian_cleared_original_site_preserved(client: TestClient, batch2_setup):
    """
    Test returning an issued asset.
    Verifies:
      - 200 OK
      - status returns to 'available'
      - current_custodian_id cleared to None
      - current_site_id preserved at the same site
      - AssetTransaction ledger written with transaction_type='returned'
      - Central AuditLog records custodian cleared
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Optical Level",
            "category": "survey_equipment",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    # Issue
    client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )

    # Return
    return_res = client.post(
        f"/api/v1/assets/{asset_id}/return",
        json={
            "employee_id": str(emp_1.id),
            "remarks": "Returned in good working condition",
        },
        headers=_auth(admin_token),
    )
    assert return_res.status_code == 200, return_res.text
    ret_data = return_res.json()

    assert ret_data["status"] == "available"
    assert ret_data["current_custodian_id"] is None
    assert ret_data["current_custodian_name"] is None
    assert ret_data["current_site_id"] == str(site_a.id)

    # Verify ledger
    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=_auth(admin_token))
    transactions = detail_res.json()["transactions"]
    assert len(transactions) == 3  # reg, issue, return
    latest_tx = transactions[0]
    assert latest_tx["transaction_type"] == "returned"
    assert latest_tx["from_employee_id"] == str(emp_1.id)
    assert latest_tx["from_employee_name"] == emp_1.name
    assert latest_tx["to_employee_id"] is None
    assert latest_tx["to_site_id"] == str(site_a.id)


@pytest.mark.asyncio
async def test_return_asset_custodian_mismatch_and_unissued_rejected(client: TestClient, batch2_setup):
    """
    Reject return if asset is not currently issued (409 Conflict) or returning employee
    does not match the recorded custodian (400 Bad Request).
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]
    emp_2 = batch2_setup["emp_2"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Concrete Rebar Cutter",
            "category": "tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    # 1. Attempt return when unissued
    unissued_return = client.post(
        f"/api/v1/assets/{asset_id}/return",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )
    assert unissued_return.status_code == 409
    assert "Asset is not currently issued" in unissued_return.text

    # Issue to emp_1
    client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )

    # 2. Attempt return by emp_2 (custodian mismatch)
    mismatch_return = client.post(
        f"/api/v1/assets/{asset_id}/return",
        json={"employee_id": str(emp_2.id)},
        headers=_auth(admin_token),
    )
    assert mismatch_return.status_code == 400
    assert "Returning employee does not match the recorded custodian" in mismatch_return.text


@pytest.mark.asyncio
async def test_return_asset_condition_and_damage_rules(client: TestClient, batch2_setup):
    """
    Test damage/condition handling on return:
      - condition 'damaged' auto-sets status to 'damaged'
      - condition 'unusable' auto-sets status to 'damaged'
      - explicit status 'under_maintenance' overrides default
      - status 'issued_employee' on return is rejected
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]

    # 1. Return with condition='damaged'
    res_1 = client.post(
        "/api/v1/assets",
        json={
            "name": "Demolition Hammer 1500W",
            "category": "power_tools",
            "condition": "good",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_1_id = res_1.json()["id"]
    client.post(f"/api/v1/assets/{asset_1_id}/issue", json={"employee_id": str(emp_1.id)}, headers=_auth(admin_token))

    ret_damaged = client.post(
        f"/api/v1/assets/{asset_1_id}/return",
        json={
            "employee_id": str(emp_1.id),
            "condition": "damaged",
            "remarks": "Chuck cracked during heavy drilling",
        },
        headers=_auth(admin_token),
    )
    assert ret_damaged.status_code == 200
    assert ret_damaged.json()["condition"] == "damaged"
    assert ret_damaged.json()["status"] == "damaged"
    assert ret_damaged.json()["current_custodian_id"] is None

    # 2. Return with condition='unusable'
    res_2 = client.post(
        "/api/v1/assets",
        json={
            "name": "Submersible Water Pump",
            "category": "pumps",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_2_id = res_2.json()["id"]
    client.post(f"/api/v1/assets/{asset_2_id}/issue", json={"employee_id": str(emp_1.id)}, headers=_auth(admin_token))

    ret_unusable = client.post(
        f"/api/v1/assets/{asset_2_id}/return",
        json={
            "employee_id": str(emp_1.id),
            "condition": "unusable",
            "remarks": "Motor burned out completely",
        },
        headers=_auth(admin_token),
    )
    assert ret_unusable.status_code == 200
    assert ret_unusable.json()["condition"] == "unusable"
    assert ret_unusable.json()["status"] == "damaged"

    # 3. Return with explicit status='under_maintenance'
    res_3 = client.post(
        "/api/v1/assets",
        json={
            "name": "Tamping Rammer",
            "category": "compaction",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_3_id = res_3.json()["id"]
    client.post(f"/api/v1/assets/{asset_3_id}/issue", json={"employee_id": str(emp_1.id)}, headers=_auth(admin_token))

    ret_maint = client.post(
        f"/api/v1/assets/{asset_3_id}/return",
        json={
            "employee_id": str(emp_1.id),
            "condition": "fair",
            "status": "under_maintenance",
            "remarks": "Needs 50-hour oil and filter service",
        },
        headers=_auth(admin_token),
    )
    assert ret_maint.status_code == 200
    assert ret_maint.json()["condition"] == "fair"
    assert ret_maint.json()["status"] == "under_maintenance"

    # 4. Attempt return with status='issued_employee' (validator rejection)
    ret_invalid_status = client.post(
        f"/api/v1/assets/{asset_3_id}/return",
        json={
            "employee_id": str(emp_1.id),
            "status": "issued_employee",
        },
        headers=_auth(admin_token),
    )
    assert ret_invalid_status.status_code == 422


# =========================================================================
# 3. SCOPE B: REASSIGNMENT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_reassign_asset_administrator_direct_transfers(client: TestClient, batch2_setup):
    """
    Test direct site reassignment by administrator:
      1. Warehouse -> Site A
      2. Site A -> Site B
      3. Site B -> Warehouse
    Verifies that no in_transit status or receipt step is involved,
    ledger is written with transaction_type='reassigned', and audit log is created.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    site_b = batch2_setup["site_b"]

    # Register in Warehouse
    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Total Station TS16",
            "category": "survey_equipment",
            "location_type": "warehouse",
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    # 1. Warehouse -> Site A
    reassign_1 = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_a.id),
            "remarks": "Deployed from warehouse to Site Alpha",
        },
        headers=_auth(admin_token),
    )
    assert reassign_1.status_code == 200, reassign_1.text
    data_1 = reassign_1.json()
    assert data_1["location_type"] == "site"
    assert data_1["current_site_id"] == str(site_a.id)
    assert data_1["current_site_name"] == site_a.name

    # 2. Site A -> Site B
    reassign_2 = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_b.id),
            "remarks": "Transferred directly from Site Alpha to Site Beta",
        },
        headers=_auth(admin_token),
    )
    assert reassign_2.status_code == 200, reassign_2.text
    data_2 = reassign_2.json()
    assert data_2["location_type"] == "site"
    assert data_2["current_site_id"] == str(site_b.id)
    assert data_2["current_site_name"] == site_b.name

    # 3. Site B -> Warehouse
    reassign_3 = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "warehouse",
            "remarks": "Returned to central warehouse for seasonal storage",
        },
        headers=_auth(admin_token),
    )
    assert reassign_3.status_code == 200, reassign_3.text
    data_3 = reassign_3.json()
    assert data_3["location_type"] == "warehouse"
    assert data_3["current_site_id"] is None
    assert data_3["current_site_name"] is None

    # Verify transaction ledger
    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=_auth(admin_token))
    transactions = detail_res.json()["transactions"]
    assert len(transactions) == 4  # reg + 3 reassignments
    assert transactions[0]["transaction_type"] == "reassigned"
    assert transactions[0]["from_location_type"] == "site"
    assert transactions[0]["to_location_type"] == "warehouse"
    assert transactions[0]["from_site_id"] == str(site_b.id)
    assert transactions[0]["to_site_id"] is None


@pytest.mark.asyncio
async def test_reassign_asset_while_issued_rejected(client: TestClient, batch2_setup):
    """
    Reject site reassignment while an asset is issued to an employee.
    It must be returned before reassignment.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    site_b = batch2_setup["site_b"]
    emp_1 = batch2_setup["emp_1"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Soil Compactor 200kg",
            "category": "compaction",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    # Issue to emp_1
    client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(admin_token),
    )

    # Attempt reassign while issued
    reassign_res = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_b.id),
        },
        headers=_auth(admin_token),
    )
    assert reassign_res.status_code == 409
    assert "Cannot reassign asset while issued to an employee" in reassign_res.text


@pytest.mark.asyncio
async def test_reassign_asset_redundant_target_rejected(client: TestClient, batch2_setup):
    """
    Reject reassign if target is identical to current location.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Hydraulic Jack 50T",
            "category": "heavy_tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    redundant_res = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    assert redundant_res.status_code == 400
    assert "Asset is already assigned to this site" in redundant_res.text


# =========================================================================
# 4. SUPERVISOR BOUNDARY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_supervisor_supported_asset_actions(client: TestClient, batch2_setup):
    """
    Test supervisor supported asset actions identical to administrator:
      - Supervisors can issue and return assets at any site (provided employee has active assignment).
      - Supervisors can reassign assets to Warehouse (200 OK).
      - Supervisors can reassign assets from Warehouse to Site (200 OK).
      - Supervisors can reassign assets across any project sites (200 OK).
    """
    admin_token = batch2_setup["tokens"]["admin"]
    sup_a_token = batch2_setup["tokens"]["supervisor_a"]
    sup_b_token = batch2_setup["tokens"]["supervisor_b"]
    site_a = batch2_setup["site_a"]
    site_b = batch2_setup["site_b"]
    site_c = batch2_setup["site_c"]
    site_other = batch2_setup["site_other"]
    emp_1 = batch2_setup["emp_1"]  # assigned to Site A

    # Register asset at Site A
    res_a = client.post(
        "/api/v1/assets",
        json={
            "name": "Supervised Site A Scaffolding Set",
            "category": "scaffolding",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_a_id = res_a.json()["id"]

    # 1. Supervisor Beta can issue asset at Site A to employee assigned to Site A -> 200 OK
    res_sup_b_issue = client.post(
        f"/api/v1/assets/{asset_a_id}/issue",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(sup_b_token),
    )
    assert res_sup_b_issue.status_code == 200
    assert res_sup_b_issue.json()["status"] == "issued_employee"

    # 2. Supervisor Alpha returns asset at Site A -> 200 OK
    res_sup_a_return = client.post(
        f"/api/v1/assets/{asset_a_id}/return",
        json={"employee_id": str(emp_1.id)},
        headers=_auth(sup_a_token),
    )
    assert res_sup_a_return.status_code == 200
    assert res_sup_a_return.json()["status"] == "available"

    # 3. Supervisor Alpha reassigns asset from Site A to Warehouse -> 200 OK
    res_sup_a_reassign_wh = client.post(
        f"/api/v1/assets/{asset_a_id}/reassign",
        json={"target_location_type": "warehouse"},
        headers=_auth(sup_a_token),
    )
    assert res_sup_a_reassign_wh.status_code == 200
    assert res_sup_a_reassign_wh.json()["location_type"] == "warehouse"
    assert res_sup_a_reassign_wh.json()["current_site_id"] is None

    # 4. Supervisor Beta reassigns asset from Warehouse to Site B -> 200 OK
    res_sup_b_reassign_site = client.post(
        f"/api/v1/assets/{asset_a_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_b.id),
        },
        headers=_auth(sup_b_token),
    )
    assert res_sup_b_reassign_site.status_code == 200
    assert res_sup_b_reassign_site.json()["location_type"] == "site"
    assert res_sup_b_reassign_site.json()["current_site_id"] == str(site_b.id)

    # 5. Supervisor Alpha reassigns to a project site of a different client (Site B -> Site Other) -> 200 OK
    res_sup_a_reassign_other = client.post(
        f"/api/v1/assets/{asset_a_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_other.id),
        },
        headers=_auth(sup_a_token),
    )
    assert res_sup_a_reassign_other.status_code == 200
    assert res_sup_a_reassign_other.json()["current_site_id"] == str(site_other.id)


@pytest.mark.asyncio
async def test_get_destination_sites_supervisor_identical_to_admin(client: TestClient, batch2_setup):
    """
    Test GET /api/v1/assets/{asset_id}/destination-sites:
      - Administrator sees all active destination sites across all projects/clients (excluding current site).
      - Supervisor Alpha sees all active destination sites across all projects/clients (excluding current site),
        identical to administrator.
      - Supervisor Beta querying destination sites sees identical sites.
      - Supervisor querying destination sites for a warehouse asset gets 200 OK with all active sites.
    """
    admin_token = batch2_setup["tokens"]["admin"]
    sup_a_token = batch2_setup["tokens"]["supervisor_a"]
    sup_b_token = batch2_setup["tokens"]["supervisor_b"]
    site_a = batch2_setup["site_a"]
    site_b = batch2_setup["site_b"]
    site_c = batch2_setup["site_c"]
    site_other = batch2_setup["site_other"]

    # Register asset at Site A
    res_a = client.post(
        "/api/v1/assets",
        json={
            "name": "Site Alpha Concrete Mixer",
            "category": "heavy_machinery",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = res_a.json()["id"]

    # 1. Administrator destination sites
    res_admin_dest = client.get(f"/api/v1/assets/{asset_id}/destination-sites", headers=_auth(admin_token))
    assert res_admin_dest.status_code == 200
    admin_dest_ids = {s["id"] for s in res_admin_dest.json()}
    assert str(site_b.id) in admin_dest_ids
    assert str(site_c.id) in admin_dest_ids
    assert str(site_other.id) in admin_dest_ids
    assert str(site_a.id) not in admin_dest_ids  # Current site excluded

    # 2. Supervisor Alpha destination sites (identical to Administrator)
    res_sup_a_dest = client.get(f"/api/v1/assets/{asset_id}/destination-sites", headers=_auth(sup_a_token))
    assert res_sup_a_dest.status_code == 200
    sup_a_dest_ids = {s["id"] for s in res_sup_a_dest.json()}
    assert sup_a_dest_ids == admin_dest_ids

    # 3. Supervisor Beta querying destination sites for Site A asset -> 200 OK (identical to Administrator)
    res_sup_b_dest = client.get(f"/api/v1/assets/{asset_id}/destination-sites", headers=_auth(sup_b_token))
    assert res_sup_b_dest.status_code == 200
    assert {s["id"] for s in res_sup_b_dest.json()} == admin_dest_ids

    # 4. Warehouse asset destination sites
    res_wh = client.post(
        "/api/v1/assets",
        json={
            "name": "Warehouse Generator",
            "category": "generators",
            "location_type": "warehouse",
        },
        headers=_auth(admin_token),
    )
    asset_wh_id = res_wh.json()["id"]

    # Admin querying warehouse asset destination sites -> 200 OK (all active sites available)
    res_admin_wh = client.get(f"/api/v1/assets/{asset_wh_id}/destination-sites", headers=_auth(admin_token))
    assert res_admin_wh.status_code == 200
    admin_wh_ids = {s["id"] for s in res_admin_wh.json()}
    assert len(admin_wh_ids) >= 4

    # Supervisor Alpha querying warehouse asset destination sites -> 200 OK (identical to Admin)
    res_sup_wh = client.get(f"/api/v1/assets/{asset_wh_id}/destination-sites", headers=_auth(sup_a_token))
    assert res_sup_wh.status_code == 200
    assert {s["id"] for s in res_sup_wh.json()} == admin_wh_ids


# =========================================================================
# 5. IDEMPOTENCY & CONCURRENCY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_idempotent_retries_for_issue_return_reassign(client: TestClient, batch2_setup):
    """
    Test idempotent retries:
      - Duplicate issue request with same key returns identical 200 without duplicate ledger or audit log
      - Duplicate return request with same key returns identical 200 without duplicate ledger or audit log
      - Duplicate reassign request with same key returns identical 200 without duplicate ledger or audit log
      - Reusing idempotency key across different assets returns 409 Conflict
    """
    admin_token = batch2_setup["tokens"]["admin"]
    site_a = batch2_setup["site_a"]
    site_b = batch2_setup["site_b"]
    emp_1 = batch2_setup["emp_1"]

    reg_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Idempotent Asset Test",
            "category": "survey_tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    asset_id = reg_res.json()["id"]

    # 1. Issue with idempotency key
    issue_key = f"key-issue-{_u()}"
    res_issue_1 = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id), "idempotency_key": issue_key},
        headers=_auth(admin_token),
    )
    assert res_issue_1.status_code == 200

    # Retry issue with exact same key
    res_issue_2 = client.post(
        f"/api/v1/assets/{asset_id}/issue",
        json={"employee_id": str(emp_1.id), "idempotency_key": issue_key},
        headers=_auth(admin_token),
    )
    assert res_issue_2.status_code == 200
    assert res_issue_2.json()["id"] == asset_id

    # Check ledger count for this key is exactly 1
    async with TestingSessionLocal() as session:
        tx_count = (
            await session.execute(
                select(func.count(AssetTransaction.id)).where(AssetTransaction.idempotency_key == issue_key)
            )
        ).scalar()
        assert tx_count == 1

    # 2. Return with idempotency key
    return_key = f"key-return-{_u()}"
    res_return_1 = client.post(
        f"/api/v1/assets/{asset_id}/return",
        json={"employee_id": str(emp_1.id), "idempotency_key": return_key},
        headers=_auth(admin_token),
    )
    assert res_return_1.status_code == 200

    # Retry return with same key
    res_return_2 = client.post(
        f"/api/v1/assets/{asset_id}/return",
        json={"employee_id": str(emp_1.id), "idempotency_key": return_key},
        headers=_auth(admin_token),
    )
    assert res_return_2.status_code == 200

    async with TestingSessionLocal() as session:
        tx_ret_count = (
            await session.execute(
                select(func.count(AssetTransaction.id)).where(AssetTransaction.idempotency_key == return_key)
            )
        ).scalar()
        assert tx_ret_count == 1

    # 3. Reassign with idempotency key
    reassign_key = f"key-reassign-{_u()}"
    res_reassign_1 = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_b.id),
            "idempotency_key": reassign_key,
        },
        headers=_auth(admin_token),
    )
    assert res_reassign_1.status_code == 200

    # Retry reassign with same key
    res_reassign_2 = client.post(
        f"/api/v1/assets/{asset_id}/reassign",
        json={
            "target_location_type": "site",
            "target_site_id": str(site_b.id),
            "idempotency_key": reassign_key,
        },
        headers=_auth(admin_token),
    )
    assert res_reassign_2.status_code == 200

    async with TestingSessionLocal() as session:
        tx_reassign_count = (
            await session.execute(
                select(func.count(AssetTransaction.id)).where(AssetTransaction.idempotency_key == reassign_key)
            )
        ).scalar()
        assert tx_reassign_count == 1

    # 4. Reusing idempotency key on a different asset returns 409
    other_reg = client.post(
        "/api/v1/assets",
        json={
            "name": "Different Asset",
            "category": "tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(admin_token),
    )
    other_id = other_reg.json()["id"]

    res_cross_reused = client.post(
        f"/api/v1/assets/{other_id}/issue",
        json={"employee_id": str(emp_1.id), "idempotency_key": issue_key},
        headers=_auth(admin_token),
    )
    assert res_cross_reused.status_code == 409


# =========================================================================
# 6. ATOMIC ROLLBACK TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_atomic_rollback_on_transaction_or_audit_failure(batch2_setup):
    """
    Verify atomic rollback:
    If a failure occurs during issue execution before commit (e.g., database error during audit write),
    the session rolls back, ensuring that the asset status, custodian, and transactions remain uncommitted.
    """
    admin_user = batch2_setup["users"]["admin"]
    site_a = batch2_setup["site_a"]
    emp_1 = batch2_setup["emp_1"]

    async with TestingSessionLocal() as session:
        # Create an available asset
        asset = Asset(
            id=_u(),
            asset_tag=f"RB-{str(_u())[:6]}",
            name="Rollback Test Asset",
            category="heavy_tools",
            condition="good",
            status="available",
            location_type="site",
            current_site_id=site_a.id,
            is_active=True,
            created_by=admin_user.id,
        )
        session.add(asset)
        await session.commit()
        asset_id = asset.id

    # Now attempt issue, but simulate an error on commit by mocking session.commit to raise an exception
    async with TestingSessionLocal() as session:
        req = AssetIssueRequest(employee_id=emp_1.id, remarks="Simulate failure")

        with patch.object(session, "commit", side_effect=RuntimeError("Simulated DB Disk Full")):
            with pytest.raises(RuntimeError):
                await AssetService.issue_asset(session, asset_id, req, admin_user)

    # Verify state in fresh session: asset must still be 'available', custodian must be None, no ledger record
    async with TestingSessionLocal() as session:
        saved = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one()
        assert saved.status == "available"
        assert saved.current_custodian_id is None

        txs = (
            await session.execute(
                select(AssetTransaction).where(
                    AssetTransaction.asset_id == asset_id,
                    AssetTransaction.transaction_type == "issued",
                )
            )
        ).scalars().all()
        assert len(txs) == 0

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app
from app.models.assets import Asset, AssetTransaction
from app.models.auth import User
from app.models.operations import Client, Project, Site
from app.models.system import AuditLog
from app.models.workforce import Employee
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def asset_test_setup():
    """Sets up test users, supervisor profiles, and sites for asset testing."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="director")
        u_sup_a = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        u_sup_b = User(id=_u(), mobile_id=f"+9198{sfx[:6]}5", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")
        session.add_all([u_admin, u_dir, u_sup_a, u_sup_b, u_emp])
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
        client = Client(id=_u(), name=f"AssetClient_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"AssetProj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        # Site Alpha supervised by emp_sup_a, Site Beta supervised by emp_sup_b
        site_a = Site(id=_u(), project_id=project.id, name=f"Site_Alpha_{sfx}", supervisor_id=emp_sup_a.id)
        site_b = Site(id=_u(), project_id=project.id, name=f"Site_Beta_{sfx}", supervisor_id=emp_sup_b.id)
        session.add_all([site_a, site_b])
        await session.flush()

        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), u_admin.role),
            "director": create_access_token(str(u_dir.id), u_dir.role),
            "supervisor": create_access_token(str(u_sup_a.id), u_sup_a.role),
            "supervisor_a": create_access_token(str(u_sup_a.id), u_sup_a.role),
            "supervisor_b": create_access_token(str(u_sup_b.id), u_sup_b.role),
            "employee": create_access_token(str(u_emp.id), u_emp.role),
        }

        return {
            "tokens": tokens,
            "client": client,
            "project": project,
            "site_a": site_a,
            "site_b": site_b,
            "users": {
                "admin": u_admin,
                "director": u_dir,
                "supervisor_a": u_sup_a,
                "supervisor_b": u_sup_b,
                "employee": u_emp,
            },
        }


# =========================================================================
# 1. REGISTRATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_register_asset_warehouse_success_auto_tag(client: TestClient, asset_test_setup):
    """
    Administrator registers an asset in the Central Warehouse without specifying a tag.
    Verifies auto-generation of tag, warehouse location state, transaction ledger, and audit log.
    """
    token = asset_test_setup["tokens"]["admin"]
    admin_user = asset_test_setup["users"]["admin"]

    payload = {
        "name": "Heavy Duty Concrete Mixer 500L",
        "category": "heavy_machinery",
        "serial_number": "MX-998811",
        "manufacturer": "Caterpillar",
        "model_number": "CAT-CM500",
        "purchase_date": "2026-01-15",
        "purchase_cost": "250000.00",
        "warranty_expiry_date": "2028-01-15",
        "condition": "new",
        "status": "available",
        "location_type": "warehouse",
        "description": "500L diesel concrete mixer stored at central warehouse",
        "remarks": "Procured under FY26 CAPEX",
    }

    res = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["name"] == payload["name"]
    assert data["category"] == payload["category"]
    assert data["location_type"] == "warehouse"
    assert data["current_site_id"] is None
    assert data["current_site_name"] is None
    assert data["asset_tag"].startswith("AST-")
    assert Decimal(data["purchase_cost"]) == Decimal("250000.00")

    asset_id = uuid.UUID(data["id"])

    # Verify database persistence & audit log
    async with TestingSessionLocal() as session:
        db_asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one()
        assert db_asset.location_type == "warehouse"
        assert db_asset.current_site_id is None
        assert db_asset.created_by == admin_user.id

        tx_stmt = select(AssetTransaction).where(AssetTransaction.asset_id == asset_id)
        db_tx = (await session.execute(tx_stmt)).scalar_one()
        assert db_tx.transaction_type == "registered"
        assert db_tx.to_location_type == "warehouse"
        assert db_tx.to_site_id is None
        assert db_tx.performed_by == admin_user.id
        assert db_tx.remarks == "Procured under FY26 CAPEX"

        audit_stmt = select(AuditLog).where(AuditLog.entity_id == asset_id)
        db_audit = (await session.execute(audit_stmt)).scalar_one()
        assert db_audit.entity_type == "asset"
        assert db_audit.action == "create"
        assert db_audit.changed_by == admin_user.id


@pytest.mark.asyncio
async def test_register_asset_site_assignment_custom_tag(client: TestClient, asset_test_setup):
    """
    Administrator registers an asset assigned directly to a specific site with a custom asset tag.
    Verifies site assignment, custom tag preservation, and site ledger entry.
    """
    token = asset_test_setup["tokens"]["admin"]
    site_a = asset_test_setup["site_a"]

    custom_tag = f"DRL-{str(_u())[:6].upper()}"
    payload = {
        "asset_tag": custom_tag,
        "name": "Rotary Hammer Drill 800W",
        "category": "power_tools",
        "serial_number": "BOSCH-RD-1122",
        "manufacturer": "Bosch",
        "model_number": "GBH-2-28",
        "purchase_date": "2026-03-01",
        "purchase_cost": "12500.00",
        "condition": "good",
        "status": "available",
        "location_type": "site",
        "current_site_id": str(site_a.id),
        "remarks": "Allocated directly to Site Alpha on receipt",
    }

    res = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["asset_tag"] == custom_tag
    assert data["location_type"] == "site"
    assert data["current_site_id"] == str(site_a.id)
    assert data["current_site_name"] == site_a.name

    asset_id = uuid.UUID(data["id"])

    async with TestingSessionLocal() as session:
        tx_stmt = select(AssetTransaction).where(AssetTransaction.asset_id == asset_id)
        db_tx = (await session.execute(tx_stmt)).scalar_one()
        assert db_tx.to_location_type == "site"
        assert db_tx.to_site_id == site_a.id


@pytest.mark.asyncio
async def test_register_asset_rejection_issued_employee_and_in_transit(client: TestClient, asset_test_setup):
    """
    Initial registration must reject status='issued_employee' (no initial issued creation without handover)
    and status='in_transit' (removed state).
    """
    token = asset_test_setup["tokens"]["admin"]

    # 1. status='issued_employee' rejected on registration
    res_issued = client.post(
        "/api/v1/assets",
        json={
            "name": "Issued Tool Attempt",
            "category": "power_tools",
            "location_type": "warehouse",
            "status": "issued_employee",
        },
        headers=_auth(token),
    )
    assert res_issued.status_code == 422
    assert "issued_employee" in res_issued.text

    # 2. status='in_transit' rejected on registration
    res_transit = client.post(
        "/api/v1/assets",
        json={
            "name": "In Transit Tool Attempt",
            "category": "power_tools",
            "location_type": "warehouse",
            "status": "in_transit",
        },
        headers=_auth(token),
    )
    assert res_transit.status_code == 422


# =========================================================================
# 2. VALIDATION & LOCATION CONSISTENCY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_register_asset_warehouse_with_site_fails(client: TestClient, asset_test_setup):
    """
    Attempting to register location_type='warehouse' while providing a site_id must fail.
    Ensures central warehouse assets are never confused with site assets.
    """
    token = asset_test_setup["tokens"]["admin"]
    site_a = asset_test_setup["site_a"]

    payload = {
        "name": "Laser Distance Meter",
        "category": "measuring_instruments",
        "location_type": "warehouse",
        "current_site_id": str(site_a.id),
    }

    res = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res.status_code == 422
    assert "warehouse" in res.text.lower()


@pytest.mark.asyncio
async def test_register_asset_site_without_site_fails(client: TestClient, asset_test_setup):
    """
    Attempting to register location_type='site' without specifying a site_id must fail.
    """
    token = asset_test_setup["tokens"]["admin"]

    payload = {
        "name": "Laser Distance Meter",
        "category": "measuring_instruments",
        "location_type": "site",
        "current_site_id": None,
    }

    res = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res.status_code == 422
    assert "site" in res.text.lower()


@pytest.mark.asyncio
async def test_register_asset_nonexistent_site_fails(client: TestClient, asset_test_setup):
    """
    Attempting to register location_type='site' with a non-existent site UUID must return 404.
    """
    token = asset_test_setup["tokens"]["admin"]
    fake_site_id = _u()

    payload = {
        "name": "Tripod Survey Level",
        "category": "measuring_instruments",
        "location_type": "site",
        "current_site_id": str(fake_site_id),
    }

    res = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res.status_code == 404
    assert f"Site {fake_site_id} not found" in res.text


@pytest.mark.asyncio
async def test_register_asset_duplicate_tag_conflict(client: TestClient, asset_test_setup):
    """
    Attempting to register an asset with a tag that already exists must return 409 Conflict.
    """
    token = asset_test_setup["tokens"]["admin"]
    tag = f"TAG-DUP-{str(_u())[:6]}"

    payload1 = {
        "asset_tag": tag,
        "name": "Safety Harness Standard",
        "category": "safety_gear",
        "location_type": "warehouse",
    }
    res1 = client.post("/api/v1/assets", json=payload1, headers=_auth(token))
    assert res1.status_code == 201

    payload2 = {
        "asset_tag": tag,
        "name": "Safety Harness Duplicate Attempt",
        "category": "safety_gear",
        "location_type": "warehouse",
    }
    res2 = client.post("/api/v1/assets", json=payload2, headers=_auth(token))
    assert res2.status_code == 409
    assert f"Asset tag '{tag}' already exists" in res2.text


@pytest.mark.asyncio
async def test_register_asset_validation_negative_cost_and_invalid_dates(client: TestClient, asset_test_setup):
    """
    Validation tests for negative purchase cost and warranty date preceding purchase date.
    """
    token = asset_test_setup["tokens"]["admin"]

    # Negative cost
    res_neg = client.post(
        "/api/v1/assets",
        json={"name": "Test Tool", "category": "tools", "purchase_cost": "-50.00"},
        headers=_auth(token),
    )
    assert res_neg.status_code == 422

    # Warranty expiry before purchase date
    res_date = client.post(
        "/api/v1/assets",
        json={
            "name": "Test Tool",
            "category": "tools",
            "purchase_date": "2026-06-01",
            "warranty_expiry_date": "2025-06-01",
        },
        headers=_auth(token),
    )
    assert res_date.status_code == 422


@pytest.mark.asyncio
async def test_register_asset_idempotency_replay(client: TestClient, asset_test_setup):
    """
    Replaying asset registration with identical idempotency_key returns original asset without duplicating.
    """
    token = asset_test_setup["tokens"]["admin"]
    idem_key = f"idem_asset_{str(_u())}"

    payload = {
        "name": "Generator 5kVA",
        "category": "heavy_machinery",
        "idempotency_key": idem_key,
        "location_type": "warehouse",
    }

    res1 = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res1.status_code == 201
    asset_id_1 = res1.json()["id"]

    res2 = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert res2.status_code == 201
    asset_id_2 = res2.json()["id"]

    assert asset_id_1 == asset_id_2

    # Verify only 1 Asset and 1 AssetTransaction exist
    async with TestingSessionLocal() as session:
        tx_count = (
            await session.execute(
                select(AssetTransaction).where(AssetTransaction.idempotency_key == idem_key)
            )
        ).scalars().all()
        assert len(tx_count) == 1


# =========================================================================
# 3. AUTHORIZATION & PERMISSION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_asset_permissions(client: TestClient, asset_test_setup):
    """
    Role check matrix:
    - Director: can register (201), can list (200), can get detail (200)
    - Administrator: can register (201), can list (200), can get detail (200)
    - Supervisor: can register (201), can list all assets (200), can get detail (200)
    - Employee: CANNOT register (403), CANNOT list (403), CANNOT get detail (403)
    - Unauthenticated: rejected (401/403)
    """
    tokens = asset_test_setup["tokens"]
    site_a = asset_test_setup["site_a"]

    # 1. Unauthenticated registration rejected
    res_unauth = client.post("/api/v1/assets", json={"name": "No Auth", "category": "tools"})
    assert res_unauth.status_code in (401, 403)

    # 2. Employee registration blocked (403)
    res_emp = client.post(
        "/api/v1/assets",
        json={"name": "Employee Attempt", "category": "tools"},
        headers=_auth(tokens["employee"]),
    )
    assert res_emp.status_code == 403

    # 3. Supervisor registration succeeds with full registry access (201)
    res_sup = client.post(
        "/api/v1/assets",
        json={
            "name": "Supervisor Registered Asset",
            "category": "tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(tokens["supervisor_a"]),
    )
    assert res_sup.status_code == 201
    created_sup_id = res_sup.json()["id"]

    # 4. Director registration succeeds at Site Alpha (201)
    res_dir = client.post(
        "/api/v1/assets",
        json={
            "name": "Director Site A Asset",
            "category": "tools",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(tokens["director"]),
    )
    assert res_dir.status_code == 201
    created_id = res_dir.json()["id"]

    # 5. Supervisor A can view list and detail of their site asset and director asset (200)
    res_sup_list = client.get("/api/v1/assets", headers=_auth(tokens["supervisor_a"]))
    assert res_sup_list.status_code == 200

    res_sup_det = client.get(f"/api/v1/assets/{created_id}", headers=_auth(tokens["supervisor_a"]))
    assert res_sup_det.status_code == 200

    # 6. Employee cannot view list or detail (403)
    res_emp_list = client.get("/api/v1/assets", headers=_auth(tokens["employee"]))
    assert res_emp_list.status_code == 403

    res_emp_det = client.get(f"/api/v1/assets/{created_id}", headers=_auth(tokens["employee"]))
    assert res_emp_det.status_code == 403


@pytest.mark.asyncio
async def test_supervisor_full_registry_access(client: TestClient, asset_test_setup):
    """
    Exhaustive tests proving Supervisors receive the exact same Asset Management Registry access as Administrators:
    - Supervisor A can view warehouse assets and all site assets in unfiltered registry list.
    - Supervisor A can view warehouse asset details and transaction history by UUID.
    - Supervisor A can view other sites' (Site Beta) asset details by UUID.
    - Supervisor A can explicitly filter by location_type=warehouse and location_type=site.
    - Supervisor A can explicitly filter by any site_id (including Site Beta).
    - Supervisor A can fetch active sites via GET /api/v1/assets/sites.
    - Administrators and directors retain global access.
    """
    token_admin = asset_test_setup["tokens"]["admin"]
    token_dir = asset_test_setup["tokens"]["director"]
    token_sup_a = asset_test_setup["tokens"]["supervisor_a"]
    token_sup_b = asset_test_setup["tokens"]["supervisor_b"]
    site_a = asset_test_setup["site_a"]
    site_b = asset_test_setup["site_b"]

    sfx = str(_u())[:6]

    # Admin registers 3 assets:
    # 1. Central warehouse asset
    res_wh = client.post(
        "/api/v1/assets",
        json={"name": f"Warehouse_Crane_{sfx}", "category": "heavy_machinery", "location_type": "warehouse"},
        headers=_auth(token_admin),
    )
    assert res_wh.status_code == 201
    ast_wh = res_wh.json()

    # 2. Site Alpha asset
    res_sa = client.post(
        "/api/v1/assets",
        json={
            "name": f"SiteA_Excavator_{sfx}",
            "category": "heavy_machinery",
            "location_type": "site",
            "current_site_id": str(site_a.id),
        },
        headers=_auth(token_admin),
    )
    assert res_sa.status_code == 201
    ast_sa = res_sa.json()

    # 3. Site Beta asset
    res_sb = client.post(
        "/api/v1/assets",
        json={
            "name": f"SiteB_Scaffolding_{sfx}",
            "category": "safety_gear",
            "location_type": "site",
            "current_site_id": str(site_b.id),
        },
        headers=_auth(token_admin),
    )
    assert res_sb.status_code == 201
    ast_sb = res_sb.json()

    # --- SUPERVISOR FULL ACCESS CHECKS ---

    # 1. Unfiltered list for Supervisor A: sees all 3 assets (warehouse, Site Alpha, and Site Beta)
    res_list_a = client.get(f"/api/v1/assets?search={sfx}", headers=_auth(token_sup_a))
    assert res_list_a.status_code == 200
    items_a = res_list_a.json()["items"]
    item_ids_a = {it["id"] for it in items_a}
    assert ast_sa["id"] in item_ids_a
    assert ast_wh["id"] in item_ids_a
    assert ast_sb["id"] in item_ids_a

    # 2. Supervisor A can view their site's asset by UUID
    res_det_sa = client.get(f"/api/v1/assets/{ast_sa['id']}", headers=_auth(token_sup_a))
    assert res_det_sa.status_code == 200
    assert res_det_sa.json()["name"] == ast_sa["name"]

    # 3. Supervisor A requesting location_type=warehouse succeeds (200 OK)
    res_wh_req = client.get(f"/api/v1/assets?location_type=warehouse&search={sfx}", headers=_auth(token_sup_a))
    assert res_wh_req.status_code == 200
    wh_items = res_wh_req.json()["items"]
    assert any(it["id"] == ast_wh["id"] for it in wh_items)

    # 4. Supervisor A requesting warehouse asset by UUID succeeds (200 OK)
    res_wh_det = client.get(f"/api/v1/assets/{ast_wh['id']}", headers=_auth(token_sup_a))
    assert res_wh_det.status_code == 200
    assert res_wh_det.json()["name"] == ast_wh["name"]

    # 5. Supervisor A supplying site_id for Site Beta succeeds (200 OK)
    res_site_b_list = client.get(f"/api/v1/assets?site_id={site_b.id}&search={sfx}", headers=_auth(token_sup_a))
    assert res_site_b_list.status_code == 200
    sb_items = res_site_b_list.json()["items"]
    assert any(it["id"] == ast_sb["id"] for it in sb_items)

    # 6. Supervisor A retrieving Site Beta asset by UUID succeeds (200 OK)
    res_site_b_det = client.get(f"/api/v1/assets/{ast_sb['id']}", headers=_auth(token_sup_a))
    assert res_site_b_det.status_code == 200
    assert res_site_b_det.json()["name"] == ast_sb["name"]

    # 7. Supervisor can retrieve active sites via GET /api/v1/assets/sites
    res_sites = client.get("/api/v1/assets/sites", headers=_auth(token_sup_a))
    assert res_sites.status_code == 200
    active_site_ids = {s["id"] for s in res_sites.json()}
    assert str(site_a.id) in active_site_ids
    assert str(site_b.id) in active_site_ids

    # --- SUPERVISOR B CHECKS ---
    # Supervisor B can view Site Alpha, Site Beta, and Warehouse assets
    assert client.get(f"/api/v1/assets/{ast_sa['id']}", headers=_auth(token_sup_b)).status_code == 200
    assert client.get(f"/api/v1/assets/{ast_sb['id']}", headers=_auth(token_sup_b)).status_code == 200
    assert client.get(f"/api/v1/assets/{ast_wh['id']}", headers=_auth(token_sup_b)).status_code == 200

    # --- ADMINISTRATOR & DIRECTOR GLOBAL ACCESS ---
    for admin_tok in [token_admin, token_dir]:
        res_glob = client.get(f"/api/v1/assets?search={sfx}", headers=_auth(admin_tok))
        assert res_glob.status_code == 200
        glob_ids = {it["id"] for it in res_glob.json()["items"]}
        assert {ast_wh["id"], ast_sa["id"], ast_sb["id"]}.issubset(glob_ids)

        assert client.get(f"/api/v1/assets/{ast_wh['id']}", headers=_auth(admin_tok)).status_code == 200
        assert client.get(f"/api/v1/assets/{ast_sa['id']}", headers=_auth(admin_tok)).status_code == 200
        assert client.get(f"/api/v1/assets/{ast_sb['id']}", headers=_auth(admin_tok)).status_code == 200

        assert client.get(f"/api/v1/assets?location_type=warehouse&search={sfx}", headers=_auth(admin_tok)).status_code == 200
        assert client.get(f"/api/v1/assets?site_id={site_b.id}&search={sfx}", headers=_auth(admin_tok)).status_code == 200


# =========================================================================
# 4. SEARCH, FILTERING, & DETAIL TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_list_and_filter_assets(client: TestClient, asset_test_setup):
    """
    Tests filtering by location_type (warehouse vs site), site_id, category, status,
    search term, and pagination for administrator.
    """
    token = asset_test_setup["tokens"]["admin"]
    site_a = asset_test_setup["site_a"]
    site_b = asset_test_setup["site_b"]

    prefix = str(_u())[:6]

    # Create 3 distinct assets:
    # 1. Warehouse asset
    res1 = client.post(
        "/api/v1/assets",
        json={
            "name": f"Fluke Multimeter {prefix}",
            "category": "electrical_testing",
            "model_number": "FLUKE-117",
            "serial_number": f"SN-FLUKE-{prefix}",
            "location_type": "warehouse",
            "status": "available",
            "condition": "good",
        },
        headers=_auth(token),
    )
    assert res1.status_code == 201
    ast_wh = res1.json()

    # 2. Site Alpha asset
    res2 = client.post(
        "/api/v1/assets",
        json={
            "name": f"Total Station Survey {prefix}",
            "category": "survey_equipment",
            "model_number": "LEICA-TS07",
            "serial_number": f"SN-LEICA-{prefix}",
            "location_type": "site",
            "current_site_id": str(site_a.id),
            "status": "available",
            "condition": "new",
        },
        headers=_auth(token),
    )
    assert res2.status_code == 201
    ast_site_a = res2.json()

    # 3. Site Beta asset
    res3 = client.post(
        "/api/v1/assets",
        json={
            "name": f"Air Compressor 100L {prefix}",
            "category": "pneumatic_tools",
            "model_number": "COMP-100",
            "serial_number": f"SN-COMP-{prefix}",
            "location_type": "site",
            "current_site_id": str(site_b.id),
            "status": "under_maintenance",
            "condition": "fair",
        },
        headers=_auth(token),
    )
    assert res3.status_code == 201
    ast_site_b = res3.json()

    # Filter 1: location_type=warehouse
    res_wh = client.get(f"/api/v1/assets?search={prefix}&location_type=warehouse", headers=_auth(token))
    assert res_wh.status_code == 200
    wh_items = res_wh.json()["items"]
    assert len(wh_items) == 1
    assert wh_items[0]["id"] == ast_wh["id"]
    assert wh_items[0]["location_type"] == "warehouse"
    assert wh_items[0]["current_site_id"] is None

    # Filter 2: location_type=site
    res_site = client.get(f"/api/v1/assets?search={prefix}&location_type=site", headers=_auth(token))
    assert res_site.status_code == 200
    site_items = res_site.json()["items"]
    assert len(site_items) == 2
    site_ids = {item["id"] for item in site_items}
    assert ast_site_a["id"] in site_ids
    assert ast_site_b["id"] in site_ids

    # Filter 3: site_id=site_a.id
    res_site_a = client.get(f"/api/v1/assets?search={prefix}&site_id={site_a.id}", headers=_auth(token))
    assert res_site_a.status_code == 200
    assert len(res_site_a.json()["items"]) == 1
    assert res_site_a.json()["items"][0]["id"] == ast_site_a["id"]
    assert res_site_a.json()["items"][0]["current_site_name"] == site_a.name

    # Filter 4: category=pneumatic_tools
    res_cat = client.get(f"/api/v1/assets?search={prefix}&category=pneumatic_tools", headers=_auth(token))
    assert res_cat.status_code == 200
    assert len(res_cat.json()["items"]) == 1
    assert res_cat.json()["items"][0]["id"] == ast_site_b["id"]

    # Filter 5: status=under_maintenance
    res_st = client.get(f"/api/v1/assets?search={prefix}&status=under_maintenance", headers=_auth(token))
    assert res_st.status_code == 200
    assert len(res_st.json()["items"]) == 1
    assert res_st.json()["items"][0]["id"] == ast_site_b["id"]

    # Filter 6: Search by model number
    res_model = client.get(f"/api/v1/assets?search=LEICA-TS07", headers=_auth(token))
    assert res_model.status_code == 200
    assert any(item["id"] == ast_site_a["id"] for item in res_model.json()["items"])

    # Filter 7: Pagination
    res_page = client.get(f"/api/v1/assets?search={prefix}&skip=0&limit=2", headers=_auth(token))
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert page_data["total"] == 3
    assert len(page_data["items"]) == 2


@pytest.mark.asyncio
async def test_get_asset_detail_with_transaction_history(client: TestClient, asset_test_setup):
    """
    Tests GET /api/v1/assets/{asset_id} detail retrieval.
    Verifies that the initial registration transaction is present in the transaction history.
    """
    token = asset_test_setup["tokens"]["admin"]
    site_a = asset_test_setup["site_a"]

    res = client.post(
        "/api/v1/assets",
        json={
            "name": "Precision Theodolite",
            "category": "survey_equipment",
            "location_type": "site",
            "current_site_id": str(site_a.id),
            "remarks": "Assigned for bridge survey",
        },
        headers=_auth(token),
    )
    assert res.status_code == 201
    asset_id = res.json()["id"]

    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=_auth(token))
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["id"] == asset_id
    assert detail["name"] == "Precision Theodolite"
    assert detail["current_site_name"] == site_a.name
    assert "transactions" in detail
    assert len(detail["transactions"]) == 1

    tx = detail["transactions"][0]
    assert tx["transaction_type"] == "registered"
    assert tx["to_location_type"] == "site"
    assert tx["to_site_id"] == str(site_a.id)
    assert tx["to_site_name"] == site_a.name
    assert tx["remarks"] == "Assigned for bridge survey"

    # Non-existent asset ID returns 404
    fake_id = _u()
    not_found_res = client.get(f"/api/v1/assets/{fake_id}", headers=_auth(token))
    assert not_found_res.status_code == 404
    assert f"Asset {fake_id} not found" in not_found_res.text

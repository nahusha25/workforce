from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.auth import User
from app.models.invoices import Invoice, InvoiceLineItem
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    Material,
    MaterialTransaction,
    Project,
    Site,
)
from app.models.workforce import Employee, Role
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def api_setup():
    """Sets up an environment with admin, director, supervisor, employee users,
    client, project, site, and billable approved records."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")
        session.add_all([u_admin, u_dir, u_sup, u_emp])
        await session.flush()

        # 2. Client, Project, Site
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Project_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        # Other client/project for scoping checks
        client_other = Client(id=_u(), name=f"ClientOther_{sfx}")
        session.add(client_other)
        await session.flush()

        project_other = Project(id=_u(), client_id=client_other.id, name=f"ProjOther_{sfx}", status="in_progress")
        session.add(project_other)
        await session.flush()

        # 3. Workforce & Catalog
        role = Role(id=_u(), name=f"Role_{sfx}")
        session.add(role)
        await session.flush()

        emp = Employee(
            id=_u(),
            user_id=u_emp.id,
            employee_code=f"EMP_{sfx}",
            mobile_id=u_emp.mobile_id,
            name=f"Worker_{sfx}",
        )
        session.add(emp)
        await session.flush()

        act1 = Activity(id=_u(), name=f"Cabling_{sfx}", unit_of_measure="metre", approved_rate=100.00, category="cable")
        mat1 = Material(id=_u(), name=f"Connectors_{sfx}", unit_of_measure="pack", category="consumable", purchase_approval_limit=5000.00)
        session.add_all([act1, mat1])
        await session.flush()

        # 4. Attendance
        att = AttendanceRecord(
            id=_u(),
            employee_id=emp.id,
            site_id=site.id,
            date=date(2026, 10, 5),
            status="approved",
            check_in_time=_now(),
        )
        session.add(att)
        await session.flush()

        # 5. Work entry (50 metres @ 100 = 5000.00)
        dwe = DailyWorkEntry(
            id=_u(),
            idempotency_key=f"dwe_api_{sfx}",
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            activity_id=act1.id,
            work_date=date(2026, 10, 5),
            quantity=50.0,
            uom="metre",
            status="approved",
        )
        session.add(dwe)
        await session.flush()

        # 6. Material entry (2 packs @ 800.00)
        mt = MaterialTransaction(
            id=_u(),
            daily_work_entry_id=dwe.id,
            material_id=mat1.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="RJ45 Connectors",
            quantity=2.0,
            amount=800.0,
            status="approved",
        )
        session.add(mt)
        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), u_admin.role),
            "director": create_access_token(str(u_dir.id), u_dir.role),
            "supervisor": create_access_token(str(u_sup.id), u_sup.role),
            "employee": create_access_token(str(u_emp.id), u_emp.role),
        }

        return {
            "users": {"admin": u_admin, "director": u_dir, "supervisor": u_sup, "employee": u_emp},
            "tokens": tokens,
            "client": client,
            "client_other": client_other,
            "project": project,
            "project_other": project_other,
            "site": site,
            "dwe": dwe,
            "mt": mt,
            "act1": act1,
            "mat1": mat1,
        }


# ---------------------------------------------------------------------------
# 1. Route Registration & OpenAPI Exposure
# ---------------------------------------------------------------------------

def test_invoice_routes_registration_and_openapi(client: TestClient):
    """Verifies that invoice endpoints are registered in FastAPI app and present in OpenAPI schema."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    expected_routes = [
        "/api/v1/invoices/preview",
        "/api/v1/invoices/generate",
        "/api/v1/invoices",
        "/api/v1/invoices/{invoice_id}",
        "/api/v1/invoices/{invoice_id}/issue",
        "/api/v1/invoices/{invoice_id}/cancel",
    ]
    for route in expected_routes:
        assert route in paths, f"Route {route} not found in OpenAPI schema!"


# ---------------------------------------------------------------------------
# 2. RBAC Protections
# ---------------------------------------------------------------------------

def test_invoice_api_rbac_protections(client: TestClient, api_setup):
    """Verifies that:
    - Unauthenticated requests receive 401
    - Employees receive 403
    - Supervisors receive 403
    - Directors and Administrators have access."""
    tokens = api_setup["tokens"]
    data = api_setup
    preview_url = (
        f"/api/v1/invoices/preview?client_id={data['client'].id}&project_id={data['project'].id}"
        f"&site_id={data['site'].id}&period_start=2026-10-01&period_end=2026-10-07"
    )

    # 1. Unauthenticated -> 401
    resp = client.get(preview_url)
    assert resp.status_code == 401

    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 401

    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/invoices/{fake_id}")
    assert resp.status_code == 401

    resp = client.post(f"/api/v1/invoices/{fake_id}/issue")
    assert resp.status_code == 401

    resp = client.post(f"/api/v1/invoices/{fake_id}/cancel", json={"cancellation_reason": "test"})
    assert resp.status_code == 401

    # 2. Employee -> 403 Forbidden
    resp = client.get(preview_url, headers=_auth(tokens["employee"]))
    assert resp.status_code == 403

    resp = client.get("/api/v1/invoices", headers=_auth(tokens["employee"]))
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["employee"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "idempotency_key": "emp_forbidden",
        },
    )
    assert resp.status_code == 403

    # 3. Supervisor -> 403 Forbidden
    resp = client.get(preview_url, headers=_auth(tokens["supervisor"]))
    assert resp.status_code == 403

    resp = client.get("/api/v1/invoices", headers=_auth(tokens["supervisor"]))
    assert resp.status_code == 403

    # 4. Administrator and Director -> 200 OK
    resp_dir = client.get(preview_url, headers=_auth(tokens["director"]))
    assert resp_dir.status_code == 200

    resp_adm = client.get(preview_url, headers=_auth(tokens["admin"]))
    assert resp_adm.status_code == 200


# ---------------------------------------------------------------------------
# 3. Preview Endpoint (GET & POST)
# ---------------------------------------------------------------------------

def test_api_preview_invoice(client: TestClient, api_setup):
    """Verifies invoice preview calculation via GET query params and POST body."""
    tokens = api_setup["tokens"]
    data = api_setup

    # GET preview
    resp = client.get(
        f"/api/v1/invoices/preview?client_id={data['client'].id}&project_id={data['project'].id}"
        f"&site_id={data['site'].id}&period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["director"]),
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["billable_work_count"] == 1
    assert res_data["billable_material_count"] == 1
    assert float(res_data["subtotal_work"]) == 5000.00  # 50 * 100
    assert float(res_data["subtotal_material"]) == 800.00
    assert float(res_data["estimated_tax"]) == 0.00
    assert float(res_data["estimated_total"]) == 5800.00

    # POST preview
    resp_post = client.post(
        "/api/v1/invoices/preview",
        headers=_auth(tokens["admin"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
        },
    )
    assert resp_post.status_code == 200
    assert resp_post.json()["estimated_total"] == res_data["estimated_total"]

    # Hierarchy validation failure (site mismatch) -> 422
    resp_err = client.get(
        f"/api/v1/invoices/preview?client_id={data['client'].id}&project_id={data['project_other'].id}"
        f"&site_id={data['site'].id}&period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["director"]),
    )
    assert resp_err.status_code == 422


# ---------------------------------------------------------------------------
# 4. Invoice Generation & Idempotency
# ---------------------------------------------------------------------------

def test_api_generate_invoice_flow(client: TestClient, api_setup):
    """Verifies invoice generation, idempotency replay, and 409 conflict handling."""
    tokens = api_setup["tokens"]
    data = api_setup
    idem_key = f"api_gen_{_u().hex[:8]}"

    payload = {
        "client_id": str(data["client"].id),
        "project_id": str(data["project"].id),
        "site_id": str(data["site"].id),
        "period_start": "2026-10-01",
        "period_end": "2026-10-07",
        "idempotency_key": idem_key,
        "client_po_number": "PO-API-001",
        "notes": "Generated via API",
    }

    # 1. Generate invoice -> 201 Created
    resp = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json=payload,
    )
    assert resp.status_code == 201
    inv = resp.json()
    assert inv["status"] == "draft"
    assert inv["invoice_number"].startswith("INV-")
    assert float(inv["subtotal_work"]) == 5000.00
    assert float(inv["subtotal_material"]) == 800.00
    assert float(inv["total_amount"]) == 5800.00
    assert len(inv["lines"]) == 2

    # 2. Replay with exact same idempotency_key -> returns same invoice (201)
    resp_replay = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json=payload,
    )
    assert resp_replay.status_code == 201
    assert resp_replay.json()["id"] == inv["id"]
    assert resp_replay.json()["invoice_number"] == inv["invoice_number"]

    # 3. Same idempotency key with conflicting period dates -> 409 Conflict
    payload_conf = dict(payload)
    payload_conf["period_end"] = "2026-10-15"
    resp_conf = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json=payload_conf,
    )
    assert resp_conf.status_code == 409

    # 4. Different idempotency key for same period -> 400 Bad Request (no unbilled records)
    payload_dup = dict(payload)
    payload_dup["idempotency_key"] = f"api_gen_dup_{_u().hex[:8]}"
    resp_dup = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json=payload_dup,
    )
    assert resp_dup.status_code == 400


# ---------------------------------------------------------------------------
# 5. Get and List Invoices
# ---------------------------------------------------------------------------

def test_api_get_and_list_invoices(client: TestClient, api_setup):
    """Verifies getting invoice by ID and listing invoices with query filters."""
    tokens = api_setup["tokens"]
    data = api_setup

    # Generate an invoice
    resp_gen = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["admin"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "idempotency_key": f"get_list_{_u().hex[:8]}",
        },
    )
    inv_id = resp_gen.json()["id"]

    # Get by ID -> 200 OK
    resp_get = client.get(f"/api/v1/invoices/{inv_id}", headers=_auth(tokens["admin"]))
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == inv_id
    assert resp_get.json()["client_name"] == data["client"].name

    # Non-existent ID -> 404
    resp_404 = client.get(f"/api/v1/invoices/{uuid.uuid4()}", headers=_auth(tokens["admin"]))
    assert resp_404.status_code == 404

    # List invoices -> 200 OK
    resp_list = client.get(
        f"/api/v1/invoices?client_id={data['client'].id}&status=draft",
        headers=_auth(tokens["director"]),
    )
    assert resp_list.status_code == 200
    invoices = resp_list.json()
    assert len(invoices) >= 1
    assert any(i["id"] == inv_id for i in invoices)


# ---------------------------------------------------------------------------
# 6. Draft Update: Metadata, Tax, and Rate Overrides
# ---------------------------------------------------------------------------

def test_api_update_draft_invoice(client: TestClient, api_setup):
    """Verifies updating draft invoice with metadata, tax amount, and Director rate override."""
    tokens = api_setup["tokens"]
    data = api_setup

    resp_gen = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "idempotency_key": f"upd_{_u().hex[:8]}",
        },
    )
    inv_id = resp_gen.json()["id"]

    # 1. Update metadata and tax -> 200 OK
    resp_upd = client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=_auth(tokens["director"]),
        json={
            "client_po_number": "PO-REVISED-002",
            "tax_amount": 500.00,
            "rate_overrides": [
                {
                    "source_id": str(data["dwe"].id),
                    "unit_rate": 120.00,
                    "rate_override_reason": "Approved higher rate for difficult terrain",
                }
            ],
        },
    )
    assert resp_upd.status_code == 200
    updated = resp_upd.json()
    assert updated["client_po_number"] == "PO-REVISED-002"
    assert float(updated["tax_amount"]) == 500.00
    # 50 * 120 = 6000 (work) + 800 (mat) = 6800 + 500 (tax) = 7300
    assert float(updated["subtotal_work"]) == 6000.00
    assert float(updated["total_amount"]) == 7300.00

    # 2. Rate override without mandatory reason -> 422
    resp_no_rsn = client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=_auth(tokens["director"]),
        json={
            "rate_overrides": [
                {
                    "source_id": str(data["dwe"].id),
                    "unit_rate": 130.00,
                    "rate_override_reason": "  ",
                }
            ]
        },
    )
    assert resp_no_rsn.status_code == 422


# ---------------------------------------------------------------------------
# 7. Issue & Cancel Lifecycle
# ---------------------------------------------------------------------------

def test_api_issue_and_cancel_lifecycle(client: TestClient, api_setup):
    """Verifies issuing draft invoice and atomic cancellation with lock release."""
    tokens = api_setup["tokens"]
    data = api_setup

    resp_gen = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "idempotency_key": f"iss_can_{_u().hex[:8]}",
        },
    )
    inv_id = resp_gen.json()["id"]

    # 1. Issue invoice -> 200 OK
    resp_iss = client.post(
        f"/api/v1/invoices/{inv_id}/issue",
        headers=_auth(tokens["director"]),
        json={"issue_date": "2026-10-08", "due_date": "2026-10-22"},
    )
    assert resp_iss.status_code == 200
    assert resp_iss.json()["status"] == "issued"
    assert resp_iss.json()["issue_date"] == "2026-10-08"

    # 2. Attempting to update issued invoice -> 400 Bad Request
    resp_bad_upd = client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=_auth(tokens["director"]),
        json={"notes": "Illegal edit"},
    )
    assert resp_bad_upd.status_code == 400

    # 3. Cancel issued unpaid invoice -> 200 OK
    resp_can = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        headers=_auth(tokens["director"]),
        json={"cancellation_reason": "Client cancelled contract scope"},
    )
    assert resp_can.status_code == 200
    assert resp_can.json()["status"] == "cancelled"

    # 4. Re-cancelling already cancelled invoice -> 400 Bad Request
    resp_re_can = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        headers=_auth(tokens["director"]),
        json={"cancellation_reason": "Repeat cancellation"},
    )
    assert resp_re_can.status_code == 400

    # 5. Operational records are unbilled and eligible for billing again
    resp_prev = client.get(
        f"/api/v1/invoices/preview?client_id={data['client'].id}&project_id={data['project'].id}"
        f"&site_id={data['site'].id}&period_start=2026-10-01&period_end=2026-10-07",
        headers=_auth(tokens["director"]),
    )
    assert resp_prev.status_code == 200
    assert resp_prev.json()["billable_work_count"] == 1
    assert resp_prev.json()["billable_material_count"] == 1


# ---------------------------------------------------------------------------
# 8. Prohibited Cancellation of Paid Invoices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_prohibited_cancellation_of_paid_invoices(client: TestClient, api_setup):
    """Verifies that attempting to cancel a paid or partially paid invoice returns 400."""
    tokens = api_setup["tokens"]
    data = api_setup

    resp_gen = client.post(
        "/api/v1/invoices/generate",
        headers=_auth(tokens["director"]),
        json={
            "client_id": str(data["client"].id),
            "project_id": str(data["project"].id),
            "site_id": str(data["site"].id),
            "period_start": "2026-10-01",
            "period_end": "2026-10-07",
            "idempotency_key": f"paid_can_{_u().hex[:8]}",
        },
    )
    inv_id = resp_gen.json()["id"]

    # Simulate paid invoice directly in DB
    async with TestingSessionLocal() as session:
        await session.execute(
            text("UPDATE invoices SET status = 'paid', paid_amount = total_amount WHERE id = :id"),
            {"id": uuid.UUID(inv_id)},
        )
        await session.commit()

    resp_can = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        headers=_auth(tokens["director"]),
        json={"cancellation_reason": "Illegal cancellation of paid invoice"},
    )
    assert resp_can.status_code == 400
    assert "Paid or partially paid invoices cannot be cancelled" in resp_can.json()["detail"]

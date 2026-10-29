from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app
from app.models.auth import User
from app.models.client_payments import ClientPayment
from app.models.invoices import Invoice
from app.models.operations import Client, Project, Site
from app.models.system import AuditLog
from app.shared.file_storage import get_file_storage
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def payment_api_setup():
    """Sets up users and an issued invoice for client payment API testing."""
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # 1. Users
        u_admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")
        session.add_all([u_admin, u_dir, u_sup, u_emp])
        await session.flush()

        # 2. Master data
        client = Client(id=_u(), name=f"Client_{sfx}")
        session.add(client)
        await session.flush()

        project = Project(id=_u(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
        session.add(project)
        await session.flush()

        site = Site(id=_u(), project_id=project.id, name=f"Site_{sfx}")
        session.add(site)
        await session.flush()

        # 3. Issued invoice with 50,000.00 total
        invoice = Invoice(
            id=_u(),
            invoice_number=f"INV-{sfx.upper()}",
            idempotency_key=f"inv_idem_{sfx}",
            client_id=client.id,
            project_id=project.id,
            site_id=site.id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 7),
            issue_date=date(2026, 10, 7),
            due_date=date(2026, 10, 21),
            status="issued",
            subtotal_work=Decimal("40000.00"),
            subtotal_material=Decimal("5000.00"),
            tax_amount=Decimal("5000.00"),
            total_amount=Decimal("50000.00"),
            paid_amount=Decimal("0.00"),
            created_by=u_dir.id,
            issued_by=u_dir.id,
        )
        session.add(invoice)
        await session.commit()

        tokens = {
            "admin": create_access_token(str(u_admin.id), u_admin.role),
            "director": create_access_token(str(u_dir.id), u_dir.role),
            "supervisor": create_access_token(str(u_sup.id), u_sup.role),
            "employee": create_access_token(str(u_emp.id), u_emp.role),
        }

        return {
            "tokens": tokens,
            "invoice": invoice,
            "client": client,
            "project": project,
            "site": site,
            "users": {
                "admin": u_admin,
                "director": u_dir,
                "supervisor": u_sup,
                "employee": u_emp,
            },
        }


# ---------------------------------------------------------------------------
# 1. Route Registration & OpenAPI Exposure
# ---------------------------------------------------------------------------

def test_client_payment_routes_openapi():
    """Verifies that client payment endpoints are registered in FastAPI app and present in OpenAPI schema."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    expected_routes = [
        "/api/v1/client-payments",
        "/api/v1/client-payments/invoice/{invoice_id}",
        "/api/v1/client-payments/{payment_id}",
        "/api/v1/client-payments/{payment_id}/void",
        "/api/v1/client-payments/{payment_id}/receipt",
    ]
    for route in expected_routes:
        assert route in paths, f"Route {route} not found in OpenAPI schema!"


# ---------------------------------------------------------------------------
# 2. RBAC Protections
# ---------------------------------------------------------------------------

def test_client_payment_api_rbac_protections(client: TestClient, payment_api_setup):
    """Verifies that:
    - Unauthenticated requests receive 401
    - Employees receive 403
    - Supervisors receive 403
    - Directors and Administrators have access."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    fake_id = str(uuid.uuid4())

    payload = {
        "idempotency_key": f"idem_rbac_{uuid.uuid4().hex[:8]}",
        "invoice_id": str(inv.id),
        "amount": "1000.00",
        "payment_date": "2026-10-08",
        "payment_method": "neft",
    }

    # 1. Unauthenticated -> 401
    assert client.post("/api/v1/client-payments", json=payload).status_code == 401
    assert client.get(f"/api/v1/client-payments/invoice/{inv.id}").status_code == 401
    assert client.get(f"/api/v1/client-payments/{fake_id}").status_code == 401
    assert client.post(f"/api/v1/client-payments/{fake_id}/void", json={"void_reason": "test"}).status_code == 401

    # 2. Employee -> 403 Forbidden
    assert client.post("/api/v1/client-payments", headers=_auth(tokens["employee"]), json=payload).status_code == 403
    assert client.get(f"/api/v1/client-payments/invoice/{inv.id}", headers=_auth(tokens["employee"])).status_code == 403
    assert client.get(f"/api/v1/client-payments/{fake_id}", headers=_auth(tokens["employee"])).status_code == 403
    assert client.post(f"/api/v1/client-payments/{fake_id}/void", headers=_auth(tokens["employee"]), json={"void_reason": "test"}).status_code == 403

    # 3. Supervisor -> 403 Forbidden
    assert client.post("/api/v1/client-payments", headers=_auth(tokens["supervisor"]), json=payload).status_code == 403
    assert client.get(f"/api/v1/client-payments/invoice/{inv.id}", headers=_auth(tokens["supervisor"])).status_code == 403
    assert client.get(f"/api/v1/client-payments/{fake_id}", headers=_auth(tokens["supervisor"])).status_code == 403
    assert client.post(f"/api/v1/client-payments/{fake_id}/void", headers=_auth(tokens["supervisor"]), json={"void_reason": "test"}).status_code == 403


# ---------------------------------------------------------------------------
# 3. Record Payment API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_payment_api_success_director(client: TestClient, payment_api_setup):
    """Verifies Director successfully records a partial payment via POST /api/v1/client-payments."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_rec_dir_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "20000.00",
            "payment_date": "2026-10-08",
            "payment_method": "neft",
            "reference_number": "UTR12345678",
            "notes": "First tranche from client",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == "20000.00"
    assert data["status"] == "recorded"
    assert data["payment_number"].startswith("CP-")
    assert data["reference_number"] == "UTR12345678"

    # Verify DB state of parent invoice
    async with TestingSessionLocal() as session:
        inv_db = await session.get(Invoice, inv.id)
        assert inv_db.paid_amount == Decimal("20000.00")
        assert inv_db.status == "partially_paid"


@pytest.mark.asyncio
async def test_record_payment_api_success_admin_full(client: TestClient, payment_api_setup):
    """Verifies Administrator successfully records a full payment transitioning invoice to 'paid'."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["admin"]),
        json={
            "idempotency_key": f"idem_rec_adm_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "50000.00",
            "payment_date": "2026-10-08",
            "payment_method": "rtgs",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == "50000.00"

    # Verify DB invoice is paid
    async with TestingSessionLocal() as session:
        inv_db = await session.get(Invoice, inv.id)
        assert inv_db.paid_amount == Decimal("50000.00")
        assert inv_db.status == "paid"


def test_record_payment_api_validations(client: TestClient, payment_api_setup):
    """Verifies schema and business rule rejections (amount <= 0, future date, overpayment, etc.)."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    # 1. Zero amount
    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_zero_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "0.00",
            "payment_date": "2026-10-08",
            "payment_method": "neft",
        },
    )
    assert resp.status_code == 422

    # 2. Future date
    tomorrow_str = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_fut_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "1000.00",
            "payment_date": tomorrow_str,
            "payment_method": "neft",
        },
    )
    assert resp.status_code == 422
    assert "future" in resp.json()["detail"].lower()

    # 3. Pre-issue date (invoice issue_date is 2026-10-07)
    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_pre_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "1000.00",
            "payment_date": "2026-10-06",
            "payment_method": "neft",
        },
    )
    assert resp.status_code == 422
    assert "precede" in resp.json()["detail"].lower()

    # 4. Invalid payment method
    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_method_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "1000.00",
            "payment_date": "2026-10-08",
            "payment_method": "bitcoin",
        },
    )
    assert resp.status_code == 422

    # 5. Overpayment (> 50,000.00)
    resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_over_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "50000.01",
            "payment_date": "2026-10-08",
            "payment_method": "neft",
        },
    )
    assert resp.status_code == 422
    assert "exceeds outstanding balance" in resp.json()["detail"].lower()


def test_record_payment_api_idempotency_replay_and_conflict(client: TestClient, payment_api_setup):
    """Verifies that repeating identical request returns existing payment, while conflicting payload returns 409."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]
    idem_key = f"idem_api_replay_{sfx}"

    payload = {
        "idempotency_key": idem_key,
        "invoice_id": str(inv.id),
        "amount": "10000.00",
        "payment_date": "2026-10-08",
        "payment_method": "neft",
    }

    # First call -> 201 Created
    r1 = client.post("/api/v1/client-payments", headers=_auth(tokens["director"]), json=payload)
    assert r1.status_code == 201
    p1 = r1.json()

    # Replay identical call -> 201 with same payment ID
    r2 = client.post("/api/v1/client-payments", headers=_auth(tokens["director"]), json=payload)
    assert r2.status_code == 201
    p2 = r2.json()
    assert p2["id"] == p1["id"]
    assert p2["payment_number"] == p1["payment_number"]

    # Conflict with same idempotency key but different amount -> 409 Conflict
    conflict_payload = {**payload, "amount": "12000.00"}
    r3 = client.post("/api/v1/client-payments", headers=_auth(tokens["director"]), json=conflict_payload)
    assert r3.status_code == 409
    assert "Idempotency conflict" in r3.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Listing and Detail Endpoints
# ---------------------------------------------------------------------------

def test_list_and_get_payment_api(client: TestClient, payment_api_setup):
    """Verifies GET /api/v1/client-payments/invoice/{invoice_id} and GET /api/v1/client-payments/{payment_id}."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    # Create payment 1
    r1 = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_list1_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "5000.00",
            "payment_date": "2026-10-07",
            "payment_method": "neft",
        },
    )
    p1_id = r1.json()["id"]

    # Create payment 2
    r2 = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_list2_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "10000.00",
            "payment_date": "2026-10-08",
            "payment_method": "rtgs",
        },
    )
    p2_id = r2.json()["id"]

    # 1. List by path: /api/v1/client-payments/invoice/{invoice_id}
    resp_path = client.get(f"/api/v1/client-payments/invoice/{inv.id}", headers=_auth(tokens["director"]))
    assert resp_path.status_code == 200
    list_data = resp_path.json()
    assert len(list_data) == 2
    # Ordered descending by payment_date
    assert list_data[0]["payment_date"] == "2026-10-08"
    assert list_data[1]["payment_date"] == "2026-10-07"

    # 2. List by query: /api/v1/client-payments?invoice_id={invoice_id}
    resp_query = client.get(f"/api/v1/client-payments?invoice_id={inv.id}", headers=_auth(tokens["admin"]))
    assert resp_query.status_code == 200
    assert len(resp_query.json()) == 2

    # 3. Get detail by ID
    resp_detail = client.get(f"/api/v1/client-payments/{p1_id}", headers=_auth(tokens["director"]))
    assert resp_detail.status_code == 200
    assert resp_detail.json()["id"] == p1_id
    assert resp_detail.json()["amount"] == "5000.00"

    # 4. Non-existent payment detail -> 404
    resp_404 = client.get(f"/api/v1/client-payments/{uuid.uuid4()}", headers=_auth(tokens["director"]))
    assert resp_404.status_code == 404


# ---------------------------------------------------------------------------
# 5. Void Payment API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_void_payment_api_success_and_idempotency(client: TestClient, payment_api_setup):
    """Verifies voiding a payment via POST /api/v1/client-payments/{id}/void and testing void idempotency."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    # Record 50k payment
    rec_resp = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_void_orig_{sfx}",
            "invoice_id": str(inv.id),
            "amount": "50000.00",
            "payment_date": "2026-10-08",
            "payment_method": "cheque",
        },
    )
    pid = rec_resp.json()["id"]

    # 1. Invalid void reason (< 10 trimmed characters) -> 422
    resp_short = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": f"void_short_{sfx}",
            "void_reason": "bounced",  # < 10 characters
        },
    )
    assert resp_short.status_code == 422

    # 2. Successful void with valid reason (>= 10 characters)
    void_key = f"void_idem_api_{sfx}"
    resp_void = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": void_key,
            "void_reason": "Cheque bounced during bank clearing process",
        },
    )
    assert resp_void.status_code == 200
    void_data = resp_void.json()
    assert void_data["status"] == "voided"
    assert void_data["void_reason"] == "Cheque bounced during bank clearing process"
    assert void_data["voided_at"] is not None

    # Check parent invoice reverted to issued
    async with TestingSessionLocal() as session:
        inv_db = await session.get(Invoice, inv.id)
        assert inv_db.paid_amount == Decimal("0.00")
        assert inv_db.status == "issued"

    # 3. Idempotent replay with SAME void_idempotency_key -> 200 OK
    resp_replay = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": void_key,
            "void_reason": "Cheque bounced during bank clearing process",
        },
    )
    assert resp_replay.status_code == 200
    assert resp_replay.json()["id"] == pid

    # 4. Conflicting void key on already voided payment -> 409 Conflict
    resp_conf = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": f"diff_void_key_{sfx}",
            "void_reason": "Second attempt with different void key",
        },
    )
    assert resp_conf.status_code == 409


# ---------------------------------------------------------------------------
# 6. Receipt Upload and Download API Tests
# ---------------------------------------------------------------------------

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
VALID_WEBP_BYTES = b"RIFF\x1c\x00\x00\x00WEBPVP8 \x10\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00"


def _create_test_payment(client: TestClient, tokens: dict, inv_id: str, amount: str = "5000.00") -> str:
    sfx = str(uuid.uuid4())[:8]
    res = client.post(
        "/api/v1/client-payments",
        headers=_auth(tokens["director"]),
        json={
            "idempotency_key": f"idem_rec_rcpt_{sfx}",
            "invoice_id": inv_id,
            "amount": amount,
            "payment_date": "2026-10-08",
            "payment_method": "neft",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_receipt_api_rbac_protections(client: TestClient, payment_api_setup):
    """Verifies that receipt upload and access require Director or Administrator authorization."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "2000.00")

    file_tuple = ("receipt.pdf", VALID_PDF_BYTES, "application/pdf")

    # 1. Unauthenticated -> 401
    assert client.post(f"/api/v1/client-payments/{pid}/receipt", files={"file": file_tuple}).status_code == 401
    assert client.get(f"/api/v1/client-payments/{pid}/receipt").status_code == 401

    # 2. Employee -> 403
    assert client.post(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["employee"]), files={"file": file_tuple}).status_code == 403
    assert client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["employee"])).status_code == 403

    # 3. Supervisor -> 403
    assert client.post(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["supervisor"]), files={"file": file_tuple}).status_code == 403
    assert client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["supervisor"])).status_code == 403


def test_receipt_api_pdf_upload_and_download(client: TestClient, payment_api_setup):
    """Verifies successful PDF receipt upload by Director and download by Administrator."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "3000.00")

    # Upload PDF
    resp_upload = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("acknowledgement.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert resp_upload.status_code == 200
    data = resp_upload.json()
    assert data["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"

    # Download receipt (Admin)
    resp_dl = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["admin"]))
    assert resp_dl.status_code == 200
    assert "application/pdf" in resp_dl.headers["content-type"]
    assert resp_dl.content == VALID_PDF_BYTES


def test_receipt_api_images_upload_jpeg_png_webp(client: TestClient, payment_api_setup):
    """Verifies that JPEG, PNG, and WebP receipts can be uploaded and downloaded."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]

    # 1. JPEG
    p_jpeg = _create_test_payment(client, tokens, str(inv.id), "1000.00")
    r_jpg = client.post(
        f"/api/v1/client-payments/{p_jpeg}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("slip.jpg", VALID_JPEG_BYTES, "image/jpeg")},
    )
    assert r_jpg.status_code == 200
    get_jpg = client.get(f"/api/v1/client-payments/{p_jpeg}/receipt", headers=_auth(tokens["director"]))
    assert get_jpg.status_code == 200
    assert "image/jpeg" in get_jpg.headers["content-type"]

    # 2. PNG
    p_png = _create_test_payment(client, tokens, str(inv.id), "1000.00")
    r_png = client.post(
        f"/api/v1/client-payments/{p_png}/receipt",
        headers=_auth(tokens["admin"]),
        files={"file": ("slip.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r_png.status_code == 200
    get_png = client.get(f"/api/v1/client-payments/{p_png}/receipt", headers=_auth(tokens["admin"]))
    assert get_png.status_code == 200
    assert "image/png" in get_png.headers["content-type"]

    # 3. WebP
    p_webp = _create_test_payment(client, tokens, str(inv.id), "1000.00")
    r_webp = client.post(
        f"/api/v1/client-payments/{p_webp}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("slip.webp", VALID_WEBP_BYTES, "image/webp")},
    )
    assert r_webp.status_code == 200
    get_webp = client.get(f"/api/v1/client-payments/{p_webp}/receipt", headers=_auth(tokens["director"]))
    assert get_webp.status_code == 200
    assert "image/webp" in get_webp.headers["content-type"]


def test_receipt_api_invalid_format_and_oversized_rejected(client: TestClient, payment_api_setup):
    """Verifies rejection of unsupported file types, empty files, and >10MB files."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "1000.00")

    # 1. Plain text file -> 400
    r_txt = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("note.txt", b"plain text content not allowed", "text/plain")},
    )
    assert r_txt.status_code == 400
    assert "Unsupported file format" in r_txt.json()["detail"]

    # 2. Empty file (0 bytes) -> 400
    r_empty = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert r_empty.status_code == 400
    assert "empty" in r_empty.json()["detail"].lower()

    # 3. Oversized file (>10MB) -> 400
    oversized_data = VALID_PDF_BYTES + b"0" * (10 * 1024 * 1024 - len(VALID_PDF_BYTES) + 1)
    r_large = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("large.pdf", oversized_data, "application/pdf")},
    )
    assert r_large.status_code == 400
    assert "exceeds the maximum limit" in r_large.json()["detail"].lower()

    # 4. Spoofed PDF (content-type application/pdf but invalid magic bytes) -> 400
    r_spoof = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("spoofed.pdf", b"<html>Fake PDF content</html>", "application/pdf")},
    )
    assert r_spoof.status_code == 400
    assert "Unsupported file format" in r_spoof.json()["detail"]

    # 5. Path traversal in filename is sanitized safely
    r_trav = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("../../etc/passwd.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert r_trav.status_code == 200


def test_receipt_api_voided_payment_rejection(client: TestClient, payment_api_setup):
    """Verifies that attaching or replacing a receipt on a voided payment is rejected with 422."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]

    pid = _create_test_payment(client, tokens, str(inv.id), "2000.00")

    # Void the payment
    res_void = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": f"void_rcpt_{sfx}",
            "void_reason": "Voiding payment to test receipt rejection",
        },
    )
    assert res_void.status_code == 200

    # Attempt to attach receipt to voided payment -> 422
    r_attach = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("receipt.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert r_attach.status_code == 422
    assert "voided" in r_attach.json()["detail"].lower()


def test_receipt_api_replacement_behavior(client: TestClient, payment_api_setup):
    """Verifies safely replacing an existing receipt: new file served, old file unlinked."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "4000.00")

    # 1. Upload initial PDF receipt
    r1 = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("original.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert r1.status_code == 200

    # Verify download returns PDF
    dl1 = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["director"]))
    assert dl1.status_code == 200
    assert dl1.content == VALID_PDF_BYTES

    # 2. Replace with PNG receipt
    r2 = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("replacement.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r2.status_code == 200

    # Verify download now returns replacement PNG
    dl2 = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["director"]))
    assert dl2.status_code == 200
    assert dl2.content == VALID_PNG_BYTES
    assert "image/png" in dl2.headers["content-type"]


def test_receipt_api_retained_on_void(client: TestClient, payment_api_setup):
    """Verifies that when a payment with a receipt is voided, the receipt is retained for audit integrity."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    sfx = str(uuid.uuid4())[:8]
    pid = _create_test_payment(client, tokens, str(inv.id), "3500.00")

    # 1. Upload receipt
    r_up = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("receipt.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert r_up.status_code == 200

    # 2. Void the payment
    res_void = client.post(
        f"/api/v1/client-payments/{pid}/void",
        headers=_auth(tokens["director"]),
        json={
            "void_idempotency_key": f"void_retain_{sfx}",
            "void_reason": "Audit verification: retain receipt test",
        },
    )
    assert res_void.status_code == 200
    # Payment receipt_url is retained in DB
    assert res_void.json()["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"

    # 3. Download receipt on voided payment succeeds (200 OK)
    dl = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["director"]))
    assert dl.status_code == 200
    assert dl.content == VALID_PDF_BYTES


def test_receipt_api_missing_receipt_returns_404(client: TestClient, payment_api_setup):
    """Verifies that requesting a receipt for a payment with no receipt returns 404."""
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "1500.00")

    # Payment has no receipt attached
    resp = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["director"]))
    assert resp.status_code == 404
    assert "no receipt" in resp.json()["detail"].lower()

    # Non-existent payment returns 404
    fake_pid = str(uuid.uuid4())
    resp_fake = client.get(f"/api/v1/client-payments/{fake_pid}/receipt", headers=_auth(tokens["director"]))
    assert resp_fake.status_code == 404


def test_receipt_api_s3_storage_response(client: TestClient, payment_api_setup, monkeypatch):
    """Verifies that when S3 storage returns file_bytes, the GET receipt endpoint correctly serves it."""
    from app.shared.file_storage import ReceiptFileResult
    from unittest.mock import AsyncMock

    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "5000.00")

    # Upload initial receipt
    client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("cheque.pdf", VALID_PDF_BYTES, "application/pdf")},
    )

    # Mock storage to return S3-style bytes
    mock_s3_result = ReceiptFileResult(
        file_bytes=VALID_PDF_BYTES,
        media_type="application/pdf",
        filename="cheque.pdf",
    )
    mock_storage = AsyncMock()
    mock_storage.get_receipt.return_value = mock_s3_result
    monkeypatch.setattr("app.modules.client_payments.service.get_file_storage", lambda: mock_storage)

    resp = client.get(f"/api/v1/client-payments/{pid}/receipt", headers=_auth(tokens["director"]))
    assert resp.status_code == 200
    assert resp.content == VALID_PDF_BYTES
    assert "application/pdf" in resp.headers["content-type"]
    assert 'filename="cheque.pdf"' in resp.headers.get("content-disposition", "")


def test_direct_uploads_receipts_route_returns_404(client: TestClient, payment_api_setup):
    """
    Verifies that receipt files cannot be accessed via the public static /uploads mount,
    ensuring receipts remain private and only accessible through authenticated endpoints.
    """
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "3500.00")

    # Upload receipt via authorized API
    res = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("confidential.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 200

    # Attempt to bypass auth by querying public static mount /uploads
    resp_static_file = client.get(f"/uploads/receipts/{pid}/confidential.pdf")
    assert resp_static_file.status_code == 404

    resp_static_dir = client.get(f"/uploads/receipts/{pid}/")
    assert resp_static_dir.status_code == 404

    resp_static_root = client.get("/uploads/receipts/")
    assert resp_static_root.status_code == 404


@pytest.mark.asyncio
async def test_receipt_api_audit_logs_created_on_upload_and_replacement(client: TestClient, payment_api_setup):
    """
    Verifies that receipt uploads and replacements via the API generate audit_logs rows.
    """
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    director = payment_api_setup["users"]["director"]
    pid = _create_test_payment(client, tokens, str(inv.id), "2800.00")
    pid_uuid = uuid.UUID(pid)

    # 1. Upload initial receipt
    r1 = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("slip1.pdf", VALID_PDF_BYTES, "application/pdf")},
    )
    assert r1.status_code == 200

    async with TestingSessionLocal() as session:
        logs_1 = (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid_uuid)
                .order_by(AuditLog.created_at.asc())
            )
        ).scalars().all()
        assert len(logs_1) == 1
        assert logs_1[0].action == "receipt_upload"
        assert logs_1[0].changed_by == director.id
        assert logs_1[0].previous_values is None
        assert logs_1[0].new_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert logs_1[0].new_values["storage_ref"].startswith(f"receipts/{pid}/")

    # 2. Replace receipt
    r2 = client.post(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
        files={"file": ("slip2.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r2.status_code == 200
    assert r2.json()["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
    assert r2.json()["receipt_storage_ref"].startswith(f"receipts/{pid}/")

    async with TestingSessionLocal() as session:
        logs_2 = (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.entity_type == "client_payment", AuditLog.entity_id == pid_uuid)
                .order_by(AuditLog.created_at.asc())
            )
        ).scalars().all()
        assert len(logs_2) == 2
        assert logs_2[1].action == "receipt_replacement"
        assert logs_2[1].changed_by == director.id
        assert logs_2[1].previous_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert logs_2[1].new_values["receipt_url"] == f"/api/v1/client-payments/{pid}/receipt"
        assert logs_2[1].previous_values["storage_ref"] == logs_1[0].new_values["storage_ref"]
        assert logs_2[1].new_values["storage_ref"].startswith(f"receipts/{pid}/")
        assert logs_2[1].new_values["storage_ref"] != logs_2[1].previous_values["storage_ref"]


@pytest.mark.asyncio
async def test_receipt_api_legacy_ambiguity_and_not_found(client: TestClient, payment_api_setup, isolate_receipts_storage):
    """
    Verifies API responses for legacy receipt reference fallback:
    - 0 files -> 404 Not Found
    - 1 file -> 200 OK
    - Multiple files with legacy /api/ reference -> 409 Conflict with clear reconciliation requirement
    - Multiple files with exact reference -> 200 OK
    """
    tokens = payment_api_setup["tokens"]
    inv = payment_api_setup["invoice"]
    pid = _create_test_payment(client, tokens, str(inv.id), "1200.00")
    pid_uuid = uuid.UUID(pid)

    # Point payment record to legacy /api/ URL in DB
    async with TestingSessionLocal() as session:
        payment = await session.get(ClientPayment, pid_uuid)
        payment.receipt_url = f"/api/v1/client-payments/{pid}/receipt"
        await session.commit()

    # 1. Zero files in storage -> 404
    r_empty = client.get(
        f"/api/v1/client-payments/{pid}/receipt",
        headers=_auth(tokens["director"]),
    )
    assert r_empty.status_code == 404
    assert r_empty.json()["detail"] == "Receipt file not found in storage."

    # 2. Exactly 1 file in storage -> 200 OK
    storage = isolate_receipts_storage
    p_dir = storage._get_receipt_dir(pid_uuid)
    p_dir.mkdir(parents=True, exist_ok=True)
    file1 = p_dir / "10101010_legacy_slip.pdf"
    file1.write_bytes(VALID_PDF_BYTES)
    file2 = None

    try:
        r_single = client.get(
            f"/api/v1/client-payments/{pid}/receipt",
            headers=_auth(tokens["director"]),
        )
        assert r_single.status_code == 200
        assert r_single.content == VALID_PDF_BYTES

        # 3. Add second file -> 409 Conflict under legacy reference
        file2 = p_dir / "20202020_legacy_slip2.png"
        file2.write_bytes(VALID_PNG_BYTES)

        r_ambiguous = client.get(
            f"/api/v1/client-payments/{pid}/receipt",
            headers=_auth(tokens["director"]),
        )
        assert r_ambiguous.status_code == 409
        assert "Receipt reference is ambiguous" in r_ambiguous.json()["detail"]
        assert "Manual reconciliation is required" in r_ambiguous.json()["detail"]

        # 4. Update DB to exact canonical reference -> 200 OK despite multiple files
        async with TestingSessionLocal() as session:
            payment = await session.get(ClientPayment, pid_uuid)
            payment.receipt_url = f"receipts/{pid}/{file1.name}"
            await session.commit()

        r_exact = client.get(
            f"/api/v1/client-payments/{pid}/receipt",
            headers=_auth(tokens["director"]),
        )
        assert r_exact.status_code == 200
        assert r_exact.content == VALID_PDF_BYTES
    finally:
        # Clean up files created in test storage
        if file1.exists():
            file1.unlink()
        if file2 and file2.exists():
            file2.unlink()



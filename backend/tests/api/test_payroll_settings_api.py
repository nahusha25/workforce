from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.auth import User
from app.models.payroll_settings import PayrollOvertimeSettings
from app.models.system import AuditLog
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def payroll_settings_setup():
    async with TestingSessionLocal() as session:
        # Clear settings and audit logs for test isolation
        await session.execute(delete(AuditLog).where(AuditLog.entity_type == "payroll_overtime_settings"))
        await session.execute(delete(PayrollOvertimeSettings))
        await session.commit()

        sfx = str(_u())[:8]

        u_admin = User(id=_u(), mobile_id=f"+9198{sfx[:6]}1", role="administrator")
        u_dir = User(id=_u(), mobile_id=f"+9198{sfx[:6]}2", role="director")
        u_sup = User(id=_u(), mobile_id=f"+9198{sfx[:6]}3", role="supervisor")
        u_emp = User(id=_u(), mobile_id=f"+9198{sfx[:6]}4", role="employee")

        session.add_all([u_admin, u_dir, u_sup, u_emp])
        await session.flush()

        # Seed initial setting effective 2026-01-01 (7.00h, 1.50x)
        initial_setting = PayrollOvertimeSettings(
            id=_u(),
            standard_workday_hours=Decimal("7.00"),
            overtime_multiplier=Decimal("1.50"),
            effective_from=date(2026, 1, 1),
            effective_to=None,
            description=f"Initial seed {sfx}",
            created_by=u_admin.id,
        )
        session.add(initial_setting)
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
            "initial_setting": initial_setting,
            "sfx": sfx,
        }


# ---------------------------------------------------------------------------
# 1. RBAC Permissions
# ---------------------------------------------------------------------------

def test_overtime_settings_rbac_history(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]

    # 1. Unauthenticated -> 401
    resp = client.get("/api/v1/payroll-settings/overtime")
    assert resp.status_code == 401

    # 2. Employee -> 403
    resp = client.get("/api/v1/payroll-settings/overtime", headers=_auth(tokens["employee"]))
    assert resp.status_code == 403

    # 3. Supervisor -> 403
    resp = client.get("/api/v1/payroll-settings/overtime", headers=_auth(tokens["supervisor"]))
    assert resp.status_code == 403

    # 4. Director -> 200
    resp = client.get("/api/v1/payroll-settings/overtime", headers=_auth(tokens["director"]))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 5. Administrator -> 200
    resp = client.get("/api/v1/payroll-settings/overtime", headers=_auth(tokens["admin"]))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_overtime_settings_rbac_create(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]
    payload = {
        "standard_workday_hours": 8.0,
        "overtime_multiplier": 1.5,
        "effective_from": "2026-11-01",
        "description": "November policy",
    }

    # 1. Unauthenticated -> 401
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload)
    assert resp.status_code == 401

    # 2. Employee -> 403
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["employee"]))
    assert resp.status_code == 403

    # 3. Supervisor -> 403
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["supervisor"]))
    assert resp.status_code == 403

    # 4. Director -> 403 (Director cannot write settings)
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["director"]))
    assert resp.status_code == 403

    # 5. Administrator -> 201 Created
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["standard_workday_hours"] == "8.00"
    assert data["overtime_multiplier"] == "1.50"
    assert data["effective_from"] == "2026-11-01"
    assert data["effective_to"] is None


# ---------------------------------------------------------------------------
# 2. Effective-Date Integrity & Timeline Closing
# ---------------------------------------------------------------------------

def test_effective_date_closing_and_timeline_continuity(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]
    initial = payroll_settings_setup["initial_setting"]

    # Post a new forward-dated setting effective 2026-11-01
    payload = {
        "standard_workday_hours": 7.5,
        "overtime_multiplier": 2.0,
        "effective_from": "2026-11-01",
        "description": "Winter revision",
    }
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))
    assert resp.status_code == 201
    new_data = resp.json()
    assert new_data["effective_from"] == "2026-11-01"
    assert new_data["effective_to"] is None

    # Retrieve history
    resp_hist = client.get("/api/v1/payroll-settings/overtime", headers=_auth(tokens["director"]))
    assert resp_hist.status_code == 200
    history = resp_hist.json()
    assert len(history) >= 2

    # Check that previous open setting closed exactly on 2026-10-31
    prev_setting = next(s for s in history if s["id"] == str(initial.id))
    assert prev_setting["effective_from"] == "2026-01-01"
    assert prev_setting["effective_to"] == "2026-10-31"
    assert prev_setting["standard_workday_hours"] == "7.00"
    assert prev_setting["overtime_multiplier"] == "1.50"

    # Test effective date queries
    # 1. Date during initial period (e.g. 2026-06-15) -> returns initial setting
    r1 = client.get("/api/v1/payroll-settings/overtime/effective?date=2026-06-15", headers=_auth(tokens["director"]))
    assert r1.status_code == 200
    assert r1.json()["id"] == str(initial.id)
    assert r1.json()["standard_workday_hours"] == "7.00"

    # 2. Exactly on closing boundary (2026-10-31) -> returns initial setting
    r2 = client.get("/api/v1/payroll-settings/overtime/effective?date=2026-10-31", headers=_auth(tokens["director"]))
    assert r2.status_code == 200
    assert r2.json()["id"] == str(initial.id)

    # 3. Exactly on new start boundary (2026-11-01) -> returns new setting
    r3 = client.get("/api/v1/payroll-settings/overtime/effective?date=2026-11-01", headers=_auth(tokens["director"]))
    assert r3.status_code == 200
    assert r3.json()["id"] == new_data["id"]
    assert r3.json()["standard_workday_hours"] == "7.50"

    # 4. Far future date (2027-02-01) -> returns new setting (open-ended)
    r4 = client.get("/api/v1/payroll-settings/overtime/effective?date=2027-02-01", headers=_auth(tokens["director"]))
    assert r4.status_code == 200
    assert r4.json()["id"] == new_data["id"]

    # 5. Pre-historical date (2025-12-31) -> returns 404
    r5 = client.get("/api/v1/payroll-settings/overtime/effective?date=2025-12-31", headers=_auth(tokens["director"]))
    assert r5.status_code == 404


# ---------------------------------------------------------------------------
# 3. Validation & Conflict Rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_hours", [0, -1, 24.1, 30])
def test_create_overtime_settings_invalid_hours(client: TestClient, payroll_settings_setup, invalid_hours):
    tokens = payroll_settings_setup["tokens"]
    payload = {
        "standard_workday_hours": invalid_hours,
        "overtime_multiplier": 1.5,
        "effective_from": "2026-12-01",
    }
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))
    assert resp.status_code == 422


@pytest.mark.parametrize("invalid_multiplier", [0.5, 0.99, 5.01, 10.0])
def test_create_overtime_settings_invalid_multiplier(client: TestClient, payroll_settings_setup, invalid_multiplier):
    tokens = payroll_settings_setup["tokens"]
    payload = {
        "standard_workday_hours": 7.0,
        "overtime_multiplier": invalid_multiplier,
        "effective_from": "2026-12-01",
    }
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))
    assert resp.status_code == 422


def test_reject_duplicate_and_backdated_effective_dates(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]

    # 1. Backdated prior to 2026-01-01
    resp = client.post(
        "/api/v1/payroll-settings/overtime",
        json={"standard_workday_hours": 8.0, "overtime_multiplier": 1.5, "effective_from": "2025-12-01"},
        headers=_auth(tokens["admin"]),
    )
    assert resp.status_code == 400
    assert "strictly after" in resp.json()["detail"]

    # 2. Duplicate exact date as active setting (2026-01-01)
    resp = client.post(
        "/api/v1/payroll-settings/overtime",
        json={"standard_workday_hours": 8.0, "overtime_multiplier": 1.5, "effective_from": "2026-01-01"},
        headers=_auth(tokens["admin"]),
    )
    assert resp.status_code == 400
    assert "strictly after" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Central AuditLog & Rollback Atomicity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_created_atomically(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]
    admin = payroll_settings_setup["users"]["admin"]

    payload = {
        "standard_workday_hours": 6.5,
        "overtime_multiplier": 1.8,
        "effective_from": "2026-12-01",
        "description": "December Audit Test",
    }
    resp = client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))
    assert resp.status_code == 201
    new_id = uuid.UUID(resp.json()["id"])

    # Query AuditLog directly from database
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == "payroll_overtime_settings",
                AuditLog.entity_id == new_id,
            )
        )
        res = await session.execute(stmt)
        logs = res.scalars().all()

        assert len(logs) == 1
        audit = logs[0]
        assert audit.action == "create_overtime_setting"
        assert audit.changed_by == admin.id
        assert audit.new_values["standard_workday_hours"] == "6.50"
        assert audit.new_values["overtime_multiplier"] == "1.80"
        assert audit.previous_values is not None
        assert audit.previous_values["effective_to"] == "2026-11-30"


@pytest.mark.asyncio
async def test_database_rollback_if_audit_fails(client: TestClient, payroll_settings_setup):
    tokens = payroll_settings_setup["tokens"]
    initial = payroll_settings_setup["initial_setting"]

    payload = {
        "standard_workday_hours": 8.0,
        "overtime_multiplier": 1.5,
        "effective_from": "2027-01-01",
        "description": "Simulated Audit Failure",
    }

    # Simulate an unhandled database error during audit logging by patching AuditLog instantiation
    with patch("app.modules.payroll_settings.service.AuditLog", side_effect=RuntimeError("Simulated Audit Storage Failure")):
        with pytest.raises(RuntimeError, match="Simulated Audit Storage Failure"):
            client.post("/api/v1/payroll-settings/overtime", json=payload, headers=_auth(tokens["admin"]))

    # Verify atomic rollback: the previous setting was NOT closed, and new setting was NOT created
    async with TestingSessionLocal() as session:
        stmt_prev = select(PayrollOvertimeSettings).where(PayrollOvertimeSettings.id == initial.id)
        prev_res = (await session.execute(stmt_prev)).scalar_one()
        assert prev_res.effective_to is None  # still open-ended!

        stmt_new = select(PayrollOvertimeSettings).where(PayrollOvertimeSettings.effective_from == date(2027, 1, 1))
        new_res = (await session.execute(stmt_new)).scalar_one_or_none()
        assert new_res is None  # rolled back completely!

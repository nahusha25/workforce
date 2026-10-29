import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_otp_hash, get_token_hash
from app.models.auth import OtpToken, RefreshToken, User


@pytest.fixture
def test_user(sync_db_session: Session):
    mobile_num = f"+123{str(uuid.uuid4().int)[:7]}"
    user = User(
        id=uuid.uuid4(),
        mobile_id=mobile_num,
        role="employee",
        is_active=True
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    sync_db_session.refresh(user)
    return user

def test_otp_request(client: TestClient, test_user: User):
    response = client.post("/api/v1/auth/otp/request", json={"mobile": test_user.mobile_id})
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent successfully"

def test_otp_request_user_not_found(client: TestClient):
    response = client.post("/api/v1/auth/otp/request", json={"mobile": "+9999999999"})
    assert response.status_code == 200

def test_otp_verify_success(client: TestClient, test_user: User, sync_db_session: Session):
    otp_plain = "123456"
    otp_token = OtpToken(
        user_id=test_user.id,
        otp_hash=get_otp_hash(otp_plain),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False
    )
    sync_db_session.add(otp_token)
    sync_db_session.commit()

    response = client.post("/api/v1/auth/otp/verify", json={"mobile": test_user.mobile_id, "otp": otp_plain})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies

def test_otp_verify_invalid(client: TestClient, test_user: User, sync_db_session: Session):
    otp_token = OtpToken(
        user_id=test_user.id,
        otp_hash=get_otp_hash("123456"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False
    )
    sync_db_session.add(otp_token)
    sync_db_session.commit()

    response = client.post("/api/v1/auth/otp/verify", json={"mobile": test_user.mobile_id, "otp": "999999"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"

def test_otp_verify_expired(client: TestClient, test_user: User, sync_db_session: Session):
    otp_token = OtpToken(
        user_id=test_user.id,
        otp_hash=get_otp_hash("123456"),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        attempts=0,
        is_used=False
    )
    sync_db_session.add(otp_token)
    sync_db_session.commit()

    response = client.post("/api/v1/auth/otp/verify", json={"mobile": test_user.mobile_id, "otp": "123456"})
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()

def test_refresh_token_success(client: TestClient, test_user: User, sync_db_session: Session):
    rt = RefreshToken(
        user_id=test_user.id,
        token_hash=get_token_hash("valid_refresh_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False
    )
    sync_db_session.add(rt)
    sync_db_session.commit()

    client.cookies.set("refresh_token", "valid_refresh_token")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.cookies.get("refresh_token") != "valid_refresh_token"

def test_unauthenticated_requests(client: TestClient):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


def test_inactive_user_otp_request_rejected(client: TestClient, sync_db_session: Session):
    inactive_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+144{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=False,
    )
    sync_db_session.add(inactive_user)
    sync_db_session.commit()

    response = client.post("/api/v1/auth/otp/request", json={"mobile": inactive_user.mobile_id})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"
    assert "deactivated" in response.json()["error"]["message"].lower()


def test_inactive_user_otp_verify_rejected(client: TestClient, sync_db_session: Session):
    inactive_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+144{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=False,
    )
    sync_db_session.add(inactive_user)
    sync_db_session.commit()

    otp_plain = "654321"
    otp_token = OtpToken(
        user_id=inactive_user.id,
        otp_hash=get_otp_hash(otp_plain),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False,
    )
    sync_db_session.add(otp_token)
    sync_db_session.commit()

    response = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile": inactive_user.mobile_id, "otp": otp_plain},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"
    assert "deactivated" in response.json()["error"]["message"].lower()


def test_inactive_user_refresh_token_rejected(client: TestClient, sync_db_session: Session):
    inactive_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+144{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=False,
    )
    sync_db_session.add(inactive_user)
    sync_db_session.commit()

    rt = RefreshToken(
        user_id=inactive_user.id,
        token_hash=get_token_hash("inactive_refresh_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    sync_db_session.add(rt)
    sync_db_session.commit()

    client.cookies.set("refresh_token", "inactive_refresh_token")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ERROR"
    assert "deactivated" in response.json()["error"]["message"].lower()


def test_inactive_user_authenticated_endpoint_rejected(client: TestClient, sync_db_session: Session):
    from app.core.security import create_access_token

    inactive_user = User(
        id=uuid.uuid4(),
        mobile_id=f"+144{str(uuid.uuid4().int)[:7]}",
        role="employee",
        is_active=False,
    )
    sync_db_session.add(inactive_user)
    sync_db_session.commit()

    token = create_access_token(subject=inactive_user.id, role=inactive_user.role)
    response = client.get("/api/v1/employees/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "deactivated" in response.json()["detail"].lower()

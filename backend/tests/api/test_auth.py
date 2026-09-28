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

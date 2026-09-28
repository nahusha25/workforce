import uuid

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.core.security import create_access_token
from app.main import app
from app.models.auth import User


# Mount test routes to test dependencies
@app.get("/api/v1/test/rbac/employee")
async def mock_rbac_employee(user: User = Depends(require_role(["employee"]))):
    return {"status": "ok", "role": user.role}

@app.get("/api/v1/test/rbac/admin")
async def mock_rbac_admin(user: User = Depends(require_role(["administrator"]))):
    return {"status": "ok", "role": user.role}

@app.get("/api/v1/test/rbac/multiple")
async def mock_rbac_multiple(user: User = Depends(require_role(["administrator", "director"]))):
    return {"status": "ok", "role": user.role}

@pytest.fixture
def create_test_user(sync_db_session: Session):
    def _create(role: str, is_active: bool = True) -> User:
        user = User(
            id=uuid.uuid4(),
            mobile_id=f"+123{str(uuid.uuid4().int)[:7]}",
            role=role,
            is_active=is_active
        )
        sync_db_session.add(user)
        sync_db_session.commit()
        sync_db_session.refresh(user)
        return user
    return _create

def test_no_auth(client: TestClient):
    response = client.get("/api/v1/test/rbac/employee")
    assert response.status_code == 401

def test_invalid_auth(client: TestClient):
    response = client.get(
        "/api/v1/test/rbac/employee",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_expired_auth(client: TestClient, create_test_user):
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import settings
    
    user = create_test_user("employee")
    expire = datetime.now(timezone.utc) - timedelta(minutes=10)
    to_encode = {"exp": expire, "sub": str(user.id), "role": user.role}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    response = client.get(
        "/api/v1/test/rbac/employee",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

def test_correct_role(client: TestClient, create_test_user):
    user = create_test_user("employee")
    token = create_access_token(str(user.id), user.role)
    response = client.get(
        "/api/v1/test/rbac/employee",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "employee"

def test_incorrect_role(client: TestClient, create_test_user):
    user = create_test_user("employee")
    token = create_access_token(str(user.id), user.role)
    response = client.get(
        "/api/v1/test/rbac/admin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_multiple_allowed_roles_success(client: TestClient, create_test_user):
    # Test for director
    user_director = create_test_user("director")
    token_director = create_access_token(str(user_director.id), user_director.role)
    response_dir = client.get(
        "/api/v1/test/rbac/multiple",
        headers={"Authorization": f"Bearer {token_director}"}
    )
    assert response_dir.status_code == 200
    
    # Test for administrator
    user_admin = create_test_user("administrator")
    token_admin = create_access_token(str(user_admin.id), user_admin.role)
    response_admin = client.get(
        "/api/v1/test/rbac/multiple",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response_admin.status_code == 200

def test_multiple_allowed_roles_failure(client: TestClient, create_test_user):
    user = create_test_user("supervisor")
    token = create_access_token(str(user.id), user.role)
    response = client.get(
        "/api/v1/test/rbac/multiple",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_inactive_user(client: TestClient, create_test_user):
    user = create_test_user("employee", is_active=False)
    token = create_access_token(str(user.id), user.role)
    response = client.get(
        "/api/v1/test/rbac/employee",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

def test_role_spoofing_in_jwt(client: TestClient, create_test_user):
    user = create_test_user("employee")
    # Force the JWT to say administrator, but the DB says employee
    token = create_access_token(str(user.id), "administrator")
    
    # It should still fail for an admin route because the DB role is used
    response = client.get(
        "/api/v1/test/rbac/admin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_nonexistent_user(client: TestClient):
    token = create_access_token(str(uuid.uuid4()), "administrator")
    response = client.get(
        "/api/v1/test/rbac/admin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

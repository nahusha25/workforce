import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User, OtpToken, RefreshToken
from app.models.workforce import Role, Employee, EmployeeRole, EmployeeRateHistory
from app.models.operations import Client, Project, Site, EmployeeSiteAssignment
from app.models.system import AuditLog

# 1. Uniqueness Constraints Tests

def test_users_unique_mobile_id(sync_db_session: Session):
    u1 = User(id=uuid.uuid4(), mobile_id="+919999900001", role="employee")
    sync_db_session.add(u1)
    sync_db_session.commit()

    u2 = User(id=uuid.uuid4(), mobile_id="+919999900001", role="employee")
    sync_db_session.add(u2)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_employees_unique_constraints(sync_db_session: Session):
    u1 = User(id=uuid.uuid4(), mobile_id="+919999900002", role="employee")
    u2 = User(id=uuid.uuid4(), mobile_id="+919999900003", role="employee")
    sync_db_session.add_all([u1, u2])
    sync_db_session.commit()

    e1 = Employee(
        id=uuid.uuid4(),
        user_id=u1.id,
        employee_code="EMP-SYS-001",
        mobile_id="+919999900002",
        name="Employee 1",
    )
    sync_db_session.add(e1)
    sync_db_session.commit()

    # Duplicate employee_code
    e2 = Employee(
        id=uuid.uuid4(),
        user_id=u2.id,
        employee_code="EMP-SYS-001",
        mobile_id="+919999900003",
        name="Employee 2",
    )
    sync_db_session.add(e2)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Duplicate mobile_id
    e3 = Employee(
        id=uuid.uuid4(),
        user_id=u2.id,
        employee_code="EMP-SYS-002",
        mobile_id="+919999900002",
        name="Employee 3",
    )
    sync_db_session.add(e3)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Duplicate user_id
    e4 = Employee(
        id=uuid.uuid4(),
        user_id=u1.id,
        employee_code="EMP-SYS-003",
        mobile_id="+919999900004",
        name="Employee 4",
    )
    sync_db_session.add(e4)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_roles_unique_name(sync_db_session: Session):
    r1 = Role(id=uuid.uuid4(), name="Electrician-Test")
    sync_db_session.add(r1)
    sync_db_session.commit()

    r2 = Role(id=uuid.uuid4(), name="Electrician-Test")
    sync_db_session.add(r2)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_refresh_tokens_unique_token_hash(sync_db_session: Session):
    u = User(id=uuid.uuid4(), mobile_id="+919999900005", role="employee")
    sync_db_session.add(u)
    sync_db_session.commit()

    t1 = RefreshToken(id=uuid.uuid4(), user_id=u.id, token_hash="hash_abc123", expires_at=datetime.now(timezone.utc))
    sync_db_session.add(t1)
    sync_db_session.commit()

    t2 = RefreshToken(id=uuid.uuid4(), user_id=u.id, token_hash="hash_abc123", expires_at=datetime.now(timezone.utc))
    sync_db_session.add(t2)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

# 2. Foreign Key Integrity Tests

def test_invalid_foreign_keys(sync_db_session: Session):
    fake_id = uuid.uuid4()

    # Invalid user_id in otp_tokens
    otp = OtpToken(id=uuid.uuid4(), user_id=fake_id, otp_hash="123", expires_at=datetime.now(timezone.utc))
    sync_db_session.add(otp)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Invalid client_id in projects
    proj = Project(id=uuid.uuid4(), client_id=fake_id, name="Invalid Proj", status="Active")
    sync_db_session.add(proj)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Invalid project_id in sites
    site = Site(id=uuid.uuid4(), project_id=fake_id, name="Invalid Site")
    sync_db_session.add(site)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

# 3. Defaults and Nullability Tests

def test_defaults_and_nullability(sync_db_session: Session):
    # Test Client defaults
    client = Client(id=uuid.uuid4(), name="Default Test Client")
    sync_db_session.add(client)
    sync_db_session.commit()

    assert client.is_active is True
    assert client.created_at is not None

    # Test Client nullability (name is required)
    invalid_client = Client(id=uuid.uuid4(), name=None) # type: ignore
    sync_db_session.add(invalid_client)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

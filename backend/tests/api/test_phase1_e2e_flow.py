import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_otp_hash, get_token_hash
from app.models.auth import User, OtpToken, RefreshToken
from app.models.workforce import Role, Employee, EmployeeRole, EmployeeRateHistory
from app.models.operations import Client, Project, Site, EmployeeSiteAssignment

def create_authenticated_user(sync_db_session: Session, client: TestClient, role_name: str, mobile: str = None):
    if not mobile:
        mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
    
    user = User(
        id=uuid.uuid4(),
        mobile_id=mobile,
        role=role_name,
        is_active=True
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    sync_db_session.refresh(user)

    emp = Employee(
        id=uuid.uuid4(),
        user_id=user.id,
        employee_code=f"EMP-E2E-{str(uuid.uuid4().int)[:5]}",
        mobile_id=user.mobile_id,
        name=f"E2E {role_name.capitalize()}",
        is_active=True
    )
    sync_db_session.add(emp)
    sync_db_session.commit()
    sync_db_session.refresh(emp)

    otp_plain = "654321"
    otp_token = OtpToken(
        id=uuid.uuid4(),
        user_id=user.id,
        otp_hash=get_otp_hash(otp_plain),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False
    )
    sync_db_session.add(otp_token)
    sync_db_session.commit()

    # Verify OTP to generate real access_token and refresh_token cookie
    res = client.post("/api/v1/auth/otp/verify", json={"mobile": mobile, "otp": otp_plain})
    assert res.status_code == 200
    token_data = res.json()
    access_token = token_data["access_token"]
    refresh_cookie = res.cookies.get("refresh_token")

    return user, access_token, refresh_cookie, mobile

def test_full_phase1_e2e_lifecycle(client: TestClient, sync_db_session: Session):
    # ==========================================
    # STEP 1: AUTHENTICATION LIFECYCLE (ADMIN)
    # ==========================================
    admin_mobile = "+919876500001"
    
    # 1a. Request OTP
    req_res = client.post("/api/v1/auth/otp/request", json={"mobile": admin_mobile})
    assert req_res.status_code == 200

    # 1b. Create Admin user and OTP token for verification
    admin_user, admin_token, admin_rf_cookie, _ = create_authenticated_user(
        sync_db_session, client, role_name="administrator", mobile=admin_mobile
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1c. Get Profile (/employees/me)
    profile_res = client.get("/api/v1/employees/me", headers=headers)
    assert profile_res.status_code == 200
    assert profile_res.json()["system_role"] == "administrator"

    # 1d. Refresh Token
    client.cookies.set("refresh_token", admin_rf_cookie)
    rf_res = client.post("/api/v1/auth/refresh")
    assert rf_res.status_code == 200
    new_admin_token = rf_res.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_admin_token}"}

    # ==========================================
    # STEP 2: MASTER DATA LIFECYCLE (CLIENT -> PROJECT -> SITE)
    # ==========================================
    
    # 2a. Create Client (ADM-001)
    client_res = client.post(
        "/api/v1/admin/clients",
        json={
            "name": "E2E Apex Infra Corp",
            "contact_person": "Vikram Sethi",
            "contact_mobile": "+919876543210",
            "is_active": True
        },
        headers=new_headers
    )
    assert client_res.status_code == 201
    created_client = client_res.json()
    client_id = created_client["id"]

    # List Clients (ADM-002)
    list_clients_res = client.get("/api/v1/admin/clients", headers=new_headers)
    assert list_clients_res.status_code == 200
    assert any(c["id"] == client_id for c in list_clients_res.json())

    # 2b. Create Project (ADM-003)
    proj_res = client.post(
        "/api/v1/admin/projects",
        json={
            "name": "E2E Metro Corridor Line 1",
            "client_id": client_id,
            "status": "Active",
            "start_date": "2026-01-01",
            "end_date": "2027-12-31"
        },
        headers=new_headers
    )
    assert proj_res.status_code == 201
    created_proj = proj_res.json()
    project_id = created_proj["id"]

    # List Projects (ADM-004)
    list_projs_res = client.get("/api/v1/admin/projects", headers=new_headers)
    assert list_projs_res.status_code == 200
    assert any(p["id"] == project_id for p in list_projs_res.json())

    # 2c. Create Site (ADM-005)
    site_res = client.post(
        "/api/v1/admin/sites",
        json={
            "name": "Central Metro Station Site",
            "project_id": project_id,
            "address": "MG Road, Bengaluru",
            "permitted_radius_m": 150.0,
            "is_active": True
        },
        headers=new_headers
    )
    assert site_res.status_code == 201
    created_site = site_res.json()
    site_id = created_site["id"]

    # List Sites (ADM-006)
    list_sites_res = client.get("/api/v1/admin/sites", headers=new_headers)
    assert list_sites_res.status_code == 200
    assert any(s["id"] == site_id for s in list_sites_res.json())

    # 2d. List Read-Only Roles (ADM-007)
    role_obj = Role(id=uuid.uuid4(), name="Carpenter E2E", description="E2E Trade Role")
    sync_db_session.add(role_obj)
    sync_db_session.commit()

    roles_res = client.get("/api/v1/admin/roles", headers=new_headers)
    assert roles_res.status_code == 200
    available_roles = roles_res.json()
    assert len(available_roles) > 0
    trade_role_id = available_roles[0]["id"]

    # ==========================================
    # STEP 3: EMPLOYEE ONBOARDING LIFECYCLE (EMP-001)
    # ==========================================
    
    # 3a. Onboard Supervisor
    sup_mobile = "+919876500002"
    sup_code = "SUP-E2E-001"
    onboard_sup_res = client.post(
        "/api/v1/employees",
        json={
            "name": "Supervisor Sharma",
            "mobile_number": sup_mobile,
            "employee_code": sup_code,
            "system_role": "supervisor",
            "trade_role_ids": [trade_role_id],
            "rate_type": "monthly",
            "rate_amount": 45000.0,
            "site_ids": [site_id]
        },
        headers=new_headers
    )
    assert onboard_sup_res.status_code == 201
    created_sup = onboard_sup_res.json()
    supervisor_emp_id = created_sup["id"]

    # 3b. Onboard Field Employee assigned to Supervisor & Site
    emp_mobile = "+919876500003"
    emp_code = "EMP-E2E-001"
    onboard_emp_res = client.post(
        "/api/v1/employees",
        json={
            "name": "Ramesh Carpenter",
            "mobile_number": emp_mobile,
            "employee_code": emp_code,
            "system_role": "employee",
            "trade_role_ids": [trade_role_id],
            "rate_type": "daily",
            "rate_amount": 750.0,
            "supervisor_id": supervisor_emp_id,
            "site_ids": [site_id]
        },
        headers=new_headers
    )
    assert onboard_emp_res.status_code == 201
    created_emp = onboard_emp_res.json()
    field_emp_id = created_emp["id"]

    # 3c. Database Assertion on Atomic Onboarding
    db_emp = sync_db_session.query(Employee).filter_by(id=uuid.UUID(field_emp_id)).first()
    assert db_emp is not None
    assert db_emp.name == "Ramesh Carpenter"
    
    # Verify EmployeeRoles relationship
    emp_roles = sync_db_session.query(EmployeeRole).filter_by(employee_id=db_emp.id).all()
    assert len(emp_roles) == 1

    # Verify RateHistory relationship
    rate_hist = sync_db_session.query(EmployeeRateHistory).filter_by(employee_id=db_emp.id).all()
    assert len(rate_hist) == 1
    assert float(rate_hist[0].rate_amount) == 750.0

    # Verify SiteAssignments relationship
    site_assigns = sync_db_session.query(EmployeeSiteAssignment).filter_by(employee_id=db_emp.id).all()
    assert len(site_assigns) == 1

    # ==========================================
    # STEP 4: SUPERVISOR AUTHENTICATION & SCOPING
    # ==========================================
    
    # Create OTP for newly onboarded Supervisor user
    sup_user = sync_db_session.query(User).filter_by(mobile_id=sup_mobile).first()
    assert sup_user is not None

    sup_otp_token = OtpToken(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        otp_hash=get_otp_hash("112233"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False
    )
    sync_db_session.add(sup_otp_token)
    sync_db_session.commit()

    # Supervisor verify OTP
    sup_verify_res = client.post("/api/v1/auth/otp/verify", json={"mobile": sup_mobile, "otp": "112233"})
    assert sup_verify_res.status_code == 200
    sup_access_token = sup_verify_res.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_access_token}"}

    # Supervisor profile
    sup_profile = client.get("/api/v1/employees/me", headers=sup_headers)
    assert sup_profile.status_code == 200
    assert sup_profile.json()["system_role"] == "supervisor"

    # Supervisor Employee List Scoping (EMP-002)
    sup_list_res = client.get("/api/v1/employees", headers=sup_headers)
    assert sup_list_res.status_code == 200
    sup_employees = sup_list_res.json()
    assert any(e["id"] == field_emp_id for e in sup_employees)

    # ==========================================
    # STEP 5: RBAC ENFORCEMENT (NON-ADMIN 403)
    # ==========================================
    
    # Supervisor attempting Admin Master Data endpoint -> 403 Forbidden
    forbidden_client_res = client.post(
        "/api/v1/admin/clients",
        json={"name": "Forbidden Client"},
        headers=sup_headers
    )
    assert forbidden_client_res.status_code == 403

    # Supervisor attempting Employee Onboarding -> 403 Forbidden
    forbidden_onboard_res = client.post(
        "/api/v1/employees",
        json={
            "name": "Forbidden Emp",
            "mobile_number": "+919900001122",
            "employee_code": "EMP-FORB-01",
            "system_role": "employee",
            "trade_role_ids": [trade_role_id],
            "rate_type": "daily",
            "rate_amount": 500.0,
            "site_ids": [site_id]
        },
        headers=sup_headers
    )
    assert forbidden_onboard_res.status_code == 403

    # ==========================================
    # STEP 6: AUTH SECURITY & LOGOUT (AUTH-004)
    # ==========================================
    
    # Unauthenticated Request -> 401 Unauthorized
    unauth_res = client.get("/api/v1/employees/me")
    assert unauth_res.status_code == 401

    # Invalid Token -> 401 Unauthorized
    invalid_res = client.get("/api/v1/employees/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert invalid_res.status_code == 401

    # Admin Logout
    client.cookies.set("refresh_token", admin_rf_cookie)
    logout_res = client.post("/api/v1/auth/logout", headers=new_headers)
    assert logout_res.status_code == 200

    # Verify revoked refresh token fails
    revoked_rf_res = client.post("/api/v1/auth/refresh")
    assert revoked_rf_res.status_code == 401

import uuid
import sys
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from tests.conftest import engine_sync_test
from sqlalchemy.orm import sessionmaker
from app.models.auth import User
from app.models.workforce import Employee, Role
from app.models.operations import Client, Project, Site, EmployeeSiteAssignment, AttendanceRecord
from app.core.security import get_otp_hash
from app.models.auth import OtpToken
from datetime import datetime, timedelta, timezone
from app.core.database import Base

# Setup TestClient
client = TestClient(app)

def setup_test_data(db: Session):
    # Setup Supervisor
    sup_user_id = uuid.uuid4()
    sup_user = User(
        id=sup_user_id,
        mobile_id=f"+100{str(sup_user_id.int)[:7]}",
        role="supervisor",
        is_active=True,
    )
    db.add(sup_user)
    db.flush()
    
    otp_sup = OtpToken(
        user_id=sup_user.id,
        otp_hash=get_otp_hash("123456"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        attempts=0,
        is_used=False
    )
    db.add(otp_sup)
    
    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user_id,
        employee_code=f"SUP-{str(sup_user_id.int)[:5]}",
        mobile_id=sup_user.mobile_id,
        name="Swagger Supervisor",
        is_active=True,
    )
    db.add(sup_emp)

    # Setup Employee
    emp_user_id = uuid.uuid4()
    emp_user = User(
        id=emp_user_id,
        mobile_id=f"+200{str(emp_user_id.int)[:7]}",
        role="employee",
        is_active=True,
    )
    db.add(emp_user)
    db.flush()
    
    otp_emp = OtpToken(
        user_id=emp_user.id,
        otp_hash=get_otp_hash("123456"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        attempts=0,
        is_used=False
    )
    db.add(otp_emp)
    
    emp_emp = Employee(
        id=uuid.uuid4(),
        user_id=emp_user_id,
        employee_code=f"EMP-{str(emp_user_id.int)[:5]}",
        mobile_id=emp_user.mobile_id,
        name="Swagger Employee",
        is_active=True,
    )
    db.add(emp_emp)
    db.flush()

    # Setup Site
    role = Role(id=uuid.uuid4(), name=f"Role-{uuid.uuid4().hex[:6]}", description="Worker")
    db.add(role)

    client_obj = Client(id=uuid.uuid4(), name=f"Test Client {uuid.uuid4().hex[:6]}")
    db.add(client_obj)

    project_obj = Project(id=uuid.uuid4(), client_id=client_obj.id, name="Test Project", status="Active")
    db.add(project_obj)

    site_obj = Site(
        id=uuid.uuid4(), 
        project_id=project_obj.id, 
        name="Swagger Test Site", 
        location="POINT(10.0 20.0)", # Longitude=10.0, Latitude=20.0
        permitted_radius_m=100.0
    )
    db.add(site_obj)
    db.flush()
    
    assignment = EmployeeSiteAssignment(
        employee_id=emp_emp.id,
        site_id=site_obj.id,
        is_active=True
    )
    db.add(assignment)

    db.commit()
    return {
        "sup_user": sup_user,
        "sup_emp": sup_emp,
        "emp_user": emp_user,
        "emp_emp": emp_emp,
        "site": site_obj
    }

def run_tests():
    Base.metadata.create_all(engine_sync_test)
    SessionLocal = sessionmaker(bind=engine_sync_test)
    db = SessionLocal()
    try:
        data = setup_test_data(db)
        print("Data setup complete.")

        report = []
        
        # 1. AUTHENTICATION
        # Employee Auth
        res = client.post("/api/v1/auth/otp/verify", json={"mobile": data["emp_user"].mobile_id, "otp": "123456"})
        emp_token = res.json().get("access_token") if res.status_code == 200 else None
        report.append(f"Employee Auth: {'PASS' if res.status_code == 200 and emp_token else 'FAIL'} (Status: {res.status_code})")
        
        # Supervisor Auth
        res = client.post("/api/v1/auth/otp/verify", json={"mobile": data["sup_user"].mobile_id, "otp": "123456"})
        sup_token = res.json().get("access_token") if res.status_code == 200 else None
        report.append(f"Supervisor Auth: {'PASS' if res.status_code == 200 and sup_token else 'FAIL'} (Status: {res.status_code})")

        # Unauthenticated
        res = client.get("/api/v1/attendance")
        report.append(f"Unauthenticated Rejected: {'PASS' if res.status_code in [401, 403] else 'FAIL'} (Status: {res.status_code})")
        
        # Invalid Auth
        res = client.get("/api/v1/attendance", headers={"Authorization": "Bearer invalid_token_123"})
        report.append(f"Invalid Auth Rejected: {'PASS' if res.status_code in [401, 403] else 'FAIL'} (Status: {res.status_code})")

        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        sup_headers = {"Authorization": f"Bearer {sup_token}"}

        # 3. GEO-FENCE (Outside)
        # 11.0, 21.0 is very far from 10.0, 20.0
        res = client.post("/api/v1/attendance/check-in", headers=emp_headers, json={"latitude": 21.0, "longitude": 11.0})
        report.append(f"Geofence Violation Rejected: {'PASS' if res.status_code == 422 else 'FAIL'} (Status: {res.status_code})")

        # 2. CHECK-IN (Inside)
        # 20.0001, 10.0001 should be inside 100m
        res = client.post("/api/v1/attendance/check-in", headers=emp_headers, json={"latitude": 20.0001, "longitude": 10.0001})
        record_id = res.json().get("record_id") if res.status_code == 201 else None
        report.append(f"Valid Check-In: {'PASS' if res.status_code == 201 else 'FAIL'} (Status: {res.status_code})")
        
        # 7. BUSINESS-RULE ERRORS (Duplicate Check-in)
        res = client.post("/api/v1/attendance/check-in", headers=emp_headers, json={"latitude": 20.0001, "longitude": 10.0001})
        report.append(f"Duplicate Check-In Rejected: {'PASS' if res.status_code == 409 else 'FAIL'} (Status: {res.status_code})")

        # 4. CHECK-OUT
        res = client.post("/api/v1/attendance/check-out", headers=emp_headers, json={"latitude": 20.0001, "longitude": 10.0001})
        report.append(f"Valid Check-Out: {'PASS' if res.status_code == 200 else 'FAIL'} (Status: {res.status_code})")

        # Duplicate Check-out
        res = client.post("/api/v1/attendance/check-out", headers=emp_headers, json={"latitude": 20.0001, "longitude": 10.0001})
        report.append(f"Duplicate Check-Out Rejected: {'PASS' if res.status_code == 409 else 'FAIL'} (Status: {res.status_code})")

        # 5. ATTENDANCE RETRIEVAL
        res = client.get("/api/v1/attendance", headers=emp_headers)
        list_passed = res.status_code == 200 and res.json()["total"] > 0
        report.append(f"List Attendance Self-Scoping: {'PASS' if list_passed else 'FAIL'} (Status: {res.status_code})")

        # Employee cannot retrieve another employee
        res = client.get(f"/api/v1/attendance?employee_id={data['sup_emp'].id}", headers=emp_headers)
        report.append(f"Employee Forbidden from Other Records: {'PASS' if res.status_code == 403 else 'FAIL'} (Status: {res.status_code})")

        # Supervisor can list any
        res = client.get(f"/api/v1/attendance?employee_id={data['emp_emp'].id}", headers=sup_headers)
        report.append(f"Supervisor List Attendance: {'PASS' if res.status_code == 200 else 'FAIL'} (Status: {res.status_code})")

        # Get individual
        res = client.get(f"/api/v1/attendance/{record_id}", headers=emp_headers)
        report.append(f"Get Attendance Record: {'PASS' if res.status_code == 200 else 'FAIL'} (Status: {res.status_code})")

        # Get invalid ID
        res = client.get(f"/api/v1/attendance/{uuid.uuid4()}", headers=emp_headers)
        report.append(f"Get Invalid Record Not Found: {'PASS' if res.status_code == 404 else 'FAIL'} (Status: {res.status_code})")

        # 6. SUPERVISOR OVERRIDE
        # Employee attempts override
        res = client.post(f"/api/v1/attendance/{record_id}/override", headers=emp_headers, json={"reason": "Valid GPS drift"})
        report.append(f"Employee Override Forbidden: {'PASS' if res.status_code == 403 else 'FAIL'} (Status: {res.status_code})")

        # Supervisor attempts override
        res = client.post(f"/api/v1/attendance/{record_id}/override", headers=sup_headers, json={"reason": "Valid GPS drift exception override testing."})
        report.append(f"Supervisor Override: {'PASS' if res.status_code == 200 else 'FAIL'} (Status: {res.status_code})")

        # 9. DATABASE VERIFICATION
        db_record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
        db_pass = db_record is not None and db_record.check_out_time is not None
        report.append(f"Database Persistence Verified: {'PASS' if db_pass else 'FAIL'} (Check_out_time exists: {db_pass})")

        print("--- SWG-002 Verification Report ---")
        for r in report:
            print(r)

        # 10. CLEANUP
        db.delete(db_record)
        db.delete(data["sup_emp"])
        db.delete(data["emp_emp"])
        db.delete(data["sup_user"])
        db.delete(data["emp_user"])
        db.commit()
        print("Cleanup complete.")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()

import asyncio
import json
import uuid
import sys
import os

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone, timedelta

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.auth import User
from app.models.workforce import Employee, EmployeeRole, EmployeeRateHistory
from app.models.operations import Activity, AttendanceRecord, Client, EmployeeSiteAssignment, Material, Project, Site, WorkOrder

async def seed_e2e_data():
    async with AsyncSessionLocal() as session:
        # Create Supervisor User & Employee
        sup_user_id = uuid.uuid4()
        sup_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        sup_user = User(id=sup_user_id, mobile_id=sup_mobile, role="supervisor", is_active=True)
        session.add(sup_user)
        
        sup_emp_id = uuid.uuid4()
        sup_emp = Employee(
            id=sup_emp_id, user_id=sup_user_id, employee_code=f"SUP-{str(uuid.uuid4().int)[:5]}",
            mobile_id=sup_mobile, name="E2E Supervisor", is_active=True
        )
        session.add(sup_emp)

        # Create Employee 1
        emp_user_id = uuid.uuid4()
        emp_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        emp_user = User(id=emp_user_id, mobile_id=emp_mobile, role="employee", is_active=True)
        session.add(emp_user)

        emp_emp_id = uuid.uuid4()
        emp_emp = Employee(
            id=emp_emp_id, user_id=emp_user_id, employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
            mobile_id=emp_mobile, name="E2E Worker 1", is_active=True
        )
        session.add(emp_emp)

        # Create Employee 2 (for J04)
        emp2_user_id = uuid.uuid4()
        emp2_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        emp2_user = User(id=emp2_user_id, mobile_id=emp2_mobile, role="employee", is_active=True)
        session.add(emp2_user)

        emp2_emp_id = uuid.uuid4()
        emp2_emp = Employee(
            id=emp2_emp_id, user_id=emp2_user_id, employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
            mobile_id=emp2_mobile, name="E2E Worker 2", is_active=True
        )
        session.add(emp2_emp)

        # Create Employee 3 (for J05)
        emp3_user_id = uuid.uuid4()
        emp3_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        emp3_user = User(id=emp3_user_id, mobile_id=emp3_mobile, role="employee", is_active=True)
        session.add(emp3_user)

        emp3_emp_id = uuid.uuid4()
        emp3_emp = Employee(
            id=emp3_emp_id, user_id=emp3_user_id, employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
            mobile_id=emp3_mobile, name="E2E Worker 3", is_active=True
        )
        session.add(emp3_emp)

        # Create Employee 4 (for Cross-Day Checkout E2E)
        emp4_user_id = uuid.uuid4()
        emp4_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        emp4_user = User(id=emp4_user_id, mobile_id=emp4_mobile, role="employee", is_active=True)
        session.add(emp4_user)

        emp4_emp_id = uuid.uuid4()
        emp4_emp = Employee(
            id=emp4_emp_id, user_id=emp4_user_id, employee_code=f"EMP-{str(uuid.uuid4().int)[:5]}",
            mobile_id=emp4_mobile, name="E2E Worker 4", is_active=True
        )
        session.add(emp4_emp)

        await session.flush()
        
        # Create Client, Project, Site
        client = Client(id=uuid.uuid4(), name="E2E Client")
        session.add(client)
        project = Project(id=uuid.uuid4(), client_id=client.id, name="E2E Project", status="active")
        session.add(project)
        
        site_id = uuid.uuid4()
        site = Site(
            id=site_id,
            project_id=project.id,
            name="E2E Site Gateway",
            location="POINT(72.834654 18.921984)",
            permitted_radius_m=200.0,
            is_active=True
        )
        session.add(site)
        await session.flush()

        # Phase 3 Master Data: Activities, Work Orders, Materials
        act1 = Activity(
            id=uuid.uuid4(),
            name="Cable Pulling",
            unit_of_measure="metres",
            approved_rate=15.0,
            category="cable",
            is_active=True,
        )
        act2 = Activity(
            id=uuid.uuid4(),
            name="Device Installation",
            unit_of_measure="devices",
            approved_rate=50.0,
            category="device",
            is_active=True,
        )
        session.add(act1)
        session.add(act2)

        wo1 = WorkOrder(
            id=uuid.uuid4(),
            order_number=f"WO-E2E-{str(uuid.uuid4().int)[:5]}",
            project_id=project.id,
            site_id=site_id,
            billing_basis="per_metre",
            status="open",
            is_active=True,
        )
        session.add(wo1)

        mat1 = Material(
            id=uuid.uuid4(),
            material_code="MAT-C6",
            name="Cat6 Cable Box",
            unit_of_measure="box",
            category="cable",
            purchase_approval_limit=5000.0,
            is_active=True,
        )
        session.add(mat1)

        # Assign Employees to Site
        assignment1 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=emp_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc)
        )
        session.add(assignment1)

        assignment2 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=emp2_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc)
        )
        session.add(assignment2)

        assignment3 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=emp3_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc)
        )
        session.add(assignment3)

        assignment4 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=emp4_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc)
        )
        session.add(assignment4)

        # Seed unclosed yesterday session for Employee 4
        yesterday_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        att_unclosed = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=emp4_emp_id,
            site_id=site_id,
            date=yesterday_date,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(days=1),
            check_in_location="POINT(72.834654 18.921984)",
            check_out_time=None,
            status="draft",
            is_within_geofence=True,
        )
        session.add(att_unclosed)

        await session.commit()
        
        emp_token = create_access_token(subject=str(emp_user_id), role="employee", employee_id=str(emp_emp_id))
        emp2_token = create_access_token(subject=str(emp2_user_id), role="employee", employee_id=str(emp2_emp_id))
        emp3_token = create_access_token(subject=str(emp3_user_id), role="employee", employee_id=str(emp3_emp_id))
        emp4_token = create_access_token(subject=str(emp4_user_id), role="employee", employee_id=str(emp4_emp_id))
        sup_token = create_access_token(subject=str(sup_user_id), role="supervisor", employee_id=str(sup_emp_id))

        out = {
            "employeeToken": emp_token,
            "employeeId": str(emp_emp_id),
            "employee2Token": emp2_token,
            "employee2Id": str(emp2_emp_id),
            "employee3Token": emp3_token,
            "employee3Id": str(emp3_emp_id),
            "employee4Token": emp4_token,
            "employee4Id": str(emp4_emp_id),
            "supervisorToken": sup_token,
            "supervisorId": str(sup_emp_id),
            "siteId": str(site_id),
            "siteLat": 18.921984,
            "siteLng": 72.834654,
            "outsideLat": 19.0,
            "outsideLng": 73.0,
            "activity1Name": "Cable Pulling",
            "activity2Name": "Device Installation",
            "materialName": "Cat6 Cable Box",
        }
        print(json.dumps(out))

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_e2e_data())

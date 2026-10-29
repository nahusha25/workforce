import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
import sys
import uuid

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Material,
    MaterialTransaction,
    Project,
    Site,
    WorkOrder,
)
from app.models.workforce import Employee


async def seed_e2e_invoices_data():
    async with AsyncSessionLocal() as session:
        today = datetime.now(timezone.utc).date()
        suffix = str(uuid.uuid4().int)[:6]

        # 1. Director User & Employee
        dir_user_id = uuid.uuid4()
        dir_mobile = f"+9199{str(uuid.uuid4().int)[:8]}"
        dir_user = User(id=dir_user_id, mobile_id=dir_mobile, role="director", is_active=True)
        session.add(dir_user)

        dir_emp_id = uuid.uuid4()
        dir_emp = Employee(
            id=dir_emp_id,
            user_id=dir_user_id,
            employee_code=f"DIR-E2E-{suffix}",
            mobile_id=dir_mobile,
            name=f"E2E Director {suffix}",
            is_active=True,
        )
        session.add(dir_emp)

        # 2. Administrator User & Employee
        admin_user_id = uuid.uuid4()
        admin_mobile = f"+9198{str(uuid.uuid4().int)[:8]}"
        admin_user = User(id=admin_user_id, mobile_id=admin_mobile, role="administrator", is_active=True)
        session.add(admin_user)

        admin_emp_id = uuid.uuid4()
        admin_emp = Employee(
            id=admin_emp_id,
            user_id=admin_user_id,
            employee_code=f"ADM-E2E-{suffix}",
            mobile_id=admin_mobile,
            name=f"E2E Admin {suffix}",
            is_active=True,
        )
        session.add(admin_emp)

        # 3. Supervisor User & Employee
        sup_user_id = uuid.uuid4()
        sup_mobile = f"+9197{str(uuid.uuid4().int)[:8]}"
        sup_user = User(id=sup_user_id, mobile_id=sup_mobile, role="supervisor", is_active=True)
        session.add(sup_user)

        sup_emp_id = uuid.uuid4()
        sup_emp = Employee(
            id=sup_emp_id,
            user_id=sup_user_id,
            employee_code=f"SUP-E2E-{suffix}",
            mobile_id=sup_mobile,
            name=f"E2E Supervisor {suffix}",
            is_active=True,
        )
        session.add(sup_emp)

        # 4. Employee User & Employee
        worker_user_id = uuid.uuid4()
        worker_mobile = f"+9196{str(uuid.uuid4().int)[:8]}"
        worker_user = User(id=worker_user_id, mobile_id=worker_mobile, role="employee", is_active=True)
        session.add(worker_user)

        worker_emp_id = uuid.uuid4()
        worker_emp = Employee(
            id=worker_emp_id,
            user_id=worker_user_id,
            employee_code=f"EMP-E2E-{suffix}",
            mobile_id=worker_mobile,
            name=f"E2E Worker {suffix}",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(worker_emp)
        await session.flush()

        # 5. Dataset A: For Issue Workflow (Client A, Project A, Site A)
        client_a = Client(id=uuid.uuid4(), name=f"Metro Client A {suffix}")
        session.add(client_a)
        project_a = Project(id=uuid.uuid4(), client_id=client_a.id, name=f"Metro Line A {suffix}", status="active")
        session.add(project_a)
        site_a = Site(
            id=uuid.uuid4(),
            project_id=project_a.id,
            name=f"Station Site A {suffix}",
            supervisor_id=sup_emp_id,
            permitted_radius_m=200.0,
            location="POINT(72.834654 18.921984)",
            is_active=True,
        )
        session.add(site_a)

        # 6. Dataset B: For Cancel Workflow (Client B, Project B, Site B)
        client_b = Client(id=uuid.uuid4(), name=f"Metro Client B {suffix}")
        session.add(client_b)
        project_b = Project(id=uuid.uuid4(), client_id=client_b.id, name=f"Metro Line B {suffix}", status="active")
        session.add(project_b)
        site_b = Site(
            id=uuid.uuid4(),
            project_id=project_b.id,
            name=f"Station Site B {suffix}",
            supervisor_id=sup_emp_id,
            permitted_radius_m=200.0,
            location="POINT(72.834654 18.921984)",
            is_active=True,
        )
        session.add(site_b)
        await session.flush()

        # Site assignments for worker
        assign_a = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=worker_emp_id,
            site_id=site_a.id,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
        )
        assign_b = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=worker_emp_id,
            site_id=site_b.id,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
        )
        session.add_all([assign_a, assign_b])

        # Activities, Work Orders, Materials
        activity = Activity(
            id=uuid.uuid4(),
            name=f"Fiber Splicing {suffix}",
            unit_of_measure="joint",
            approved_rate=120.0,
            category="cable",
            is_active=True,
        )
        session.add(activity)

        wo_a = WorkOrder(
            id=uuid.uuid4(),
            order_number=f"WO-A-{suffix}",
            project_id=project_a.id,
            site_id=site_a.id,
            billing_basis="per_metre",
            status="open",
            is_active=True,
        )
        wo_b = WorkOrder(
            id=uuid.uuid4(),
            order_number=f"WO-B-{suffix}",
            project_id=project_b.id,
            site_id=site_b.id,
            billing_basis="per_metre",
            status="open",
            is_active=True,
        )
        session.add_all([wo_a, wo_b])

        mat = Material(
            id=uuid.uuid4(),
            material_code=f"MAT-{suffix}",
            name=f"Splice Protector {suffix}",
            unit_of_measure="piece",
            category="consumable",
            purchase_approval_limit=5000.0,
            is_active=True,
        )
        session.add(mat)
        await session.flush()

        # Approved Work & Material on Site A
        att_a = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=worker_emp_id,
            site_id=site_a.id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
            check_out_time=datetime.now(timezone.utc),
            working_hours=8.0,
            is_within_geofence=True,
            status="approved",
        )
        session.add(att_a)
        await session.flush()

        dwe_a = DailyWorkEntry(
            id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att_a.id,
            employee_id=worker_emp_id,
            site_id=site_a.id,
            activity_id=activity.id,
            work_order_id=wo_a.id,
            work_date=today,
            quantity=25.0,
            uom=activity.unit_of_measure,
            remarks="Completed 25 fiber joints",
            status="approved",
        )
        session.add(dwe_a)
        await session.flush()

        tx_a = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe_a.id,
            material_id=mat.id,
            site_id=site_a.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=25.0,
            amount=250.0,
            is_high_value=False,
            status="approved",
        )
        session.add(tx_a)

        # Approved Work & Material on Site B
        att_b = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=worker_emp_id,
            site_id=site_b.id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
            check_out_time=datetime.now(timezone.utc),
            working_hours=8.0,
            is_within_geofence=True,
            status="approved",
        )
        session.add(att_b)
        await session.flush()

        dwe_b = DailyWorkEntry(
            id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att_b.id,
            employee_id=worker_emp_id,
            site_id=site_b.id,
            activity_id=activity.id,
            work_order_id=wo_b.id,
            work_date=today,
            quantity=15.0,
            uom=activity.unit_of_measure,
            remarks="Completed 15 fiber joints on Site B",
            status="approved",
        )
        session.add(dwe_b)
        await session.flush()

        tx_b = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe_b.id,
            material_id=mat.id,
            site_id=site_b.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=15.0,
            amount=150.0,
            is_high_value=False,
            status="approved",
        )
        session.add(tx_b)

        await session.commit()

        # Generate tokens
        dir_token = create_access_token(subject=str(dir_user_id), role="director", employee_id=str(dir_emp_id))
        admin_token = create_access_token(subject=str(admin_user_id), role="administrator", employee_id=str(admin_emp_id))
        sup_token = create_access_token(subject=str(sup_user_id), role="supervisor", employee_id=str(sup_emp_id))
        worker_token = create_access_token(subject=str(worker_user_id), role="employee", employee_id=str(worker_emp_id))

        output_data = {
            "today": today.isoformat(),
            "directorToken": dir_token,
            "directorName": dir_emp.name,
            "adminToken": admin_token,
            "adminName": admin_emp.name,
            "supervisorToken": sup_token,
            "supervisorName": sup_emp.name,
            "workerToken": worker_token,
            "workerName": worker_emp.name,
            "clientAId": str(client_a.id),
            "clientAName": client_a.name,
            "projectAId": str(project_a.id),
            "projectAName": project_a.name,
            "siteAId": str(site_a.id),
            "siteAName": site_a.name,
            "clientBId": str(client_b.id),
            "clientBName": client_b.name,
            "projectBId": str(project_b.id),
            "projectBName": project_b.name,
            "siteBId": str(site_b.id),
            "siteBName": site_b.name,
            "activityName": activity.name,
        }
        print(json.dumps(output_data))


if __name__ == "__main__":
    asyncio.run(seed_e2e_invoices_data())

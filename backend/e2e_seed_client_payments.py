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
    Project,
    Site,
    WorkOrder,
)
from app.models.workforce import Employee
from app.models.invoices import Invoice, InvoiceLineItem


async def seed_e2e_client_payments_data():
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
            employee_code=f"DIR-PAY-{suffix}",
            mobile_id=dir_mobile,
            name=f"E2E Pay Director {suffix}",
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
            employee_code=f"ADM-PAY-{suffix}",
            mobile_id=admin_mobile,
            name=f"E2E Pay Admin {suffix}",
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
            employee_code=f"SUP-PAY-{suffix}",
            mobile_id=sup_mobile,
            name=f"E2E Pay Supervisor {suffix}",
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
            employee_code=f"EMP-PAY-{suffix}",
            mobile_id=worker_mobile,
            name=f"E2E Pay Worker {suffix}",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(worker_emp)
        await session.flush()

        # 5. Client, Project, Site
        client = Client(id=uuid.uuid4(), name=f"Metro Rail Corp {suffix}")
        session.add(client)
        project = Project(id=uuid.uuid4(), client_id=client.id, name=f"Line 3 Substation {suffix}", status="active")
        session.add(project)
        site = Site(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"Terminal Station {suffix}",
            supervisor_id=sup_emp_id,
            permitted_radius_m=200.0,
            location="POINT(72.834654 18.921984)",
            is_active=True,
        )
        session.add(site)

        # Activity & Work Order
        activity = Activity(
            id=uuid.uuid4(),
            name=f"Cable Laying {suffix}",
            unit_of_measure="metre",
            approved_rate=100.0,
            category="cable",
            is_active=True,
        )
        session.add(activity)

        wo = WorkOrder(
            id=uuid.uuid4(),
            order_number=f"WO-PAY-{suffix}",
            project_id=project.id,
            site_id=site.id,
            billing_basis="per_metre",
            status="open",
            is_active=True,
        )
        session.add(wo)
        await session.flush()

        # Attendance & Approved Work Entry
        att = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=worker_emp_id,
            site_id=site.id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
            check_out_time=datetime.now(timezone.utc),
            working_hours=8.0,
            is_within_geofence=True,
            status="approved",
        )
        session.add(att)
        await session.flush()

        dwe = DailyWorkEntry(
            id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp_id,
            site_id=site.id,
            activity_id=activity.id,
            work_order_id=wo.id,
            work_date=today,
            quantity=100.0,
            uom="metre",
            remarks="Completed 100 metres cable laying",
            status="approved",
        )
        session.add(dwe)
        await session.flush()

        # 6. Issued Invoice with ₹10,000.00 total
        inv_id = uuid.uuid4()
        inv_number = f"INV-PAY-{suffix}"
        invoice = Invoice(
            id=inv_id,
            invoice_number=inv_number,
            idempotency_key=str(uuid.uuid4()),
            client_id=client.id,
            project_id=project.id,
            site_id=site.id,
            period_start=today - timedelta(days=7),
            period_end=today,
            status="issued",
            subtotal_work=Decimal("10000.00"),
            subtotal_material=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("10000.00"),
            paid_amount=Decimal("0.00"),
            issue_date=today,
            due_date=today + timedelta(days=14),
            client_po_number=f"PO-PAY-{suffix}",
            notes="Ready for client payments E2E test",
            created_by=dir_user_id,
            issued_by=dir_user_id,
            issued_at=datetime.now(timezone.utc),
        )
        session.add(invoice)
        await session.flush()

        # Line item
        line = InvoiceLineItem(
            id=uuid.uuid4(),
            invoice_id=inv_id,
            line_type="work",
            source_daily_work_entry_id=dwe.id,
            source_date=today,
            item_description=activity.name,
            quantity=Decimal("100.00"),
            uom="metre",
            standard_rate=Decimal("100.00"),
            unit_rate=Decimal("100.00"),
            line_amount=Decimal("10000.00"),
            is_active=True,
        )
        session.add(line)

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
            "clientId": str(client.id),
            "clientName": client.name,
            "projectId": str(project.id),
            "projectName": project.name,
            "siteId": str(site.id),
            "siteName": site.name,
            "invoiceId": str(inv_id),
            "invoiceNumber": inv_number,
            "invoiceTotal": "10000.00",
        }
        print(json.dumps(output_data))


if __name__ == "__main__":
    asyncio.run(seed_e2e_client_payments_data())

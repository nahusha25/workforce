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
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.auth import User
from app.models.operations import AttendanceRecord, Client, Project, Site
from app.models.workforce import Employee, EmployeeRateHistory
from app.models.employee_payments import EmployeePayment, EmployeePaymentLine


async def seed_e2e_employee_payments_data():
    async with AsyncSessionLocal() as session:
        today = datetime.now(timezone.utc).date()
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
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
            employee_code=f"DIR-EP-{suffix}",
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
            employee_code=f"ADM-EP-{suffix}",
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
            employee_code=f"SUP-EP-{suffix}",
            mobile_id=sup_mobile,
            name=f"E2E Supervisor {suffix}",
            is_active=True,
        )
        session.add(sup_emp)

        # 4. Worker User & Employee
        worker_user_id = uuid.uuid4()
        worker_mobile = f"+9196{str(uuid.uuid4().int)[:8]}"
        worker_user = User(id=worker_user_id, mobile_id=worker_mobile, role="employee", is_active=True)
        session.add(worker_user)

        worker_emp_id = uuid.uuid4()
        worker_emp = Employee(
            id=worker_emp_id,
            user_id=worker_user_id,
            employee_code=f"WRK-EP-{suffix}",
            mobile_id=worker_mobile,
            name=f"E2E Worker {suffix}",
            is_active=True,
        )
        session.add(worker_emp)

        # 5. Client, Project, Site
        client = Client(id=uuid.uuid4(), name=f"E2E Client {suffix}", is_active=True)
        session.add(client)
        project = Project(id=uuid.uuid4(), client_id=client.id, name=f"E2E Project {suffix}", status="active")
        session.add(project)
        site = Site(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"E2E Site {suffix}",
            is_active=True,
        )
        session.add(site)

        # 6. Target Employee 1 for Full Lifecycle (Draft -> Approved -> Paid)
        emp1_user_id = uuid.uuid4()
        emp1_mobile = f"+9195{str(uuid.uuid4().int)[:8]}"
        emp1_user = User(id=emp1_user_id, mobile_id=emp1_mobile, role="employee", is_active=True)
        session.add(emp1_user)

        emp1_id = uuid.uuid4()
        emp1 = Employee(
            id=emp1_id,
            user_id=emp1_user_id,
            employee_code=f"EMP-LC-{suffix}",
            mobile_id=emp1_mobile,
            name=f"Lifecycle Worker {suffix}",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(emp1)

        rate1 = EmployeeRateHistory(
            id=uuid.uuid4(),
            employee_id=emp1_id,
            rate_type="daily",
            rate_amount=Decimal("800.00"),
            effective_from=today - timedelta(days=30),
            effective_to=None,
            changed_by=dir_emp_id,
        )
        session.add(rate1)

        await session.flush()

        att1_a = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=emp1_id,
            site_id=site.id,
            date=today - timedelta(days=5),
            status="approved",
        )
        session.add(att1_a)

        att1_b = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=emp1_id,
            site_id=site.id,
            date=today - timedelta(days=4),
            status="approved",
        )
        session.add(att1_b)

        # Pre-seed Draft Payment 1
        pay1_id = uuid.uuid4()
        pay1_num = f"PAY-{today_str}-LC{suffix}"
        pay1 = EmployeePayment(
            id=pay1_id,
            payment_number=pay1_num,
            idempotency_key=f"idem-seed-lc-{suffix}",
            employee_id=emp1_id,
            period_start=today - timedelta(days=7),
            period_end=today,
            status="draft",
            total_amount=Decimal("1600.00"),
            total_days=Decimal("2.00"),
            total_quantity=Decimal("0.00"),
            created_by=dir_user_id,
        )
        session.add(pay1)

        line1_a = EmployeePaymentLine(
            id=uuid.uuid4(),
            payment_id=pay1_id,
            source_attendance_id=att1_a.id,
            source_daily_work_entry_id=None,
            source_date=today - timedelta(days=5),
            rate_type="daily",
            rate_amount=Decimal("800.00"),
            rate_effective_from=today - timedelta(days=30),
            rate_effective_to=None,
            days=Decimal("1.00"),
            quantity=Decimal("0.00"),
            amount=Decimal("800.00"),
            is_active=True,
        )
        session.add(line1_a)

        line1_b = EmployeePaymentLine(
            id=uuid.uuid4(),
            payment_id=pay1_id,
            source_attendance_id=att1_b.id,
            source_daily_work_entry_id=None,
            source_date=today - timedelta(days=4),
            rate_type="daily",
            rate_amount=Decimal("800.00"),
            rate_effective_from=today - timedelta(days=30),
            rate_effective_to=None,
            days=Decimal("1.00"),
            quantity=Decimal("0.00"),
            amount=Decimal("800.00"),
            is_active=True,
        )
        session.add(line1_b)

        # 7. Target Employee 2 for Cancellation Flow
        emp2_user_id = uuid.uuid4()
        emp2_mobile = f"+9194{str(uuid.uuid4().int)[:8]}"
        emp2_user = User(id=emp2_user_id, mobile_id=emp2_mobile, role="employee", is_active=True)
        session.add(emp2_user)

        emp2_id = uuid.uuid4()
        emp2 = Employee(
            id=emp2_id,
            user_id=emp2_user_id,
            employee_code=f"EMP-CX-{suffix}",
            mobile_id=emp2_mobile,
            name=f"Cancel Worker {suffix}",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(emp2)

        rate2 = EmployeeRateHistory(
            id=uuid.uuid4(),
            employee_id=emp2_id,
            rate_type="daily",
            rate_amount=Decimal("750.00"),
            effective_from=today - timedelta(days=30),
            effective_to=None,
            changed_by=dir_emp_id,
        )
        session.add(rate2)

        await session.flush()

        att2 = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=emp2_id,
            site_id=site.id,
            date=today - timedelta(days=3),
            status="approved",
        )
        session.add(att2)

        # Pre-seed Draft Payment 2
        pay2_id = uuid.uuid4()
        pay2_num = f"PAY-{today_str}-CX{suffix}"
        pay2 = EmployeePayment(
            id=pay2_id,
            payment_number=pay2_num,
            idempotency_key=f"idem-seed-cx-{suffix}",
            employee_id=emp2_id,
            period_start=today - timedelta(days=7),
            period_end=today,
            status="draft",
            total_amount=Decimal("750.00"),
            total_days=Decimal("1.00"),
            total_quantity=Decimal("0.00"),
            created_by=dir_user_id,
        )
        session.add(pay2)

        line2 = EmployeePaymentLine(
            id=uuid.uuid4(),
            payment_id=pay2_id,
            source_attendance_id=att2.id,
            source_daily_work_entry_id=None,
            source_date=today - timedelta(days=3),
            rate_type="daily",
            rate_amount=Decimal("750.00"),
            rate_effective_from=today - timedelta(days=30),
            rate_effective_to=None,
            days=Decimal("1.00"),
            quantity=Decimal("0.00"),
            amount=Decimal("750.00"),
            is_active=True,
        )
        session.add(line2)

        await session.commit()

        # Generate tokens
        dir_token = create_access_token(subject=str(dir_user_id), role="director", employee_id=str(dir_emp_id))
        admin_token = create_access_token(subject=str(admin_user_id), role="administrator", employee_id=str(admin_emp_id))
        sup_token = create_access_token(subject=str(sup_user_id), role="supervisor", employee_id=str(sup_emp_id))
        worker_token = create_access_token(subject=str(worker_user_id), role="employee", employee_id=str(worker_emp_id))

        output_data = {
            "directorToken": dir_token,
            "adminToken": admin_token,
            "supervisorToken": sup_token,
            "workerToken": worker_token,
            "lifecyclePaymentId": str(pay1_id),
            "lifecyclePaymentNumber": pay1_num,
            "lifecycleEmployeeName": emp1.name,
            "cancellablePaymentId": str(pay2_id),
            "cancellablePaymentNumber": pay2_num,
            "cancellableEmployeeName": emp2.name,
        }
        print(json.dumps(output_data))


if __name__ == "__main__":
    asyncio.run(seed_e2e_employee_payments_data())

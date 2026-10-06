import asyncio
from datetime import date, datetime, timedelta, timezone
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
    WorkPhoto,
)
from app.models.workforce import Employee


async def seed_e2e_verification_data():
    async with AsyncSessionLocal() as session:
        today = datetime.now(timezone.utc).date()
        suffix = str(uuid.uuid4().int)[:6]

        # 1. Supervisor User & Employee
        sup_user_id = uuid.uuid4()
        sup_mobile = f"+9188{str(uuid.uuid4().int)[:8]}"
        sup_user = User(id=sup_user_id, mobile_id=sup_mobile, role="supervisor", is_active=True)
        session.add(sup_user)

        sup_emp_id = uuid.uuid4()
        sup_emp = Employee(
            id=sup_emp_id,
            user_id=sup_user_id,
            employee_code=f"SUP-E2E-{suffix}",
            mobile_id=sup_mobile,
            name="E2E Supervisor",
            is_active=True,
        )
        session.add(sup_emp)

        # 2. Administrator User & Employee
        admin_user_id = uuid.uuid4()
        admin_mobile = f"+9188{str(uuid.uuid4().int)[:8]}"
        admin_user = User(id=admin_user_id, mobile_id=admin_mobile, role="administrator", is_active=True)
        session.add(admin_user)

        admin_emp_id = uuid.uuid4()
        admin_emp = Employee(
            id=admin_emp_id,
            user_id=admin_user_id,
            employee_code=f"ADM-E2E-{suffix}",
            mobile_id=admin_mobile,
            name="E2E Administrator",
            is_active=True,
        )
        session.add(admin_emp)

        # 3. Worker 1 (for Approval & Reopen flow)
        worker1_user_id = uuid.uuid4()
        worker1_mobile = f"+9188{str(uuid.uuid4().int)[:8]}"
        worker1_user = User(id=worker1_user_id, mobile_id=worker1_mobile, role="employee", is_active=True)
        session.add(worker1_user)

        worker1_emp_id = uuid.uuid4()
        worker1_emp = Employee(
            id=worker1_emp_id,
            user_id=worker1_user_id,
            employee_code=f"EMP-APP-{suffix}",
            mobile_id=worker1_mobile,
            name="E2E Worker Approved",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(worker1_emp)

        # 4. Worker 2 (for Rejection flow)
        worker2_user_id = uuid.uuid4()
        worker2_mobile = f"+9188{str(uuid.uuid4().int)[:8]}"
        worker2_user = User(id=worker2_user_id, mobile_id=worker2_mobile, role="employee", is_active=True)
        session.add(worker2_user)

        worker2_emp_id = uuid.uuid4()
        worker2_emp = Employee(
            id=worker2_emp_id,
            user_id=worker2_user_id,
            employee_code=f"EMP-REJ-{suffix}",
            mobile_id=worker2_mobile,
            name="E2E Worker Rejected",
            supervisor_id=sup_emp_id,
            is_active=True,
        )
        session.add(worker2_emp)

        await session.flush()

        # 5. Client, Project, Site
        client = Client(id=uuid.uuid4(), name=f"E2E Client {suffix}")
        session.add(client)
        project = Project(id=uuid.uuid4(), client_id=client.id, name=f"E2E Project {suffix}", status="active")
        session.add(project)

        site_id = uuid.uuid4()
        site = Site(
            id=site_id,
            project_id=project.id,
            name=f"E2E Metro Site {suffix}",
            supervisor_id=sup_emp_id,
            permitted_radius_m=200.0,
            location="POINT(72.834654 18.921984)",
            is_active=True,
        )
        session.add(site)
        await session.flush()

        # 6. Site assignments
        assign1 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=worker1_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
        )
        assign2 = EmployeeSiteAssignment(
            id=uuid.uuid4(),
            employee_id=worker2_emp_id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
        )
        session.add_all([assign1, assign2])

        # 7. Activities, Work Orders, Materials
        activity = Activity(
            id=uuid.uuid4(),
            name="Optical Fiber Splicing",
            unit_of_measure="joints",
            approved_rate=80.0,
            category="cable",
            is_active=True,
        )
        session.add(activity)

        wo = WorkOrder(
            id=uuid.uuid4(),
            order_number=f"WO-VER-{suffix}",
            project_id=project.id,
            site_id=site_id,
            billing_basis="per_metre",
            status="open",
            is_active=True,
        )
        session.add(wo)

        mat_normal = Material(
            id=uuid.uuid4(),
            material_code=f"MAT-NORM-{suffix}",
            name="Heat Shrink Sleeve",
            unit_of_measure="piece",
            category="consumable",
            purchase_approval_limit=5000.0,
            is_active=True,
        )
        mat_high = Material(
            id=uuid.uuid4(),
            material_code=f"MAT-HIGH-{suffix}",
            name="Fusion Cleaver Blade",
            unit_of_measure="unit",
            category="tool",
            purchase_approval_limit=1000.0,  # Any purchase > 1000 is high-value
            is_active=True,
        )
        session.add_all([mat_normal, mat_high])
        await session.flush()

        # 8. Worker 1 Records (Today): Attendance (Out of geofence), Daily Work (with Photo), Normal Material, High-Value Material
        att1 = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=worker1_emp_id,
            site_id=site_id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
            check_in_location="POINT(73.000000 19.000000)",  # Far away from site
            check_out_time=datetime.now(timezone.utc),
            check_out_location="POINT(73.000000 19.000000)",
            working_hours=8.0,
            is_within_geofence=False,  # Triggers out_of_location exception flag
            status="submitted",
        )
        session.add(att1)
        await session.flush()

        dwe1 = DailyWorkEntry(
            id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att1.id,
            employee_id=worker1_emp_id,
            site_id=site_id,
            activity_id=activity.id,
            work_order_id=wo.id,
            work_date=today,
            quantity=15.0,
            uom=activity.unit_of_measure,
            remarks="Completed corridor cabling and joint splices",
            status="submitted",
        )
        session.add(dwe1)
        await session.flush()

        # Photo attached to DWE 1
        photo1 = WorkPhoto(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe1.id,
            image_url="/uploads/photos/seed_photo.jpg",
            thumbnail_url="/uploads/photos/seed_photo_thumb.jpg",
            file_size_bytes=22836,
        )
        session.add(photo1)

        # Material 1: Normal Consumed
        tx_norm = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe1.id,
            material_id=mat_normal.id,
            site_id=site_id,
            transaction_type="consumed",
            item_name="Heat Shrink Sleeve",
            quantity=15.0,
            amount=150.0,
            is_high_value=False,
            status="submitted",
        )
        # Material 2: High-Value Purchased (amount 4500 > limit 1000)
        tx_high = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe1.id,
            material_id=mat_high.id,
            site_id=site_id,
            transaction_type="purchased",
            item_name="Fusion Cleaver Blade",
            quantity=1.0,
            amount=4500.0,
            is_high_value=True,
            bill_image_url="/uploads/photos/seed_bill.jpg",
            status="submitted",
        )
        session.add_all([tx_norm, tx_high])

        # 9. Worker 2 Records (Today): For Rejection test path
        att2 = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=worker2_emp_id,
            site_id=site_id,
            date=today,
            session_number=1,
            check_in_time=datetime.now(timezone.utc) - timedelta(hours=6),
            check_in_location="POINT(72.834654 18.921984)",
            check_out_time=datetime.now(timezone.utc),
            working_hours=6.0,
            is_within_geofence=True,
            status="submitted",
        )
        session.add(att2)
        await session.flush()

        dwe2 = DailyWorkEntry(
            id=uuid.uuid4(),
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att2.id,
            employee_id=worker2_emp_id,
            site_id=site_id,
            activity_id=activity.id,
            work_order_id=wo.id,
            work_date=today,
            quantity=5.0,
            uom=activity.unit_of_measure,
            remarks="Rough cabling without OTDR tests",
            status="submitted",
        )
        session.add(dwe2)

        await session.commit()

        # Generate tokens
        sup_token = create_access_token(subject=str(sup_user_id), role="supervisor", employee_id=str(sup_emp_id))
        admin_token = create_access_token(subject=str(admin_user_id), role="administrator", employee_id=str(admin_emp_id))
        worker1_token = create_access_token(subject=str(worker1_user_id), role="employee", employee_id=str(worker1_emp_id))
        worker2_token = create_access_token(subject=str(worker2_user_id), role="employee", employee_id=str(worker2_emp_id))

        output_data = {
            "today": today.isoformat(),
            "supervisorToken": sup_token,
            "supervisorName": sup_emp.name,
            "adminToken": admin_token,
            "adminName": admin_emp.name,
            "worker1Token": worker1_token,
            "worker1Id": str(worker1_emp_id),
            "worker1Name": worker1_emp.name,
            "worker2Token": worker2_token,
            "worker2Id": str(worker2_emp_id),
            "worker2Name": worker2_emp.name,
            "dwe1Id": str(dwe1.id),
            "dwe2Id": str(dwe2.id),
            "matNormalId": str(tx_norm.id),
            "matHighId": str(tx_high.id),
            "att1Id": str(att1.id),
            "att2Id": str(att2.id),
        }
        print(json.dumps(output_data))


if __name__ == "__main__":
    asyncio.run(seed_e2e_verification_data())

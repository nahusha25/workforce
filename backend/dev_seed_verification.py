"""Throwaway dev-only seed script to create one messy day of verification data for manual testing.

Usage:
    .venv/Scripts/python dev_seed_verification.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
import sys
import uuid

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_otp_hash
from app.models.auth import OtpToken, User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
from app.models.workforce import Employee


async def seed_messy_verification_day():
    async with AsyncSessionLocal() as session:
        print("\n" + "=" * 60)
        print("SEEDING MESSY DAY FOR MANUAL VERIFICATION TESTING")
        print("=" * 60)

        # 1. Locate Target Employee
        # First try finding Nahus Test Worker by code/mobile or name
        stmt_emp = select(Employee).where(
            (Employee.employee_code == "EMP-77604")
            | (Employee.mobile_id == "+917760443750")
            | (Employee.name.ilike("%Nahus%"))
        )
        res_emp = await session.execute(stmt_emp)
        emp = res_emp.scalars().first()

        if not emp:
            # Fallback to any employee who is a worker
            stmt_fallback = select(Employee).limit(1)
            res_fallback = await session.execute(stmt_fallback)
            emp = res_fallback.scalars().first()
            if not emp:
                raise RuntimeError("No employee found in dev database to attach test data to.")

        print(f"[OK] Target Employee: {emp.name} (Code: {emp.employee_code}, Mobile: {emp.mobile_id}, ID: {emp.id})")

        # 2. Locate Site
        # Check if employee has an existing site assignment
        stmt_assign = (
            select(Site)
            .join(EmployeeSiteAssignment, EmployeeSiteAssignment.site_id == Site.id)
            .where(EmployeeSiteAssignment.employee_id == emp.id)
        )
        res_assign = await session.execute(stmt_assign)
        site = res_assign.scalars().first()

        if not site:
            # Check any active site
            stmt_site = select(Site).limit(1)
            res_site = await session.execute(stmt_site)
            site = res_site.scalars().first()
            if not site:
                raise RuntimeError("No site found in dev database.")
            # Create assignment
            new_assign = EmployeeSiteAssignment(
                id=uuid.uuid4(),
                employee_id=emp.id,
                site_id=site.id,
                assigned_at=datetime.now(timezone.utc),
            )
            session.add(new_assign)
            await session.flush()

        print(f"[OK] Target Site: {site.name} (ID: {site.id})")

        # 3. Create or Update Supervisor User & Employee
        sup_mobile = "+919876543210"
        stmt_sup_user = select(User).where(User.mobile_id == sup_mobile)
        res_sup_user = await session.execute(stmt_sup_user)
        sup_user = res_sup_user.scalars().first()

        if not sup_user:
            sup_user = User(
                id=uuid.uuid4(),
                mobile_id=sup_mobile,
                role="supervisor",
                is_active=True,
            )
            session.add(sup_user)
            await session.flush()
        else:
            sup_user.role = "supervisor"
            sup_user.is_active = True

        stmt_sup_emp = select(Employee).where(Employee.user_id == sup_user.id)
        res_sup_emp = await session.execute(stmt_sup_emp)
        sup_emp = res_sup_emp.scalars().first()

        if not sup_emp:
            sup_emp = Employee(
                id=uuid.uuid4(),
                user_id=sup_user.id,
                employee_code="SUP-DEV01",
                mobile_id=sup_mobile,
                name="Dev Verification Supervisor",
                is_active=True,
            )
            session.add(sup_emp)
            await session.flush()

        # Wire Supervisor to Site AND directly to Employee
        site.supervisor_id = sup_emp.id
        emp.supervisor_id = sup_emp.id
        await session.flush()
        print(f"[OK] Supervisor: {sup_emp.name} (Mobile: {sup_mobile}, Employee ID: {sup_emp.id})")
        print(f"  -> Linked as supervisor of site '{site.name}' AND direct supervisor of '{emp.name}'")

        # Pre-seed OTP token '123456' for Supervisor
        await session.execute(delete(OtpToken).where(OtpToken.user_id == sup_user.id))
        sup_otp_token = OtpToken(
            id=uuid.uuid4(),
            user_id=sup_user.id,
            otp_hash=get_otp_hash("123456"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            attempts=0,
            is_used=False,
        )
        session.add(sup_otp_token)

        # Also pre-seed OTP token '123456' for Administrator (+919999999999) if exists
        stmt_admin = select(User).where(User.mobile_id == "+919999999999")
        res_admin = await session.execute(stmt_admin)
        admin_user = res_admin.scalars().first()
        if admin_user:
            await session.execute(delete(OtpToken).where(OtpToken.user_id == admin_user.id))
            admin_otp = OtpToken(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                otp_hash=get_otp_hash("123456"),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                attempts=0,
                is_used=False,
            )
            session.add(admin_otp)

        # 4. Master Data: Activities, Material, Work Order
        stmt_acts = select(Activity).limit(5)
        res_acts = await session.execute(stmt_acts)
        acts = res_acts.scalars().all()
        if len(acts) < 2:
            act1 = Activity(
                id=uuid.uuid4(),
                name="Cable Pulling & Laying",
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
            session.add_all([act1, act2])
            await session.flush()
        else:
            act1, act2 = acts[0], acts[1]

        # Material with purchase limit
        stmt_mat = select(Material).where(Material.purchase_approval_limit.isnot(None)).limit(1)
        res_mat = await session.execute(stmt_mat)
        mat = res_mat.scalars().first()
        if not mat:
            mat = Material(
                id=uuid.uuid4(),
                material_code="MAT-C6",
                name="Cat6 Cable Box",
                unit_of_measure="box",
                category="cable",
                purchase_approval_limit=5000.0,
                is_active=True,
            )
            session.add(mat)
            await session.flush()

        # Work Order
        stmt_wo = select(WorkOrder).where(WorkOrder.site_id == site.id).limit(1)
        res_wo = await session.execute(stmt_wo)
        wo = res_wo.scalars().first()
        if not wo:
            stmt_any_wo = select(WorkOrder).limit(1)
            res_any_wo = await session.execute(stmt_any_wo)
            wo = res_any_wo.scalars().first()

        today = date.today()

        # 5. Clean up any existing records for this employee on today's date
        # (Allows the script to be run multiple times idempotently)
        stmt_existing_dwe = select(DailyWorkEntry).where(
            DailyWorkEntry.employee_id == emp.id, DailyWorkEntry.work_date == today
        )
        res_existing_dwe = await session.execute(stmt_existing_dwe)
        existing_dwes = res_existing_dwe.scalars().all()
        for dwe_item in existing_dwes:
            await session.execute(
                delete(VerificationRecord).where(VerificationRecord.daily_work_entry_id == dwe_item.id)
            )
            await session.execute(delete(WorkPhoto).where(WorkPhoto.daily_work_entry_id == dwe_item.id))
            stmt_mats = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == dwe_item.id)
            res_mats = await session.execute(stmt_mats)
            for mat_item in res_mats.scalars().all():
                await session.execute(
                    delete(VerificationRecord).where(VerificationRecord.material_transaction_id == mat_item.id)
                )
            await session.execute(
                delete(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == dwe_item.id)
            )
            await session.delete(dwe_item)

        stmt_existing_att = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == emp.id, AttendanceRecord.date == today
        )
        res_existing_att = await session.execute(stmt_existing_att)
        for att_item in res_existing_att.scalars().all():
            await session.execute(
                delete(VerificationRecord).where(VerificationRecord.attendance_record_id == att_item.id)
            )
            await session.delete(att_item)

        await session.flush()

        # 6. Seed Messy Day Data
        print(f"\n--- Seeding records for date: {today} ---")

        # 6a. Attendance: Out-of-geofence (is_within_geofence=False), checked in and out, status='submitted'
        now_utc = datetime.now(timezone.utc)
        check_in_dt = now_utc.replace(hour=3, minute=30, second=0, microsecond=0)  # 09:00 AM IST
        check_out_dt = now_utc.replace(hour=12, minute=0, second=0, microsecond=0)  # 05:30 PM IST

        att = AttendanceRecord(
            id=uuid.uuid4(),
            employee_id=emp.id,
            site_id=site.id,
            date=today,
            session_number=1,
            check_in_time=check_in_dt,
            check_in_location="POINT(72.850000 19.000000)",
            check_in_distance_m=1250.0,
            check_out_time=check_out_dt,
            check_out_location="POINT(72.855000 19.005000)",
            check_out_distance_m=1420.0,
            is_within_geofence=False,  # Triggers 'out_of_location' exception!
            working_hours=Decimal("8.50"),
            overtime_hours=Decimal("0.50"),
            status="submitted",
            override_by=None,
        )
        session.add(att)
        await session.flush()
        print("[OK] Created Attendance: submitted, 8.5 hrs, is_within_geofence=False (Out of location exception)")

        # 6b. Submitted Daily Work Entry 1 (normal quantity)
        dwe_submitted = DailyWorkEntry(
            id=uuid.uuid4(),
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            work_order_id=wo.id if wo else None,
            activity_id=act1.id,
            work_date=today,
            quantity=Decimal("45.00"),
            uom=act1.unit_of_measure,
            remarks="Pulled and laid 45m of primary backbone trunk cable along floor 2 corridor.",
            status="submitted",
            idempotency_key=str(uuid.uuid4()),
        )
        session.add(dwe_submitted)
        await session.flush()
        print(f"[OK] Created Work Entry 1 (Submitted): Activity='{act1.name}', Quantity=45 {act1.unit_of_measure}")

        # 6c. Attached Work Photo to Submitted Entry 1
        # Uses a real JPEG in backend/uploads/photos/ so the StaticFiles
        # mount at /uploads serves it correctly — no external URL dependency.
        photo = WorkPhoto(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe_submitted.id,
            image_url="/uploads/photos/seed_photo.jpg",
            thumbnail_url="/uploads/photos/seed_photo_thumb.jpg",
            file_size_bytes=22836,
            uploaded_at=datetime.now(timezone.utc),
        )
        session.add(photo)
        print("[OK] Attached Photo to Work Entry 1 (local: /uploads/photos/seed_photo.jpg)")

        # 6d. Submitted Material Transaction 1: High Value (amount > purchase limit)
        mat_tx_high = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe_submitted.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="purchased",
            item_name=f"{mat.name} Drum 500m (Bulk Urgent Purchase)",
            quantity=Decimal("3.00"),
            amount=Decimal("18500.00"),
            bill_image_url="/uploads/photos/seed_bill.jpg",
            is_high_value=True,  # Triggers high-value warning and badge!
            status="submitted",
        )
        session.add(mat_tx_high)
        print(f"[OK] Created Material 1 (Submitted, HIGH VALUE): '{mat_tx_high.item_name}', Amount=Rs.18,500 (Limit=Rs.{mat.purchase_approval_limit})")

        # 6e. Submitted Material Transaction 2: Normal value (amount <= limit)
        mat_tx_normal = MaterialTransaction(
            id=uuid.uuid4(),
            daily_work_entry_id=dwe_submitted.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name="RJ45 Patch Connectors Box",
            quantity=Decimal("1.00"),
            amount=Decimal("1200.00"),
            bill_image_url=None,
            is_high_value=False,
            status="submitted",
        )
        session.add(mat_tx_normal)
        print(f"[OK] Created Material 2 (Submitted, Normal): '{mat_tx_normal.item_name}', Amount=Rs.1,200")

        # 6f. Draft Daily Work Entry 2 (different activity, not submitted yet)
        dwe_draft = DailyWorkEntry(
            id=uuid.uuid4(),
            attendance_record_id=att.id,
            employee_id=emp.id,
            site_id=site.id,
            work_order_id=wo.id if wo else None,
            activity_id=act2.id,
            work_date=today,
            quantity=Decimal("6.00"),
            uom=act2.unit_of_measure,
            remarks="Rough-in installation underway; draft pending inspection.",
            status="draft",
            idempotency_key=str(uuid.uuid4()),
        )
        session.add(dwe_draft)
        print(f"[OK] Created Work Entry 2 (DRAFT): Activity='{act2.name}', Quantity=6 {act2.unit_of_measure} (Not submitted yet)")

        await session.commit()

        print("\n" + "=" * 60)
        print("DEV SEED COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nSUPERVISOR LOGIN CREDENTIALS:")
        print(f"   Mobile Number : {sup_mobile}")
        print(f"   Pre-seeded OTP: 123456  (valid for 7 days)")
        print(f"   Role          : supervisor")
        print(f"\nADMINISTRATOR LOGIN CREDENTIALS:")
        print(f"   Mobile Number : +919999999999")
        print(f"   Pre-seeded OTP: 123456  (valid for 7 days)")
        print(f"   Role          : administrator")
        print(f"\nTARGET EMPLOYEE FOR REVIEW:")
        print(f"   Name          : {emp.name}")
        print(f"   Employee Code : {emp.employee_code}")
        print(f"   Employee ID   : {emp.id}")
        print(f"   Review Date   : {today}")
        print(f"\nDIRECT URLS TO TEST:")
        print(f"   Verification Queue: http://localhost:5173/verification?date={today}")
        print(f"   Day Detail Page   : http://localhost:5173/verification/{emp.id}?date={today}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed_messy_verification_day())

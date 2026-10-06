import asyncio
import sys
import os
import uuid

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, delete, update
from app.core.database import AsyncSessionLocal
from app.models.auth import User, OtpToken, RefreshToken
from app.models.system import AuditLog
from app.models.workforce import Employee, EmployeeRole, EmployeeRateHistory
from app.models.operations import (
    Site,
    EmployeeSiteAssignment,
    AttendanceRecord,
    DailyWorkEntry,
    WorkPhoto,
    MaterialTransaction,
    VerificationRecord,
    ExceptionFlag
)

ADMIN_MOBILE = "+917760443750"
SUPERVISOR_MOBILE = "+919876543210"

async def setup_users():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Nullify supervisor_id references in sites and employees
            await session.execute(update(Site).values(supervisor_id=None))
            await session.execute(update(Employee).values(supervisor_id=None))

            # 2. Delete all operational records
            await session.execute(delete(VerificationRecord))
            await session.execute(delete(ExceptionFlag))
            await session.execute(delete(WorkPhoto))
            await session.execute(delete(MaterialTransaction))
            await session.execute(delete(DailyWorkEntry))
            await session.execute(delete(AttendanceRecord))
            await session.execute(delete(EmployeeSiteAssignment))
            await session.execute(delete(EmployeeRateHistory))
            await session.execute(delete(EmployeeRole))
            await session.execute(delete(Employee))
            
            # 3. Delete all audit logs, otp tokens, refresh tokens
            await session.execute(delete(AuditLog))
            await session.execute(delete(OtpToken))
            await session.execute(delete(RefreshToken))

            # 4. Delete all existing users
            res_users = await session.execute(delete(User))
            print(f"Removed {res_users.rowcount} old users.")

            # 5. Create Administrator / Director User
            admin_id = uuid.uuid4()
            admin_user = User(
                id=admin_id,
                mobile_id=ADMIN_MOBILE,
                role="administrator",
                is_active=True
            )
            session.add(admin_user)

            # 6. Create Supervisor User
            sup_user_id = uuid.uuid4()
            sup_user = User(
                id=sup_user_id,
                mobile_id=SUPERVISOR_MOBILE,
                role="supervisor",
                is_active=True
            )
            session.add(sup_user)
            await session.flush()

            # 7. Create Supervisor Employee profile (required for supervisor actions & scope)
            sup_emp_id = uuid.uuid4()
            sup_emp = Employee(
                id=sup_emp_id,
                user_id=sup_user.id,
                employee_code="SUP-98765",
                mobile_id=SUPERVISOR_MOBILE,
                name="Site Supervisor",
                is_active=True
            )
            session.add(sup_emp)
            await session.flush()

            # 8. Link supervisor to active site(s)
            res_sites = await session.execute(select(Site))
            sites = res_sites.scalars().all()
            for s in sites:
                s.supervisor_id = sup_emp.id
            
            print(f"Created Administrator/Director ({ADMIN_MOBILE}) and Supervisor ({SUPERVISOR_MOBILE}).")
            print(f"Linked supervisor to {len(sites)} sites.")

        # Output final verified state
        users = (await session.execute(select(User))).scalars().all()
        emps = (await session.execute(select(Employee))).scalars().all()
        print("\n" + "=" * 55)
        print("DATABASE LOGIN USERS:")
        for u in users:
            print(f"  Mobile: {u.mobile_id} | Role: {u.role} | Active: {u.is_active}")
        print("\nEMPLOYEE PROFILES:")
        for e in emps:
            print(f"  Code: {e.employee_code} | Name: {e.name} | Mobile: {e.mobile_id}")
        print("=" * 55 + "\n")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_users())

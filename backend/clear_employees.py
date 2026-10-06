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

ADMIN_MOBILE = "+919999999999"

async def clear_employees():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Ensure administrator user exists
            res_admin = await session.execute(select(User).where(User.mobile_id == ADMIN_MOBILE))
            admin_user = res_admin.scalar_one_or_none()
            if not admin_user:
                admin_user = User(
                    id=uuid.uuid4(),
                    mobile_id=ADMIN_MOBILE,
                    role="administrator",
                    is_active=True
                )
                session.add(admin_user)
                await session.flush()
                print(f"Created Administrator user: {ADMIN_MOBILE}")
            else:
                admin_user.is_active = True
                admin_user.role = "administrator"
                print(f"Preserving Administrator user: {ADMIN_MOBILE}")

            # 2. Nullify supervisor_id references in sites and employees
            await session.execute(update(Site).values(supervisor_id=None))
            await session.execute(update(Employee).values(supervisor_id=None))

            # 3. Delete verification records
            res_ver = await session.execute(delete(VerificationRecord))
            print(f"Deleted {res_ver.rowcount} verification records")

            # 4. Delete exception flags
            res_exc = await session.execute(delete(ExceptionFlag))
            print(f"Deleted {res_exc.rowcount} exception flags")

            # 5. Delete work photos
            res_photos = await session.execute(delete(WorkPhoto))
            print(f"Deleted {res_photos.rowcount} work photos")

            # 6. Delete material transactions
            res_mat = await session.execute(delete(MaterialTransaction))
            print(f"Deleted {res_mat.rowcount} material transactions")

            # 7. Delete daily work entries
            res_work = await session.execute(delete(DailyWorkEntry))
            print(f"Deleted {res_work.rowcount} daily work entries")

            # 8. Delete attendance records
            res_att = await session.execute(delete(AttendanceRecord))
            print(f"Deleted {res_att.rowcount} attendance records")

            # 9. Delete employee site assignments
            res_assign = await session.execute(delete(EmployeeSiteAssignment))
            print(f"Deleted {res_assign.rowcount} site assignments")

            # 10. Delete rate history and roles
            res_rate = await session.execute(delete(EmployeeRateHistory))
            res_role = await session.execute(delete(EmployeeRole))
            print(f"Deleted {res_rate.rowcount} rate history and {res_role.rowcount} role rows")

            # 11. Delete all employee records
            res_emp = await session.execute(delete(Employee))
            print(f"Deleted {res_emp.rowcount} employee records")

            # 12. Delete audit logs associated with employee users
            emp_user_subquery = select(User.id).where(User.role == "employee")
            res_audit = await session.execute(delete(AuditLog).where(AuditLog.changed_by.in_(emp_user_subquery)))
            print(f"Deleted {res_audit.rowcount} audit logs")

            # 13. Delete OTP tokens and refresh tokens for employee users
            res_otp = await session.execute(delete(OtpToken).where(OtpToken.user_id.in_(emp_user_subquery)))
            res_ref = await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(emp_user_subquery)))
            print(f"Deleted {res_otp.rowcount} OTP tokens and {res_ref.rowcount} refresh tokens")

            # 14. Delete all users with role 'employee'
            res_user = await session.execute(delete(User).where(User.role == "employee"))
            print(f"Deleted {res_user.rowcount} employee user logins")

        # Output final state
        remaining_users = (await session.execute(select(User))).scalars().all()
        remaining_emps = (await session.execute(select(Employee))).scalars().all()

        print("\n" + "=" * 55)
        print("DATABASE STATUS AFTER CLEANUP:")
        print(f"Total Employees : {len(remaining_emps)}")
        print(f"Total Users     : {len(remaining_users)}")
        for u in remaining_users:
            print(f"  User: Mobile={u.mobile_id} | Role={u.role} | Active={u.is_active}")
        print("=" * 55 + "\n")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(clear_employees())

import uuid
from collections.abc import Sequence
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.operations import EmployeeSiteAssignment, Site
from app.models.workforce import Employee, EmployeeRateHistory, EmployeeRole, Role


class EmployeeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_mobile(self, mobile_id: str) -> User | None:
        stmt = select(User).where(User.mobile_id == mobile_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_employee_by_code(self, code: str) -> Employee | None:
        stmt = select(Employee).where(Employee.employee_code == code)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_employee_by_mobile(self, mobile_id: str) -> Employee | None:
        stmt = select(Employee).where(Employee.mobile_id == mobile_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Employee | None:
        stmt = select(Employee).where(Employee.id == employee_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_employee_by_user_id(self, user_id: uuid.UUID) -> Employee | None:
        stmt = select(Employee).where(Employee.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_roles_by_ids(self, role_ids: list[uuid.UUID]) -> Sequence[Role]:
        stmt = select(Role).where(Role.id.in_(role_ids))
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_sites_by_ids(self, site_ids: list[uuid.UUID]) -> Sequence[Site]:
        stmt = select(Site).where(Site.id.in_(site_ids))
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create_employee_atomic(
        self,
        user: User,
        employee: Employee,
        role_ids: list[uuid.UUID],
        rate_history: EmployeeRateHistory,
        site_ids: list[uuid.UUID],
    ) -> Employee:
        self.db.add(user)
        await self.db.flush()

        employee.user_id = user.id
        self.db.add(employee)
        await self.db.flush()

        for rid in role_ids:
            er = EmployeeRole(employee_id=employee.id, role_id=rid)
            self.db.add(er)

        rate_history.employee_id = employee.id
        self.db.add(rate_history)

        for sid in site_ids:
            esa = EmployeeSiteAssignment(
                employee_id=employee.id,
                site_id=sid,
                assigned_at=datetime.now(timezone.utc),
                is_active=True,
            )
            self.db.add(esa)

        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def get_employees(
        self, skip: int = 0, limit: int = 100, supervisor_id: uuid.UUID | None = None
    ) -> Sequence[Employee]:
        stmt = select(Employee)
        if supervisor_id:
            stmt = stmt.where(Employee.supervisor_id == supervisor_id)
        stmt = stmt.order_by(Employee.created_at.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_employee_trade_roles(self, employee_id: uuid.UUID) -> Sequence[Role]:
        stmt = (
            select(Role)
            .join(EmployeeRole, Role.id == EmployeeRole.role_id)
            .where(EmployeeRole.employee_id == employee_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_active_rate_history(self, employee_id: uuid.UUID) -> EmployeeRateHistory | None:
        stmt = (
            select(EmployeeRateHistory)
            .where(
                EmployeeRateHistory.employee_id == employee_id,
                EmployeeRateHistory.effective_to.is_(None),
            )
            .order_by(EmployeeRateHistory.effective_from.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_active_assigned_sites(self, employee_id: uuid.UUID) -> Sequence[Site]:
        stmt = (
            select(Site)
            .join(EmployeeSiteAssignment, Site.id == EmployeeSiteAssignment.site_id)
            .where(
                EmployeeSiteAssignment.employee_id == employee_id,
                EmployeeSiteAssignment.is_active.is_(True),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update_employee(self, employee: Employee) -> Employee:
        employee.updated_at = datetime.now(timezone.utc)
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def update_rate_history_atomic(
        self,
        employee_id: uuid.UUID,
        old_rate: EmployeeRateHistory | None,
        new_rate: EmployeeRateHistory,
    ) -> None:
        if old_rate:
            old_rate.effective_to = date.today()
            self.db.add(old_rate)
        self.db.add(new_rate)
        await self.db.commit()

    async def set_employee_trade_roles(self, employee_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        from sqlalchemy import delete
        stmt_del = delete(EmployeeRole).where(EmployeeRole.employee_id == employee_id)
        await self.db.execute(stmt_del)
        await self.db.execute(stmt_del)
        for rid in role_ids:
            self.db.add(EmployeeRole(employee_id=employee_id, role_id=rid))
        await self.db.commit()

    async def add_site_assignment(self, assignment: EmployeeSiteAssignment) -> EmployeeSiteAssignment:
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def update_user(self, user: User) -> User:
        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_employee_site_assignments(
        self, employee_id: uuid.UUID, site_ids: list[uuid.UUID]
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = select(EmployeeSiteAssignment).where(
            EmployeeSiteAssignment.employee_id == employee_id,
            EmployeeSiteAssignment.is_active.is_(True),
        )
        res = await self.db.execute(stmt)
        current_assignments = res.scalars().all()
        current_site_ids = {a.site_id for a in current_assignments}

        for a in current_assignments:
            if a.site_id not in site_ids:
                a.is_active = False
                a.unassigned_at = now
                self.db.add(a)

        for sid in site_ids:
            if sid not in current_site_ids:
                new_assign = EmployeeSiteAssignment(
                    employee_id=employee_id,
                    site_id=sid,
                    assigned_at=now,
                    is_active=True,
                )
                self.db.add(new_assign)

        await self.db.commit()

    async def delete_employee_atomic(self, employee_id: uuid.UUID, user_id: uuid.UUID) -> None:
        from sqlalchemy import delete, select, update
        from app.models.auth import OtpToken, RefreshToken, User
        from app.models.operations import (
            AttendanceRecord,
            DailyWorkEntry,
            EmployeeSiteAssignment,
            ExceptionFlag,
            MaterialTransaction,
            Site,
            VerificationRecord,
            WorkPhoto,
        )
        from app.models.system import AuditLog

        # 1. Nullify supervisor references in other employees and sites
        await self.db.execute(update(Employee).where(Employee.supervisor_id == employee_id).values(supervisor_id=None))
        await self.db.execute(update(Site).where(Site.supervisor_id == employee_id).values(supervisor_id=None))

        # 2. Site assignments, roles, rate history
        await self.db.execute(delete(EmployeeSiteAssignment).where(EmployeeSiteAssignment.employee_id == employee_id))
        await self.db.execute(
            delete(EmployeeRateHistory).where(
                (EmployeeRateHistory.employee_id == employee_id) | (EmployeeRateHistory.changed_by == employee_id)
            )
        )
        await self.db.execute(delete(EmployeeRole).where(EmployeeRole.employee_id == employee_id))

        # 3. Daily work entries
        res_dwe = await self.db.execute(select(DailyWorkEntry.id).where(DailyWorkEntry.employee_id == employee_id))
        dwe_ids = res_dwe.scalars().all()
        if dwe_ids:
            await self.db.execute(delete(WorkPhoto).where(WorkPhoto.daily_work_entry_id.in_(dwe_ids)))
            res_mat = await self.db.execute(
                select(MaterialTransaction.id).where(MaterialTransaction.daily_work_entry_id.in_(dwe_ids))
            )
            mat_ids = res_mat.scalars().all()
            if mat_ids:
                await self.db.execute(delete(VerificationRecord).where(VerificationRecord.material_transaction_id.in_(mat_ids)))
                await self.db.execute(
                    delete(ExceptionFlag).where((ExceptionFlag.entity_type == "material") & (ExceptionFlag.entity_id.in_(mat_ids)))
                )
                await self.db.execute(delete(MaterialTransaction).where(MaterialTransaction.id.in_(mat_ids)))
            await self.db.execute(delete(VerificationRecord).where(VerificationRecord.daily_work_entry_id.in_(dwe_ids)))
            await self.db.execute(
                delete(ExceptionFlag).where((ExceptionFlag.entity_type == "daily_work") & (ExceptionFlag.entity_id.in_(dwe_ids)))
            )
            await self.db.execute(delete(DailyWorkEntry).where(DailyWorkEntry.id.in_(dwe_ids)))

        # 4. Attendance records
        res_att = await self.db.execute(select(AttendanceRecord.id).where(AttendanceRecord.employee_id == employee_id))
        att_ids = res_att.scalars().all()
        if att_ids:
            await self.db.execute(delete(VerificationRecord).where(VerificationRecord.attendance_record_id.in_(att_ids)))
            await self.db.execute(
                delete(ExceptionFlag).where((ExceptionFlag.entity_type == "attendance") & (ExceptionFlag.entity_id.in_(att_ids)))
            )
            await self.db.execute(delete(AttendanceRecord).where(AttendanceRecord.id.in_(att_ids)))

        # 5. User-level references
        await self.db.execute(update(AttendanceRecord).where(AttendanceRecord.override_by == user_id).values(override_by=None))
        await self.db.execute(update(ExceptionFlag).where(ExceptionFlag.resolved_by == user_id).values(resolved_by=None))
        await self.db.execute(delete(VerificationRecord).where(VerificationRecord.verified_by == user_id))
        await self.db.execute(delete(AuditLog).where(AuditLog.changed_by == user_id))
        await self.db.execute(delete(OtpToken).where(OtpToken.user_id == user_id))
        await self.db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))

        # 6. Delete Employee and User
        await self.db.execute(delete(Employee).where(Employee.id == employee_id))
        await self.db.execute(delete(User).where(User.id == user_id))

        await self.db.commit()

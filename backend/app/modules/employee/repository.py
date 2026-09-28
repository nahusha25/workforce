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

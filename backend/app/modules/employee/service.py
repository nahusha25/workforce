import uuid
from datetime import date, datetime, timezone

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.models.auth import User
from app.models.operations import EmployeeSiteAssignment
from app.models.workforce import Employee, EmployeeRateHistory
from app.modules.employee.repository import EmployeeRepository
from app.modules.employee.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    RateHistoryResponse,
    RoleBriefResponse,
    SiteBriefResponse,
)


class EmployeeService:
    def __init__(self, repository: EmployeeRepository):
        self.repo = repository

    async def _format_employee_response(self, employee: Employee) -> EmployeeResponse:
        user = await self.repo.get_user_by_id(employee.user_id)
        system_role = user.role if user else "employee"

        trade_roles = await self.repo.get_employee_trade_roles(employee.id)
        current_rate = await self.repo.get_active_rate_history(employee.id)
        active_sites = await self.repo.get_active_assigned_sites(employee.id)

        return EmployeeResponse(
            id=employee.id,
            user_id=employee.user_id,
            employee_code=employee.employee_code,
            mobile_id=employee.mobile_id,
            name=employee.name,
            system_role=system_role,
            supervisor_id=employee.supervisor_id,
            is_active=employee.is_active,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
            trade_roles=[RoleBriefResponse(id=r.id, name=r.name) for r in trade_roles],
            current_rate=RateHistoryResponse.model_validate(current_rate) if current_rate else None,
            active_sites=[SiteBriefResponse(id=s.id, name=s.name) for s in active_sites],
        )

    async def create_employee(self, emp_in: EmployeeCreate, admin_user: User) -> EmployeeResponse:
        existing_user = await self.repo.get_user_by_mobile(emp_in.mobile_number)
        if existing_user:
            raise ConflictError(f"User with mobile number {emp_in.mobile_number} already exists")

        existing_emp_mobile = await self.repo.get_employee_by_mobile(emp_in.mobile_number)
        if existing_emp_mobile:
            raise ConflictError(f"Employee with mobile number {emp_in.mobile_number} already exists")

        existing_emp_code = await self.repo.get_employee_by_code(emp_in.employee_code)
        if existing_emp_code:
            raise ConflictError(f"Employee with code {emp_in.employee_code} already exists")

        if emp_in.supervisor_id:
            supervisor = await self.repo.get_employee_by_id(emp_in.supervisor_id)
            if not supervisor or not supervisor.is_active:
                raise NotFoundError(f"Active supervisor with ID {emp_in.supervisor_id} not found")

        roles = await self.repo.get_roles_by_ids(emp_in.trade_role_ids)
        if len(roles) != len(set(emp_in.trade_role_ids)):
            raise NotFoundError("One or more specified trade roles do not exist")

        sites = await self.repo.get_sites_by_ids(emp_in.site_ids)
        if len(sites) != len(set(emp_in.site_ids)):
            raise NotFoundError("One or more specified sites do not exist")

        user = User(
            mobile_id=emp_in.mobile_number,
            role=emp_in.system_role,
            is_active=True,
        )

        admin_emp = await self.repo.get_employee_by_user_id(admin_user.id)

        employee = Employee(
            employee_code=emp_in.employee_code,
            mobile_id=emp_in.mobile_number,
            name=emp_in.name,
            supervisor_id=emp_in.supervisor_id,
            is_active=True,
        )

        # Ensure changed_by_id points to an employee ID (either admin_emp.id or new employee.id)
        changed_by_id = admin_emp.id if admin_emp else employee.id

        rate_history = EmployeeRateHistory(
            rate_type=emp_in.rate_type,
            rate_amount=emp_in.rate_amount,
            effective_from=date.today(),
            effective_to=None,
            changed_by=changed_by_id,
        )

        created_employee = await self.repo.create_employee_atomic(
            user=user,
            employee=employee,
            role_ids=emp_in.trade_role_ids,
            rate_history=rate_history,
            site_ids=emp_in.site_ids,
        )

        return await self._format_employee_response(created_employee)

    async def get_employees(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> list[EmployeeResponse]:
        supervisor_id_filter = None
        if current_user.role == "supervisor":
            sup_emp = await self.repo.get_employee_by_user_id(current_user.id)
            if not sup_emp:
                return []
            supervisor_id_filter = sup_emp.id

        employees = await self.repo.get_employees(skip=skip, limit=limit, supervisor_id=supervisor_id_filter)
        res = []
        for emp in employees:
            res.append(await self._format_employee_response(emp))
        return res

    async def get_employee_by_id(self, employee_id: uuid.UUID, current_user: User) -> EmployeeResponse:
        employee = await self.repo.get_employee_by_id(employee_id)
        if not employee:
            raise NotFoundError(f"Employee with ID {employee_id} not found")

        if current_user.role == "supervisor":
            sup_emp = await self.repo.get_employee_by_user_id(current_user.id)
            if not sup_emp or (employee.supervisor_id != sup_emp.id and employee.id != sup_emp.id):
                raise ForbiddenError("Not authorized to view this employee record")

        return await self._format_employee_response(employee)

    async def get_my_profile(self, current_user: User) -> EmployeeResponse:
        employee = await self.repo.get_employee_by_user_id(current_user.id)
        if not employee:
            if current_user.role in ("administrator", "director"):
                return EmployeeResponse(
                    id=current_user.id,
                    user_id=current_user.id,
                    employee_code=f"ADM-{str(current_user.id)[:6].upper()}",
                    mobile_id=current_user.mobile_id,
                    name=f"System {current_user.role.title()}",
                    system_role=current_user.role,
                    supervisor_id=None,
                    is_active=current_user.is_active,
                    created_at=current_user.created_at,
                    updated_at=current_user.updated_at,
                    trade_roles=[],
                    current_rate=None,
                    active_sites=[],
                )
            raise NotFoundError(f"No employee profile linked to user {current_user.id}")
        return await self._format_employee_response(employee)

    async def update_employee(
        self, employee_id: uuid.UUID, emp_update: EmployeeUpdate, admin_user: User
    ) -> EmployeeResponse:
        employee = await self.repo.get_employee_by_id(employee_id)
        if not employee:
            raise NotFoundError(f"Employee with ID {employee_id} not found")

        if emp_update.name is not None:
            employee.name = emp_update.name

        if emp_update.supervisor_id is not None:
            supervisor = await self.repo.get_employee_by_id(emp_update.supervisor_id)
            if not supervisor or not supervisor.is_active:
                raise NotFoundError(f"Active supervisor with ID {emp_update.supervisor_id} not found")
            employee.supervisor_id = emp_update.supervisor_id

        if emp_update.is_active is not None:
            employee.is_active = emp_update.is_active

        if emp_update.trade_role_ids is not None:
            roles = await self.repo.get_roles_by_ids(emp_update.trade_role_ids)
            if len(roles) != len(set(emp_update.trade_role_ids)):
                raise NotFoundError("One or more specified trade roles do not exist")
            await self.repo.set_employee_trade_roles(employee.id, emp_update.trade_role_ids)

        if emp_update.rate_type is not None or emp_update.rate_amount is not None:
            current_rate = await self.repo.get_active_rate_history(employee.id)
            new_type = emp_update.rate_type if emp_update.rate_type is not None else (current_rate.rate_type if current_rate else "daily")
            new_amount = emp_update.rate_amount if emp_update.rate_amount is not None else (float(current_rate.rate_amount) if current_rate else 0.0)

            admin_emp = await self.repo.get_employee_by_user_id(admin_user.id)
            changed_by_id = admin_emp.id if admin_emp else employee.id

            new_rate_record = EmployeeRateHistory(
                employee_id=employee.id,
                rate_type=new_type,
                rate_amount=new_amount,
                effective_from=date.today(),
                effective_to=None,
                changed_by=changed_by_id,
            )

            await self.repo.update_rate_history_atomic(
                employee_id=employee.id, old_rate=current_rate, new_rate=new_rate_record
            )

        updated_emp = await self.repo.update_employee(employee)
        return await self._format_employee_response(updated_emp)

    async def assign_site(self, employee_id: uuid.UUID, site_id: uuid.UUID) -> EmployeeResponse:
        employee = await self.repo.get_employee_by_id(employee_id)
        if not employee:
            raise NotFoundError(f"Employee with ID {employee_id} not found")

        sites = await self.repo.get_sites_by_ids([site_id])
        if not sites:
            raise NotFoundError(f"Site with ID {site_id} not found")

        assignment = EmployeeSiteAssignment(
            employee_id=employee.id,
            site_id=site_id,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
        )
        await self.repo.add_site_assignment(assignment)
        return await self._format_employee_response(employee)

    async def delete_employee(self, employee_id: uuid.UUID, admin_user: User) -> None:
        employee = await self.repo.get_employee_by_id(employee_id)
        if not employee:
            raise NotFoundError(f"Employee with ID {employee_id} not found")

        if employee.user_id == admin_user.id:
            raise BusinessRuleError("Cannot delete your own administrator account")

        await self.repo.delete_employee_atomic(employee.id, employee.user_id)

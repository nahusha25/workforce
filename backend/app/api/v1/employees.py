import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.employee.repository import EmployeeRepository
from app.modules.employee.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    SiteAssignmentCreate,
)
from app.modules.employee.service import EmployeeService

router = APIRouter()


def get_employee_service(db: AsyncSession = Depends(get_db)) -> EmployeeService:
    repo = EmployeeRepository(db)
    return EmployeeService(repo)


# EMP-001: Onboard new employee
@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    emp_in: EmployeeCreate,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator"])),
):
    return await service.create_employee(emp_in, admin_user=current_user)


# EMP-002: List employees
@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator", "director", "supervisor"])),
):
    return await service.get_employees(current_user=current_user, skip=skip, limit=limit)


# EMP-005: Get own profile (must be defined before /{id})
@router.get("/me", response_model=EmployeeResponse)
async def get_my_profile(
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator", "director", "supervisor", "employee"])),
):
    return await service.get_my_profile(current_user=current_user)


# EMP-003: Get employee details
@router.get("/{id}", response_model=EmployeeResponse)
async def get_employee_by_id(
    id: uuid.UUID,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator", "director", "supervisor"])),
):
    return await service.get_employee_by_id(employee_id=id, current_user=current_user)


# EMP-004: Update employee profile
@router.put("/{id}", response_model=EmployeeResponse)
async def update_employee(
    id: uuid.UUID,
    emp_update: EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator"])),
):
    return await service.update_employee(employee_id=id, emp_update=emp_update, admin_user=current_user)


# EMP-006: Assign site
@router.post("/{id}/site-assignments", response_model=EmployeeResponse)
async def assign_site(
    id: uuid.UUID,
    assignment_in: SiteAssignmentCreate,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(require_role(["administrator"])),
):
    return await service.assign_site(employee_id=id, site_id=assignment_in.site_id)

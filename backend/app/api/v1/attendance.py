import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.auth import User
from app.models.workforce import Employee
from app.modules.attendance.schemas import CheckInRequest, CheckOutRequest, OverrideRequest
from app.modules.attendance.service import AttendanceService

router = APIRouter()

async def get_current_employee(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Employee:
    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await db.execute(stmt)
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
    if not employee.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee profile is inactive")
    return employee

async def get_optional_employee(current_user: User, db: AsyncSession) -> Optional[Employee]:
    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().first()

@router.post("/check-in", status_code=status.HTTP_201_CREATED)
async def check_in(
    data: CheckInRequest,
    employee: Employee = Depends(get_current_employee),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = await AttendanceService.check_in(db, employee.id, current_user.id, data)
    res = {
        "status": "success",
        "record_id": record.id,
        "record": {
            "id": record.id,
            "employee_id": record.employee_id,
            "site_id": record.site_id,
            "date": record.date,
            "check_in_time": record.check_in_time,
            "status": record.status,
            "is_within_geofence": record.is_within_geofence,
        }
    }
    if not record.is_within_geofence:
        res["warning"] = "Supervisor override is required: Check-in outside permitted geofence"
    return res

@router.post("/check-out", status_code=status.HTTP_200_OK)
async def check_out(
    data: CheckOutRequest,
    employee: Employee = Depends(get_current_employee),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = await AttendanceService.check_out(db, employee.id, current_user.id, data)
    res = {"status": "success", "record_id": record.id}
    if getattr(record, "requires_confirmation", False):
        res["requires_confirmation"] = True
        res["warning"] = getattr(record, "warning", None)
    return res

@router.get("", status_code=status.HTTP_200_OK)
async def list_attendance(
    employee_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    emp = await get_optional_employee(current_user, db)
    
    supervisor_emp_id = None
    is_admin = False
    
    if current_user.role == "employee":
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
        if employee_id is not None and employee_id != emp.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other employee records")
        employee_id = emp.id
    elif current_user.role == "supervisor":
        if not emp:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor profile not found")
        supervisor_emp_id = emp.id
    elif current_user.role == "administrator":
        is_admin = True

    items, total = await AttendanceService.list_attendance(
        db, employee_id=employee_id, supervisor_emp_id=supervisor_emp_id, is_admin=is_admin, skip=skip, limit=limit
    )
    
    result_list = []
    for item in items:
        result_list.append({
            "id": item.id,
            "employee_id": item.employee_id,
            "employee_name": getattr(item, "employee_name", None),
            "site_id": item.site_id,
            "site_name": getattr(item, "site_name", None),
            "date": item.date,
            "check_in_time": item.check_in_time,
            "check_out_time": item.check_out_time,
            "status": item.status,
            "working_hours": item.working_hours,
            "is_within_geofence": item.is_within_geofence
        })
        
    return {
        "data": result_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_attendance(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.models.operations import AttendanceRecord
    stmt = select(AttendanceRecord).where(AttendanceRecord.id == id)
    result = await db.execute(stmt)
    record = result.scalars().first()
    
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    emp = await get_optional_employee(current_user, db)

    if current_user.role == "employee":
        if not emp or record.employee_id != emp.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other employee records")
    elif current_user.role == "supervisor":
        if not emp:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor profile not found")
        is_auth = await AttendanceService.is_supervisor_authorized(db, emp.id, record.employee_id)
        if not is_auth:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other employee records")

    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "site_id": record.site_id,
        "date": record.date,
        "check_in_time": record.check_in_time,
        "check_out_time": record.check_out_time,
        "status": record.status,
        "working_hours": record.working_hours,
        "is_within_geofence": record.is_within_geofence
    }

@router.post("/{id}/override", status_code=status.HTTP_200_OK)
async def override_attendance(
    id: uuid.UUID,
    data: OverrideRequest,
    supervisor_user: User = Depends(require_role(["supervisor", "administrator"])),
    db: AsyncSession = Depends(get_db)
):
    if supervisor_user.role == "administrator":
        # Admins might not have an employee profile, or might bypass check
        # But wait, override_geofence requires supervisor_emp_id
        # Let's see if admin has employee
        emp = await get_optional_employee(supervisor_user, db)
        supervisor_emp_id = emp.id if emp else supervisor_user.id 
        # actually if it's admin, they should bypass authorization. I should fix service.py override_geofence to allow admin.
    else:
        emp = await get_optional_employee(supervisor_user, db)
        if not emp:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor profile not found")
        supervisor_emp_id = emp.id

    # Wait, in the user instruction: "Only an authorized supervisor/admin role can perform the override."
    record = await AttendanceService.override_geofence(
        db, id, supervisor_user.id, supervisor_emp_id, data, is_admin=(supervisor_user.role == "administrator")
    )
    return {"status": "success", "record_id": record.id}

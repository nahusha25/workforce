import uuid
from datetime import date
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.auth import User
from app.models.workforce import Employee
from app.modules.verification.schemas import (
    EmployeeDayDetailResponse,
    VerificationActionRequest,
    VerificationActionResponse,
    VerificationSummaryResponse,
)
from app.modules.verification.service import VerificationService

router = APIRouter()


async def get_supervisor_context(
    current_user: User = Depends(require_role(["supervisor", "administrator", "director"])),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, Optional[Employee], bool]:
    """Retrieve supervisor user and employee profile, setting is_admin flag for privileged roles."""
    is_admin = current_user.role in ("administrator", "director")

    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await db.execute(stmt)
    employee = result.scalars().first()

    if not is_admin:
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisor employee profile not found",
            )
        if not employee.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisor employee profile is inactive",
            )

    return current_user, employee, is_admin


@router.get("/summary", response_model=VerificationSummaryResponse, status_code=status.HTTP_200_OK)
async def get_verification_summary(
    review_date: date = Query(..., alias="date", description="Target date for verification summary (YYYY-MM-DD)"),
    site_id: Optional[uuid.UUID] = Query(None, description="Optional site filter"),
    sup_ctx: Tuple[User, Optional[Employee], bool] = Depends(get_supervisor_context),
    db: AsyncSession = Depends(get_db),
) -> VerificationSummaryResponse:
    """VER-001: Retrieve list of employees with submitted attendance, work, and materials for EOD verification."""
    current_user, employee, is_admin = sup_ctx
    supervisor_emp_id = employee.id if employee else None

    return await VerificationService.get_eod_summary(
        session=db,
        supervisor_emp_id=supervisor_emp_id,
        review_date=review_date,
        site_id=site_id,
        is_admin=is_admin,
    )


@router.get("/summary/{employee_id}", response_model=EmployeeDayDetailResponse, status_code=status.HTTP_200_OK)
async def get_employee_day_detail(
    employee_id: uuid.UUID,
    review_date: date = Query(..., alias="date", description="Target review date (YYYY-MM-DD)"),
    sup_ctx: Tuple[User, Optional[Employee], bool] = Depends(get_supervisor_context),
    db: AsyncSession = Depends(get_db),
) -> EmployeeDayDetailResponse:
    """VER-002: Retrieve full consolidated day detail (attendance, work entries, photos, materials) for an employee."""
    current_user, employee, is_admin = sup_ctx
    supervisor_emp_id = employee.id if employee else None

    return await VerificationService.get_employee_detail(
        session=db,
        supervisor_emp_id=supervisor_emp_id,
        employee_id=employee_id,
        review_date=review_date,
        is_admin=is_admin,
    )


@router.post("/{id}/approve", response_model=VerificationActionResponse, status_code=status.HTTP_200_OK)
async def approve_entity(
    id: uuid.UUID,
    data: VerificationActionRequest,
    sup_ctx: Tuple[User, Optional[Employee], bool] = Depends(get_supervisor_context),
    db: AsyncSession = Depends(get_db),
) -> VerificationActionResponse:
    """VER-003: Approve an attendance record, daily work entry, or material transaction with idempotency protection."""
    current_user, employee, is_admin = sup_ctx
    supervisor_emp_id = employee.id if employee else None

    vr, target_status, is_replay = await VerificationService.verify_entity(
        session=db,
        entity_type=data.entity_type,
        entity_id=id,
        action="approved",
        idempotency_key=data.idempotency_key,
        supervisor_user_id=current_user.id,
        supervisor_emp_id=supervisor_emp_id,
        remarks=data.remarks,
        is_admin=is_admin,
    )

    return VerificationActionResponse(
        id=vr.id,
        verification_record_id=vr.id,
        idempotency_key=vr.idempotency_key,
        target_id=id,
        entity_type=data.entity_type,
        action="approved",
        status=target_status,
        target_status=target_status,
        remarks=vr.remarks,
        verified_by=vr.verified_by,
        verified_at=vr.verified_at,
        is_replay=is_replay,
    )


@router.post("/{id}/reject", response_model=VerificationActionResponse, status_code=status.HTTP_200_OK)
async def reject_entity(
    id: uuid.UUID,
    data: VerificationActionRequest,
    sup_ctx: Tuple[User, Optional[Employee], bool] = Depends(get_supervisor_context),
    db: AsyncSession = Depends(get_db),
) -> VerificationActionResponse:
    """VER-004: Reject an attendance record, daily work entry, or material transaction with mandatory remarks."""
    current_user, employee, is_admin = sup_ctx
    supervisor_emp_id = employee.id if employee else None

    vr, target_status, is_replay = await VerificationService.verify_entity(
        session=db,
        entity_type=data.entity_type,
        entity_id=id,
        action="rejected",
        idempotency_key=data.idempotency_key,
        supervisor_user_id=current_user.id,
        supervisor_emp_id=supervisor_emp_id,
        remarks=data.remarks,
        is_admin=is_admin,
    )

    return VerificationActionResponse(
        id=vr.id,
        verification_record_id=vr.id,
        idempotency_key=vr.idempotency_key,
        target_id=id,
        entity_type=data.entity_type,
        action="rejected",
        status=target_status,
        target_status=target_status,
        remarks=vr.remarks,
        verified_by=vr.verified_by,
        verified_at=vr.verified_at,
        is_replay=is_replay,
    )


@router.post("/{id}/return", response_model=VerificationActionResponse, status_code=status.HTTP_200_OK)
async def return_entity(
    id: uuid.UUID,
    data: VerificationActionRequest,
    sup_ctx: Tuple[User, Optional[Employee], bool] = Depends(get_supervisor_context),
    db: AsyncSession = Depends(get_db),
) -> VerificationActionResponse:
    """VER-005: Return an entity for correction (or admin reopen) with mandatory remarks."""
    current_user, employee, is_admin = sup_ctx
    supervisor_emp_id = employee.id if employee else None

    vr, target_status, is_replay = await VerificationService.verify_entity(
        session=db,
        entity_type=data.entity_type,
        entity_id=id,
        action="correction_required",
        idempotency_key=data.idempotency_key,
        supervisor_user_id=current_user.id,
        supervisor_emp_id=supervisor_emp_id,
        remarks=data.remarks,
        is_admin=is_admin,
    )

    return VerificationActionResponse(
        id=vr.id,
        verification_record_id=vr.id,
        idempotency_key=vr.idempotency_key,
        target_id=id,
        entity_type=data.entity_type,
        action="correction_required",
        status=target_status,
        target_status=target_status,
        remarks=vr.remarks,
        verified_by=vr.verified_by,
        verified_at=vr.verified_at,
        is_replay=is_replay,
    )

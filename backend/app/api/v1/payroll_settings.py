from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.payroll_settings.schemas import (
    PayrollOvertimeSettingsCreateRequest,
    PayrollOvertimeSettingsResponse,
)
from app.modules.payroll_settings.service import PayrollOvertimeSettingsService

router = APIRouter()


@router.get(
    "",
    response_model=List[PayrollOvertimeSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get overtime settings timeline history",
)
async def get_overtime_settings_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await PayrollOvertimeSettingsService.get_settings_history(session=db)


@router.get(
    "/effective",
    response_model=PayrollOvertimeSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get overtime setting effective on a specific date",
)
async def get_effective_overtime_setting(
    target_date: Optional[date] = Query(None, alias="date", description="Target calendar date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await PayrollOvertimeSettingsService.get_effective_setting(
        session=db,
        target_date=target_date,
    )


@router.post(
    "",
    response_model=PayrollOvertimeSettingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new effective-dated overtime setting",
)
async def create_overtime_setting(
    request: PayrollOvertimeSettingsCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["administrator"])),
):
    return await PayrollOvertimeSettingsService.create_overtime_setting(
        session=db,
        request=request,
        admin_user=current_user,
    )

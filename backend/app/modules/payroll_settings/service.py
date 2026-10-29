from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.payroll_settings import PayrollOvertimeSettings
from app.models.system import AuditLog
from app.modules.payroll_settings.schemas import (
    PayrollOvertimeSettingsCreateRequest,
    PayrollOvertimeSettingsResponse,
)


class PayrollOvertimeSettingsService:
    @staticmethod
    async def get_settings_history(
        session: AsyncSession,
    ) -> List[PayrollOvertimeSettingsResponse]:
        """
        Retrieves complete overtime configuration timeline ordered from latest to earliest.
        """
        stmt = select(PayrollOvertimeSettings).order_by(
            PayrollOvertimeSettings.effective_from.desc()
        )
        res = await session.execute(stmt)
        settings = res.scalars().all()
        return [PayrollOvertimeSettingsResponse.model_validate(s) for s in settings]

    @staticmethod
    async def get_effective_setting(
        session: AsyncSession,
        target_date: Optional[date] = None,
    ) -> PayrollOvertimeSettingsResponse:
        """
        Retrieves the overtime configuration active on the specified date (or today if omitted).
        """
        lookup_date = target_date or date.today()

        stmt = (
            select(PayrollOvertimeSettings)
            .where(
                PayrollOvertimeSettings.effective_from <= lookup_date,
                or_(
                    PayrollOvertimeSettings.effective_to.is_(None),
                    PayrollOvertimeSettings.effective_to >= lookup_date,
                ),
            )
            .order_by(PayrollOvertimeSettings.effective_from.desc())
        )
        res = await session.execute(stmt)
        setting = res.scalars().first()

        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No overtime setting found effective on {lookup_date}",
            )

        return PayrollOvertimeSettingsResponse.model_validate(setting)

    @staticmethod
    async def create_overtime_setting(
        session: AsyncSession,
        request: PayrollOvertimeSettingsCreateRequest,
        admin_user: User,
    ) -> PayrollOvertimeSettingsResponse:
        """
        Atomically creates a new effective-dated overtime configuration, closes the previous
        open-ended setting on the day prior to effective_from, and writes an AuditLog entry.
        Never alters historical setting start dates or multipliers.
        """
        try:
            # 1. Fetch existing settings ordered chronologically
            stmt = select(PayrollOvertimeSettings).order_by(
                PayrollOvertimeSettings.effective_from.asc()
            )
            res = await session.execute(stmt)
            existing_settings = list(res.scalars().all())

            latest_open_setting: Optional[PayrollOvertimeSettings] = None

            if existing_settings:
                open_settings = [s for s in existing_settings if s.effective_to is None]

                if open_settings:
                    # There should only ever be at most one open setting
                    latest_open_setting = open_settings[-1]

                    # Validate that new effective date is strictly after current open setting start
                    if request.effective_from <= latest_open_setting.effective_from:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"New effective start date ({request.effective_from}) must be strictly after "
                                f"the start date of the current active setting ({latest_open_setting.effective_from}). "
                                "Backdated or duplicate start dates are not allowed."
                            ),
                        )

                    # Ensure no historical setting overlaps or exists on or after request.effective_from
                    conflicting = [
                        s for s in existing_settings
                        if s.id != latest_open_setting.id and s.effective_from >= request.effective_from
                    ]
                    if conflicting:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"A setting already exists on or after {request.effective_from}.",
                        )

                    # Close previous open setting on the day before the new start date
                    previous_effective_to = request.effective_from - timedelta(days=1)
                    latest_open_setting.effective_to = previous_effective_to
                    session.add(latest_open_setting)
                else:
                    # All existing settings have effective_to; ensure new start date is after max effective_to
                    max_effective_to = max(s.effective_to for s in existing_settings if s.effective_to)
                    if request.effective_from <= max_effective_to:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"New effective start date ({request.effective_from}) conflicts with existing closed setting range up to {max_effective_to}.",
                        )

            # 2. Instantiate new open-ended setting
            new_setting = PayrollOvertimeSettings(
                id=uuid.uuid4(),
                standard_workday_hours=request.standard_workday_hours,
                overtime_multiplier=request.overtime_multiplier,
                effective_from=request.effective_from,
                effective_to=None,
                description=request.description,
                created_by=admin_user.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(new_setting)
            await session.flush()

            # 3. Create AuditLog entry in the same transaction
            prev_values = None
            if latest_open_setting:
                prev_values = {
                    "id": str(latest_open_setting.id),
                    "standard_workday_hours": str(latest_open_setting.standard_workday_hours),
                    "overtime_multiplier": str(latest_open_setting.overtime_multiplier),
                    "effective_from": str(latest_open_setting.effective_from),
                    "effective_to": str(latest_open_setting.effective_to),
                    "description": latest_open_setting.description,
                }

            audit_log = AuditLog(
                id=uuid.uuid4(),
                entity_type="payroll_overtime_settings",
                entity_id=new_setting.id,
                action="create_overtime_setting",
                changed_by=admin_user.id,
                created_at=new_setting.created_at,
                previous_values=prev_values,
                new_values={
                    "id": str(new_setting.id),
                    "standard_workday_hours": str(new_setting.standard_workday_hours),
                    "overtime_multiplier": str(new_setting.overtime_multiplier),
                    "effective_from": str(new_setting.effective_from),
                    "effective_to": None,
                    "description": new_setting.description,
                },
            )
            session.add(audit_log)

            # 4. Commit atomic transaction
            await session.commit()
            await session.refresh(new_setting)

            return PayrollOvertimeSettingsResponse.model_validate(new_setting)

        except HTTPException:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise

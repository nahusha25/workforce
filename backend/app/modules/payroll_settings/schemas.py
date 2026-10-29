from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayrollOvertimeSettingsCreateRequest(BaseModel):
    standard_workday_hours: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        le=Decimal("24.00"),
        description="Standard workday threshold in hours (must be > 0 and <= 24)",
    )
    overtime_multiplier: Decimal = Field(
        ...,
        ge=Decimal("1.00"),
        le=Decimal("5.00"),
        description="Overtime pay multiplier (must be between 1.00 and 5.00)",
    )
    effective_from: date = Field(
        ...,
        description="Effective start date (inclusive) for this configuration",
    )
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional administrative justification or policy note",
    )

    @field_validator("standard_workday_hours", mode="after")
    @classmethod
    def validate_standard_hours(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("overtime_multiplier", mode="after")
    @classmethod
    def validate_multiplier(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("description", mode="after")
    @classmethod
    def clean_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class PayrollOvertimeSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    standard_workday_hours: Decimal
    overtime_multiplier: Decimal
    effective_from: date
    effective_to: Optional[date] = None
    description: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

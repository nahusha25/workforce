from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RateBandSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rate_type: str
    rate_amount: Decimal
    rate_effective_from: date
    rate_effective_to: Optional[date] = None
    approved_days: Decimal
    approved_quantity: Decimal
    gross_amount: Decimal


class EmployeePaymentLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    source_attendance_id: Optional[uuid.UUID] = None
    source_daily_work_entry_id: Optional[uuid.UUID] = None
    source_date: date
    rate_type: str
    rate_amount: Decimal
    rate_effective_from: date
    rate_effective_to: Optional[date] = None
    days: Decimal
    quantity: Decimal
    regular_hours: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = Decimal("0.00")
    standard_day_hours: Optional[Decimal] = None
    hourly_equivalent_rate: Optional[Decimal] = None
    overtime_multiplier: Optional[Decimal] = None
    regular_amount: Optional[Decimal] = None
    overtime_amount: Optional[Decimal] = Decimal("0.00")
    amount: Decimal
    is_active: bool
    created_at: datetime


class EmployeePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_number: str
    idempotency_key: str
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    period_start: date
    period_end: date
    status: str
    total_amount: Decimal
    total_regular_amount: Decimal = Decimal("0.00")
    total_overtime_hours: Decimal = Decimal("0.00")
    total_overtime_amount: Decimal = Decimal("0.00")
    total_days: Decimal
    total_quantity: Decimal
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    paid_by: Optional[uuid.UUID] = None
    paid_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmployeePaymentDetailResponse(EmployeePaymentResponse):
    lines: List[EmployeePaymentLineResponse] = []
    rate_band_summaries: List[RateBandSummaryResponse] = []


class EmployeePaymentPreviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: uuid.UUID
    employee_name: str
    period_start: date
    period_end: date
    rate_band_summaries: List[RateBandSummaryResponse]
    total_days: Decimal
    total_quantity: Decimal
    total_regular_amount: Decimal = Decimal("0.00")
    total_overtime_hours: Decimal = Decimal("0.00")
    total_overtime_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    eligible_attendance_count: int
    eligible_work_entry_count: int


class EmployeePaymentPreviewResponse(BaseModel):
    period_start: date
    period_end: date
    total_employees: int
    grand_total_regular_amount: Decimal = Decimal("0.00")
    grand_total_overtime_hours: Decimal = Decimal("0.00")
    grand_total_overtime_amount: Decimal = Decimal("0.00")
    grand_total_amount: Decimal
    items: List[EmployeePaymentPreviewItem]


class GeneratePaymentRequest(BaseModel):
    period_start: date
    period_end: date
    idempotency_key: str = Field(..., min_length=1, max_length=100, description="Unique key to prevent duplicate runs")
    employee_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be greater than or equal to period_start")
        return self


class PayPaymentRequest(BaseModel):
    payment_date: Optional[date] = None
    payment_method: str = Field(..., min_length=1, max_length=50, description="e.g. bank_transfer, cash, upi, cheque")
    reference_number: Optional[str] = Field(None, max_length=100, description="Transaction ref or check number")
    remarks: Optional[str] = None


class CancelPaymentRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for cancellation")

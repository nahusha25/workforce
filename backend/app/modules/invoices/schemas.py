from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RateOverrideItem(BaseModel):
    source_id: uuid.UUID = Field(..., description="ID of source DailyWorkEntry to override")
    unit_rate: Decimal = Field(..., ge=0, description="Overridden rate for the line item")
    rate_override_reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for overriding standard rate")


class InvoiceLinePreviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str = Field(..., description="'work' or 'material'")
    source_id: uuid.UUID
    source_date: date
    item_description: str
    quantity: Decimal
    uom: str
    standard_rate: Decimal
    unit_rate: Decimal
    line_amount: Decimal


class InvoicePreviewRequest(BaseModel):
    client_id: uuid.UUID
    project_id: uuid.UUID
    site_id: uuid.UUID
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be greater than or equal to period_start")
        return self


class InvoicePreviewResponse(BaseModel):
    client_id: uuid.UUID
    client_name: str
    project_id: uuid.UUID
    project_name: str
    site_id: uuid.UUID
    site_name: str
    period_start: date
    period_end: date
    billable_work_count: int
    billable_material_count: int
    subtotal_work: Decimal
    subtotal_material: Decimal
    estimated_tax: Decimal
    estimated_total: Decimal
    items: List[InvoiceLinePreviewItem]


class GenerateInvoiceRequest(BaseModel):
    client_id: uuid.UUID
    project_id: uuid.UUID
    site_id: uuid.UUID
    period_start: date
    period_end: date
    idempotency_key: str = Field(..., min_length=1, max_length=100, description="Unique replay prevention key")
    client_po_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    remarks: Optional[str] = None
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="Optional manual tax amount (defaults to 0.00)")
    rate_overrides: Optional[List[RateOverrideItem]] = Field(default=None, description="Optional Director rate overrides for work entries")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be greater than or equal to period_start")
        return self


class UpdateDraftInvoiceRequest(BaseModel):
    client_po_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    remarks: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    due_date: Optional[date] = None
    rate_overrides: Optional[List[RateOverrideItem]] = None


class IssueInvoiceRequest(BaseModel):
    issue_date: Optional[date] = None
    due_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValueError("due_date must be greater than or equal to issue_date")
        return self


class CancelInvoiceRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for cancellation")


class InvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    line_type: str
    source_daily_work_entry_id: Optional[uuid.UUID] = None
    source_material_transaction_id: Optional[uuid.UUID] = None
    source_date: date
    item_description: str
    quantity: Decimal
    uom: str
    standard_rate: Decimal
    unit_rate: Decimal
    line_amount: Decimal
    rate_override_reason: Optional[str] = None
    is_active: bool
    created_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    idempotency_key: str
    client_id: uuid.UUID
    client_name: Optional[str] = None
    project_id: uuid.UUID
    project_name: Optional[str] = None
    site_id: uuid.UUID
    site_name: Optional[str] = None
    period_start: date
    period_end: date
    status: str
    subtotal_work: Decimal
    subtotal_material: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    client_po_number: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    issued_by: Optional[uuid.UUID] = None
    issued_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InvoiceDetailResponse(InvoiceResponse):
    lines: List[InvoiceLineItemResponse] = []

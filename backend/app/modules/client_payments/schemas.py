from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PaymentMethodType = Literal["neft", "rtgs", "imps", "upi", "cheque", "cash", "other"]
PaymentStatusType = Literal["recorded", "voided"]

ALLOWED_PAYMENT_METHODS = {"neft", "rtgs", "imps", "upi", "cheque", "cash", "other"}


class RecordPaymentRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=100, description="Client-provided idempotency key")
    invoice_id: uuid.UUID = Field(..., description="ID of the issued invoice")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Payment amount in INR (must be > 0)")
    payment_date: date = Field(..., description="Date payment was received (cannot be in future)")
    payment_method: PaymentMethodType = Field(..., description="Payment channel: neft, rtgs, imps, upi, cheque, cash, other")
    reference_number: Optional[str] = Field(None, max_length=100, description="UTR, cheque number, or transaction reference")
    notes: Optional[str] = Field(None, description="Internal notes regarding payment")
    receipt_url: Optional[str] = Field(None, max_length=500, description="Attachment URL of deposit slip/receipt")

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("idempotency_key cannot be empty or whitespace only")
        return s

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method: {v}. Must be one of {sorted(ALLOWED_PAYMENT_METHODS)}")
        return s


class VoidPaymentRequest(BaseModel):
    void_idempotency_key: str = Field(..., min_length=1, max_length=100, description="Client-provided void idempotency key")
    void_reason: str = Field(..., description="Mandatory audit explanation for voiding payment (min 10 trimmed characters)")

    @field_validator("void_idempotency_key")
    @classmethod
    def validate_void_idempotency_key(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("void_idempotency_key cannot be empty or whitespace only")
        return s

    @field_validator("void_reason")
    @classmethod
    def validate_void_reason(cls, v: str) -> str:
        s = v.strip() if v else ""
        if len(s) < 10:
            raise ValueError("void_reason must contain at least 10 non-whitespace characters")
        return s


class ClientPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_number: str
    idempotency_key: str
    invoice_id: uuid.UUID
    amount: Decimal
    payment_date: date
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_storage_ref: Optional[str] = None
    status: str
    recorded_by: Optional[uuid.UUID] = None
    recorded_by_name: Optional[str] = None
    voided_by: Optional[uuid.UUID] = None
    voided_by_name: Optional[str] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    void_idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="wrap")
    @classmethod
    def resolve_receipt_fields(cls, data: Any, handler) -> ClientPaymentResponse:
        if isinstance(data, cls):
            return data
        validated = handler(data)
        raw_storage_ref = (
            getattr(data, "receipt_storage_ref", None)
            if not isinstance(data, dict)
            else data.get("receipt_storage_ref")
        )
        raw_receipt_url = (
            getattr(data, "receipt_url", None)
            if not isinstance(data, dict)
            else data.get("receipt_url")
        )
        raw_ref = raw_storage_ref or raw_receipt_url
        if raw_ref:
            validated.receipt_storage_ref = raw_ref
            if not raw_ref.startswith("http://") and not raw_ref.startswith("https://"):
                validated.receipt_url = f"/api/v1/client-payments/{validated.id}/receipt"
        else:
            validated.receipt_url = None
            validated.receipt_storage_ref = None
        return validated


class InvoicePaymentsSummaryResponse(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    invoice_status: str
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    payments_count: int
    payments: List[ClientPaymentResponse]

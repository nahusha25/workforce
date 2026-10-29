from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Sequence,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.invoices import Invoice

client_payment_number_seq = Sequence("client_payment_number_seq", start=1, increment=1, metadata=Base.metadata)


class ClientPayment(Base):
    """
    Financial transaction record capturing funds received against an issued client invoice.
    Maintains single source of truth for paid amounts.
    Audit rules:
      - strictly immutable once recorded
      - soft-voidable with mandatory void reason, voided_by, voided_at, and void_idempotency_key
    """
    __tablename__ = "client_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="recorded", server_default="recorded")

    recorded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    voided_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    void_idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_client_payments_amount"),
        CheckConstraint("status IN ('recorded', 'voided')", name="check_client_payments_status"),
        CheckConstraint(
            "payment_method IN ('neft', 'rtgs', 'imps', 'upi', 'cheque', 'cash', 'other')",
            name="check_client_payments_method",
        ),
        CheckConstraint(
            "(status = 'recorded' AND voided_by IS NULL AND voided_at IS NULL AND void_reason IS NULL AND void_idempotency_key IS NULL) "
            "OR (status = 'voided' AND voided_by IS NOT NULL AND voided_at IS NOT NULL AND void_reason IS NOT NULL AND length(trim(void_reason)) >= 10 AND void_idempotency_key IS NOT NULL)",
            name="check_client_payments_void_integrity",
        ),
        Index("ix_client_payments_invoice_status", "invoice_id", "status"),
    )

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")
    recorded_by_user = relationship("User", foreign_keys=[recorded_by])
    voided_by_user = relationship("User", foreign_keys=[voided_by])

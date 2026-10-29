from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.models.client_payments import ClientPayment

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Sequence,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

invoice_number_seq = Sequence("invoice_number_seq", metadata=Base.metadata)


class Invoice(Base):
    """
    Header record representing an invoice issued to a client for a project/site over a billing period.
    Lifecycle: draft -> approved -> issued -> partially_paid / paid (or cancelled).
    Rates, quantities, descriptions, and amounts become permanently immutable upon transition to 'issued'.
    """
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft", index=True)

    subtotal_work: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    subtotal_material: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")

    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    client_po_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    remarks: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    issued_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'issued', 'partially_paid', 'paid', 'cancelled')",
            name="check_invoices_status",
        ),
        CheckConstraint("period_end >= period_start", name="check_invoices_period_dates"),
        CheckConstraint("subtotal_work >= 0", name="check_invoices_subtotal_work"),
        CheckConstraint("subtotal_material >= 0", name="check_invoices_subtotal_material"),
        CheckConstraint("tax_amount >= 0", name="check_invoices_tax_amount"),
        CheckConstraint("total_amount >= 0", name="check_invoices_total_amount"),
        CheckConstraint("paid_amount >= 0", name="check_invoices_paid_amount"),
        CheckConstraint(
            "due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date",
            name="check_invoices_due_date",
        ),
        Index("ix_invoices_period_dates", "period_start", "period_end"),
    )

    client = relationship("Client")
    project = relationship("Project")
    site = relationship("Site")
    created_by_user = relationship("User", foreign_keys=[created_by])
    issued_by_user = relationship("User", foreign_keys=[issued_by])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])

    lines: Mapped[List[InvoiceLineItem]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.source_date.asc()",
    )
    payments: Mapped[List[ClientPayment]] = relationship(
        "ClientPayment",
        back_populates="invoice",
        order_by="ClientPayment.payment_date.desc()",
    )


class InvoiceLineItem(Base):
    """
    Itemized detail record linking an approved daily work entry or approved material transaction to an invoice.
    Maintains concurrency lock and double-billing prevention via PostgreSQL partial unique indexes.
    Cancelled invoices retain lines with is_active = FALSE.
    """
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_daily_work_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_work_entries.id", ondelete="SET NULL"), nullable=True
    )
    source_material_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_transactions.id", ondelete="SET NULL"), nullable=True
    )
    source_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    uom: Mapped[str] = mapped_column(String(50), nullable=False)
    standard_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rate_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("line_type IN ('work', 'material')", name="check_invoice_lines_line_type"),
        CheckConstraint(
            "(line_type = 'work' AND source_daily_work_entry_id IS NOT NULL AND source_material_transaction_id IS NULL) OR "
            "(line_type = 'material' AND source_material_transaction_id IS NOT NULL AND source_daily_work_entry_id IS NULL)",
            name="check_invoice_lines_exactly_one_source",
        ),
        CheckConstraint("quantity > 0", name="check_invoice_lines_quantity"),
        CheckConstraint("standard_rate >= 0", name="check_invoice_lines_standard_rate"),
        CheckConstraint("unit_rate >= 0", name="check_invoice_lines_unit_rate"),
        CheckConstraint("line_amount >= 0", name="check_invoice_lines_line_amount"),
        Index(
            "uq_active_invoice_work_entry",
            "source_daily_work_entry_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND source_daily_work_entry_id IS NOT NULL"),
        ),
        Index(
            "uq_active_invoice_material",
            "source_material_transaction_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND source_material_transaction_id IS NOT NULL"),
        ),
    )

    invoice = relationship("Invoice", back_populates="lines")
    source_daily_work_entry = relationship("DailyWorkEntry")
    source_material_transaction = relationship("MaterialTransaction")

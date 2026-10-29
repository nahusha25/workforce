from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.payroll_settings import PayrollOvertimeSettings


class EmployeePayment(Base):
    """
    Header record representing an employee's payment statement for a given period.
    Lifecycle: draft -> approved -> paid (with cancelled).
    Gross pay only; rate is snapshotted from effective EmployeeRateHistory.
    """
    __tablename__ = "employee_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)

    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_regular_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    total_overtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    total_overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    total_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("0.00"))
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'paid', 'cancelled')", name="check_employee_payments_status"),
        CheckConstraint("period_end >= period_start", name="check_employee_payments_period_dates"),
    )

    employee = relationship("Employee")
    lines: Mapped[List[EmployeePaymentLine]] = relationship(
        "EmployeePaymentLine",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="EmployeePaymentLine.source_date.asc()",
    )


class EmployeePaymentLine(Base):
    """
    Itemized detail record linking an approved attendance or daily work record to an employee payment.
    Snapshots the exact rate and rate band active on the source record date.
    Maintains concurrency lock and double-payment prevention via PostgreSQL partial unique indexes.
    """
    __tablename__ = "employee_payment_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_attendance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_records.id", ondelete="SET NULL"), nullable=True
    )
    source_daily_work_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_work_entries.id", ondelete="SET NULL"), nullable=True
    )
    source_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rate_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rate_effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    rate_effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("0.00"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    regular_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    overtime_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True, default=Decimal("0.00"), server_default="0.00")
    standard_day_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    hourly_equivalent_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    overtime_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    regular_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    overtime_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True, default=Decimal("0.00"), server_default="0.00")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("rate_type IN ('daily', 'weekly', 'piece', 'monthly')", name="check_payment_lines_rate_type"),
        CheckConstraint(
            "(source_attendance_id IS NOT NULL AND source_daily_work_entry_id IS NULL) OR "
            "(source_attendance_id IS NULL AND source_daily_work_entry_id IS NOT NULL)",
            name="check_payment_lines_exactly_one_source",
        ),
        Index(
            "uq_active_payment_attendance",
            "source_attendance_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND source_attendance_id IS NOT NULL"),
        ),
        Index(
            "uq_active_payment_work_entry",
            "source_daily_work_entry_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND source_daily_work_entry_id IS NOT NULL"),
        ),
    )

    payment = relationship("EmployeePayment", back_populates="lines")
    source_attendance = relationship("AttendanceRecord")
    source_daily_work_entry = relationship("DailyWorkEntry")

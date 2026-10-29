from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PayrollOvertimeSettings(Base):
    """
    Configuration table for effective-dated overtime parameters.
    Administrators configure standard workday threshold and overtime multiplier.
    Historical payroll generation queries settings effective for each attendance date.
    """
    __tablename__ = "payroll_overtime_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_workday_hours: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("7.00"), server_default="7.00"
    )
    overtime_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.50"), server_default="1.50"
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "standard_workday_hours > 0 AND standard_workday_hours <= 24",
            name="check_overtime_standard_hours_valid",
        ),
        CheckConstraint(
            "overtime_multiplier >= 1.0 AND overtime_multiplier <= 5.0",
            name="check_overtime_multiplier_valid",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="check_overtime_effective_dates",
        ),
        Index("ix_payroll_overtime_settings_dates", "effective_from", "effective_to"),
    )

    creator = relationship("User", foreign_keys=[created_by])

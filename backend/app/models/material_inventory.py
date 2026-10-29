from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.operations import Material, MaterialTransaction, Site


class MaterialStock(Base):
    """
    Represents the current stock balance of one consumable material at one client site.
    Enforces non-negative quantity and exactly one balance record per (site_id, material_id).
    """
    __tablename__ = "material_stocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    site: Mapped["Site"] = relationship("Site")
    material: Mapped["Material"] = relationship("Material")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="check_material_stocks_quantity_non_negative"),
        UniqueConstraint("site_id", "material_id", name="uq_material_stocks_site_material"),
    )


class MaterialStockMovement(Base):
    """
    Append-only audit ledger recording every change to site material stock.
    Tracks inward replenishment, consumption, returns, and adjustments.
    Requires positive movement quantity, non-negative balance_after, and unique idempotency key.
    """
    __tablename__ = "material_stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    material_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    site: Mapped["Site"] = relationship("Site")
    material: Mapped["Material"] = relationship("Material")
    material_transaction: Mapped[Optional["MaterialTransaction"]] = relationship("MaterialTransaction")
    actor: Mapped["User"] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('inward', 'consumed', 'returned', 'adjustment')",
            name="check_stock_movement_type",
        ),
        CheckConstraint("quantity > 0", name="check_stock_movement_quantity_positive"),
        CheckConstraint("balance_after >= 0", name="check_stock_movement_balance_after_non_negative"),
        Index("ix_material_stock_movements_site_material", "site_id", "material_id"),
    )

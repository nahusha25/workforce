from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.operations import Site
    from app.models.workforce import Employee

# Forward-only sequence for generating standard asset tags (e.g. AST-000001)
asset_tag_seq = Sequence("asset_tag_seq", start=1, increment=1, metadata=Base.metadata)


class Asset(Base):
    """
    Physical reusable equipment/tool/machinery asset.
    Distinct from consumable materials.
    Tracks location (Central Warehouse vs. Specific Site), condition, status, and lifecycle.
    """
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_tag: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    warranty_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    condition: Mapped[str] = mapped_column(String(30), nullable=False, default="new", server_default="new")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available", server_default="available", index=True)

    # Location architecture:
    # Exactly one central warehouse ('warehouse', current_site_id IS NULL)
    # or allocated to a specific site ('site', current_site_id IS NOT NULL)
    location_type: Mapped[str] = mapped_column(String(20), nullable=False, default="warehouse", server_default="warehouse", index=True)
    current_site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # Custody pointer for employee issue/return (enforced by check_assets_custody_status_consistency)
    current_custodian_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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

    # Relationships
    site: Mapped[Optional[Site]] = relationship("Site", foreign_keys=[current_site_id], lazy="selectin")
    custodian: Mapped[Optional[Employee]] = relationship("Employee", foreign_keys=[current_custodian_id], lazy="selectin")
    transactions: Mapped[List[AssetTransaction]] = relationship(
        "AssetTransaction",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="AssetTransaction.transaction_date.desc(), AssetTransaction.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "condition IN ('new', 'good', 'fair', 'damaged', 'unusable')",
            name="check_assets_condition",
        ),
        CheckConstraint(
            "status IN ('available', 'under_maintenance', 'damaged', 'lost', 'retired', 'issued_employee')",
            name="check_assets_status",
        ),
        CheckConstraint(
            "location_type IN ('warehouse', 'site')",
            name="check_assets_location_type",
        ),
        CheckConstraint(
            "(location_type = 'warehouse' AND current_site_id IS NULL) "
            "OR (location_type = 'site' AND current_site_id IS NOT NULL)",
            name="check_assets_location_consistency",
        ),
        CheckConstraint(
            "(status = 'issued_employee' AND current_custodian_id IS NOT NULL) "
            "OR (status != 'issued_employee' AND current_custodian_id IS NULL)",
            name="check_assets_custody_status_consistency",
        ),
        CheckConstraint(
            "purchase_cost IS NULL OR purchase_cost >= 0",
            name="check_assets_purchase_cost",
        ),
        Index("ix_assets_location_site", "location_type", "current_site_id"),
        Index("ix_assets_status_condition", "status", "condition"),
    )


class AssetTransaction(Base):
    """
    Immutable audit ledger of asset location, custody, status, and condition changes.
    Every lifecycle transition produces an append-only transaction record.
    """
    __tablename__ = "asset_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    from_location_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    to_location_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    from_site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True
    )

    from_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )

    condition_before: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    condition_after: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    asset: Mapped[Asset] = relationship("Asset", back_populates="transactions")
    performer: Mapped[Optional[User]] = relationship("User", foreign_keys=[performed_by], lazy="selectin")
    to_site: Mapped[Optional[Site]] = relationship("Site", foreign_keys=[to_site_id], lazy="selectin")
    from_site: Mapped[Optional[Site]] = relationship("Site", foreign_keys=[from_site_id], lazy="selectin")
    to_employee: Mapped[Optional[Employee]] = relationship("Employee", foreign_keys=[to_employee_id], lazy="selectin")
    from_employee: Mapped[Optional[Employee]] = relationship("Employee", foreign_keys=[from_employee_id], lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('registered', 'reassigned', 'issued', 'returned', 'status_change', 'condition_update', 'maintenance', 'retired')",
            name="check_asset_transactions_type",
        ),
        Index("ix_asset_transactions_asset_date", "asset_id", "transaction_date"),
    )

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StockInwardRequest(BaseModel):
    """Payload for recording stock received at a specific site."""

    site_id: uuid.UUID = Field(..., description="Target site receiving stock")
    material_id: uuid.UUID = Field(..., description="Material received")
    quantity: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Positive decimal quantity received (never float, strictly > 0)",
    )
    remarks: Optional[str] = Field(None, max_length=500, description="Optional remarks or delivery reference")
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique replay-prevention idempotency key",
    )


class StockInwardResponse(BaseModel):
    """Response returned after recording stock inward movement."""

    model_config = ConfigDict(from_attributes=True)

    movement_id: uuid.UUID = Field(..., description="ID of the stock movement ledger entry")
    site_id: uuid.UUID
    material_id: uuid.UUID
    material_name: str
    material_code: Optional[str] = None
    unit_of_measure: str
    movement_type: str = "inward"
    quantity: Decimal
    balance_after: Decimal
    idempotency_key: str
    remarks: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime


class SiteInventoryItemResponse(BaseModel):
    """Inventory balance and details for one material at a site."""

    model_config = ConfigDict(from_attributes=True)

    material_id: uuid.UUID
    material_code: Optional[str] = None
    material_name: str
    unit_of_measure: str
    category: str
    quantity_available: Decimal
    last_movement_at: Optional[datetime] = None
    is_active: bool


class SiteInventoryListResponse(BaseModel):
    """Paginated inventory listing for a site."""

    model_config = ConfigDict(from_attributes=True)

    items: List[SiteInventoryItemResponse]
    total: int
    skip: int
    limit: int
    site_id: uuid.UUID
    site_name: str


class MaterialSiteStockResponse(BaseModel):
    """Current stock balance for a specific site/material pair."""

    model_config = ConfigDict(from_attributes=True)

    site_id: uuid.UUID
    site_name: str
    material_id: uuid.UUID
    material_code: Optional[str] = None
    material_name: str
    unit_of_measure: str
    category: str
    quantity_available: Decimal
    last_movement_at: Optional[datetime] = None
    is_active: bool


class StockMovementItemResponse(BaseModel):
    """Individual stock movement ledger entry with actor and transaction details."""

    model_config = ConfigDict(from_attributes=True)

    movement_id: uuid.UUID
    site_id: uuid.UUID
    material_id: uuid.UUID
    movement_type: str
    quantity: Decimal
    balance_after: Decimal
    material_transaction_id: Optional[uuid.UUID] = None
    idempotency_key: str
    remarks: Optional[str] = None
    created_by: uuid.UUID
    actor_name: Optional[str] = None
    created_at: datetime


class StockMovementHistoryResponse(BaseModel):
    """Paginated stock movement history for a specific site and material."""

    model_config = ConfigDict(from_attributes=True)

    items: List[StockMovementItemResponse]
    total: int
    skip: int
    limit: int
    site_id: uuid.UUID
    material_id: uuid.UUID
    material_name: str
    material_code: Optional[str] = None
    unit_of_measure: str


class InventorySiteResponse(BaseModel):
    """Site item authorized for material inventory tracking."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    project_id: uuid.UUID
    address: Optional[str] = None
    location: Optional[str] = None
    permitted_radius_m: Optional[float] = None
    supervisor_id: Optional[uuid.UUID] = None
    is_active: bool = True



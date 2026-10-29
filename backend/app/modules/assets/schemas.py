from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AssetConditionType = Literal["new", "good", "fair", "damaged", "unusable"]
AssetStatusType = Literal["available", "under_maintenance", "damaged", "lost", "retired", "issued_employee"]
LocationType = Literal["warehouse", "site"]

ALLOWED_CONDITIONS = {"new", "good", "fair", "damaged", "unusable"}
ALLOWED_STATUSES = {"available", "under_maintenance", "damaged", "lost", "retired", "issued_employee"}
ALLOWED_LOCATION_TYPES = {"warehouse", "site"}


class AssetRegisterRequest(BaseModel):
    asset_tag: Optional[str] = Field(
        None,
        max_length=50,
        description="Optional unique identifier/barcode. If omitted or empty, automatically generated (e.g. AST-000001)",
    )
    name: str = Field(..., min_length=1, max_length=200, description="Asset display name or title")
    category: str = Field(..., min_length=1, max_length=100, description="Asset classification category")
    serial_number: Optional[str] = Field(None, max_length=100, description="Manufacturer serial number")
    manufacturer: Optional[str] = Field(None, max_length=100, description="Asset manufacturer or brand")
    model_number: Optional[str] = Field(None, max_length=100, description="Model number or specification code")
    purchase_date: Optional[date] = Field(None, description="Date asset was purchased")
    purchase_cost: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2, description="Purchase cost in INR")
    warranty_expiry_date: Optional[date] = Field(None, description="Warranty expiration date")
    condition: AssetConditionType = Field(default="new", description="Initial physical condition")
    status: AssetStatusType = Field(default="available", description="Initial operational status")
    location_type: LocationType = Field(
        default="warehouse",
        description="Location assignment: 'warehouse' (Central Warehouse) or 'site' (Assigned to Site)",
    )
    current_site_id: Optional[uuid.UUID] = Field(
        None,
        description="Assigned site ID. Required when location_type is 'site'; must be None when location_type is 'warehouse'",
    )
    site_id: Optional[uuid.UUID] = Field(
        None,
        description="Convenience alias for current_site_id",
    )
    description: Optional[str] = Field(None, description="General asset notes or specifications")
    remarks: Optional[str] = Field(None, description="Remarks for registration ledger transaction")
    idempotency_key: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional client idempotency key to prevent duplicate registration",
    )

    @field_validator("asset_tag")
    @classmethod
    def clean_asset_tag(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            return s if s else None
        return None

    @field_validator("name", "category")
    @classmethod
    def non_empty_string(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v: str) -> str:
        if v == "issued_employee":
            raise ValueError(
                "Initial asset registration cannot have status 'issued_employee'. "
                "Assets must be registered in the warehouse or at a site before being issued to employees."
            )
        return v

    @model_validator(mode="after")
    def validate_location_and_dates(self) -> AssetRegisterRequest:
        # Resolve site_id alias
        if self.current_site_id is None and self.site_id is not None:
            self.current_site_id = self.site_id

        # Central warehouse vs site rules
        if self.location_type == "warehouse":
            if self.current_site_id is not None:
                raise ValueError("Central warehouse assets cannot have a site assigned. current_site_id must be None.")
        elif self.location_type == "site":
            if self.current_site_id is None:
                raise ValueError("Assets assigned to a site must specify current_site_id.")

        # Purchase and warranty dates
        if self.purchase_date and self.warranty_expiry_date:
            if self.warranty_expiry_date < self.purchase_date:
                raise ValueError("Warranty expiry date cannot precede purchase date.")

        return self


class AssetIssueRequest(BaseModel):
    employee_id: uuid.UUID = Field(..., description="ID of employee to issue asset to")
    remarks: Optional[str] = Field(None, description="Optional remarks or operational notes")
    idempotency_key: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional client idempotency key to prevent duplicate issue",
    )


class AssetReturnRequest(BaseModel):
    employee_id: uuid.UUID = Field(
        ...,
        description="ID of employee returning the asset (must match current custodian)",
    )
    condition: Optional[AssetConditionType] = Field(
        None,
        description="Physical condition upon return. If omitted, retains current condition.",
    )
    status: Optional[AssetStatusType] = Field(
        None,
        description="Target status after return. If omitted, auto-set to 'damaged' if condition is damaged/unusable, else 'available'.",
    )
    remarks: Optional[str] = Field(None, description="Return inspection remarks")
    idempotency_key: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional client idempotency key to prevent duplicate return",
    )

    @field_validator("status")
    @classmethod
    def validate_return_status(cls, v: Optional[str]) -> Optional[str]:
        if v == "issued_employee":
            raise ValueError("Returned asset cannot remain in 'issued_employee' status.")
        return v


class AssetReassignRequest(BaseModel):
    target_location_type: LocationType = Field(
        ...,
        description="Target location: 'warehouse' (Central Warehouse) or 'site' (Assigned to Site)",
    )
    target_site_id: Optional[uuid.UUID] = Field(
        None,
        description="Target site ID. Required when target_location_type is 'site'; must be None when 'warehouse'",
    )
    site_id: Optional[uuid.UUID] = Field(
        None,
        description="Convenience alias for target_site_id",
    )
    remarks: Optional[str] = Field(None, description="Remarks for reassignment ledger transaction")
    idempotency_key: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional client idempotency key to prevent duplicate reassignment",
    )

    @model_validator(mode="after")
    def validate_target_location(self) -> AssetReassignRequest:
        if self.target_site_id is None and self.site_id is not None:
            self.target_site_id = self.site_id

        if self.target_location_type == "warehouse":
            if self.target_site_id is not None:
                raise ValueError("Target warehouse location cannot specify a site ID.")
        elif self.target_location_type == "site":
            if self.target_site_id is None:
                raise ValueError("Target site location must specify target_site_id.")

        return self


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_tag: str
    name: str
    category: str
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = None
    warranty_expiry_date: Optional[date] = None
    condition: str
    status: str
    location_type: str
    current_site_id: Optional[uuid.UUID] = None
    current_site_name: Optional[str] = None
    current_custodian_id: Optional[uuid.UUID] = None
    current_custodian_name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class AssetTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    transaction_type: str
    from_location_type: Optional[str] = None
    to_location_type: Optional[str] = None
    from_site_id: Optional[uuid.UUID] = None
    to_site_id: Optional[uuid.UUID] = None
    from_site_name: Optional[str] = None
    to_site_name: Optional[str] = None
    from_employee_id: Optional[uuid.UUID] = None
    to_employee_id: Optional[uuid.UUID] = None
    from_employee_name: Optional[str] = None
    to_employee_name: Optional[str] = None
    condition_before: Optional[str] = None
    condition_after: Optional[str] = None
    transaction_date: datetime
    performed_by: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime


class AssetDetailResponse(AssetResponse):
    transactions: List[AssetTransactionResponse] = []


class AssetListResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    skip: int
    limit: int

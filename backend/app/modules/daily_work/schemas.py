import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class DailyWorkEntryCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=100, description="Client-generated unique key to prevent duplicate submissions")
    activity_id: uuid.UUID
    work_order_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(..., ge=0)
    work_date: Optional[date] = None
    remarks: Optional[str] = None

class DailyWorkEntryUpdate(BaseModel):
    activity_id: Optional[uuid.UUID] = None
    work_order_id: Optional[uuid.UUID] = None
    quantity: Optional[Decimal] = Field(default=None, ge=0)
    remarks: Optional[str] = None

class WorkPhotoResponse(BaseModel):
    id: uuid.UUID
    daily_work_entry_id: uuid.UUID
    image_url: str
    thumbnail_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MaterialTransactionResponse(BaseModel):
    id: uuid.UUID
    daily_work_entry_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    site_id: uuid.UUID
    transaction_type: str
    item_name: str
    quantity: Decimal
    amount: Decimal
    bill_image_url: Optional[str] = None
    is_high_value: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DailyWorkEntryResponse(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    attendance_record_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    site_id: uuid.UUID
    site_name: Optional[str] = None
    activity_id: uuid.UUID
    activity_name: Optional[str] = None
    work_order_id: Optional[uuid.UUID] = None
    work_date: date
    quantity: Decimal
    uom: str
    status: str
    remarks: Optional[str] = None
    photos: List[WorkPhotoResponse] = Field(default_factory=list)
    materials: List[MaterialTransactionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DailyWorkEntryListResponse(BaseModel):
    data: List[DailyWorkEntryResponse]
    total: int
    skip: int
    limit: int
    page: Optional[int] = None
    page_size: Optional[int] = None

class MaterialTransactionCreate(BaseModel):
    transaction_type: str = Field(..., pattern="^(consumed|purchased)$")
    item_name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal = Field(..., gt=0)
    amount: Decimal = Field(default=Decimal("0.0"), ge=0)
    material_id: Optional[uuid.UUID] = None
    bill_image_url: Optional[str] = None

class MaterialTransactionUpdate(BaseModel):
    transaction_type: Optional[str] = Field(default=None, pattern="^(consumed|purchased)$")
    item_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    material_id: Optional[uuid.UUID] = None
    bill_image_url: Optional[str] = None

class BillUploadResponse(BaseModel):
    id: uuid.UUID
    bill_image_url: str

    model_config = ConfigDict(from_attributes=True)



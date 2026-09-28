import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

EntityTypeLiteral = Literal["attendance", "daily_work", "material", "material_transaction"]
VerificationActionLiteral = Literal["approved", "rejected", "correction_required"]


class VerificationHistoryEvent(BaseModel):
    """A single entry in an entity's full verification audit trail.

    Populated from verification_records ordered by verified_at ASC.
    verified_by_name resolves via the verifier's Employee record;
    falls back to a role label (e.g. "Administrator") when the
    verifier has no Employee row (admin/director without a field account).
    The raw mobile_id / phone number is never exposed here.
    """

    id: uuid.UUID
    action: str
    remarks: Optional[str] = None
    verified_by: uuid.UUID
    verified_by_name: str
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)




class VerificationActionRequest(BaseModel):
    entity_type: EntityTypeLiteral = Field(
        ..., description="Target entity type: 'attendance', 'daily_work', or 'material'"
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Client-generated unique key to prevent duplicate action processing",
    )
    remarks: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Mandatory remarks for rejection or return (minimum 10 characters)",
    )


class VerificationActionResponse(BaseModel):
    id: uuid.UUID
    verification_record_id: Optional[uuid.UUID] = None
    idempotency_key: str
    target_id: uuid.UUID
    entity_type: str
    action: str
    status: Optional[str] = None
    target_status: str
    remarks: Optional[str] = None
    verified_by: uuid.UUID
    verified_at: datetime
    is_replay: bool = False

    model_config = ConfigDict(from_attributes=True)


class VerificationSummaryItem(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    employee_code: str
    site_id: Optional[uuid.UUID] = None
    site_name: Optional[str] = None
    attendance_record_id: Optional[uuid.UUID] = None
    attendance_status: Optional[str] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    working_hours: Optional[float] = None
    work_entry_count: int = 0
    photo_count: int = 0
    material_count: int = 0
    total_material_cost: Decimal = Decimal("0.00")
    exception_flags: List[str] = []
    has_pending_verification: bool = False

    model_config = ConfigDict(from_attributes=True)


class VerificationSummaryResponse(BaseModel):
    date: date
    site_id: Optional[uuid.UUID] = None
    items: List[VerificationSummaryItem]
    total_employees: int
    pending_verification_count: int


class EmployeeDayAttendanceDetail(BaseModel):
    id: uuid.UUID
    date: date
    session_number: Optional[int] = None
    check_in_time: Optional[datetime] = None
    check_in_distance_m: Optional[float] = None
    check_out_time: Optional[datetime] = None
    check_out_distance_m: Optional[float] = None
    is_within_geofence: Optional[bool] = None
    working_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    status: str
    override_by: Optional[uuid.UUID] = None
    verification_record_id: Optional[uuid.UUID] = None
    verification_action: Optional[str] = None
    verification_remarks: Optional[str] = None
    # Full chronological audit trail (oldest first).
    # Empty list when no verification actions have been taken yet.
    history: List[VerificationHistoryEvent] = []

    model_config = ConfigDict(from_attributes=True)



class EmployeeDayPhotoDetail(BaseModel):
    id: uuid.UUID
    daily_work_entry_id: uuid.UUID
    image_url: str
    thumbnail_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeDayMaterialDetail(BaseModel):
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
    verification_record_id: Optional[uuid.UUID] = None
    verification_action: Optional[str] = None
    verification_remarks: Optional[str] = None
    # Full chronological audit trail.
    history: List[VerificationHistoryEvent] = []

    model_config = ConfigDict(from_attributes=True)



class EmployeeDayWorkEntryDetail(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    activity_id: uuid.UUID
    activity_name: str
    activity_category: Optional[str] = None
    work_order_id: Optional[uuid.UUID] = None
    work_order_number: Optional[str] = None
    work_date: date
    quantity: Decimal
    uom: str
    status: str
    remarks: Optional[str] = None
    verification_record_id: Optional[uuid.UUID] = None
    verification_action: Optional[str] = None
    verification_remarks: Optional[str] = None
    # Full chronological audit trail.
    history: List[VerificationHistoryEvent] = []
    photos: List[EmployeeDayPhotoDetail] = []
    materials: List[EmployeeDayMaterialDetail] = []

    model_config = ConfigDict(from_attributes=True)



class EmployeeDayDetailResponse(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    employee_code: str
    date: date
    site_id: Optional[uuid.UUID] = None
    site_name: Optional[str] = None
    attendance: Optional[EmployeeDayAttendanceDetail] = None
    work_entries: List[EmployeeDayWorkEntryDetail] = []
    exception_flags: List[str] = []
    all_verified: bool = False

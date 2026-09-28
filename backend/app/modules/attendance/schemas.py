from datetime import date, datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

class CheckInRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class CheckOutRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class OverrideRequest(BaseModel):
    override_reason: str = Field(..., min_length=10, max_length=500)

class AttendanceResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    site_id: uuid.UUID
    date: date
    session_number: Optional[int] = None
    check_in_time: Optional[datetime] = None
    check_in_latitude: Optional[float] = None
    check_in_longitude: Optional[float] = None
    check_in_distance_m: Optional[float] = None
    check_out_time: Optional[datetime] = None
    check_out_latitude: Optional[float] = None
    check_out_longitude: Optional[float] = None
    check_out_distance_m: Optional[float] = None
    is_within_geofence: Optional[bool] = None
    working_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    status: str
    override_by: Optional[uuid.UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

class AttendanceListResponse(BaseModel):
    items: List[AttendanceResponse]
    total: int
    page: int
    page_size: int

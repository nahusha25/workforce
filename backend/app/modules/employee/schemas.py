import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    mobile_number: str = Field(..., min_length=8, max_length=20)
    employee_code: str = Field(..., min_length=1, max_length=50)
    system_role: str = Field(default="employee", max_length=50)
    trade_role_ids: list[uuid.UUID] = Field(..., min_length=1)
    rate_type: str = Field(..., max_length=50)
    rate_amount: float = Field(..., ge=0)
    supervisor_id: uuid.UUID | None = None
    site_ids: list[uuid.UUID] = Field(..., min_length=1)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    supervisor_id: uuid.UUID | None = None
    is_active: bool | None = None
    rate_type: str | None = Field(None, max_length=50)
    rate_amount: float | None = Field(None, ge=0)
    trade_role_ids: list[uuid.UUID] | None = None


class SiteAssignmentCreate(BaseModel):
    site_id: uuid.UUID


class RateHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rate_type: str
    rate_amount: float
    effective_from: date
    effective_to: date | None = None


class SiteBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class RoleBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    employee_code: str
    mobile_id: str
    name: str
    system_role: str
    supervisor_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    trade_roles: list[RoleBriefResponse] = []
    current_rate: RateHistoryResponse | None = None
    active_sites: list[SiteBriefResponse] = []

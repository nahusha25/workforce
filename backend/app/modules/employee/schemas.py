import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    mobile_number: str = Field(..., min_length=8, max_length=20)
    employee_code: str = Field(..., min_length=1, max_length=50)
    system_role: str = Field(default="employee", max_length=50)
    classification: str = Field(default="regular", max_length=50)
    trade_role_ids: list[uuid.UUID] = Field(default_factory=list)
    rate_type: str = Field(default="monthly", max_length=50)
    rate_amount: float = Field(..., ge=0)
    supervisor_id: uuid.UUID | None = None
    site_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: str) -> str:
        if v not in ("regular", "contract"):
            raise ValueError("Employee classification must be 'regular' or 'contract'")
        return v

    @field_validator("rate_type")
    @classmethod
    def validate_rate_type(cls, v: str) -> str:
        if v != "monthly":
            raise ValueError("Only monthly pay frequency is supported for employees")
        return v

    @field_validator("trade_role_ids", mode="before")
    @classmethod
    def set_trade_role_ids_default(cls, v):
        if v is None:
            return []
        return v

    @field_validator("site_ids", mode="before")
    @classmethod
    def set_site_ids_default(cls, v):
        if v is None:
            return []
        return v

    @model_validator(mode="after")
    def validate_trade_roles_for_role(self) -> "EmployeeCreate":
        if self.system_role == "employee" and not self.trade_role_ids:
            raise ValueError("Trade / Job Role is mandatory for employee (field worker)")
        return self

    @model_validator(mode="after")
    def validate_site_ids_for_role_and_classification(self) -> "EmployeeCreate":
        if self.classification == "contract" and not self.site_ids:
            raise ValueError("At least one assigned client site or project is mandatory for contract employees")
        if self.system_role in ("employee", "supervisor") and not self.site_ids:
            raise ValueError("At least one assigned client site is mandatory for employee and supervisor roles")
        return self


class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    mobile_number: str | None = Field(None, min_length=8, max_length=20)
    system_role: str | None = Field(None, max_length=50)
    classification: str | None = Field(None, max_length=50)
    supervisor_id: uuid.UUID | None = None
    is_active: bool | None = None
    rate_type: str | None = Field(None, max_length=50)
    rate_amount: float | None = Field(None, ge=0)
    trade_role_ids: list[uuid.UUID] | None = None
    site_ids: list[uuid.UUID] | None = None

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: str | None) -> str | None:
        if v is not None and v not in ("regular", "contract"):
            raise ValueError("Employee classification must be 'regular' or 'contract'")
        return v

    @field_validator("rate_type")
    @classmethod
    def validate_rate_type(cls, v: str | None) -> str | None:
        if v is not None and v != "monthly":
            raise ValueError("Only monthly pay frequency is supported for employees")
        return v

    @model_validator(mode="after")
    def validate_sites_for_role_and_classification(self) -> "EmployeeUpdate":
        if self.classification == "contract" and self.site_ids is not None and not self.site_ids:
            raise ValueError("At least one assigned client site or project is mandatory for contract employees")
        if self.system_role in ("employee", "supervisor") and self.site_ids is not None and not self.site_ids:
            raise ValueError("At least one assigned client site is mandatory for employee and supervisor roles")
        return self


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
    project_id: uuid.UUID | None = None
    project_name: str | None = None


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
    classification: str = "regular"
    supervisor_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    trade_roles: list[RoleBriefResponse] = []
    current_rate: RateHistoryResponse | None = None
    active_sites: list[SiteBriefResponse] = []

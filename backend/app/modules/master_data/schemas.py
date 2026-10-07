from decimal import Decimal
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# Clients
class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    contact_mobile: str | None = Field(None, max_length=20)
    is_active: bool = True

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ClientUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    contact_mobile: str | None = Field(None, max_length=20)
    is_active: bool | None = None

# Projects
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    status: str = Field(..., max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    client_id: uuid.UUID

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    status: str | None = Field(None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    client_id: uuid.UUID | None = None

class ProjectResponse(ProjectBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

# Sites
class SiteBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: str | None = None
    location: str | None = None
    permitted_radius_m: float | None = Field(None, ge=0)
    supervisor_id: uuid.UUID | None = None
    is_active: bool = True
    project_id: uuid.UUID

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    address: str | None = None
    location: str | None = None
    permitted_radius_m: float | None = Field(None, ge=0)
    supervisor_id: uuid.UUID | None = None
    is_active: bool | None = None
    project_id: uuid.UUID | None = None

class SiteResponse(SiteBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

# Roles
class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


# Work Orders
class WorkOrderBase(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=100)
    project_id: uuid.UUID
    site_id: uuid.UUID
    description: str | None = None
    target_quantities: dict | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_basis: str | None = Field(None, pattern="^(per_metre|per_device|lump_sum)$")
    status: str = Field(default="draft", pattern="^(draft|open|in_progress|completed|closed)$")
    is_active: bool = True

class WorkOrderCreate(WorkOrderBase):
    pass

class WorkOrderUpdate(BaseModel):
    order_number: str | None = Field(None, min_length=1, max_length=100)
    project_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    description: str | None = None
    target_quantities: dict | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_basis: str | None = Field(None, pattern="^(per_metre|per_device|lump_sum)$")
    status: str | None = Field(None, pattern="^(draft|open|in_progress|completed|closed)$")
    is_active: bool | None = None

class WorkOrderResponse(WorkOrderBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Activities
class ActivityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    unit_of_measure: str = Field(..., min_length=1, max_length=50)
    approved_rate: Decimal = Field(..., ge=0)
    category: str = Field(..., pattern="^(cable|device|drilling|mounting|testing|commissioning)$")
    is_active: bool = True

class ActivityCreate(ActivityBase):
    pass

class ActivityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    unit_of_measure: str | None = Field(None, min_length=1, max_length=50)
    approved_rate: Decimal | None = Field(None, ge=0)
    category: str | None = Field(None, pattern="^(cable|device|drilling|mounting|testing|commissioning)$")
    is_active: bool | None = None

class ActivityResponse(ActivityBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Materials
class MaterialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    material_code: str | None = Field(None, max_length=50)
    description: str | None = None
    unit_of_measure: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., pattern="^(cable|device|tool|consumable)$")
    purchase_approval_limit: Decimal = Field(..., ge=0)
    is_active: bool = True

class MaterialCreate(MaterialBase):
    pass

class MaterialUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    material_code: str | None = Field(None, max_length=50)
    description: str | None = None
    unit_of_measure: str | None = Field(None, min_length=1, max_length=50)
    category: str | None = Field(None, pattern="^(cable|device|tool|consumable)$")
    purchase_approval_limit: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None

class MaterialResponse(MaterialBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

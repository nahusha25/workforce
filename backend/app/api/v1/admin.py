
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.master_data.repository import MasterDataRepository
from app.modules.master_data.schemas import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    ClientCreate,
    ClientResponse,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    ProjectCreate,
    ProjectResponse,
    RoleResponse,
    SiteCreate,
    SiteResponse,
    WorkOrderCreate,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.modules.master_data.service import MasterDataService

router = APIRouter()

def get_master_data_service(db: AsyncSession = Depends(get_db)) -> MasterDataService:
    repo = MasterDataRepository(db)
    return MasterDataService(repo)

# ADM-001: Create Client
@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_in: ClientCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.create_client(client_in)

# ADM-002: List Clients
@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.get_clients(skip=skip, limit=limit)

@router.delete("/clients/{id}", status_code=status.HTTP_200_OK)
async def delete_client(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    await service.delete_client(id)
    return {"status": "success", "message": "Client deleted successfully"}

# ADM-003: Create Project
@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.create_project(project_in)

# ADM-004: List Projects
@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.get_projects(skip=skip, limit=limit)

@router.delete("/projects/{id}", status_code=status.HTTP_200_OK)
async def delete_project(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    await service.delete_project(id)
    return {"status": "success", "message": "Project deleted successfully"}

# ADM-005: Create Site
@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_in: SiteCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.create_site(site_in)

# ADM-006: List Sites
@router.get("/sites", response_model=list[SiteResponse])
async def list_sites(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    return await service.get_sites(skip=skip, limit=limit)

@router.delete("/sites/{id}", status_code=status.HTTP_200_OK)
async def delete_site(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator"]))
):
    await service.delete_site(id)
    return {"status": "success", "message": "Site deleted successfully"}

# ADM-007: List Roles
@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"]))
):
    return await service.get_roles(skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# Work Orders Admin CRUD (ADM-007 to ADM-010 in Phase 3 Plan)
# ---------------------------------------------------------------------------

@router.post("/work-orders", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
@router.post("/work_orders", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_work_order(
    wo_in: WorkOrderCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.create_work_order(wo_in)


@router.get("/work-orders", response_model=list[WorkOrderResponse])
@router.get("/work_orders", response_model=list[WorkOrderResponse], include_in_schema=False)
async def list_work_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_work_orders(skip=skip, limit=limit)


@router.get("/work-orders/{id}", response_model=WorkOrderResponse)
@router.get("/work_orders/{id}", response_model=WorkOrderResponse, include_in_schema=False)
async def get_work_order(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_work_order(id)


@router.put("/work-orders/{id}", response_model=WorkOrderResponse)
@router.put("/work_orders/{id}", response_model=WorkOrderResponse, include_in_schema=False)
async def update_work_order(
    id: uuid.UUID,
    wo_in: WorkOrderUpdate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.update_work_order(id, wo_in)


# ---------------------------------------------------------------------------
# Activities Admin CRUD (ADM-011 to ADM-013 in Phase 3 Plan)
# ---------------------------------------------------------------------------

@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_in: ActivityCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.create_activity(activity_in)


@router.get("/activities", response_model=list[ActivityResponse])
async def list_activities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_activities(skip=skip, limit=limit)


@router.get("/activities/{id}", response_model=ActivityResponse)
async def get_activity(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_activity(id)


@router.put("/activities/{id}", response_model=ActivityResponse)
async def update_activity(
    id: uuid.UUID,
    activity_in: ActivityUpdate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.update_activity(id, activity_in)


# ---------------------------------------------------------------------------
# Materials Admin CRUD (ADM-014 to ADM-016 in Phase 3 Plan)
# ---------------------------------------------------------------------------

@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    material_in: MaterialCreate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.create_material(material_in)


@router.get("/materials", response_model=list[MaterialResponse])
async def list_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_materials(skip=skip, limit=limit)


@router.get("/materials/{id}", response_model=MaterialResponse)
async def get_material(
    id: uuid.UUID,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.get_material(id)


@router.put("/materials/{id}", response_model=MaterialResponse)
async def update_material(
    id: uuid.UUID,
    material_in: MaterialUpdate,
    service: MasterDataService = Depends(get_master_data_service),
    current_user: User = Depends(require_role(["administrator", "director"])),
):
    return await service.update_material(id, material_in)


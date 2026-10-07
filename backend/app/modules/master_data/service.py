import uuid
from collections.abc import Sequence

from app.core.exceptions import ConflictError, NotFoundError
from app.models.operations import Activity, Client, Material, Project, Site, WorkOrder
from app.models.workforce import Role
from app.modules.master_data.repository import MasterDataRepository
from app.modules.master_data.schemas import (
    ActivityCreate,
    ActivityUpdate,
    ClientCreate,
    MaterialCreate,
    MaterialUpdate,
    ProjectCreate,
    SiteCreate,
    WorkOrderCreate,
    WorkOrderUpdate,
)


class MasterDataService:
    def __init__(self, repository: MasterDataRepository):
        self.repo = repository

    async def create_client(self, client_in: ClientCreate) -> Client:
        client = Client(
            name=client_in.name,
            contact_person=client_in.contact_person,
            contact_mobile=client_in.contact_mobile,
            is_active=client_in.is_active
        )
        return await self.repo.create_client(client)

    async def get_clients(self, skip: int = 0, limit: int = 100) -> Sequence[Client]:
        return await self.repo.get_clients(skip=skip, limit=limit)

    async def create_project(self, project_in: ProjectCreate) -> Project:
        client = await self.repo.get_client_by_id(project_in.client_id)
        if not client:
            raise NotFoundError(f"Client with id {project_in.client_id} not found")

        project = Project(
            name=project_in.name,
            status=project_in.status,
            start_date=project_in.start_date,
            end_date=project_in.end_date,
            client_id=project_in.client_id
        )
        return await self.repo.create_project(project)

    async def get_projects(self, skip: int = 0, limit: int = 100) -> Sequence[Project]:
        return await self.repo.get_projects(skip=skip, limit=limit)

    async def create_site(self, site_in: SiteCreate) -> Site:
        project = await self.repo.get_project_by_id(site_in.project_id)
        if not project:
            raise NotFoundError(f"Project with id {site_in.project_id} not found")

        site = Site(
            name=site_in.name,
            address=site_in.address,
            location=site_in.location,
            permitted_radius_m=site_in.permitted_radius_m,
            supervisor_id=site_in.supervisor_id,
            project_id=site_in.project_id,
            is_active=site_in.is_active
        )
        return await self.repo.create_site(site)

    async def get_sites(self, skip: int = 0, limit: int = 100) -> Sequence[Site]:
        return await self.repo.get_sites(skip=skip, limit=limit)

    async def get_roles(self, skip: int = 0, limit: int = 100) -> Sequence[Role]:
        return await self.repo.get_roles(skip=skip, limit=limit)

    # Work Orders
    async def create_work_order(self, wo_in: WorkOrderCreate) -> WorkOrder:
        existing = await self.repo.get_work_order_by_number(wo_in.order_number)
        if existing:
            raise ConflictError(f"Work order with order number '{wo_in.order_number}' already exists")

        project = await self.repo.get_project_by_id(wo_in.project_id)
        if not project:
            raise NotFoundError(f"Project with id {wo_in.project_id} not found")

        site = await self.repo.get_site_by_id(wo_in.site_id)
        if not site:
            raise NotFoundError(f"Site with id {wo_in.site_id} not found")

        wo = WorkOrder(
            order_number=wo_in.order_number,
            project_id=wo_in.project_id,
            site_id=wo_in.site_id,
            description=wo_in.description,
            target_quantities=wo_in.target_quantities,
            start_date=wo_in.start_date,
            end_date=wo_in.end_date,
            billing_basis=wo_in.billing_basis,
            status=wo_in.status,
            is_active=wo_in.is_active,
        )
        return await self.repo.create_work_order(wo)

    async def get_work_orders(self, skip: int = 0, limit: int = 100) -> Sequence[WorkOrder]:
        return await self.repo.get_work_orders(skip=skip, limit=limit)

    async def get_work_order(self, work_order_id: uuid.UUID) -> WorkOrder:
        wo = await self.repo.get_work_order_by_id(work_order_id)
        if not wo:
            raise NotFoundError(f"Work order with id {work_order_id} not found")
        return wo

    async def update_work_order(self, work_order_id: uuid.UUID, wo_in: WorkOrderUpdate) -> WorkOrder:
        wo = await self.get_work_order(work_order_id)
        update_data = wo_in.model_dump(exclude_unset=True)

        if "order_number" in update_data and update_data["order_number"] != wo.order_number:
            existing = await self.repo.get_work_order_by_number(update_data["order_number"])
            if existing and existing.id != wo.id:
                raise ConflictError(f"Work order with order number '{update_data['order_number']}' already exists")

        if "project_id" in update_data and update_data["project_id"] is not None:
            project = await self.repo.get_project_by_id(update_data["project_id"])
            if not project:
                raise NotFoundError(f"Project with id {update_data['project_id']} not found")

        if "site_id" in update_data and update_data["site_id"] is not None:
            site = await self.repo.get_site_by_id(update_data["site_id"])
            if not site:
                raise NotFoundError(f"Site with id {update_data['site_id']} not found")

        for key, value in update_data.items():
            setattr(wo, key, value)

        return await self.repo.update_work_order(wo)

    # Activities
    async def create_activity(self, act_in: ActivityCreate) -> Activity:
        act = Activity(
            name=act_in.name,
            unit_of_measure=act_in.unit_of_measure,
            approved_rate=float(act_in.approved_rate),
            category=act_in.category,
            is_active=act_in.is_active,
        )
        return await self.repo.create_activity(act)

    async def get_activities(self, skip: int = 0, limit: int = 100) -> Sequence[Activity]:
        return await self.repo.get_activities(skip=skip, limit=limit)

    async def get_activity(self, activity_id: uuid.UUID) -> Activity:
        act = await self.repo.get_activity_by_id(activity_id)
        if not act:
            raise NotFoundError(f"Activity with id {activity_id} not found")
        return act

    async def update_activity(self, activity_id: uuid.UUID, act_in: ActivityUpdate) -> Activity:
        act = await self.get_activity(activity_id)
        update_data = act_in.model_dump(exclude_unset=True)

        if "approved_rate" in update_data and update_data["approved_rate"] is not None:
            update_data["approved_rate"] = float(update_data["approved_rate"])

        for key, value in update_data.items():
            setattr(act, key, value)

        return await self.repo.update_activity(act)

    # Materials
    async def create_material(self, mat_in: MaterialCreate) -> Material:
        mat = Material(
            name=mat_in.name,
            material_code=mat_in.material_code,
            description=mat_in.description,
            unit_of_measure=mat_in.unit_of_measure,
            category=mat_in.category,
            purchase_approval_limit=float(mat_in.purchase_approval_limit),
            is_active=mat_in.is_active,
        )
        return await self.repo.create_material(mat)

    async def get_materials(self, skip: int = 0, limit: int = 100) -> Sequence[Material]:
        return await self.repo.get_materials(skip=skip, limit=limit)

    async def get_material(self, material_id: uuid.UUID) -> Material:
        mat = await self.repo.get_material_by_id(material_id)
        if not mat:
            raise NotFoundError(f"Material with id {material_id} not found")
        return mat

    async def update_material(self, material_id: uuid.UUID, mat_in: MaterialUpdate) -> Material:
        mat = await self.get_material(material_id)
        update_data = mat_in.model_dump(exclude_unset=True)

        if "purchase_approval_limit" in update_data and update_data["purchase_approval_limit"] is not None:
            update_data["purchase_approval_limit"] = float(update_data["purchase_approval_limit"])

        for key, value in update_data.items():
            setattr(mat, key, value)

        return await self.repo.update_material(mat)

    async def delete_site(self, site_id: uuid.UUID) -> None:
        site = await self.repo.get_site_by_id(site_id)
        if not site:
            raise NotFoundError(f"Site with id {site_id} not found")
        await self.repo.delete_site_atomic(site_id)

    async def delete_project(self, project_id: uuid.UUID) -> None:
        project = await self.repo.get_project_by_id(project_id)
        if not project:
            raise NotFoundError(f"Project with id {project_id} not found")
        await self.repo.delete_project_atomic(project_id)

    async def delete_client(self, client_id: uuid.UUID) -> None:
        client = await self.repo.get_client_by_id(client_id)
        if not client:
            raise NotFoundError(f"Client with id {client_id} not found")
        await self.repo.delete_client_atomic(client_id)


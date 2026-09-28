import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.operations import Activity, Client, Material, Project, Site, WorkOrder
from app.models.workforce import Role


class MasterDataRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Clients
    async def create_client(self, client: Client) -> Client:
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def get_client_by_id(self, client_id: uuid.UUID) -> Client | None:
        stmt = select(Client).where(Client.id == client_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_clients(self, skip: int = 0, limit: int = 100) -> Sequence[Client]:
        stmt = select(Client).order_by(Client.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # Projects
    async def create_project(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project_by_id(self, project_id: uuid.UUID) -> Project | None:
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_projects(self, skip: int = 0, limit: int = 1000) -> Sequence[Project]:
        stmt = select(Project).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # Sites
    async def create_site(self, site: Site) -> Site:
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def get_site_by_id(self, site_id: uuid.UUID) -> Site | None:
        stmt = select(Site).where(Site.id == site_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_sites(self, skip: int = 0, limit: int = 1000) -> Sequence[Site]:
        stmt = select(Site).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # Roles
    async def get_roles(self, skip: int = 0, limit: int = 100) -> Sequence[Role]:
        stmt = select(Role).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # Work Orders
    async def create_work_order(self, work_order: WorkOrder) -> WorkOrder:
        self.db.add(work_order)
        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    async def get_work_order_by_id(self, work_order_id: uuid.UUID) -> WorkOrder | None:
        stmt = select(WorkOrder).where(WorkOrder.id == work_order_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_work_order_by_number(self, order_number: str) -> WorkOrder | None:
        stmt = select(WorkOrder).where(WorkOrder.order_number == order_number)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_work_orders(self, skip: int = 0, limit: int = 100) -> Sequence[WorkOrder]:
        stmt = select(WorkOrder).order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_work_order(self, work_order: WorkOrder) -> WorkOrder:
        await self.db.commit()
        await self.db.refresh(work_order)
        return work_order

    # Activities
    async def create_activity(self, activity: Activity) -> Activity:
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def get_activity_by_id(self, activity_id: uuid.UUID) -> Activity | None:
        stmt = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_activities(self, skip: int = 0, limit: int = 100) -> Sequence[Activity]:
        stmt = select(Activity).order_by(Activity.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_activity(self, activity: Activity) -> Activity:
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    # Materials
    async def create_material(self, material: Material) -> Material:
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def get_material_by_id(self, material_id: uuid.UUID) -> Material | None:
        stmt = select(Material).where(Material.id == material_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_materials(self, skip: int = 0, limit: int = 100) -> Sequence[Material]:
        stmt = select(Material).order_by(Material.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_material(self, material: Material) -> Material:
        await self.db.commit()
        await self.db.refresh(material)
        return material


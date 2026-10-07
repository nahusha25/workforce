import uuid
from collections.abc import Sequence

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    ExceptionFlag,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
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

    async def _delete_site_internal(self, site_id: uuid.UUID) -> None:
        # 1. Site assignments
        await self.db.execute(delete(EmployeeSiteAssignment).where(EmployeeSiteAssignment.site_id == site_id))

        # 2. Daily work entries at site
        res_dwe = await self.db.execute(select(DailyWorkEntry.id).where(DailyWorkEntry.site_id == site_id))
        dwe_ids = res_dwe.scalars().all()
        if dwe_ids:
            await self.db.execute(delete(WorkPhoto).where(WorkPhoto.daily_work_entry_id.in_(dwe_ids)))
            res_mat = await self.db.execute(
                select(MaterialTransaction.id).where(MaterialTransaction.daily_work_entry_id.in_(dwe_ids))
            )
            mat_ids = res_mat.scalars().all()
            if mat_ids:
                await self.db.execute(delete(VerificationRecord).where(VerificationRecord.material_transaction_id.in_(mat_ids)))
                await self.db.execute(
                    delete(ExceptionFlag).where((ExceptionFlag.entity_type == "material") & (ExceptionFlag.entity_id.in_(mat_ids)))
                )
                await self.db.execute(delete(MaterialTransaction).where(MaterialTransaction.id.in_(mat_ids)))
            await self.db.execute(delete(VerificationRecord).where(VerificationRecord.daily_work_entry_id.in_(dwe_ids)))
            await self.db.execute(
                delete(ExceptionFlag).where((ExceptionFlag.entity_type == "daily_work") & (ExceptionFlag.entity_id.in_(dwe_ids)))
            )
            await self.db.execute(delete(DailyWorkEntry).where(DailyWorkEntry.id.in_(dwe_ids)))

        # 3. Any additional material transactions at site
        res_mat_site = await self.db.execute(select(MaterialTransaction.id).where(MaterialTransaction.site_id == site_id))
        mat_site_ids = res_mat_site.scalars().all()
        if mat_site_ids:
            await self.db.execute(delete(VerificationRecord).where(VerificationRecord.material_transaction_id.in_(mat_site_ids)))
            await self.db.execute(
                delete(ExceptionFlag).where((ExceptionFlag.entity_type == "material") & (ExceptionFlag.entity_id.in_(mat_site_ids)))
            )
            await self.db.execute(delete(MaterialTransaction).where(MaterialTransaction.id.in_(mat_site_ids)))

        # 4. Attendance records at site
        res_att = await self.db.execute(select(AttendanceRecord.id).where(AttendanceRecord.site_id == site_id))
        att_ids = res_att.scalars().all()
        if att_ids:
            res_dwe_att = await self.db.execute(
                select(DailyWorkEntry.id).where(DailyWorkEntry.attendance_record_id.in_(att_ids))
            )
            dwe_att_ids = res_dwe_att.scalars().all()
            if dwe_att_ids:
                await self.db.execute(delete(WorkPhoto).where(WorkPhoto.daily_work_entry_id.in_(dwe_att_ids)))
                await self.db.execute(delete(VerificationRecord).where(VerificationRecord.daily_work_entry_id.in_(dwe_att_ids)))
                await self.db.execute(
                    delete(ExceptionFlag).where((ExceptionFlag.entity_type == "daily_work") & (ExceptionFlag.entity_id.in_(dwe_att_ids)))
                )
                await self.db.execute(delete(DailyWorkEntry).where(DailyWorkEntry.id.in_(dwe_att_ids)))
            await self.db.execute(delete(VerificationRecord).where(VerificationRecord.attendance_record_id.in_(att_ids)))
            await self.db.execute(
                delete(ExceptionFlag).where((ExceptionFlag.entity_type == "attendance") & (ExceptionFlag.entity_id.in_(att_ids)))
            )
            await self.db.execute(delete(AttendanceRecord).where(AttendanceRecord.id.in_(att_ids)))

        # 5. Work orders at site
        res_wo = await self.db.execute(select(WorkOrder.id).where(WorkOrder.site_id == site_id))
        wo_ids = res_wo.scalars().all()
        if wo_ids:
            await self.db.execute(update(DailyWorkEntry).where(DailyWorkEntry.work_order_id.in_(wo_ids)).values(work_order_id=None))
            await self.db.execute(delete(WorkOrder).where(WorkOrder.id.in_(wo_ids)))

        # 6. Site itself
        await self.db.execute(delete(Site).where(Site.id == site_id))

    async def _delete_project_internal(self, project_id: uuid.UUID) -> None:
        res_sites = await self.db.execute(select(Site.id).where(Site.project_id == project_id))
        site_ids = res_sites.scalars().all()
        for sid in site_ids:
            await self._delete_site_internal(sid)

        res_wo = await self.db.execute(select(WorkOrder.id).where(WorkOrder.project_id == project_id))
        wo_ids = res_wo.scalars().all()
        if wo_ids:
            await self.db.execute(update(DailyWorkEntry).where(DailyWorkEntry.work_order_id.in_(wo_ids)).values(work_order_id=None))
            await self.db.execute(delete(WorkOrder).where(WorkOrder.id.in_(wo_ids)))

        await self.db.execute(delete(Project).where(Project.id == project_id))

    async def delete_site_atomic(self, site_id: uuid.UUID) -> None:
        await self._delete_site_internal(site_id)
        await self.db.commit()

    async def delete_project_atomic(self, project_id: uuid.UUID) -> None:
        await self._delete_project_internal(project_id)
        await self.db.commit()

    async def delete_client_atomic(self, client_id: uuid.UUID) -> None:
        res_projs = await self.db.execute(select(Project.id).where(Project.client_id == client_id))
        proj_ids = res_projs.scalars().all()
        for pid in proj_ids:
            await self._delete_project_internal(pid)
        await self.db.execute(delete(Client).where(Client.id == client_id))
        await self.db.commit()


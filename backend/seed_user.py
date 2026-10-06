import asyncio
import uuid
import sys
import os
from datetime import datetime, timezone, date

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.auth import User
from app.models.workforce import Employee
from app.models.operations import Client, Project, Site, Activity, WorkOrder

ADMIN_MOBILE = "+917760443750"
SUPERVISOR_MOBILE = "+919876543210"

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # 1. Administrator / Director User
        res = await session.execute(select(User).where(User.mobile_id == ADMIN_MOBILE))
        admin_user = res.scalar_one_or_none()
        if admin_user:
            admin_user.role = "administrator"
            admin_user.is_active = True
        else:
            admin_user = User(
                id=uuid.uuid4(),
                mobile_id=ADMIN_MOBILE,
                role="administrator",
                is_active=True
            )
            session.add(admin_user)
        await session.flush()
        print(f"Configured Administrator user ({ADMIN_MOBILE})")

        # 2. Supervisor User
        res_sup = await session.execute(select(User).where(User.mobile_id == SUPERVISOR_MOBILE))
        sup_user = res_sup.scalar_one_or_none()
        if sup_user:
            sup_user.role = "supervisor"
            sup_user.is_active = True
        else:
            sup_user = User(
                id=uuid.uuid4(),
                mobile_id=SUPERVISOR_MOBILE,
                role="supervisor",
                is_active=True
            )
            session.add(sup_user)
        await session.flush()

        # 3. Supervisor Employee Profile
        res_emp = await session.execute(select(Employee).where(Employee.user_id == sup_user.id))
        sup_emp = res_emp.scalar_one_or_none()
        if not sup_emp:
            sup_emp = Employee(
                id=uuid.uuid4(),
                user_id=sup_user.id,
                employee_code="SUP-98765",
                mobile_id=SUPERVISOR_MOBILE,
                name="Site Supervisor",
                is_active=True
            )
            session.add(sup_emp)
            await session.flush()
        print(f"Configured Supervisor user & profile ({SUPERVISOR_MOBILE})")

        # 4. Master Data (Client, Project, Site)
        res_c = await session.execute(select(Client).limit(1))
        client = res_c.scalar_one_or_none()
        if not client:
            client = Client(id=uuid.uuid4(), name="Metro Infrastructure Corp")
            session.add(client)
            await session.flush()

        res_p = await session.execute(select(Project).where(Project.client_id == client.id).limit(1))
        project = res_p.scalar_one_or_none()
        if not project:
            project = Project(id=uuid.uuid4(), client_id=client.id, name="Metro Line 3 Project", status="active")
            session.add(project)
            await session.flush()

        res_s = await session.execute(select(Site).where(Site.project_id == project.id).limit(1))
        site = res_s.scalar_one_or_none()
        if not site:
            site = Site(
                id=uuid.uuid4(),
                project_id=project.id,
                name="Central Station Site",
                location="POINT(72.834654 18.921984)",
                permitted_radius_m=10000.0,
                supervisor_id=sup_emp.id,
                is_active=True
            )
            session.add(site)
            await session.flush()
        else:
            site.supervisor_id = sup_emp.id

        # 5. Master Data Activities
        res_a = await session.execute(select(Activity).limit(1))
        activity = res_a.scalar_one_or_none()
        if not activity:
            act1 = Activity(
                id=uuid.uuid4(),
                name="Cable Pulling & Laying",
                unit_of_measure="metre",
                approved_rate=25.00,
                category="cable",
                is_active=True
            )
            act2 = Activity(
                id=uuid.uuid4(),
                name="Device Installation",
                unit_of_measure="device",
                approved_rate=150.00,
                category="device",
                is_active=True
            )
            act3 = Activity(
                id=uuid.uuid4(),
                name="Wall Drilling & Chipping",
                unit_of_measure="hole",
                approved_rate=45.00,
                category="drilling",
                is_active=True
            )
            session.add_all([act1, act2, act3])
            await session.flush()

        # 6. Master Data Work Order
        res_wo = await session.execute(select(WorkOrder).limit(1))
        wo = res_wo.scalar_one_or_none()
        if not wo:
            wo = WorkOrder(
                id=uuid.uuid4(),
                order_number="WO-2026-001",
                project_id=project.id,
                site_id=site.id,
                description="Main Terminal Cabling & Fitout",
                status="open",
                is_active=True,
                start_date=date.today()
            )
            session.add(wo)
            await session.flush()

        await session.commit()
        print("\n=== SEED COMPLETE ===")
        print(f"Administrator/Director : {ADMIN_MOBILE}")
        print(f"Supervisor             : {SUPERVISOR_MOBILE}")
        print(f"Active Employees       : None (ready for admin onboarding)")

    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())

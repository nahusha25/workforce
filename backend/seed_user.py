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
from app.models.operations import Client, Project, Site, EmployeeSiteAssignment, Activity, WorkOrder

TARGET_MOBILE = "+917760443750"

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Check if user already exists
        res = await session.execute(select(User).where(User.mobile_id == TARGET_MOBILE))
        existing_user = res.scalar_one_or_none()

        if existing_user:
            print(f"User with mobile {TARGET_MOBILE} already exists (ID: {existing_user.id}). Updating to active employee...")
            existing_user.is_active = True
            existing_user.role = "employee"
            user = existing_user
        else:
            user = User(
                id=uuid.uuid4(),
                mobile_id=TARGET_MOBILE,
                role="employee",
                is_active=True
            )
            session.add(user)
            await session.flush()
            print(f"Created user with mobile {TARGET_MOBILE} (ID: {user.id})")

        # Check or create Employee
        res = await session.execute(select(Employee).where(Employee.user_id == user.id))
        emp = res.scalar_one_or_none()
        if not emp:
            emp = Employee(
                id=uuid.uuid4(),
                user_id=user.id,
                employee_code="EMP-77604",
                mobile_id=TARGET_MOBILE,
                name="Nahus Test Worker",
                is_active=True
            )
            session.add(emp)
            await session.flush()
            print(f"Created employee record (ID: {emp.id})")
        else:
            print(f"Employee record already exists (ID: {emp.id})")

        # Check or create Client, Project, Site
        res = await session.execute(select(Client).limit(1))
        client = res.scalar_one_or_none()
        if not client:
            client = Client(id=uuid.uuid4(), name="Metro Infrastructure Corp")
            session.add(client)
            await session.flush()

        res = await session.execute(select(Project).where(Project.client_id == client.id).limit(1))
        project = res.scalar_one_or_none()
        if not project:
            project = Project(id=uuid.uuid4(), client_id=client.id, name="Metro Line 3 Project", status="active")
            session.add(project)
            await session.flush()

        res = await session.execute(select(Site).where(Site.project_id == project.id).limit(1))
        site = res.scalar_one_or_none()
        if not site:
            site = Site(
                id=uuid.uuid4(),
                project_id=project.id,
                name="Central Station Site",
                location="POINT(72.834654 18.921984)",
                permitted_radius_m=10000.0, # Generous radius for dev/testing
                is_active=True
            )
            session.add(site)
            await session.flush()

        # Check or create Site Assignment
        res = await session.execute(
            select(EmployeeSiteAssignment).where(
                EmployeeSiteAssignment.employee_id == emp.id,
                EmployeeSiteAssignment.site_id == site.id
            )
        )
        assignment = res.scalar_one_or_none()
        if not assignment:
            assignment = EmployeeSiteAssignment(
                id=uuid.uuid4(),
                employee_id=emp.id,
                site_id=site.id,
                assigned_at=datetime.now(timezone.utc)
            )
            session.add(assignment)
            await session.flush()
            print(f"Assigned employee {emp.name} to site {site.name}")

        # Check or create Reference Activities
        res = await session.execute(select(Activity).limit(1))
        activity = res.scalar_one_or_none()
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
            print("Created default activities (Cable, Device, Drilling)")

        # Check or create Work Order
        res = await session.execute(select(WorkOrder).limit(1))
        wo = res.scalar_one_or_none()
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
            print("Created default Work Order WO-2026-001")

        await session.commit()
        print("\n=== SEED COMPLETE ===")
        print(f"User Mobile: {TARGET_MOBILE}")
        print(f"User ID:     {user.id}")
        print(f"Employee ID: {emp.id}")
        print(f"Site ID:     {site.id} ({site.name})")

    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())

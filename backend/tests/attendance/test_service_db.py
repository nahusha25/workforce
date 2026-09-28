import pytest
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.modules.attendance.service import AttendanceService
from app.modules.attendance.schemas import CheckInRequest, CheckOutRequest
from app.models.operations import EmployeeSiteAssignment, Site, AttendanceRecord, Client, Project

from app.models.auth import User
from app.models.workforce import Employee, Role
from tests.conftest import TestingSessionLocal

@pytest.mark.asyncio
async def test_check_in_and_out_success():
    async with TestingSessionLocal() as session:
        # 1. Setup Data
        client = Client(name="Test Client")
        session.add(client)
        await session.commit()
        await session.refresh(client)

        project = Project(name="Test Project", status="Active", client_id=client.id)
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Site location: roughly Paris
        site = Site(name="Test Site", project_id=project.id, location="POINT(2.3522 48.8566)", permitted_radius_m=500.0)
        session.add(site)
        await session.commit()
        await session.refresh(site)

        role = Role(name="Test Role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            id=uuid.uuid4(),
            mobile_id=f"123456{uuid.uuid4().hex[:4]}",
            role="employee",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        employee = Employee(
            user_id=user.id,
            name="John Doe", 
            employee_code=f"EMP{uuid.uuid4().hex[:4]}",
            mobile_id=f"DEV{uuid.uuid4().hex[:4]}",
            is_active=True
        )
        session.add(employee)
        await session.commit()
        await session.refresh(employee)

        assignment = EmployeeSiteAssignment(
            employee_id=employee.id,
            site_id=site.id,
            is_active=True
        )
        session.add(assignment)
        await session.commit()

        # 2. Test Check-In (within radius)
        # Very close to Paris coordinates (within 500m)
        req = CheckInRequest(latitude=48.8567, longitude=2.3523)
        record = await AttendanceService.check_in(session, employee.id, user.id, req)
        
        assert record.id is not None
        assert record.is_within_geofence is True
        assert record.check_in_time is not None
        assert record.status == "draft"

        # 3. Test Duplicate Check-in while session is active (should block)
        try:
            await AttendanceService.check_in(session, employee.id, user.id, req)
            assert False, "Duplicate check-in should have raised an exception"
        except HTTPException as e:
            assert e.status_code == 409

        # 4. Test Check-Out
        req_out = CheckOutRequest(latitude=48.8568, longitude=2.3524)
        out_record = await AttendanceService.check_out(session, employee.id, user.id, req_out)

        assert out_record.id == record.id
        assert out_record.check_out_time is not None
        assert out_record.working_hours is not None

        # 5. Test Geo-fence violation (London coordinates vs Paris Site)
        # We need a new date or employee, but since we already have a check-in, 
        # let's just make a new employee for the geofence test
        user2 = User(
            id=uuid.uuid4(),
            mobile_id=f"123456{uuid.uuid4().hex[:4]}",
            role="employee",
            is_active=True
        )
        session.add(user2)
        await session.commit()
        await session.refresh(user2)

        employee2 = Employee(
            user_id=user2.id,
            name="Jane Doe",
            employee_code=f"EMP{uuid.uuid4().hex[:4]}",
            mobile_id=f"DEV{uuid.uuid4().hex[:4]}",
            is_active=True
        )
        session.add(employee2)
        await session.commit()
        await session.refresh(employee2)

        assignment2 = EmployeeSiteAssignment(
            employee_id=employee2.id,
            site_id=site.id,
            is_active=True
        )
        session.add(assignment2)
        await session.commit()

        req_fail = CheckInRequest(latitude=51.5074, longitude=-0.1278) # London
        flagged_record = await AttendanceService.check_in(session, employee2.id, user2.id, req_fail)
        assert flagged_record.id is not None
        assert flagged_record.is_within_geofence is False
        assert flagged_record.status == "flagged"

        from app.models.operations import ExceptionFlag
        from sqlalchemy import select
        flag_stmt = select(ExceptionFlag).where(ExceptionFlag.entity_id == flagged_record.id)
        flag_res = await session.execute(flag_stmt)
        flag_obj = flag_res.scalars().first()
        assert flag_obj is not None
        assert flag_obj.flag_type == "out_of_location"
        assert flag_obj.is_resolved is False

import pytest
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.attendance.service import AttendanceService
from app.modules.attendance.schemas import CheckInRequest, CheckOutRequest, OverrideRequest
from app.models.operations import EmployeeSiteAssignment, Site, AttendanceRecord
from fastapi import HTTPException

# Mocking the session and models
class MockSession:
    def __init__(self):
        self.added = []
    def add(self, item):
        self.added.append(item)
    async def commit(self):
        pass
    async def refresh(self, item):
        pass

@pytest.mark.asyncio
async def test_extract_lat_lng():
    lat, lng = AttendanceService.extract_lat_lng_from_wkt("POINT(77.5946 12.9716)")
    assert lat == 12.9716
    assert lng == 77.5946

    lat, lng = AttendanceService.extract_lat_lng_from_wkt("0101000020E6100000D56763A5FCA453406CEB18244CA92940") # WKB format
    assert lat == 0.0
    assert lng == 0.0

@pytest.mark.asyncio
async def test_check_in_out_of_geofence_flags_and_persists(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from app.models.operations import ExceptionFlag

    mock_session = MockSession()
    mock_session.flush = AsyncMock()

    # Mock no existing record
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_scalars.first.return_value = None
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock assignment & site
    site_id = uuid.uuid4()
    mock_assignment = EmployeeSiteAssignment(
        employee_id=uuid.uuid4(),
        site_id=site_id,
        is_active=True
    )
    mock_site = Site(
        id=site_id,
        name="Test Site",
        location="POINT(2.3522 48.8566)",
        permitted_radius_m=500.0
    )

    monkeypatch.setattr(AttendanceService, "get_active_assignment", AsyncMock(return_value=mock_assignment))
    monkeypatch.setattr(AttendanceService, "get_site", AsyncMock(return_value=mock_site))

    employee_id = mock_assignment.employee_id
    user_id = uuid.uuid4()
    # Coordinates in London (far from Paris site)
    req = CheckInRequest(latitude=51.5074, longitude=-0.1278)

    record = await AttendanceService.check_in(mock_session, employee_id, user_id, req)

    assert record.is_within_geofence is False
    assert record.status == "flagged"
    assert record.employee_id == employee_id

    # Verify ExceptionFlag was added
    flags = [item for item in mock_session.added if isinstance(item, ExceptionFlag)]
    assert len(flags) == 1
    assert flags[0].entity_type == "attendance_record"
    assert flags[0].entity_id == record.id
    assert flags[0].flag_type == "out_of_location"
    assert flags[0].is_resolved is False

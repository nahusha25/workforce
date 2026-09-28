import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.operations import DailyWorkEntry, WorkPhoto, Site, Activity, Project, Client, AttendanceRecord
from app.models.auth import User
from app.models.workforce import Employee

@pytest.fixture
def test_deps(sync_db_session: Session):
    unique_suffix = str(uuid.uuid4())[:8]
    user = User(mobile_id=f"M-{unique_suffix}", role="employee", is_active=True)
    sync_db_session.add(user)
    sync_db_session.flush()

    emp = Employee(user_id=user.id, employee_code=f"E-{unique_suffix}", mobile_id=f"M-{unique_suffix}", name="John Doe", is_active=True)
    sync_db_session.add(emp)
    sync_db_session.flush()

    client = Client(name=f"WP Client {unique_suffix}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.flush()

    project = Project(client_id=client.id, name=f"WP Project {unique_suffix}", status="active")
    sync_db_session.add(project)
    sync_db_session.flush()

    site = Site(project_id=project.id, name=f"WP Site {unique_suffix}", permitted_radius_m=100.0, is_active=True)
    sync_db_session.add(site)
    sync_db_session.flush()

    activity = Activity(name=f"WP Activity {unique_suffix}", unit_of_measure="m", approved_rate=100, category="cable", is_active=True)
    sync_db_session.add(activity)
    sync_db_session.flush()

    attendance = AttendanceRecord(
        employee_id=emp.id,
        site_id=site.id,
        date=datetime.now(timezone.utc).date(),
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        status="active"
    )
    sync_db_session.add(attendance)
    sync_db_session.flush()

    return {"employee": emp, "site": site, "activity": activity, "attendance": attendance}

def make_dwe(sync_db_session, test_deps):
    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        employee_id=test_deps["employee"].id,
        site_id=test_deps["site"].id,
        activity_id=test_deps["activity"].id,
        attendance_record_id=test_deps["attendance"].id,
        work_date=datetime.now(timezone.utc).date(),
        quantity=1.0,
        uom=test_deps["activity"].unit_of_measure,
        status="draft",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()
    return dwe

def test_work_photo_valid_creation(sync_db_session, test_deps):
    """Test creating a valid WorkPhoto."""
    dwe = make_dwe(sync_db_session, test_deps)

    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo.jpg",
        thumbnail_url="https://example.com/photo_thumb.jpg",
        file_size_bytes=1024
    )
    sync_db_session.add(photo)
    sync_db_session.commit()

    assert photo.id is not None
    assert photo.uploaded_at is not None

def test_work_photo_image_url_required(sync_db_session, test_deps):
    """Test image_url cannot be NULL."""
    dwe = make_dwe(sync_db_session, test_deps)

    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        thumbnail_url="https://example.com/photo_thumb.jpg",
        file_size_bytes=1024
    )
    sync_db_session.add(photo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_work_photo_optional_fields(sync_db_session, test_deps):
    """Test thumbnail_url and file_size_bytes can be NULL."""
    dwe = make_dwe(sync_db_session, test_deps)

    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo.jpg"
    )
    sync_db_session.add(photo)
    sync_db_session.commit()

    assert photo.id is not None
    assert photo.thumbnail_url is None
    assert photo.file_size_bytes is None

def test_work_photo_file_size_constraint(sync_db_session, test_deps):
    """Test file_size_bytes database-level CHECK constraint."""
    dwe = make_dwe(sync_db_session, test_deps)

    photo1 = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo1.jpg",
        file_size_bytes=0
    )
    sync_db_session.add(photo1)
    sync_db_session.commit()
    assert photo1.id is not None

    photo2 = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo2.jpg",
        file_size_bytes=100
    )
    sync_db_session.add(photo2)
    sync_db_session.commit()
    assert photo2.id is not None

    photo3 = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo3.jpg",
        file_size_bytes=-1
    )
    sync_db_session.add(photo3)
    with pytest.raises(IntegrityError, match="check_work_photos_file_size_bytes"):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_work_photo_foreign_key_missing(sync_db_session):
    """Test nonexistent daily_work_entry_id is rejected."""
    photo = WorkPhoto(
        daily_work_entry_id=uuid.uuid4(),
        image_url="https://example.com/photo.jpg"
    )
    sync_db_session.add(photo)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_work_photo_cascade_delete(sync_db_session, test_deps):
    """Test WorkPhoto is deleted when DailyWorkEntry is deleted."""
    dwe = make_dwe(sync_db_session, test_deps)

    photo = WorkPhoto(
        daily_work_entry_id=dwe.id,
        image_url="https://example.com/photo.jpg"
    )
    sync_db_session.add(photo)
    sync_db_session.commit()

    photo_id = photo.id

    sync_db_session.delete(dwe)
    sync_db_session.commit()

    deleted_photo = sync_db_session.query(WorkPhoto).filter_by(id=photo_id).first()
    assert deleted_photo is None

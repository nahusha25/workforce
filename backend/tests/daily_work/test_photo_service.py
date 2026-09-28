import os
import tempfile
import uuid
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Project,
    Site,
    WorkPhoto,
)
from app.models.workforce import Employee
from app.modules.daily_work.photo_service import WorkPhotoService
from app.shared.file_storage import LocalFileStorage
from tests.conftest import TestingSessionLocal

# Valid binary image payloads for testing
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"A" * 100)
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"B" * 100)
VALID_WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBPVP8 " + (b"C" * 100)


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalFileStorage(base_dir=tmpdir, base_url="/uploads")


async def setup_photo_fixtures(session: AsyncSession):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # Users
    user1 = User(id=uuid.uuid4(), mobile_id=f"M-P1-{suffix}", role="employee", is_active=True)
    user2 = User(id=uuid.uuid4(), mobile_id=f"M-P2-{suffix}", role="employee", is_active=True)
    user_sup = User(id=uuid.uuid4(), mobile_id=f"M-PS-{suffix}", role="supervisor", is_active=True)
    user_sup2 = User(id=uuid.uuid4(), mobile_id=f"M-PS2-{suffix}", role="supervisor", is_active=True)
    session.add_all([user1, user2, user_sup, user_sup2])
    await session.commit()

    # Supervisors
    sup = Employee(
        id=uuid.uuid4(),
        user_id=user_sup.id,
        name=f"Sup {suffix}",
        employee_code=f"SUP-{suffix}",
        mobile_id=f"M-PS-{suffix}",
        is_active=True,
    )
    sup2 = Employee(
        id=uuid.uuid4(),
        user_id=user_sup2.id,
        name=f"Other Sup {suffix}",
        employee_code=f"SUP2-{suffix}",
        mobile_id=f"M-PS2-{suffix}",
        is_active=True,
    )
    session.add_all([sup, sup2])
    await session.commit()

    # Employees: emp1 reports to sup; emp2 reports to sup2
    emp1 = Employee(
        id=uuid.uuid4(),
        user_id=user1.id,
        name=f"Worker One {suffix}",
        employee_code=f"W1-{suffix}",
        mobile_id=f"M-P1-{suffix}",
        supervisor_id=sup.id,
        is_active=True,
    )
    emp2 = Employee(
        id=uuid.uuid4(),
        user_id=user2.id,
        name=f"Worker Two {suffix}",
        employee_code=f"W2-{suffix}",
        mobile_id=f"M-P2-{suffix}",
        supervisor_id=sup2.id,
        is_active=True,
    )
    session.add_all([emp1, emp2])
    await session.commit()

    # Project and Site
    client = Client(name=f"Client {suffix}", is_active=True)
    session.add(client)
    await session.commit()

    project = Project(client_id=client.id, name=f"Project {suffix}", status="active")
    session.add(project)
    await session.commit()

    site = Site(
        name=f"Site {suffix}",
        project_id=project.id,
        supervisor_id=sup.id,
        location="POINT(77.5946 12.9716)",
        permitted_radius_m=500.0,
    )
    session.add(site)
    await session.commit()

    assign1 = EmployeeSiteAssignment(employee_id=emp1.id, site_id=site.id, is_active=True)
    session.add(assign1)

    activity = Activity(name=f"Act {suffix}", unit_of_measure="m", approved_rate=10.0, category="cable")
    session.add(activity)
    await session.commit()

    att = AttendanceRecord(
        employee_id=emp1.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        status="draft",
    )
    session.add(att)
    await session.commit()

    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=att.id,
        employee_id=emp1.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=today,
        quantity=2.0,
        uom=activity.unit_of_measure,
        status="draft",
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return {
        "emp1": emp1,
        "emp2": emp2,
        "sup": sup,
        "sup2": sup2,
        "entry": entry,
        "today": today,
    }


# ==============================================================================
# 1. UPLOAD PHOTO TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_upload_photo_success(temp_storage):
    """Owner employee successfully uploads a valid JPEG photo to a draft entry."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            filename="site_photo.jpg",
            content_type="image/jpeg",
            employee_id=emp1.id,
            storage=temp_storage,
        )

        assert photo.id is not None
        assert photo.daily_work_entry_id == entry.id
        assert photo.image_url.startswith("/uploads/photos/")
        assert photo.file_size_bytes == len(VALID_JPEG_BYTES)

        # Verify destination path structure: photos/{employee_id}/{date}/{entry_id}/{photo_id}.jpg
        date_str = entry.date.strftime("%Y-%m-%d")
        expected_prefix = f"/uploads/photos/{emp1.id}/{date_str}/{entry.id}/"
        assert photo.image_url.startswith(expected_prefix)
        assert photo.image_url.endswith(".jpg")

        # Verify file actually persisted on disk in temp_storage
        clean_path = photo.image_url.replace("/uploads/", "")
        assert await temp_storage.file_exists(clean_path)


@pytest.mark.asyncio
async def test_upload_photo_png_and_webp(temp_storage):
    """Uploads PNG and WebP images and infers appropriate extensions."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        # PNG without filename
        photo_png = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_PNG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert photo_png.image_url.endswith(".png")

        # WebP with filename
        photo_webp = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_WEBP_BYTES,
            filename="capture.webp",
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert photo_webp.image_url.endswith(".webp")


@pytest.mark.asyncio
async def test_upload_photo_correction_required(temp_storage):
    """Allows photo upload when entry status is 'correction_required'."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        entry.status = "correction_required"
        await session.commit()

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert photo.id is not None


@pytest.mark.asyncio
async def test_upload_photo_admin_access(temp_storage):
    """Admin can upload photo regardless of employee_id."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            is_admin=True,
            storage=temp_storage,
        )
        assert photo.id is not None


@pytest.mark.asyncio
async def test_upload_photo_rejects_disallowed_statuses(temp_storage):
    """Rejects photo uploads when entry is in submitted, approved, or rejected status."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        for blocked_status in ["submitted", "approved", "rejected"]:
            entry.status = blocked_status
            await session.commit()

            with pytest.raises(HTTPException) as exc_info:
                await WorkPhotoService.upload_photo(
                    session=session,
                    daily_work_entry_id=entry.id,
                    file_data=VALID_JPEG_BYTES,
                    employee_id=emp1.id,
                    storage=temp_storage,
                )
            assert exc_info.value.status_code == 400
            assert blocked_status in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_photo_rejects_unauthorized_employee(temp_storage):
    """Worker B cannot upload photo to Worker A's entry."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp2 = data["emp2"]
        entry = data["entry"]  # belongs to emp1

        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=entry.id,
                file_data=VALID_JPEG_BYTES,
                employee_id=emp2.id,
                storage=temp_storage,
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_upload_photo_rejects_nonexistent_entry(temp_storage):
    """Uploading to non-existent entry raises 404."""
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=uuid.uuid4(),
                file_data=VALID_JPEG_BYTES,
                storage=temp_storage,
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_upload_photo_rejects_invalid_file(temp_storage):
    """Rejects invalid mime type or empty bytes with 400."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        # Plain text
        with pytest.raises(HTTPException) as exc1:
            await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=entry.id,
                file_data=b"this is plain text not an image",
                employee_id=emp1.id,
                storage=temp_storage,
            )
        assert exc1.value.status_code == 400

        # Empty file
        with pytest.raises(HTTPException) as exc2:
            await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=entry.id,
                file_data=b"",
                employee_id=emp1.id,
                storage=temp_storage,
            )
        assert exc2.value.status_code == 400


# ==============================================================================
# 2. LIST PHOTOS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_list_photos_self_and_supervisor(temp_storage):
    """Employee and direct supervisor can list photos of the work entry."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        sup = data["sup"]
        entry = data["entry"]

        # Upload 2 photos
        p1 = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        p2 = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_PNG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        # 1. Employee lists
        photos_emp = await WorkPhotoService.list_photos(
            session=session,
            daily_work_entry_id=entry.id,
            user_role="employee",
            employee_id=emp1.id,
        )
        assert len(photos_emp) == 2
        photo_ids = [p.id for p in photos_emp]
        assert p1.id in photo_ids
        assert p2.id in photo_ids

        # 2. Supervisor lists
        photos_sup = await WorkPhotoService.list_photos(
            session=session,
            daily_work_entry_id=entry.id,
            user_role="supervisor",
            employee_id=sup.id,
        )
        assert len(photos_sup) == 2


@pytest.mark.asyncio
async def test_list_photos_rejects_unauthorized(temp_storage):
    """Unauthorized employee or supervisor cannot list photos."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp2 = data["emp2"]
        sup2 = data["sup2"]
        entry = data["entry"]

        # Other employee
        with pytest.raises(HTTPException) as exc1:
            await WorkPhotoService.list_photos(
                session=session,
                daily_work_entry_id=entry.id,
                user_role="employee",
                employee_id=emp2.id,
            )
        assert exc1.value.status_code == 403

        # Other supervisor
        with pytest.raises(HTTPException) as exc2:
            await WorkPhotoService.list_photos(
                session=session,
                daily_work_entry_id=entry.id,
                user_role="supervisor",
                employee_id=sup2.id,
            )
        assert exc2.value.status_code == 403


# ==============================================================================
# 3. DELETE PHOTO TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_delete_photo_success_draft(temp_storage):
    """Owner employee can delete photo while entry is draft; deletes DB record and stored file."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        clean_path = photo.image_url.replace("/uploads/", "")
        assert await temp_storage.file_exists(clean_path)

        # Delete photo
        deleted = await WorkPhotoService.delete_photo(
            session=session,
            photo_id=photo.id,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert deleted is True

        # Verify DB record removed
        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.get_photo(session, photo.id)
        assert exc_info.value.status_code == 404

        # Verify storage file deleted
        assert not await temp_storage.file_exists(clean_path)


@pytest.mark.asyncio
async def test_delete_photo_rejects_when_entry_submitted(temp_storage):
    """Cannot delete photo if entry has been submitted, approved, or rejected."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        # Submit entry
        entry.status = "submitted"
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.delete_photo(
                session=session,
                photo_id=photo.id,
                employee_id=emp1.id,
                storage=temp_storage,
            )
        assert exc_info.value.status_code == 400
        assert "submitted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_photo_rejects_unauthorized_employee(temp_storage):
    """Employee B cannot delete photo uploaded for Employee A's entry."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.delete_photo(
                session=session,
                photo_id=photo.id,
                employee_id=emp2.id,
                storage=temp_storage,
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_photo_admin_access(temp_storage):
    """Admin can delete a photo while entry is still in draft."""
    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        deleted = await WorkPhotoService.delete_photo(
            session=session,
            photo_id=photo.id,
            is_admin=True,
            storage=temp_storage,
        )
        assert deleted is True

        clean_path = photo.image_url.replace("/uploads/", "")
        assert not await temp_storage.file_exists(clean_path)


@pytest.mark.asyncio
async def test_delete_photo_tolerates_missing_storage_file(temp_storage, monkeypatch):
    """If file is already missing in storage (FileNotFoundStorageError), DB record is still cleaned up."""
    from app.shared.file_storage import FileNotFoundStorageError

    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        # Mock delete_file to simulate FileNotFoundStorageError
        async def mock_delete_missing(path):
            raise FileNotFoundStorageError("File already gone")

        monkeypatch.setattr(temp_storage, "delete_file", mock_delete_missing)

        deleted = await WorkPhotoService.delete_photo(
            session=session,
            photo_id=photo.id,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert deleted is True

        # DB record is cleaned up
        with pytest.raises(HTTPException) as exc_info:
            await WorkPhotoService.get_photo(session, photo.id)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_photo_propagates_real_storage_error(temp_storage, monkeypatch):
    """If delete_file raises an unexpected storage error, it propagates and DB record is not deleted."""
    from app.shared.file_storage import FileStorageError

    async with TestingSessionLocal() as session:
        data = await setup_photo_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        photo = await WorkPhotoService.upload_photo(
            session=session,
            daily_work_entry_id=entry.id,
            file_data=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        async def mock_delete_failure(path):
            raise FileStorageError("Disk I/O permission denied")

        monkeypatch.setattr(temp_storage, "delete_file", mock_delete_failure)

        with pytest.raises(FileStorageError) as exc_info:
            await WorkPhotoService.delete_photo(
                session=session,
                photo_id=photo.id,
                employee_id=emp1.id,
                storage=temp_storage,
            )
        assert "Disk I/O permission denied" in str(exc_info.value)

        # DB record is preserved because transaction was not committed
        persisted = await WorkPhotoService.get_photo(session, photo.id)
        assert persisted.id == photo.id


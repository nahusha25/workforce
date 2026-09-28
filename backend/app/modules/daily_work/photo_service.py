import os
from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import BinaryIO, List, Optional, Union

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import DailyWorkEntry, WorkPhoto
from app.modules.daily_work.service import DailyWorkService, EDITABLE_STATUSES
from app.shared.file_storage import (
    FileNotFoundStorageError,
    FileStorageError,
    FileSizeLimitExceededError,
    FileStorageService,
    InvalidFileTypeError,
    detect_mime_type_from_bytes,
    get_file_storage,
)


def _extract_storage_path(url: str) -> str:
    """Extract relative storage path from stored URL."""
    if ".amazonaws.com/" in url:
        return url.split(".amazonaws.com/", 1)[1]
    if "/uploads/" in url:
        return url.split("/uploads/", 1)[1]
    if url.startswith("/"):
        return url.lstrip("/")
    return url


def _determine_extension(filename: Optional[str], raw_bytes: bytes) -> str:
    """Determine file extension from filename or magic bytes."""
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in (".jpg", ".jpeg"):
            return ".jpg"
        if ext in (".png", ".webp"):
            return ext

    detected_mime = detect_mime_type_from_bytes(raw_bytes)
    if detected_mime == "image/jpeg":
        return ".jpg"
    if detected_mime == "image/png":
        return ".png"
    if detected_mime == "image/webp":
        return ".webp"
    return ".jpg"


class WorkPhotoService:
    @staticmethod
    async def upload_photo(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        storage: Optional[FileStorageService] = None,
    ) -> WorkPhoto:
        """Upload a progress photo linked to a daily work entry.

        Validates:
        1. Daily work entry exists.
        2. Entry belongs to requesting employee (unless admin).
        3. Entry status is 'draft' or 'correction_required' (rejects submitted/approved/rejected).
        4. Validates and stores file via file_storage abstraction.
        5. Generates an organized, collision-safe destination path:
           photos/{employee_id}/{date}/{entry_id}/{photo_id}.{ext}
        6. Persists WorkPhoto record with returned URL.
        """
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == daily_work_entry_id)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Ownership validation
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot upload photo for another employee's work entry",
                )

        # Status editability validation
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot upload photo for entry with status '{entry.status}'. Only draft and correction_required entries can receive photos.",
            )

        # Read bytes for extension determination and size calculation
        if isinstance(file_data, (bytes, bytearray)):
            raw_bytes = bytes(file_data)
        elif hasattr(file_data, "read"):
            raw_bytes = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file data: must be bytes or file-like object",
            )

        ext = _determine_extension(filename, raw_bytes)
        date_str = entry.date.strftime("%Y-%m-%d") if entry.date else "unknown"
        photo_id = uuid.uuid4()
        dest_path = f"photos/{entry.employee_id}/{date_str}/{entry.id}/{photo_id}{ext}"

        storage_client = storage or get_file_storage()
        try:
            image_url = await storage_client.upload_file(
                file_data=file_data,
                destination_path=dest_path,
                content_type=content_type,
            )
        except (InvalidFileTypeError, FileSizeLimitExceededError, FileStorageError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        file_size_bytes = len(raw_bytes) if raw_bytes else None

        photo = WorkPhoto(
            id=photo_id,
            daily_work_entry_id=entry.id,
            image_url=image_url,
            thumbnail_url=None,
            file_size_bytes=file_size_bytes,
            uploaded_at=datetime.now(timezone.utc),
        )
        session.add(photo)
        await session.commit()
        await session.refresh(photo)
        return photo

    @staticmethod
    async def list_photos(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        is_admin: bool = False,
    ) -> List[WorkPhoto]:
        """List all photos linked to a specific daily work entry."""
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == daily_work_entry_id)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Access check
        if not (is_admin or user_role in ("administrator", "director")):
            if user_role == "employee":
                if employee_id and entry.employee_id != employee_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot access photos for another employee's work entry",
                    )
            elif user_role == "supervisor" or supervisor_emp_id:
                sup_id = supervisor_emp_id or employee_id
                if not sup_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Supervisor profile required",
                    )
                is_auth = await DailyWorkService.is_supervisor_authorized(
                    session, sup_id, entry.employee_id, site_id=entry.site_id
                )
                if not is_auth:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot access photos for another employee's work entry",
                    )
            elif employee_id:
                if entry.employee_id != employee_id:
                    is_auth = await DailyWorkService.is_supervisor_authorized(
                        session, employee_id, entry.employee_id, site_id=entry.site_id
                    )
                    if not is_auth:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Cannot access photos for another employee's work entry",
                        )

        photo_stmt = (
            select(WorkPhoto)
            .where(WorkPhoto.daily_work_entry_id == daily_work_entry_id)
            .order_by(WorkPhoto.uploaded_at.asc())
        )
        photo_res = await session.execute(photo_stmt)
        return list(photo_res.scalars().all())

    @staticmethod
    async def delete_photo(
        session: AsyncSession,
        photo_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        storage: Optional[FileStorageService] = None,
    ) -> bool:
        """Delete a photo record and its underlying stored file.

        Can only be deleted by the uploading employee or admin, and only while
        the entry is still in an editable status ('draft' or 'correction_required').
        """
        stmt = select(WorkPhoto).where(WorkPhoto.id == photo_id)
        result = await session.execute(stmt)
        photo = result.scalars().first()
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work photo not found",
            )

        entry_stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == photo.daily_work_entry_id)
        entry_res = await session.execute(entry_stmt)
        entry = entry_res.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Status editability check
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete photo for entry with status '{entry.status}'. Photos can only be deleted while entry is in draft or correction_required status.",
            )

        # Ownership authorization check
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete photo uploaded by another employee",
                )

        # Remove physical file from storage; allow FileNotFoundStorageError if already removed
        storage_client = storage or get_file_storage()
        storage_path = _extract_storage_path(photo.image_url)
        if storage_path:
            try:
                await storage_client.delete_file(storage_path)
            except FileNotFoundStorageError:
                pass

        await session.delete(photo)
        await session.commit()
        return True

    @staticmethod
    async def get_photo(
        session: AsyncSession,
        photo_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        is_admin: bool = False,
    ) -> WorkPhoto:
        """Retrieve a single photo record by ID with access control."""
        stmt = select(WorkPhoto).where(WorkPhoto.id == photo_id)
        result = await session.execute(stmt)
        photo = result.scalars().first()
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work photo not found",
            )

        # Validate access to linked entry
        await WorkPhotoService.list_photos(
            session=session,
            daily_work_entry_id=photo.daily_work_entry_id,
            employee_id=employee_id,
            supervisor_emp_id=supervisor_emp_id,
            user_role=user_role,
            is_admin=is_admin,
        )
        return photo

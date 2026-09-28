import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.auth import User
from app.models.operations import Activity, DailyWorkEntry, MaterialTransaction, WorkOrder, WorkPhoto
from app.models.workforce import Employee
from app.modules.daily_work.material_service import MaterialTransactionService
from app.modules.daily_work.photo_service import WorkPhotoService
from app.modules.daily_work.schemas import (
    BillUploadResponse,
    DailyWorkEntryCreate,
    DailyWorkEntryListResponse,
    DailyWorkEntryResponse,
    DailyWorkEntryUpdate,
    MaterialTransactionCreate,
    MaterialTransactionResponse,
    MaterialTransactionUpdate,
    WorkPhotoResponse,
)
from app.modules.daily_work.service import EDITABLE_STATUSES, DailyWorkService
from app.modules.master_data.repository import MasterDataRepository
from app.modules.master_data.schemas import ActivityResponse, WorkOrderResponse
from app.modules.master_data.service import MasterDataService
from app.shared.file_storage import detect_mime_type_from_bytes

router = APIRouter()


async def get_current_employee(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await db.execute(stmt)
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee profile is inactive",
        )
    return employee


async def get_optional_employee(
    current_user: User,
    db: AsyncSession,
) -> Optional[Employee]:
    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().first()


# ---------------------------------------------------------------------------
# Specific Photo & Material Deletions (Declared first to avoid path collisions)
# ---------------------------------------------------------------------------

@router.delete("/photos/{photo_id}", status_code=status.HTTP_200_OK)
async def delete_photo(
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    is_admin = current_user.role == "administrator"
    if not is_admin and not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )
    await WorkPhotoService.delete_photo(
        session=db,
        photo_id=photo_id,
        employee_id=emp.id if emp else None,
        is_admin=is_admin,
    )
    return {"status": "success", "message": "Photo deleted"}


@router.delete("/materials/{transaction_id}", status_code=status.HTTP_200_OK)
async def delete_material_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    is_admin = current_user.role == "administrator"
    if not is_admin and not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )
    await MaterialTransactionService.delete_material_transaction(
        session=db,
        transaction_id=transaction_id,
        employee_id=emp.id if emp else None,
        is_admin=is_admin,
    )
    return {"status": "success", "message": "Material transaction deleted"}


# ---------------------------------------------------------------------------
# WRK-001: Create Daily Work Entry
# ---------------------------------------------------------------------------

@router.post("", response_model=DailyWorkEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_work_entry(
    data: DailyWorkEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    employee = await get_current_employee(current_user=current_user, db=db)

    try:
        entry = await DailyWorkService.create_work_entry(
            session=db,
            employee_id=employee.id,
            data=data,
            user_id=current_user.id,
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_400_BAD_REQUEST and "active check-in" in str(e.detail).lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must be checked in to create work entry",
            )
        raise e

    entry.photos = []
    entry.materials = []
    return entry


# ---------------------------------------------------------------------------
# WRK-002: List Daily Work Entries
# ---------------------------------------------------------------------------

@router.get("", response_model=DailyWorkEntryListResponse, status_code=status.HTTP_200_OK)
async def list_work_entries(
    employee_id: Optional[uuid.UUID] = None,
    date: Optional[date] = Query(None),
    work_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    site_id: Optional[uuid.UUID] = Query(None),
    activity_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skip: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    supervisor_emp_id = None
    target_emp_id = None
    is_admin = False

    if current_user.role == "employee":
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found",
            )
        if employee_id is not None and employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other employee records",
            )
        target_emp_id = emp.id
    elif current_user.role == "supervisor":
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisor profile not found",
            )
        supervisor_emp_id = emp.id
        if employee_id:
            is_auth = await DailyWorkService.is_supervisor_authorized(db, emp.id, employee_id)
            if not is_auth:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorised for this employee",
                )
            target_emp_id = employee_id
    elif current_user.role in ["administrator", "director"]:
        is_admin = True
        target_emp_id = employee_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to list work entries",
        )

    offset = skip if skip is not None else (page - 1) * page_size
    page_limit = limit if limit is not None else page_size

    items, total = await DailyWorkService.list_work_entries(
        session=db,
        employee_id=target_emp_id,
        supervisor_emp_id=supervisor_emp_id,
        date=work_date or date,
        is_admin=is_admin,
        status=status_filter,
        site_id=site_id,
        activity_id=activity_id,
        date_from=date_from,
        date_to=date_to,
        skip=offset,
        limit=page_limit,
    )

    if items:
        entry_ids = [item.id for item in items]
        stmt_photos = (
            select(WorkPhoto)
            .where(WorkPhoto.daily_work_entry_id.in_(entry_ids))
            .order_by(WorkPhoto.uploaded_at.desc())
        )
        res_photos = await db.execute(stmt_photos)
        all_photos = res_photos.scalars().all()
        photos_by_entry: dict[uuid.UUID, list] = {eid: [] for eid in entry_ids}
        for p in all_photos:
            photos_by_entry[p.daily_work_entry_id].append(p)

        stmt_mat = (
            select(MaterialTransaction)
            .where(MaterialTransaction.daily_work_entry_id.in_(entry_ids))
            .order_by(MaterialTransaction.created_at.desc())
        )
        res_mat = await db.execute(stmt_mat)
        all_materials = res_mat.scalars().all()
        materials_by_entry: dict[uuid.UUID, list] = {eid: [] for eid in entry_ids}
        for m in all_materials:
            materials_by_entry[m.daily_work_entry_id].append(m)

        for item in items:
            item.photos = photos_by_entry.get(item.id, [])
            item.materials = materials_by_entry.get(item.id, [])

    return DailyWorkEntryListResponse(
        data=items,
        total=total,
        skip=offset,
        limit=page_limit,
        page=page,
        page_size=page_limit,
    )


# ---------------------------------------------------------------------------
# Reference Data Endpoints for Daily Work Authoring
# ---------------------------------------------------------------------------

@router.get("/activities", response_model=list[ActivityResponse], status_code=status.HTTP_200_OK)
async def list_daily_work_activities(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Activity).where(Activity.is_active == True).order_by(Activity.name.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/work-orders", response_model=list[WorkOrderResponse], status_code=status.HTTP_200_OK)
@router.get("/work_orders", response_model=list[WorkOrderResponse], include_in_schema=False)
async def list_daily_work_work_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(WorkOrder).where(WorkOrder.is_active == True).order_by(WorkOrder.order_number.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# WRK-003: Get Daily Work Entry Detail
# ---------------------------------------------------------------------------

@router.get("/{id}", response_model=DailyWorkEntryResponse, status_code=status.HTTP_200_OK)
async def get_work_entry(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    entry = await DailyWorkService.get_work_entry(
        session=db,
        entry_id=id,
        requester_employee_id=emp.id if emp else None,
        supervisor_emp_id=emp.id if emp and current_user.role == "supervisor" else None,
        user_role=current_user.role,
        is_admin=current_user.role == "administrator",
    )
    photos = await WorkPhotoService.list_photos(session=db, daily_work_entry_id=id, is_admin=True)
    materials = await MaterialTransactionService.list_material_transactions(session=db, daily_work_entry_id=id, is_admin=True)
    entry.photos = photos
    entry.materials = materials
    return entry


# ---------------------------------------------------------------------------
# WRK-004: Update Daily Work Entry
# ---------------------------------------------------------------------------

@router.put("/{id}", response_model=DailyWorkEntryResponse, status_code=status.HTTP_200_OK)
async def update_work_entry(
    id: uuid.UUID,
    data: DailyWorkEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit another employee's work entry",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit {entry.status} entry",
        )

    updated_entry = await DailyWorkService.update_work_entry(
        session=db,
        entry_id=id,
        data=data,
        employee_id=emp.id,
        user_id=current_user.id,
        is_admin=False,
    )
    photos = await WorkPhotoService.list_photos(session=db, daily_work_entry_id=id, is_admin=True)
    materials = await MaterialTransactionService.list_material_transactions(session=db, daily_work_entry_id=id, is_admin=True)
    updated_entry.photos = photos
    updated_entry.materials = materials
    return updated_entry


# ---------------------------------------------------------------------------
# WRK-005: Submit Daily Work Entry
# ---------------------------------------------------------------------------

@router.post("/{id}/submit", response_model=DailyWorkEntryResponse, status_code=status.HTTP_200_OK)
async def submit_work_entry(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot submit another employee's work entry",
        )
    if entry.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entry already submitted",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit {entry.status} entry",
        )

    submitted_entry = await DailyWorkService.submit_work_entry(
        session=db,
        entry_id=id,
        employee_id=emp.id,
        user_id=current_user.id,
        is_admin=False,
    )
    photos = await WorkPhotoService.list_photos(session=db, daily_work_entry_id=id, is_admin=True)
    materials = await MaterialTransactionService.list_material_transactions(session=db, daily_work_entry_id=id, is_admin=True)
    submitted_entry.photos = photos
    submitted_entry.materials = materials
    return submitted_entry


# ---------------------------------------------------------------------------
# WRK-006: Upload Work Progress Photo
# ---------------------------------------------------------------------------

@router.post("/{id}/photos", response_model=WorkPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload photo for another employee's work entry",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add photos to {entry.status} entry",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file uploaded",
        )
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File size exceeds 10MB limit",
        )
    mime = detect_mime_type_from_bytes(contents)
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file type. Only JPEG/PNG/WEBP allowed.",
        )

    photo = await WorkPhotoService.upload_photo(
        session=db,
        daily_work_entry_id=id,
        file_data=contents,
        filename=file.filename,
        content_type=file.content_type,
        employee_id=emp.id,
        is_admin=False,
    )
    return photo


@router.get("/{id}/photos", response_model=List[WorkPhotoResponse], status_code=status.HTTP_200_OK)
async def list_photos(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    photos = await WorkPhotoService.list_photos(
        session=db,
        daily_work_entry_id=id,
        employee_id=emp.id if emp else None,
        supervisor_emp_id=emp.id if emp and current_user.role == "supervisor" else None,
        user_role=current_user.role,
        is_admin=current_user.role == "administrator",
    )
    return photos


# ---------------------------------------------------------------------------
# WRK-007: Add Material Transaction (supports combined multipart & JSON)
# ---------------------------------------------------------------------------

@router.post("/{id}/materials", response_model=MaterialTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_material_transaction(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add material to another employee's work entry",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add materials to {entry.status} entry",
        )

    content_type = request.headers.get("content-type", "")
    bill_file_bytes = None
    bill_filename = None
    bill_content_type = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        raw_mat_id = form.get("material_id")
        try:
            data = MaterialTransactionCreate(
                transaction_type=form.get("transaction_type"),
                item_name=form.get("item_name"),
                quantity=form.get("quantity"),
                amount=form.get("amount", Decimal("0.0")),
                material_id=uuid.UUID(str(raw_mat_id)) if raw_mat_id else None,
            )
        except ValidationError as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(val_err.errors()),
            )
        file_obj = form.get("bill_file") or form.get("file")
        if file_obj and hasattr(file_obj, "read"):
            contents = await file_obj.read()
            if len(contents) > 0:
                if len(contents) > 10 * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="File size exceeds 10MB limit",
                    )
                mime = detect_mime_type_from_bytes(contents)
                if mime not in ("image/jpeg", "image/png", "image/webp"):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Invalid file type. Only JPEG/PNG/WEBP allowed.",
                    )
                bill_file_bytes = contents
                bill_filename = getattr(file_obj, "filename", "bill.jpg")
                bill_content_type = getattr(file_obj, "content_type", mime)
    else:
        try:
            body = await request.json()
            data = MaterialTransactionCreate(**body)
        except ValidationError as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(val_err.errors()),
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid request body",
            )

    tx = await MaterialTransactionService.create_material_transaction(
        session=db,
        daily_work_entry_id=id,
        data=data,
        bill_file=bill_file_bytes,
        bill_filename=bill_filename,
        bill_content_type=bill_content_type,
        employee_id=emp.id,
        is_admin=False,
    )
    return tx


# ---------------------------------------------------------------------------
# WRK-008: Update Material Transaction
# ---------------------------------------------------------------------------

@router.put("/{id}/materials/{mid}", response_model=MaterialTransactionResponse, status_code=status.HTTP_200_OK)
async def update_material_transaction(
    id: uuid.UUID,
    mid: uuid.UUID,
    data: MaterialTransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit another employee's material transaction",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit materials on {entry.status} entry",
        )

    stmt_tx = select(MaterialTransaction).where(
        MaterialTransaction.id == mid,
        MaterialTransaction.daily_work_entry_id == id,
    )
    res_tx = await db.execute(stmt_tx)
    tx = res_tx.scalars().first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material transaction not found",
        )

    updated_tx = await MaterialTransactionService.update_material_transaction(
        session=db,
        daily_work_entry_id=id,
        transaction_id=mid,
        data=data,
        employee_id=emp.id,
        is_admin=False,
    )
    return updated_tx


# ---------------------------------------------------------------------------
# WRK-009: Upload Material Bill Image
# ---------------------------------------------------------------------------

@router.post("/{id}/materials/{mid}/bill", response_model=BillUploadResponse, status_code=status.HTTP_200_OK)
async def upload_bill_image(
    id: uuid.UUID,
    mid: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee role required",
        )
    emp = await get_optional_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found",
        )

    stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily work entry not found",
        )
    if entry.employee_id != emp.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload bill for another employee's material transaction",
        )
    if entry.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot upload bill for {entry.status} entry",
        )

    stmt_tx = select(MaterialTransaction).where(
        MaterialTransaction.id == mid,
        MaterialTransaction.daily_work_entry_id == id,
    )
    res_tx = await db.execute(stmt_tx)
    tx = res_tx.scalars().first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material transaction not found",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file uploaded",
        )
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File size exceeds 10MB limit",
        )
    mime = detect_mime_type_from_bytes(contents)
    if mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file type. Only JPEG/PNG/WEBP allowed.",
        )

    result = await MaterialTransactionService.upload_bill_image(
        session=db,
        daily_work_entry_id=id,
        transaction_id=mid,
        file_data=contents,
        filename=file.filename,
        content_type=file.content_type,
        employee_id=emp.id,
        is_admin=False,
    )
    return BillUploadResponse(id=result["id"], bill_image_url=result["bill_image_url"])


# ---------------------------------------------------------------------------
# List Materials for Entry
# ---------------------------------------------------------------------------

@router.get("/{id}/materials", response_model=List[MaterialTransactionResponse], status_code=status.HTTP_200_OK)
async def list_material_transactions(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await get_optional_employee(current_user, db)
    txs = await MaterialTransactionService.list_material_transactions(
        session=db,
        daily_work_entry_id=id,
        employee_id=emp.id if emp else None,
        supervisor_emp_id=emp.id if emp and current_user.role == "supervisor" else None,
        user_role=current_user.role,
        is_admin=current_user.role == "administrator",
    )
    return txs

from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import Any, BinaryIO, List, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import DailyWorkEntry, Material, MaterialTransaction
from app.modules.daily_work.schemas import MaterialTransactionCreate, MaterialTransactionUpdate
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


def _get_data_dict(data: Any) -> dict:
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    if hasattr(data, "dict"):
        return data.dict(exclude_unset=True)
    return vars(data)


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


class MaterialTransactionService:
    @staticmethod
    async def compute_high_value(
        session: AsyncSession,
        transaction_type: str,
        amount: float,
        material_id: Optional[uuid.UUID] = None,
        item_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[Material]]:
        """Compute the server-side is_high_value flag.

        Rules:
        1. If material_id is provided, lookup Material in master data:
           - is_high_value = (amount > material.purchase_approval_limit)
        2. If material_id is None, search master data by name (case-insensitive):
           - If a matching Material exists, use its purchase_approval_limit:
             is_high_value = (amount > matching_material.purchase_approval_limit)
        3. If no matching master material exists:
           - For 'purchased' items with amount > 0: default to is_high_value = True.
             Reasoning: Uncataloged purchases lack standard procurement limits and
             represent unvetted expenditure that must be reviewed by a supervisor.
           - For 'consumed' items or amount == 0: default to is_high_value = False.
        """
        if material_id:
            stmt = select(Material).where(Material.id == material_id)
            result = await session.execute(stmt)
            mat = result.scalars().first()
            if not mat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Material not found in master data",
                )
            is_high = float(amount) > float(mat.purchase_approval_limit)
            return is_high, mat

        if item_name:
            stmt = select(Material).where(
                func.lower(Material.name) == func.lower(item_name.strip())
            )
            result = await session.execute(stmt)
            mat = result.scalars().first()
            if mat:
                is_high = float(amount) > float(mat.purchase_approval_limit)
                return is_high, mat

        # No matching material record in master data
        if transaction_type == "purchased" and float(amount) > 0:
            return True, None
        return False, None

    @staticmethod
    async def create_material_transaction(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        data: Union[MaterialTransactionCreate, dict],
        bill_file: Optional[Union[bytes, BinaryIO]] = None,
        bill_filename: Optional[str] = None,
        bill_content_type: Optional[str] = None,
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        storage: Optional[FileStorageService] = None,
    ) -> MaterialTransaction:
        """Record a new material transaction (consumption or purchase)."""
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
                    detail="Cannot record material transaction for another employee's work entry",
                )

        # Status editability validation
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add material transaction for entry with status '{entry.status}'. Only draft and correction_required entries can be edited.",
            )

        data_dict = _get_data_dict(data)

        # Validate transaction_type
        tx_type = (data_dict.get("transaction_type") or "").lower().strip()
        if tx_type not in ("consumed", "purchased"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="transaction_type must be either 'consumed' or 'purchased'",
            )

        # Validate item_name
        item_name = (data_dict.get("item_name") or "").strip()
        if not item_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_name is required",
            )

        # Validate quantity
        try:
            quantity = float(data_dict.get("quantity", 0))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity must be a valid number",
            )
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity must be greater than zero",
            )

        # Validate amount
        try:
            amount = float(data_dict.get("amount", 0.0) or 0.0)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount must be a valid number",
            )
        if amount < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount must be non-negative",
            )

        material_id = data_dict.get("material_id")
        if isinstance(material_id, str):
            material_id = uuid.UUID(material_id)

        bill_image_url = data_dict.get("bill_image_url")

        # Handle optional bill photo upload
        if bill_file is not None:
            if isinstance(bill_file, (bytes, bytearray)):
                raw_bytes = bytes(bill_file)
            elif hasattr(bill_file, "read"):
                raw_bytes = bill_file.read()
                if hasattr(bill_file, "seek"):
                    bill_file.seek(0)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid bill file data: must be bytes or file-like object",
                )

            ext = _determine_extension(bill_filename, raw_bytes)
            date_str = entry.date.strftime("%Y-%m-%d") if entry.date else "unknown"
            tx_id = uuid.uuid4()
            dest_path = f"materials/{entry.employee_id}/{date_str}/{entry.id}/{tx_id}{ext}"

            storage_client = storage or get_file_storage()
            try:
                bill_image_url = await storage_client.upload_file(
                    file_data=bill_file,
                    destination_path=dest_path,
                    content_type=bill_content_type,
                )
            except (InvalidFileTypeError, FileSizeLimitExceededError, FileStorageError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
        else:
            tx_id = uuid.uuid4()

        # Compute is_high_value
        is_high_value, matched_mat = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type=tx_type,
            amount=amount,
            material_id=material_id,
            item_name=item_name,
        )

        if matched_mat and material_id is None:
            material_id = matched_mat.id

        tx = MaterialTransaction(
            id=tx_id,
            daily_work_entry_id=entry.id,
            material_id=material_id,
            site_id=entry.site_id,
            transaction_type=tx_type,
            item_name=item_name,
            quantity=quantity,
            amount=amount,
            bill_image_url=bill_image_url,
            is_high_value=is_high_value,
            status="draft",
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx

    @staticmethod
    async def list_material_transactions(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        is_admin: bool = False,
    ) -> List[MaterialTransaction]:
        """List all material transactions linked to a daily work entry."""
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == daily_work_entry_id)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Access authorization check
        if not (is_admin or user_role in ("administrator", "director")):
            if user_role == "employee":
                if employee_id and entry.employee_id != employee_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot access material transactions for another employee's work entry",
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
                        detail="Cannot access material transactions for another employee's work entry",
                    )
            elif employee_id:
                if entry.employee_id != employee_id:
                    is_auth = await DailyWorkService.is_supervisor_authorized(
                        session, employee_id, entry.employee_id, site_id=entry.site_id
                    )
                    if not is_auth:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Cannot access material transactions for another employee's work entry",
                        )

        tx_stmt = (
            select(MaterialTransaction)
            .where(MaterialTransaction.daily_work_entry_id == daily_work_entry_id)
            .order_by(MaterialTransaction.created_at.asc())
        )
        tx_res = await session.execute(tx_stmt)
        return list(tx_res.scalars().all())

    @staticmethod
    async def delete_material_transaction(
        session: AsyncSession,
        transaction_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        storage: Optional[FileStorageService] = None,
    ) -> bool:
        """Delete a material transaction.

        Can only be deleted by the recording employee or admin, and only while
        the entry is in an editable status ('draft' or 'correction_required').
        """
        stmt = select(MaterialTransaction).where(MaterialTransaction.id == transaction_id)
        result = await session.execute(stmt)
        tx = result.scalars().first()
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material transaction not found",
            )

        entry_stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == tx.daily_work_entry_id)
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
                detail=f"Cannot delete material transaction for entry with status '{entry.status}'. Material transactions can only be deleted while entry is in draft or correction_required status.",
            )

        # Ownership authorization check
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete material transaction recorded by another employee",
                )

        # Remove bill image file from storage if present
        if tx.bill_image_url:
            storage_client = storage or get_file_storage()
            storage_path = _extract_storage_path(tx.bill_image_url)
            if storage_path:
                try:
                    await storage_client.delete_file(storage_path)
                except FileNotFoundStorageError:
                    pass

        await session.delete(tx)
        await session.commit()
        return True

    @staticmethod
    async def get_material_transaction(
        session: AsyncSession,
        transaction_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        is_admin: bool = False,
    ) -> MaterialTransaction:
        """Retrieve a single material transaction by ID with access control."""
        stmt = select(MaterialTransaction).where(MaterialTransaction.id == transaction_id)
        result = await session.execute(stmt)
        tx = result.scalars().first()
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material transaction not found",
            )

        await MaterialTransactionService.list_material_transactions(
            session=session,
            daily_work_entry_id=tx.daily_work_entry_id,
            employee_id=employee_id,
            supervisor_emp_id=supervisor_emp_id,
            user_role=user_role,
            is_admin=is_admin,
        )
        return tx

    @staticmethod
    async def update_material_transaction(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        transaction_id: uuid.UUID,
        data: Union[MaterialTransactionUpdate, dict],
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> MaterialTransaction:
        """Update an existing material transaction."""
        stmt = (
            select(MaterialTransaction)
            .where(
                MaterialTransaction.id == transaction_id,
                MaterialTransaction.daily_work_entry_id == daily_work_entry_id,
            )
        )
        res = await session.execute(stmt)
        tx = res.scalars().first()
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material transaction not found",
            )

        entry_stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == daily_work_entry_id)
        entry_res = await session.execute(entry_stmt)
        entry = entry_res.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Status constraint
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit material transaction for entry with status '{entry.status}'. Material transactions can only be edited while entry is in draft or correction_required status.",
            )

        # Ownership authorization check
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot edit material transaction recorded by another employee",
                )

        data_dict = _get_data_dict(data)

        if "transaction_type" in data_dict and data_dict["transaction_type"] is not None:
            tx_type = str(data_dict["transaction_type"]).lower().strip()
            if tx_type not in ("consumed", "purchased"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="transaction_type must be either 'consumed' or 'purchased'",
                )
            tx.transaction_type = tx_type

        if "item_name" in data_dict and data_dict["item_name"] is not None:
            item_name = str(data_dict["item_name"]).strip()
            if not item_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="item_name cannot be empty",
                )
            tx.item_name = item_name

        if "quantity" in data_dict and data_dict["quantity"] is not None:
            try:
                qty = float(data_dict["quantity"])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quantity must be a valid number",
                )
            if qty <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quantity must be greater than zero",
                )
            tx.quantity = qty

        if "amount" in data_dict and data_dict["amount"] is not None:
            try:
                amt = float(data_dict["amount"])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="amount must be a valid number",
                )
            if amt < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="amount must be non-negative",
                )
            tx.amount = amt

        if "material_id" in data_dict:
            mat_id = data_dict["material_id"]
            if isinstance(mat_id, str) and mat_id.strip():
                tx.material_id = uuid.UUID(mat_id.strip())
            elif mat_id is None:
                tx.material_id = None
            elif isinstance(mat_id, uuid.UUID):
                tx.material_id = mat_id

        if "bill_image_url" in data_dict and data_dict["bill_image_url"] is not None:
            tx.bill_image_url = data_dict["bill_image_url"]

        # Recompute is_high_value
        is_high_value, matched_mat = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type=tx.transaction_type,
            amount=tx.amount,
            material_id=tx.material_id,
            item_name=tx.item_name,
        )
        if matched_mat and tx.material_id is None:
            tx.material_id = matched_mat.id
        tx.is_high_value = is_high_value

        tx.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tx)
        return tx

    @staticmethod
    async def upload_bill_image(
        session: AsyncSession,
        daily_work_entry_id: uuid.UUID,
        transaction_id: uuid.UUID,
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        storage: Optional[FileStorageService] = None,
    ) -> dict:
        """Upload a receipt/bill image for a material transaction."""
        stmt = (
            select(MaterialTransaction)
            .where(
                MaterialTransaction.id == transaction_id,
                MaterialTransaction.daily_work_entry_id == daily_work_entry_id,
            )
        )
        res = await session.execute(stmt)
        tx = res.scalars().first()
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material transaction not found",
            )

        entry_stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == daily_work_entry_id)
        entry_res = await session.execute(entry_stmt)
        entry = entry_res.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Status constraint
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot upload bill for entry with status '{entry.status}'. Bills can only be uploaded while entry is in draft or correction_required status.",
            )

        # Ownership authorization check
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot upload bill for material transaction recorded by another employee",
                )

        if isinstance(file_data, (bytes, bytearray)):
            raw_bytes = bytes(file_data)
        elif hasattr(file_data, "read"):
            raw_bytes = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bill file data: must be bytes or file-like object",
            )

        ext = _determine_extension(filename, raw_bytes)
        date_str = entry.date.strftime("%Y-%m-%d") if entry.date else "unknown"
        dest_path = f"materials/{entry.employee_id}/{date_str}/{entry.id}/{tx.id}{ext}"

        storage_client = storage or get_file_storage()
        try:
            bill_image_url = await storage_client.upload_file(
                file_data=file_data,
                destination_path=dest_path,
                content_type=content_type,
            )
        except (InvalidFileTypeError, FileSizeLimitExceededError, FileStorageError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        tx.bill_image_url = bill_image_url
        tx.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tx)
        return {"id": tx.id, "bill_image_url": tx.bill_image_url}

    # Aliases
    create = create_material_transaction
    create_transaction = create_material_transaction
    update = update_material_transaction
    update_transaction = update_material_transaction
    upload_bill = upload_bill_image
    list = list_material_transactions
    list_transactions = list_material_transactions
    get = get_material_transaction
    get_transaction = get_material_transaction
    delete = delete_material_transaction
    delete_transaction = delete_material_transaction

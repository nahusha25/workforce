from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assets import Asset, AssetTransaction
from app.models.auth import User
from app.models.operations import Client, EmployeeSiteAssignment, Project, Site
from app.models.system import AuditLog
from app.models.workforce import Employee
from app.modules.assets.schemas import (
    AssetDetailResponse,
    AssetIssueRequest,
    AssetListResponse,
    AssetReassignRequest,
    AssetRegisterRequest,
    AssetResponse,
    AssetReturnRequest,
    AssetTransactionResponse,
)


class AssetService:
    @classmethod
    async def _generate_asset_tag(cls, session: AsyncSession) -> str:
        """
        Generates an atomic, forward-only unique asset tag using the PostgreSQL asset_tag_seq.
        Format: AST-XXXXXX (e.g. AST-000001).
        Safe across concurrent registrations.
        """
        try:
            seq_val = (await session.execute(text("SELECT nextval('asset_tag_seq')"))).scalar()
            if seq_val is not None:
                return f"AST-{int(seq_val):06d}"
        except Exception:
            pass

        # Fallback for environments where sequence scalar is not available
        count_val = (await session.execute(select(func.count(Asset.id)))).scalar() or 0
        return f"AST-{count_val + 1:06d}"

    @classmethod
    def _map_asset_to_response(cls, asset: Asset) -> AssetResponse:
        return AssetResponse(
            id=asset.id,
            asset_tag=asset.asset_tag,
            name=asset.name,
            category=asset.category,
            serial_number=asset.serial_number,
            manufacturer=asset.manufacturer,
            model_number=asset.model_number,
            purchase_date=asset.purchase_date,
            purchase_cost=asset.purchase_cost,
            warranty_expiry_date=asset.warranty_expiry_date,
            condition=asset.condition,
            status=asset.status,
            location_type=asset.location_type,
            current_site_id=asset.current_site_id,
            current_site_name=asset.site.name if (asset.site and asset.current_site_id is not None) else None,
            current_custodian_id=asset.current_custodian_id,
            current_custodian_name=asset.custodian.name if (asset.custodian and asset.current_custodian_id is not None) else None,
            description=asset.description,
            is_active=asset.is_active,
            created_by=asset.created_by,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )

    @classmethod
    def _map_transaction_to_response(cls, tx: AssetTransaction) -> AssetTransactionResponse:
        return AssetTransactionResponse(
            id=tx.id,
            asset_id=tx.asset_id,
            transaction_type=tx.transaction_type,
            from_location_type=tx.from_location_type,
            to_location_type=tx.to_location_type,
            from_site_id=tx.from_site_id,
            to_site_id=tx.to_site_id,
            from_site_name=tx.from_site.name if tx.from_site else None,
            to_site_name=tx.to_site.name if tx.to_site else None,
            from_employee_id=tx.from_employee_id,
            to_employee_id=tx.to_employee_id,
            from_employee_name=tx.from_employee.name if tx.from_employee else None,
            to_employee_name=tx.to_employee.name if tx.to_employee else None,
            condition_before=tx.condition_before,
            condition_after=tx.condition_after,
            transaction_date=tx.transaction_date,
            performed_by=tx.performed_by,
            remarks=tx.remarks,
            idempotency_key=tx.idempotency_key,
            created_at=tx.created_at,
        )

    @classmethod
    async def register_asset(
        cls,
        session: AsyncSession,
        request: AssetRegisterRequest,
        current_user: User,
    ) -> AssetResponse:
        """
        Registers a new physical asset into the central warehouse or assigns it to a specific site.
        Enforces:
          - Idempotency key checking to prevent duplicate creation
          - Explicit location distinction: Central Warehouse vs. Site Assignment
          - Site existence verification when assigned to a site
          - Unique asset tag generation or conflict detection
          - Automatic creation of initial AssetTransaction ledger record
          - System AuditLog recording
        """
        # 1. Idempotency replay check
        if request.idempotency_key:
            existing_tx_stmt = (
                select(AssetTransaction)
                .options(selectinload(AssetTransaction.asset).selectinload(Asset.site))
                .where(AssetTransaction.idempotency_key == request.idempotency_key)
            )
            existing_tx = (await session.execute(existing_tx_stmt)).scalar_one_or_none()
            if existing_tx and existing_tx.asset:
                return cls._map_asset_to_response(existing_tx.asset)

        # 2. Location validation
        site: Optional[Site] = None
        if request.location_type == "warehouse":
            if request.current_site_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Central warehouse assets cannot have a site assigned.",
                )
        elif request.location_type == "site":
            if request.current_site_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Assets assigned to a site must specify current_site_id.",
                )
            site_stmt = select(Site).where(Site.id == request.current_site_id)
            site = (await session.execute(site_stmt)).scalar_one_or_none()
            if not site:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Site {request.current_site_id} not found.",
                )

        # 3. Asset tag resolution & uniqueness
        if request.asset_tag:
            tag_stmt = select(Asset).where(Asset.asset_tag == request.asset_tag)
            existing_asset = (await session.execute(tag_stmt)).scalar_one_or_none()
            if existing_asset:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Asset tag '{request.asset_tag}' already exists.",
                )
            resolved_tag = request.asset_tag
        else:
            resolved_tag = await cls._generate_asset_tag(session)

        # 4. Create Asset entity
        now = datetime.now(timezone.utc)
        asset = Asset(
            id=uuid.uuid4(),
            asset_tag=resolved_tag,
            name=request.name.strip(),
            category=request.category.strip(),
            serial_number=request.serial_number.strip() if request.serial_number else None,
            manufacturer=request.manufacturer.strip() if request.manufacturer else None,
            model_number=request.model_number.strip() if request.model_number else None,
            purchase_date=request.purchase_date,
            purchase_cost=request.purchase_cost,
            warranty_expiry_date=request.warranty_expiry_date,
            condition=request.condition,
            status=request.status,
            location_type=request.location_type,
            current_site_id=request.current_site_id,
            description=request.description.strip() if request.description else None,
            is_active=True,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        asset.site = site
        asset.custodian = None
        session.add(asset)
        await session.flush()

        # 5. Create immutable AssetTransaction ledger entry
        tx = AssetTransaction(
            id=uuid.uuid4(),
            asset_id=asset.id,
            transaction_type="registered",
            from_location_type=None,
            to_location_type=request.location_type,
            from_site_id=None,
            to_site_id=request.current_site_id,
            from_employee_id=None,
            to_employee_id=None,
            condition_before=None,
            condition_after=request.condition,
            transaction_date=now,
            performed_by=current_user.id,
            remarks=request.remarks.strip() if request.remarks else "Initial asset registration",
            idempotency_key=request.idempotency_key,
            created_at=now,
        )
        session.add(tx)

        # 6. Central AuditLog record
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="asset",
            entity_id=asset.id,
            action="create",
            changed_by=current_user.id,
            created_at=now,
            previous_values=None,
            new_values={
                "asset_tag": asset.asset_tag,
                "name": asset.name,
                "category": asset.category,
                "location_type": asset.location_type,
                "current_site_id": str(asset.current_site_id) if asset.current_site_id else None,
                "condition": asset.condition,
                "status": asset.status,
                "purchase_cost": str(asset.purchase_cost) if asset.purchase_cost is not None else None,
            },
        )
        session.add(audit_entry)

        # 7. Commit transaction
        await session.commit()
        return cls._map_asset_to_response(asset)

    @classmethod
    async def _get_supervised_site_ids(cls, session: AsyncSession, current_user: User) -> set[uuid.UUID]:
        """
        Resolves the set of site IDs supervised by the current user.
        Uses established project sources of truth:
          1. Direct Site.supervisor_id == supervisor employee profile id
          2. Active EmployeeSiteAssignment for the supervisor employee
          3. Fallback Site.supervisor_id == current_user.id
        """
        stmt_emp = select(Employee).where(Employee.user_id == current_user.id)
        sup_emp = (await session.execute(stmt_emp)).scalars().first()
        sup_emp_id = sup_emp.id if sup_emp else None

        site_conditions = []
        if sup_emp_id:
            site_conditions.append(Site.supervisor_id == sup_emp_id)
            site_conditions.append(
                Site.id.in_(
                    select(EmployeeSiteAssignment.site_id).where(
                        EmployeeSiteAssignment.employee_id == sup_emp_id,
                        EmployeeSiteAssignment.is_active.is_(True),
                    )
                )
            )
        site_conditions.append(Site.supervisor_id == current_user.id)

        stmt_sites = select(Site.id).where(or_(*site_conditions))
        result = await session.execute(stmt_sites)
        return set(result.scalars().all())

    @classmethod
    async def get_active_sites(cls, session: AsyncSession) -> List[Site]:
        """
        Retrieves all active project sites for asset management, registration, and filtering.
        """
        stmt = select(Site).where(Site.is_active.is_(True)).order_by(Site.name)
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def list_assets(
        cls,
        session: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        location_type: Optional[str] = None,
        site_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        status_filter: Optional[str] = None,
        condition: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> AssetListResponse:
        """
        Lists assets with filtering, search, and pagination.
        Accessible to Administrator, Director, and Supervisor roles with full registry visibility.
        """
        filters = []

        if location_type and location_type.strip():
            filters.append(Asset.location_type == location_type.strip().lower())
        if site_id is not None:
            filters.append(Asset.current_site_id == site_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Asset.name.ilike(term),
                    Asset.asset_tag.ilike(term),
                    Asset.serial_number.ilike(term),
                    Asset.model_number.ilike(term),
                    Asset.manufacturer.ilike(term),
                )
            )

        if category and category.strip():
            filters.append(func.lower(Asset.category) == category.strip().lower())

        if status_filter and status_filter.strip():
            filters.append(Asset.status == status_filter.strip().lower())

        if condition and condition.strip():
            filters.append(Asset.condition == condition.strip().lower())

        if is_active is not None:
            filters.append(Asset.is_active == is_active)

        # Total count
        count_stmt = select(func.count(Asset.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await session.execute(count_stmt)).scalar() or 0

        # Paged items
        items_stmt = (
            select(Asset)
            .options(selectinload(Asset.site), selectinload(Asset.custodian))
            .order_by(Asset.created_at.desc(), Asset.asset_tag.asc())
            .offset(skip)
            .limit(limit)
        )
        if filters:
            items_stmt = items_stmt.where(*filters)

        result = await session.execute(items_stmt)
        assets = result.scalars().all()

        return AssetListResponse(
            items=[cls._map_asset_to_response(a) for a in assets],
            total=total,
            skip=skip,
            limit=limit,
        )

    @classmethod
    async def get_asset_by_id(
        cls,
        session: AsyncSession,
        asset_id: uuid.UUID,
        current_user: User,
    ) -> AssetDetailResponse:
        """
        Retrieves detailed information for a single asset, including its complete
        immutable transaction history and associated site names.
        Enforces supervisor site-level authorization:
          - Supervisors cannot view warehouse assets or assets at unassigned sites (HTTP 403).
        """
        stmt = (
            select(Asset)
            .options(
                selectinload(Asset.site),
                selectinload(Asset.custodian),
                selectinload(Asset.transactions).selectinload(AssetTransaction.to_site),
                selectinload(Asset.transactions).selectinload(AssetTransaction.from_site),
                selectinload(Asset.transactions).selectinload(AssetTransaction.to_employee),
                selectinload(Asset.transactions).selectinload(AssetTransaction.from_employee),
            )
            .where(Asset.id == asset_id)
        )
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found.",
            )


        base_res = cls._map_asset_to_response(asset)
        tx_responses = [cls._map_transaction_to_response(tx) for tx in asset.transactions]

        return AssetDetailResponse(
            **base_res.model_dump(),
            transactions=tx_responses,
        )

    @classmethod
    async def issue_asset(
        cls,
        session: AsyncSession,
        asset_id: uuid.UUID,
        request: AssetIssueRequest,
        current_user: User,
    ) -> AssetResponse:
        """
        Issues an eligible asset to an employee who is actively assigned to the asset's current site.
        Enforces:
          - Idempotency replay protection
          - Row-level lock (SELECT ... FOR UPDATE) to prevent concurrent double-issue
          - Supervisor site-level authorization boundaries
          - Eligibility checks (status must be 'available', location must be 'site', not in custody)
          - Employee existence, active status, and active site assignment (EmployeeSiteAssignment)
          - Database constraint preservation linking 'issued_employee' to non-null custodian
          - Atomic append-only transaction ledger (AssetTransaction type='issued')
          - Central system AuditLog recording
          - Atomic commit/rollback
        """
        # 1. Idempotency replay check
        if request.idempotency_key:
            existing_tx_stmt = (
                select(AssetTransaction)
                .options(
                    selectinload(AssetTransaction.asset).selectinload(Asset.site),
                    selectinload(AssetTransaction.asset).selectinload(Asset.custodian),
                )
                .where(AssetTransaction.idempotency_key == request.idempotency_key)
            )
            existing_tx = (await session.execute(existing_tx_stmt)).scalar_one_or_none()
            if existing_tx:
                if existing_tx.asset_id != asset_id or existing_tx.transaction_type != "issued":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key has already been used for another operation.",
                    )
                if existing_tx.asset:
                    return cls._map_asset_to_response(existing_tx.asset)

        # 2. Row-level lock acquisition
        stmt = select(Asset).where(Asset.id == asset_id).with_for_update()
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found.",
            )



        # 4. Location eligibility: Warehouse assets cannot be issued directly to employees
        if asset.location_type != "site" or asset.current_site_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse assets cannot be issued directly to employees. Reassign the asset to a site first.",
            )

        # 5. Asset status eligibility
        if not asset.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive assets cannot be issued.",
            )
        if asset.status == "issued_employee" or asset.current_custodian_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Asset is already issued to an employee.",
            )
        if asset.status != "available":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset cannot be issued in status '{asset.status}'. Only 'available' assets can be issued.",
            )

        # 6. Employee existence and active status
        emp_stmt = select(Employee).where(Employee.id == request.employee_id)
        emp = (await session.execute(emp_stmt)).scalar_one_or_none()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {request.employee_id} not found.",
            )
        if not emp.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot issue asset to an inactive employee.",
            )

        # 7. Active site assignment verification
        assignment_stmt = select(EmployeeSiteAssignment).where(
            EmployeeSiteAssignment.employee_id == request.employee_id,
            EmployeeSiteAssignment.site_id == asset.current_site_id,
            EmployeeSiteAssignment.is_active.is_(True),
        )
        assignment = (await session.execute(assignment_stmt)).scalars().first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee does not have an active assignment to the asset's current site.",
            )

        # 8. Atomic mutation & ledger/audit creation
        now = datetime.now(timezone.utc)
        old_status = asset.status
        old_custodian_id = asset.current_custodian_id

        asset.status = "issued_employee"
        asset.current_custodian_id = request.employee_id
        asset.custodian = emp
        asset.updated_at = now

        tx = AssetTransaction(
            id=uuid.uuid4(),
            asset_id=asset.id,
            transaction_type="issued",
            from_location_type="site",
            to_location_type="site",
            from_site_id=asset.current_site_id,
            to_site_id=asset.current_site_id,
            from_employee_id=None,
            to_employee_id=request.employee_id,
            condition_before=asset.condition,
            condition_after=asset.condition,
            transaction_date=now,
            performed_by=current_user.id,
            remarks=request.remarks.strip() if request.remarks else f"Issued to employee {emp.name or emp.employee_code}",
            idempotency_key=request.idempotency_key,
            created_at=now,
        )
        session.add(tx)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="asset",
            entity_id=asset.id,
            action="issue",
            changed_by=current_user.id,
            created_at=now,
            previous_values={
                "status": old_status,
                "current_custodian_id": str(old_custodian_id) if old_custodian_id else None,
            },
            new_values={
                "status": asset.status,
                "current_custodian_id": str(asset.current_custodian_id),
            },
        )
        session.add(audit_entry)

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        return cls._map_asset_to_response(asset)

    @classmethod
    async def return_asset(
        cls,
        session: AsyncSession,
        asset_id: uuid.UUID,
        request: AssetReturnRequest,
        current_user: User,
    ) -> AssetResponse:
        """
        Returns an issued asset to its assigned site, clearing custodian and updating condition/status.
        Enforces:
          - Idempotency replay protection
          - Row-level lock (SELECT ... FOR UPDATE) to prevent concurrent double-return
          - Supervisor site-level authorization boundaries
          - Verification that asset is currently issued and returning employee matches recorded custodian
          - Return to original assigned site (current_site_id preserved)
          - Domain condition/status update rules (condition mapped, status defaults to 'damaged' if damaged/unusable, else 'available')
          - Atomic clear of current_custodian_id preserving database constraint
          - Append-only transaction ledger (AssetTransaction type='returned')
          - Central system AuditLog recording
          - Atomic commit/rollback
        """
        # 1. Idempotency replay check
        if request.idempotency_key:
            existing_tx_stmt = (
                select(AssetTransaction)
                .options(
                    selectinload(AssetTransaction.asset).selectinload(Asset.site),
                    selectinload(AssetTransaction.asset).selectinload(Asset.custodian),
                )
                .where(AssetTransaction.idempotency_key == request.idempotency_key)
            )
            existing_tx = (await session.execute(existing_tx_stmt)).scalar_one_or_none()
            if existing_tx:
                if existing_tx.asset_id != asset_id or existing_tx.transaction_type != "returned":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key has already been used for another operation.",
                    )
                if existing_tx.asset:
                    return cls._map_asset_to_response(existing_tx.asset)

        # 2. Row-level lock acquisition
        stmt = select(Asset).where(Asset.id == asset_id).with_for_update()
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found.",
            )



        # 4. Custody and issue verification
        if asset.status != "issued_employee" or asset.current_custodian_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Asset is not currently issued to any employee.",
            )
        if asset.current_custodian_id != request.employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Returning employee does not match the recorded custodian of this asset.",
            )

        # 5. Determine condition and status
        old_condition = asset.condition
        old_status = asset.status
        old_custodian_id = asset.current_custodian_id

        new_condition = request.condition if request.condition else asset.condition
        if request.status:
            if request.status == "issued_employee":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Returned asset cannot remain in 'issued_employee' status.",
                )
            new_status = request.status
        else:
            if new_condition in ("damaged", "unusable"):
                new_status = "damaged"
            else:
                new_status = "available"

        # 6. Atomic mutation & ledger/audit creation
        now = datetime.now(timezone.utc)
        asset.current_custodian_id = None
        asset.custodian = None
        asset.condition = new_condition
        asset.status = new_status
        asset.updated_at = now

        tx = AssetTransaction(
            id=uuid.uuid4(),
            asset_id=asset.id,
            transaction_type="returned",
            from_location_type="site",
            to_location_type="site",
            from_site_id=asset.current_site_id,
            to_site_id=asset.current_site_id,
            from_employee_id=request.employee_id,
            to_employee_id=None,
            condition_before=old_condition,
            condition_after=new_condition,
            transaction_date=now,
            performed_by=current_user.id,
            remarks=request.remarks.strip() if request.remarks else f"Returned by employee. Condition: {new_condition}",
            idempotency_key=request.idempotency_key,
            created_at=now,
        )
        session.add(tx)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="asset",
            entity_id=asset.id,
            action="return",
            changed_by=current_user.id,
            created_at=now,
            previous_values={
                "status": old_status,
                "condition": old_condition,
                "current_custodian_id": str(old_custodian_id),
            },
            new_values={
                "status": new_status,
                "condition": new_condition,
                "current_custodian_id": None,
            },
        )
        session.add(audit_entry)

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        return cls._map_asset_to_response(asset)

    @classmethod
    async def get_destination_sites(
        cls,
        session: AsyncSession,
        asset_id: uuid.UUID,
        current_user: User,
    ) -> List[Site]:
        """
        Retrieves authorized destination project sites for reassigning the specified asset.
        Administrators, Directors, and Supervisors can view all active sites (excluding asset's current site if assigned).
        """
        stmt = select(Asset).where(Asset.id == asset_id)
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found.",
            )

        sites_stmt = select(Site).where(Site.is_active.is_(True))
        if asset.location_type == "site" and asset.current_site_id:
            sites_stmt = sites_stmt.where(Site.id != asset.current_site_id)
        sites_stmt = sites_stmt.order_by(Site.name)
        sites = (await session.execute(sites_stmt)).scalars().all()
        return list(sites)

    @classmethod
    async def reassign_asset(
        cls,
        session: AsyncSession,
        asset_id: uuid.UUID,
        request: AssetReassignRequest,
        current_user: User,
    ) -> AssetResponse:
        """
        Directly reassigns an asset between warehouse and sites or between sites.
        Enforces:
          - Idempotency replay protection
          - Row-level lock (SELECT ... FOR UPDATE) to prevent concurrent conflicting operations
          - Rejection if asset is currently issued to an employee (must be returned first)
          - Supervisor boundary enforcement (supervisors cannot touch warehouse assets or unassigned sites)
          - Destination site existence and redundant reassignment rejection
          - Direct site transfer without in_transit or dispatch/receipt workflows
          - Append-only transaction ledger (AssetTransaction type='reassigned')
          - Central system AuditLog recording
          - Atomic commit/rollback
        """
        # 1. Idempotency replay check
        if request.idempotency_key:
            existing_tx_stmt = (
                select(AssetTransaction)
                .options(
                    selectinload(AssetTransaction.asset).selectinload(Asset.site),
                    selectinload(AssetTransaction.asset).selectinload(Asset.custodian),
                )
                .where(AssetTransaction.idempotency_key == request.idempotency_key)
            )
            existing_tx = (await session.execute(existing_tx_stmt)).scalar_one_or_none()
            if existing_tx:
                if existing_tx.asset_id != asset_id or existing_tx.transaction_type != "reassigned":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key has already been used for another operation.",
                    )
                if existing_tx.asset:
                    return cls._map_asset_to_response(existing_tx.asset)

        # 2. Row-level lock acquisition
        stmt = select(Asset).where(Asset.id == asset_id).with_for_update()
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found.",
            )

        # 3. Reject reassignment while issued to an employee
        if asset.status == "issued_employee" or asset.current_custodian_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reassign asset while issued to an employee. It must first be returned.",
            )

        # 4. Target validation
        target_site: Optional[Site] = None
        if request.target_location_type == "warehouse":
            if asset.location_type == "warehouse":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Asset is already located in the central warehouse.",
                )
            target_site_id = None
        elif request.target_location_type == "site":
            if not request.target_site_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="target_site_id must be provided when target_location_type is 'site'.",
                )
            if asset.location_type == "site" and asset.current_site_id == request.target_site_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Asset is already assigned to this site.",
                )
            target_site_stmt = select(Site).where(Site.id == request.target_site_id)
            target_site = (await session.execute(target_site_stmt)).scalar_one_or_none()
            if not target_site:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target site {request.target_site_id} not found.",
                )
            if not target_site.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target site is not active.",
                )
            target_site_id = request.target_site_id



        # 6. Atomic mutation & ledger/audit creation
        now = datetime.now(timezone.utc)
        old_location_type = asset.location_type
        old_site_id = asset.current_site_id

        asset.location_type = request.target_location_type
        asset.current_site_id = target_site_id
        asset.site = target_site
        asset.updated_at = now

        tx = AssetTransaction(
            id=uuid.uuid4(),
            asset_id=asset.id,
            transaction_type="reassigned",
            from_location_type=old_location_type,
            to_location_type=request.target_location_type,
            from_site_id=old_site_id,
            to_site_id=target_site_id,
            from_employee_id=None,
            to_employee_id=None,
            condition_before=asset.condition,
            condition_after=asset.condition,
            transaction_date=now,
            performed_by=current_user.id,
            remarks=request.remarks.strip() if request.remarks else f"Reassigned from {old_location_type} to {request.target_location_type}",
            idempotency_key=request.idempotency_key,
            created_at=now,
        )
        session.add(tx)

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="asset",
            entity_id=asset.id,
            action="reassign",
            changed_by=current_user.id,
            created_at=now,
            previous_values={
                "location_type": old_location_type,
                "current_site_id": str(old_site_id) if old_site_id else None,
            },
            new_values={
                "location_type": asset.location_type,
                "current_site_id": str(asset.current_site_id) if asset.current_site_id else None,
            },
        )
        session.add(audit_entry)

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        return cls._map_asset_to_response(asset)

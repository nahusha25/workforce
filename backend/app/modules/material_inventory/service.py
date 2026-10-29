from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence, Set

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.material_inventory import MaterialStock, MaterialStockMovement
from app.models.operations import EmployeeSiteAssignment, Material, Site
from app.models.system import AuditLog
from app.models.workforce import Employee
from app.modules.material_inventory.schemas import (
    InventorySiteResponse,
    MaterialSiteStockResponse,
    SiteInventoryItemResponse,
    SiteInventoryListResponse,
    StockInwardRequest,
    StockInwardResponse,
    StockMovementHistoryResponse,
    StockMovementItemResponse,
)


class MaterialInventoryService:
    """
    Core service handling consumable material inventory tracking,
    stock inward receipts, ledger auditing, and site balance queries.
    """

    @classmethod
    async def get_supervised_site_ids(cls, session: AsyncSession, current_user: User) -> Set[uuid.UUID]:
        """
        Resolves the set of site IDs supervised by the current user.
        Sources of truth:
          1. Direct Site.supervisor_id == supervisor employee profile id
          2. Active EmployeeSiteAssignment for the supervisor employee
          3. Direct Site.supervisor_id == current_user.id
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
    async def get_authorized_inventory_sites(
        cls,
        session: AsyncSession,
        current_user: User,
    ) -> Sequence[Site]:
        """
        Retrieves active sites authorized for material inventory tracking:
        - Administrator & Director: all active sites.
        - Supervisor: active sites supervised by or assigned to the supervisor.
        - Employee & others: raises 403 Forbidden.
        """
        if current_user.role not in ("administrator", "director", "supervisor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access inventory sites.",
            )

        if current_user.role in ("administrator", "director"):
            stmt = select(Site).where(Site.is_active.is_(True)).order_by(Site.name)
            res = await session.execute(stmt)
            return res.scalars().all()

        supervised_ids = await cls.get_supervised_site_ids(session, current_user)
        if not supervised_ids:
            return []

        stmt = (
            select(Site)
            .where(
                Site.id.in_(supervised_ids),
                Site.is_active.is_(True),
            )
            .order_by(Site.name)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def record_stock_inward(
        cls,
        session: AsyncSession,
        request: StockInwardRequest,
        current_user: User,
    ) -> StockInwardResponse:
        """
        Records stock received at a specific client site with strict concurrency safety,
        positive Decimal quantities, idempotent retry handling, and centralized audit logging.
        """
        # 1. Permission check
        if current_user.role not in ("administrator", "director", "supervisor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to record stock inward.",
            )

        if current_user.role == "supervisor":
            supervised_sites = await cls.get_supervised_site_ids(session, current_user)
            if request.site_id not in supervised_sites:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor is not authorized to record stock inward for this site.",
                )

        # 2. Validate quantity strictly positive
        if request.quantity is None or request.quantity <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inward stock quantity must be a positive decimal greater than 0.",
            )

        # 3. Validate site existence
        stmt_site = select(Site).where(Site.id == request.site_id)
        site = (await session.execute(stmt_site)).scalar_one_or_none()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {request.site_id} not found.",
            )

        # 4. Validate material existence and active status
        stmt_mat = select(Material).where(Material.id == request.material_id)
        material = (await session.execute(stmt_mat)).scalar_one_or_none()
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material with id {request.material_id} not found.",
            )
        if not material.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Material '{material.name}' is inactive and cannot receive stock.",
            )

        # 5. Check idempotency key before attempting mutation
        stmt_idem = (
            select(MaterialStockMovement)
            .options(
                selectinload(MaterialStockMovement.material),
            )
            .where(MaterialStockMovement.idempotency_key == request.idempotency_key)
        )
        existing_mvt = (await session.execute(stmt_idem)).scalar_one_or_none()
        if existing_mvt:
            # Verify identical parameters for replay
            if (
                existing_mvt.site_id == request.site_id
                and existing_mvt.material_id == request.material_id
                and existing_mvt.quantity == request.quantity
                and existing_mvt.movement_type == "inward"
            ):
                return cls._map_movement_to_response(existing_mvt, material)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency conflict: idempotency_key '{request.idempotency_key}' already used with different parameters.",
            )

        # 6. Retrieve previous balance for audit logging
        stmt_prev = select(MaterialStock.quantity).where(
            MaterialStock.site_id == request.site_id,
            MaterialStock.material_id == request.material_id,
        )
        prev_balance = (await session.execute(stmt_prev)).scalar()
        if prev_balance is None:
            prev_balance = Decimal("0.00")

        now = datetime.now(timezone.utc)

        # 7. Atomic upsert into material_stocks
        stmt_upsert = (
            pg_insert(MaterialStock)
            .values(
                id=uuid.uuid4(),
                site_id=request.site_id,
                material_id=request.material_id,
                quantity=request.quantity,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_material_stocks_site_material",
                set_={
                    "quantity": MaterialStock.quantity + request.quantity,
                    "updated_at": now,
                },
            )
            .returning(MaterialStock.id, MaterialStock.quantity)
        )

        try:
            upsert_res = (await session.execute(stmt_upsert)).one()
            _, new_balance = upsert_res

            # 8. Insert ledger movement record
            movement = MaterialStockMovement(
                id=uuid.uuid4(),
                site_id=request.site_id,
                material_id=request.material_id,
                movement_type="inward",
                quantity=request.quantity,
                balance_after=new_balance,
                material_transaction_id=None,
                idempotency_key=request.idempotency_key,
                remarks=request.remarks,
                created_by=current_user.id,
                created_at=now,
            )
            session.add(movement)

            # 9. Insert central AuditLog entry in the same transaction
            audit_entry = AuditLog(
                id=uuid.uuid4(),
                entity_type="material_stock_movement",
                entity_id=movement.id,
                action="stock_inward",
                changed_by=current_user.id,
                previous_values={"balance": str(prev_balance)},
                new_values={
                    "movement_id": str(movement.id),
                    "site_id": str(request.site_id),
                    "material_id": str(request.material_id),
                    "movement_type": "inward",
                    "quantity": str(request.quantity),
                    "balance_after": str(new_balance),
                    "idempotency_key": request.idempotency_key,
                    "remarks": request.remarks,
                },
                created_at=now,
            )
            session.add(audit_entry)

            # 10. Commit all operations atomically
            await session.commit()
            await session.refresh(movement)
            return cls._map_movement_to_response(movement, material)

        except IntegrityError:
            await session.rollback()
            # Check if this was a concurrent race on the idempotency key
            recheck_stmt = (
                select(MaterialStockMovement)
                .options(selectinload(MaterialStockMovement.material))
                .where(MaterialStockMovement.idempotency_key == request.idempotency_key)
            )
            recheck_mvt = (await session.execute(recheck_stmt)).scalar_one_or_none()
            if recheck_mvt:
                if (
                    recheck_mvt.site_id == request.site_id
                    and recheck_mvt.material_id == request.material_id
                    and recheck_mvt.quantity == request.quantity
                    and recheck_mvt.movement_type == "inward"
                ):
                    return cls._map_movement_to_response(recheck_mvt, material)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency conflict: idempotency_key '{request.idempotency_key}' already used with different parameters.",
                )
            raise
        except Exception:
            await session.rollback()
            raise

    @classmethod
    async def get_site_inventory(
        cls,
        session: AsyncSession,
        site_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> SiteInventoryListResponse:
        """
        Lists catalogue materials and their stock balances for a site with pagination and filtering.
        Returns 0.00 available stock for materials without a stock row, without creating records.
        """
        # 1. Permissions
        if current_user.role not in ("administrator", "director", "supervisor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view site inventory.",
            )

        if current_user.role == "supervisor":
            supervised_sites = await cls.get_supervised_site_ids(session, current_user)
            if site_id not in supervised_sites:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor is not authorized to view inventory for this site.",
                )

        # 2. Site validation
        stmt_site = select(Site).where(Site.id == site_id)
        site = (await session.execute(stmt_site)).scalar_one_or_none()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found.",
            )

        # 3. Filters
        filters = []
        if is_active is not None:
            filters.append(Material.is_active == is_active)
        if category and category.strip():
            filters.append(Material.category == category.strip())
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(or_(Material.name.ilike(term), Material.material_code.ilike(term)))

        # 4. Total count query
        count_stmt = select(func.count(Material.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await session.execute(count_stmt)).scalar() or 0

        # 5. Last movement correlated subquery
        last_movement_subquery = (
            select(func.max(MaterialStockMovement.created_at))
            .where(
                MaterialStockMovement.site_id == site_id,
                MaterialStockMovement.material_id == Material.id,
            )
            .scalar_subquery()
        )

        # 6. Inventory query
        stmt = (
            select(
                Material,
                func.coalesce(MaterialStock.quantity, Decimal("0.00")).label("quantity_available"),
                last_movement_subquery.label("last_movement_at"),
            )
            .outerjoin(
                MaterialStock,
                and_(
                    MaterialStock.site_id == site_id,
                    MaterialStock.material_id == Material.id,
                ),
            )
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Material.name.asc()).offset(skip).limit(limit)
        results = (await session.execute(stmt)).all()

        items = [
            SiteInventoryItemResponse(
                material_id=mat.id,
                material_code=mat.material_code,
                material_name=mat.name,
                unit_of_measure=mat.unit_of_measure,
                category=mat.category,
                quantity_available=qty,
                last_movement_at=last_mvt,
                is_active=mat.is_active,
            )
            for mat, qty, last_mvt in results
        ]

        return SiteInventoryListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            site_id=site.id,
            site_name=site.name,
        )

    @classmethod
    async def get_material_stock_at_site(
        cls,
        session: AsyncSession,
        site_id: uuid.UUID,
        material_id: uuid.UUID,
        current_user: User,
    ) -> MaterialSiteStockResponse:
        """
        Retrieves the stock balance for a specified site and material pair.
        Returns 0.00 available stock without creating a database row if no balance exists yet.
        """
        # 1. Permissions
        if current_user.role not in ("administrator", "director", "supervisor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view material stock.",
            )

        if current_user.role == "supervisor":
            supervised_sites = await cls.get_supervised_site_ids(session, current_user)
            if site_id not in supervised_sites:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor is not authorized to view inventory for this site.",
                )

        # 2. Site validation
        stmt_site = select(Site).where(Site.id == site_id)
        site = (await session.execute(stmt_site)).scalar_one_or_none()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found.",
            )

        # 3. Material validation
        stmt_mat = select(Material).where(Material.id == material_id)
        material = (await session.execute(stmt_mat)).scalar_one_or_none()
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material with id {material_id} not found.",
            )

        # 4. Stock row query (read-only, does not create row)
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == site_id,
            MaterialStock.material_id == material_id,
        )
        stock = (await session.execute(stmt_stock)).scalar_one_or_none()
        qty = stock.quantity if stock else Decimal("0.00")

        # 5. Last movement timestamp query
        stmt_mvt = (
            select(func.max(MaterialStockMovement.created_at))
            .where(
                MaterialStockMovement.site_id == site_id,
                MaterialStockMovement.material_id == material_id,
            )
        )
        last_mvt = (await session.execute(stmt_mvt)).scalar()

        return MaterialSiteStockResponse(
            site_id=site.id,
            site_name=site.name,
            material_id=material.id,
            material_code=material.material_code,
            material_name=material.name,
            unit_of_measure=material.unit_of_measure,
            category=material.category,
            quantity_available=qty,
            last_movement_at=last_mvt,
            is_active=material.is_active,
        )

    @classmethod
    def _map_movement_to_response(
        cls,
        movement: MaterialStockMovement,
        material: Optional[Material] = None,
    ) -> StockInwardResponse:
        mat_name = material.name if material else (movement.material.name if movement.material else "")
        mat_code = material.material_code if material else (movement.material.material_code if movement.material else "")
        uom = material.unit_of_measure if material else (movement.material.unit_of_measure if movement.material else "")

        return StockInwardResponse(
            movement_id=movement.id,
            site_id=movement.site_id,
            material_id=movement.material_id,
            material_name=mat_name,
            material_code=mat_code,
            unit_of_measure=uom,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            balance_after=movement.balance_after,
            idempotency_key=movement.idempotency_key,
            remarks=movement.remarks,
            created_by=movement.created_by,
            created_at=movement.created_at,
        )

    @classmethod
    async def get_material_stock_movements(
        cls,
        session: AsyncSession,
        site_id: uuid.UUID,
        material_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> StockMovementHistoryResponse:
        """
        Retrieves paginated stock movement history for a specified site and material.
        Authorized for Directors, Administrators, and Supervisors (assigned to the site).
        """
        # 1. Permissions
        if current_user.role not in ("administrator", "director", "supervisor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to view stock movement history.",
            )

        if current_user.role == "supervisor":
            supervised_sites = await cls.get_supervised_site_ids(session, current_user)
            if site_id not in supervised_sites:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor is not authorized to view movement history for this site.",
                )

        # 2. Site validation
        stmt_site = select(Site).where(Site.id == site_id)
        site = (await session.execute(stmt_site)).scalar_one_or_none()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found.",
            )

        # 3. Material validation
        stmt_mat = select(Material).where(Material.id == material_id)
        material = (await session.execute(stmt_mat)).scalar_one_or_none()
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material with id {material_id} not found.",
            )

        # 4. Total count
        count_stmt = select(func.count(MaterialStockMovement.id)).where(
            MaterialStockMovement.site_id == site_id,
            MaterialStockMovement.material_id == material_id,
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        # 5. Movements with actor
        stmt = (
            select(
                MaterialStockMovement,
                User.mobile_id.label("user_mobile"),
                Employee.name.label("emp_name"),
            )
            .outerjoin(User, User.id == MaterialStockMovement.created_by)
            .outerjoin(Employee, Employee.user_id == User.id)
            .where(
                MaterialStockMovement.site_id == site_id,
                MaterialStockMovement.material_id == material_id,
            )
            .order_by(MaterialStockMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        results = (await session.execute(stmt)).all()

        items = []
        for mvt, user_mob, emp_name in results:
            actor = emp_name or user_mob or str(mvt.created_by)
            items.append(
                StockMovementItemResponse(
                    movement_id=mvt.id,
                    site_id=mvt.site_id,
                    material_id=mvt.material_id,
                    movement_type=mvt.movement_type,
                    quantity=mvt.quantity,
                    balance_after=mvt.balance_after,
                    material_transaction_id=mvt.material_transaction_id,
                    idempotency_key=mvt.idempotency_key,
                    remarks=mvt.remarks,
                    created_by=mvt.created_by,
                    actor_name=actor,
                    created_at=mvt.created_at,
                )
            )

        return StockMovementHistoryResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            site_id=site.id,
            material_id=material.id,
            material_name=material.name,
            material_code=material.material_code,
            unit_of_measure=material.unit_of_measure,
        )

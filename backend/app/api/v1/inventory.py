from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.material_inventory.schemas import (
    InventorySiteResponse,
    MaterialSiteStockResponse,
    SiteInventoryListResponse,
    StockInwardRequest,
    StockInwardResponse,
    StockMovementHistoryResponse,
)
from app.modules.material_inventory.service import MaterialInventoryService

router = APIRouter()


@router.get(
    "/sites",
    response_model=list[InventorySiteResponse],
    status_code=status.HTTP_200_OK,
    summary="List authorized sites for material inventory tracking",
)
async def get_authorized_inventory_sites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves sites authorized for material inventory tracking.
    - Authorized for Directors, Administrators, and Supervisors.
    - Administrators and Directors: all active sites.
    - Supervisors: only active sites supervised by or assigned to the supervisor.
    - Employees: 403 Forbidden.
    """
    return await MaterialInventoryService.get_authorized_inventory_sites(
        session=db,
        current_user=current_user,
    )


@router.post(
    "/inward",
    response_model=StockInwardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record stock inward for a site",
)
async def record_stock_inward(
    request: StockInwardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Records stock received at a specific client site.
    - Authorized for Directors, Administrators, and Supervisors (assigned to the site).
    - Ensures strictly positive Decimal quantities.
    - Atomically updates MaterialStock and inserts MaterialStockMovement.
    - Idempotency key prevents duplicate receipts on retry and rejects conflicting reuse.
    - Emits central AuditLog entry.
    """
    return await MaterialInventoryService.record_stock_inward(
        session=db,
        request=request,
        current_user=current_user,
    )


@router.get(
    "/sites/{site_id}",
    response_model=SiteInventoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List materials and stock balances for a site",
)
async def get_site_inventory(
    site_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination page size"),
    search: Optional[str] = Query(None, description="Search term for material name or code"),
    category: Optional[str] = Query(None, description="Filter by material category"),
    is_active: Optional[bool] = Query(None, description="Filter by material active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves catalogue materials and their stock balances for a specific site.
    - Authorized for Directors, Administrators, and Supervisors (assigned to the site).
    - Unstocked materials return 0.00 quantity without creating database rows.
    - Supports full-text search, category filtering, and pagination.
    """
    return await MaterialInventoryService.get_site_inventory(
        session=db,
        site_id=site_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        is_active=is_active,
    )


@router.get(
    "/sites/{site_id}/materials/{material_id}",
    response_model=MaterialSiteStockResponse,
    status_code=status.HTTP_200_OK,
    summary="Get stock balance for a site/material pair",
)
async def get_material_stock_at_site(
    site_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves the stock balance for a specified site and material.
    - Authorized for Directors, Administrators, and Supervisors (assigned to the site).
    - If no stock row exists, returns 0.00 without creating a database row.
    - Includes last movement timestamp where available.
    """
    return await MaterialInventoryService.get_material_stock_at_site(
        session=db,
        site_id=site_id,
        material_id=material_id,
        current_user=current_user,
    )


@router.get(
    "/sites/{site_id}/materials/{material_id}/movements",
    response_model=StockMovementHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get stock movement history for a site/material pair",
)
async def get_material_stock_movements(
    site_id: uuid.UUID,
    material_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves the stock movement audit ledger for a specified site and material.
    - Authorized for Directors, Administrators, and Supervisors (assigned to the site).
    - Returns historical inward receipts, consumption, returns, and adjustments.
    - Includes movement type, quantity, balance_after, timestamp, actor, and linked transaction.
    """
    return await MaterialInventoryService.get_material_stock_movements(
        session=db,
        site_id=site_id,
        material_id=material_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


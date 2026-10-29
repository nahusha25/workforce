from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.auth import User
from app.modules.assets.schemas import (
    AssetDetailResponse,
    AssetIssueRequest,
    AssetListResponse,
    AssetReassignRequest,
    AssetRegisterRequest,
    AssetResponse,
    AssetReturnRequest,
)
from app.modules.assets.service import AssetService
from app.modules.master_data.schemas import SiteResponse

router = APIRouter()


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new asset",
)
async def register_asset(
    request: AssetRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Registers a new physical asset in the system.
    Can be placed directly in the Central Warehouse or assigned to a specific Site.
    Accessible to Administrator, Director, and Supervisor roles.
    Enforces atomic asset tag allocation, location consistency, transaction ledgering, and audit logging.
    """
    return await AssetService.register_asset(
        session=db,
        request=request,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=AssetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List, search, and filter assets",
)
async def list_assets(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination page size"),
    search: Optional[str] = Query(None, description="Search term for name, tag, serial, model, manufacturer"),
    location_type: Optional[str] = Query(None, description="Filter by location: 'warehouse' or 'site'"),
    site_id: Optional[uuid.UUID] = Query(None, description="Filter by specific site ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by operational status"),
    condition: Optional[str] = Query(None, description="Filter by physical condition"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Lists physical assets with multi-parameter filtering, full-text search, and pagination.
    Accessible to Administrator, Director, and Supervisor roles.
    Warehouse assets are explicitly distinguishable from site-assigned assets.
    """
    return await AssetService.list_assets(
        session=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        search=search,
        location_type=location_type,
        site_id=site_id,
        category=category,
        status_filter=status,
        condition=condition,
        is_active=is_active,
    )


@router.get(
    "/sites",
    response_model=list[SiteResponse],
    status_code=status.HTTP_200_OK,
    summary="Get active sites for asset management",
)
async def get_asset_sites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves all active project sites for asset filtering, registration, and management.
    Accessible to Administrator, Director, and Supervisor roles.
    """
    return await AssetService.get_active_sites(session=db)


@router.get(
    "/{asset_id}",
    response_model=AssetDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get asset details with transaction history",
)
async def get_asset_detail(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves full details of an asset, including its complete chronological transaction history.
    Accessible to Administrator, Director, and Supervisor roles.
    Enforces supervisor site-level authorization.
    """
    return await AssetService.get_asset_by_id(
        session=db,
        asset_id=asset_id,
        current_user=current_user,
    )


@router.post(
    "/{asset_id}/issue",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue asset to an assigned employee",
)
async def issue_asset(
    asset_id: uuid.UUID,
    request: AssetIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Issues an asset to an employee who has an active site assignment for the asset's current site.
    Atomically updates asset status to 'issued_employee' and records custodian.
    Writes immutable transaction ledger record and central audit log.
    """
    return await AssetService.issue_asset(
        session=db,
        asset_id=asset_id,
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{asset_id}/return",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Return an issued asset",
)
async def return_asset(
    asset_id: uuid.UUID,
    request: AssetReturnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Returns an asset from an employee custodian back to its assigned site.
    Verifies custodian identity and updates condition/status according to domain rules.
    Clears custodian atomically, writes transaction ledger record and central audit log.
    """
    return await AssetService.return_asset(
        session=db,
        asset_id=asset_id,
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{asset_id}/reassign",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reassign asset location (Warehouse <-> Site or Site A <-> Site B)",
)
async def reassign_asset(
    asset_id: uuid.UUID,
    request: AssetReassignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Reassigns an asset's location directly between warehouse and sites or between sites.
    Cannot reassign an asset while it is currently issued to an employee.
    Enforces supervisor site-level boundaries and writes transaction ledger and central audit records.
    """
    return await AssetService.reassign_asset(
        session=db,
        asset_id=asset_id,
        request=request,
        current_user=current_user,
    )


@router.get(
    "/{asset_id}/destination-sites",
    response_model=list[SiteResponse],
    status_code=status.HTTP_200_OK,
    summary="Get authorized destination sites for asset reassignment",
)
async def get_destination_sites(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["director", "administrator", "supervisor"])),
):
    """
    Retrieves authorized destination project sites for reassigning the specified asset.
    - Administrators & Directors: all active sites (excluding asset's current site).
    - Supervisors: only active project sites permitted by the client's asset-transfer rules
      (all active sites belonging to the asset's client, excluding the asset's current site).
      Supervisors cannot query destination sites for assets in the central warehouse or at
      sites they do not supervise (403 Forbidden).
    """
    return await AssetService.get_destination_sites(
        session=db,
        asset_id=asset_id,
        current_user=current_user,
    )

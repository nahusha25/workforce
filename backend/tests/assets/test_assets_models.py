from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.assets import Asset, AssetTransaction
from app.models.auth import User
from app.models.operations import Client, Project, Site
from app.models.workforce import Employee
from tests.conftest import TestingSessionLocal


def _u() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_asset_model_warehouse_location_consistency():
    """
    Direct model check: warehouse asset with a site_id violates check_assets_location_consistency.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        client = Client(id=_u(), name=f"C_{sfx}")
        project = Project(id=_u(), client_id=client.id, name=f"P_{sfx}", status="in_progress")
        site = Site(id=_u(), project_id=project.id, name=f"S_{sfx}")
        session.add_all([client, project, site])
        await session.flush()

        invalid_asset = Asset(
            id=_u(),
            asset_tag=f"INV-WH-{sfx}",
            name="Invalid Warehouse Asset",
            category="machinery",
            location_type="warehouse",
            current_site_id=site.id,  # Invalid!
        )
        session.add(invalid_asset)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_asset_model_site_location_consistency():
    """
    Direct model check: site asset without site_id violates check_assets_location_consistency.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        invalid_asset = Asset(
            id=_u(),
            asset_tag=f"INV-SITE-{sfx}",
            name="Invalid Site Asset",
            category="machinery",
            location_type="site",
            current_site_id=None,  # Invalid!
        )
        session.add(invalid_asset)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_asset_model_negative_purchase_cost_rejected():
    """
    Direct model check: negative purchase cost violates check_assets_purchase_cost.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        invalid_asset = Asset(
            id=_u(),
            asset_tag=f"INV-COST-{sfx}",
            name="Negative Cost Asset",
            category="machinery",
            location_type="warehouse",
            purchase_cost=Decimal("-100.00"),
        )
        session.add(invalid_asset)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_asset_model_invalid_condition_rejected():
    """
    Direct model check: condition outside allowed domain violates check_assets_condition.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        invalid_asset = Asset(
            id=_u(),
            asset_tag=f"INV-COND-{sfx}",
            name="Bad Condition Asset",
            category="machinery",
            location_type="warehouse",
            condition="destroyed_completely",  # Invalid!
        )
        session.add(invalid_asset)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_asset_model_in_transit_status_rejected():
    """
    Direct model check: status 'in_transit' is removed from allowed domain
    and violates check_assets_status.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]
        invalid_asset = Asset(
            id=_u(),
            asset_tag=f"INV-TRANSIT-{sfx}",
            name="In Transit Asset",
            category="machinery",
            location_type="warehouse",
            status="in_transit",  # Invalid!
        )
        session.add(invalid_asset)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_asset_model_custody_status_consistency():
    """
    Verifies check_assets_custody_status_consistency constraint:
      (status = 'issued_employee' AND current_custodian_id IS NOT NULL)
      OR (status != 'issued_employee' AND current_custodian_id IS NULL)
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        # Create user and employee for custodian testing
        u = User(id=_u(), mobile_id=f"+9188{sfx[:6]}1", role="employee")
        emp = Employee(
            id=_u(),
            user_id=u.id,
            employee_code=f"EMP_{sfx}",
            mobile_id=f"+9188{sfx[:6]}1",
            name=f"Worker_{sfx}",
            is_active=True,
        )
        session.add_all([u, emp])
        await session.flush()

        # Case 1: status='issued_employee' with current_custodian_id=None must FAIL
        asset_no_custodian = Asset(
            id=_u(),
            asset_tag=f"INV-CUST-1-{sfx}",
            name="Issued Without Custodian",
            category="power_tools",
            location_type="warehouse",
            status="issued_employee",
            current_custodian_id=None,
        )
        session.add(asset_no_custodian)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # Re-fetch or re-add employee if rollback cleared session
        session.add_all([u, emp])
        await session.flush()

        # Case 2: status='available' with current_custodian_id!=None must FAIL
        asset_available_with_custodian = Asset(
            id=_u(),
            asset_tag=f"INV-CUST-2-{sfx}",
            name="Available With Custodian",
            category="power_tools",
            location_type="warehouse",
            status="available",
            current_custodian_id=emp.id,
        )
        session.add(asset_available_with_custodian)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # Case 3: status='issued_employee' WITH current_custodian_id must SUCCEED
        session.add_all([u, emp])
        await session.flush()
        valid_issued_asset = Asset(
            id=_u(),
            asset_tag=f"VAL-CUST-{sfx}",
            name="Validly Issued Asset",
            category="power_tools",
            location_type="warehouse",
            status="issued_employee",
            current_custodian_id=emp.id,
        )
        session.add(valid_issued_asset)
        await session.commit()

        # Verify persisted
        persisted = (
            await session.execute(select(Asset).where(Asset.id == valid_issued_asset.id))
        ).scalar_one()
        assert persisted.status == "issued_employee"
        assert persisted.current_custodian_id == emp.id


@pytest.mark.asyncio
async def test_asset_model_employee_delete_restricted():
    """
    Verifies that deleting an employee who is recorded as current_custodian_id
    is BLOCKED with an IntegrityError by the ON DELETE RESTRICT foreign key.
    """
    async with TestingSessionLocal() as session:
        sfx = str(_u())[:8]

        u = User(id=_u(), mobile_id=f"+9187{sfx[:6]}1", role="employee")
        emp = Employee(
            id=_u(),
            user_id=u.id,
            employee_code=f"EMP_{sfx}",
            mobile_id=f"+9187{sfx[:6]}1",
            name=f"Worker_{sfx}",
            is_active=True,
        )
        session.add_all([u, emp])
        await session.flush()

        asset = Asset(
            id=_u(),
            asset_tag=f"DEL-RESTRICT-{sfx}",
            name="Restricted Asset",
            category="power_tools",
            location_type="warehouse",
            status="issued_employee",
            current_custodian_id=emp.id,
        )
        session.add(asset)
        await session.commit()

        # Attempt to delete the employee holding the asset -> Must FAIL due to RESTRICT
        await session.delete(emp)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

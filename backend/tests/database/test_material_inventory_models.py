from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.material_inventory import MaterialStock, MaterialStockMovement
from app.models.workforce import Employee
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    Material,
    MaterialTransaction,
    Project,
    Site,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def inventory_setup(sync_db_session: Session):
    """Fixture providing client, project, site, material, user, employee, DWE and material_transaction."""
    sfx = str(_uuid())[:8]

    client = Client(id=_uuid(), name=f"Test Client {sfx}")
    project = Project(id=_uuid(), client_id=client.id, name=f"Test Project {sfx}", status="in_progress")
    site1 = Site(id=_uuid(), project_id=project.id, name=f"Test Site A {sfx}", is_active=True)
    site2 = Site(id=_uuid(), project_id=project.id, name=f"Test Site B {sfx}", is_active=True)

    material1 = Material(
        id=_uuid(),
        material_code=f"MAT-CCTV-{sfx}",
        name=f"CCTV Camera {sfx}",
        unit_of_measure="nos",
        category="device",
        purchase_approval_limit=5000.00,
        is_active=True,
    )
    material2 = Material(
        id=_uuid(),
        material_code=f"MAT-CAB-{sfx}",
        name=f"Cat6 Cable {sfx}",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=2000.00,
        is_active=True,
    )

    user = User(id=_uuid(), mobile_id=f"+9188{sfx}", role="supervisor")
    sync_db_session.add(user)
    sync_db_session.commit()

    emp = Employee(
        id=_uuid(),
        user_id=user.id,
        employee_code=f"EMP-{sfx}",
        mobile_id=user.mobile_id,
        name=f"Worker {sfx}",
        is_active=True,
    )

    sync_db_session.add_all([client, project, site1, site2, material1, material2, emp])
    sync_db_session.commit()

    return {
        "client": client,
        "project": project,
        "site1": site1,
        "site2": site2,
        "material1": material1,
        "material2": material2,
        "user": user,
        "employee": emp,
    }


# ===========================================================================
# 1. MaterialStock: Defaults, Constraints, and Relationships
# ===========================================================================

def test_material_stock_defaults_and_creation(sync_db_session: Session, inventory_setup):
    """Test creating MaterialStock with default 0.00 balance."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
    )
    sync_db_session.add(stock)
    sync_db_session.commit()
    sync_db_session.refresh(stock)

    assert stock.id is not None
    assert stock.site_id == env["site1"].id
    assert stock.material_id == env["material1"].id
    assert stock.quantity == Decimal("0.00")
    assert stock.created_at is not None
    assert stock.updated_at is not None
    assert stock.site.name == env["site1"].name
    assert stock.material.name == env["material1"].name


def test_material_stock_positive_quantity(sync_db_session: Session, inventory_setup):
    """Test MaterialStock stores positive Decimal quantity accurately."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("10.00"),
    )
    sync_db_session.add(stock)
    sync_db_session.commit()
    sync_db_session.refresh(stock)

    assert stock.quantity == Decimal("10.00")


def test_material_stock_rejects_negative_quantity_on_insert(sync_db_session: Session, inventory_setup):
    """Test CheckConstraint rejects inserting a negative stock quantity."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("-1.00"),
    )
    sync_db_session.add(stock)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_material_stocks_quantity_non_negative" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_rejects_negative_quantity_on_update(sync_db_session: Session, inventory_setup):
    """Test CheckConstraint rejects updating an existing stock quantity to negative."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("5.00"),
    )
    sync_db_session.add(stock)
    sync_db_session.commit()

    stock.quantity = Decimal("-0.01")
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_material_stocks_quantity_non_negative" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_unique_site_material_constraint(sync_db_session: Session, inventory_setup):
    """Test unique constraint: only one stock record allowed per (site_id, material_id)."""
    env = inventory_setup
    stock1 = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("10.00"),
    )
    sync_db_session.add(stock1)
    sync_db_session.commit()

    stock2 = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("20.00"),
    )
    sync_db_session.add(stock2)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "uq_material_stocks_site_material" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_allows_same_material_across_different_sites(sync_db_session: Session, inventory_setup):
    """Test that different sites can track stock for the same material independently."""
    env = inventory_setup
    stock_site1 = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("10.00"),
    )
    stock_site2 = MaterialStock(
        id=_uuid(),
        site_id=env["site2"].id,
        material_id=env["material1"].id,
        quantity=Decimal("25.00"),
    )
    sync_db_session.add_all([stock_site1, stock_site2])
    sync_db_session.commit()

    assert stock_site1.quantity == Decimal("10.00")
    assert stock_site2.quantity == Decimal("25.00")


def test_material_stock_foreign_key_violations(sync_db_session: Session, inventory_setup):
    """Test foreign key validation: invalid site_id or material_id is rejected."""
    env = inventory_setup
    invalid_stock_site = MaterialStock(
        id=_uuid(),
        site_id=_uuid(),
        material_id=env["material1"].id,
        quantity=Decimal("5.00"),
    )
    sync_db_session.add(invalid_stock_site)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    invalid_stock_mat = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=_uuid(),
        quantity=Decimal("5.00"),
    )
    sync_db_session.add(invalid_stock_mat)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


# ===========================================================================
# 2. MaterialStockMovement: Audit Ledger, Categories & Constraints
# ===========================================================================

@pytest.mark.parametrize("movement_type", ["inward", "consumed", "returned", "adjustment"])
def test_material_stock_movement_valid_categories(sync_db_session: Session, inventory_setup, movement_type: str):
    """Test all valid movement types are accepted by check_stock_movement_type."""
    env = inventory_setup
    mvt = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type=movement_type,
        quantity=Decimal("5.00"),
        balance_after=Decimal("15.00"),
        idempotency_key=f"IDEMP-{movement_type}-{_uuid()}",
        remarks=f"Test {movement_type} movement",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt)
    sync_db_session.commit()
    sync_db_session.refresh(mvt)

    assert mvt.id is not None
    assert mvt.movement_type == movement_type
    assert mvt.quantity == Decimal("5.00")
    assert mvt.balance_after == Decimal("15.00")
    assert mvt.created_at is not None
    assert mvt.site.name == env["site1"].name
    assert mvt.material.name == env["material1"].name
    assert mvt.actor.mobile_id == env["user"].mobile_id


def test_material_stock_movement_invalid_type_rejected(sync_db_session: Session, inventory_setup):
    """Test CheckConstraint rejects invalid movement types (e.g. 'damaged', 'lost', 'sold')."""
    env = inventory_setup
    mvt = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="invalid_type",
        quantity=Decimal("2.00"),
        balance_after=Decimal("8.00"),
        idempotency_key=f"IDEMP-INVALID-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_stock_movement_type" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_movement_requires_strictly_positive_quantity(sync_db_session: Session, inventory_setup):
    """Test CheckConstraint rejects quantity <= 0."""
    env = inventory_setup
    # Zero quantity
    mvt_zero = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="inward",
        quantity=Decimal("0.00"),
        balance_after=Decimal("10.00"),
        idempotency_key=f"IDEMP-ZERO-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt_zero)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_stock_movement_quantity_positive" in str(exc_info.value)
    sync_db_session.rollback()

    # Negative quantity
    mvt_neg = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="consumed",
        quantity=Decimal("-2.00"),
        balance_after=Decimal("8.00"),
        idempotency_key=f"IDEMP-NEG-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt_neg)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_stock_movement_quantity_positive" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_movement_rejects_negative_balance_after(sync_db_session: Session, inventory_setup):
    """Test CheckConstraint rejects balance_after < 0."""
    env = inventory_setup
    mvt = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="consumed",
        quantity=Decimal("12.00"),
        balance_after=Decimal("-2.00"),
        idempotency_key=f"IDEMP-NEG-BAL-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "check_stock_movement_balance_after_non_negative" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_movement_idempotency_uniqueness(sync_db_session: Session, inventory_setup):
    """Test unique constraint on idempotency_key prevents duplicate ledger movements."""
    env = inventory_setup
    key = f"IDEMP-DUP-{_uuid()}"
    mvt1 = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="inward",
        quantity=Decimal("10.00"),
        balance_after=Decimal("10.00"),
        idempotency_key=key,
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt1)
    sync_db_session.commit()

    mvt2 = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="inward",
        quantity=Decimal("10.00"),
        balance_after=Decimal("20.00"),
        idempotency_key=key,
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt2)
    with pytest.raises(IntegrityError) as exc_info:
        sync_db_session.commit()
    assert "material_stock_movements_idempotency_key" in str(exc_info.value)
    sync_db_session.rollback()


def test_material_stock_movement_links_optional_material_transaction(sync_db_session: Session, inventory_setup):
    """Test linking a movement to an existing material_transaction with ON DELETE SET NULL behavior."""
    env = inventory_setup

    # Create dummy attendance, activity, DWE, and MaterialTransaction
    att = AttendanceRecord(
        id=_uuid(),
        employee_id=env["employee"].id,
        site_id=env["site1"].id,
        date=datetime.now(timezone.utc).date(),
        status="verified",
    )
    act = Activity(
        id=_uuid(),
        name="CCTV Installation",
        category="device",
        approved_rate=150.00,
        unit_of_measure="nos",
    )
    sync_db_session.add_all([att, act])
    sync_db_session.commit()

    dwe = DailyWorkEntry(
        id=_uuid(),
        idempotency_key=f"DWE-IDEMP-{_uuid()}",
        attendance_record_id=att.id,
        employee_id=env["employee"].id,
        site_id=env["site1"].id,
        activity_id=act.id,
        work_date=datetime.now(timezone.utc).date(),
        quantity=1.0,
        uom="nos",
        status="approved",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()

    mt = MaterialTransaction(
        id=_uuid(),
        daily_work_entry_id=dwe.id,
        material_id=env["material1"].id,
        site_id=env["site1"].id,
        transaction_type="consumed",
        item_name=env["material1"].name,
        quantity=2.0,
        amount=0.0,
        status="approved",
    )
    sync_db_session.add(mt)
    sync_db_session.commit()

    # Link movement to material transaction
    mvt = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="consumed",
        quantity=Decimal("2.00"),
        balance_after=Decimal("8.00"),
        material_transaction_id=mt.id,
        idempotency_key=f"IDEMP-LINK-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt)
    sync_db_session.commit()
    sync_db_session.refresh(mvt)

    assert mvt.material_transaction_id == mt.id
    assert mvt.material_transaction.item_name == env["material1"].name


# ===========================================================================
# 3. Migration Downgrade Guard Tests
# ===========================================================================

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_MIGRATION_PATH = (
    Path(__file__).parent.parent.parent
    / "alembic"
    / "versions"
    / "e5b2c9a1d3f4_create_material_inventory_tables.py"
)


def _load_inventory_migration():
    spec = importlib.util.spec_from_file_location("migration_e5b2", _MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_downgrade_guard_blocks_when_nonzero_stock_exists(sync_db_session: Session, inventory_setup):
    """Test that downgrade raises RuntimeError when a non-zero stock row exists."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("10.00"),
    )
    sync_db_session.add(stock)
    sync_db_session.commit()

    mod = _load_inventory_migration()
    conn = sync_db_session.connection()
    original_get_bind = mod.op.get_bind
    mod.op.get_bind = lambda: conn

    try:
        with pytest.raises(RuntimeError) as exc_info:
            mod.downgrade()
        assert "material inventory or movement records exist in database" in str(exc_info.value)
    finally:
        mod.op.get_bind = original_get_bind
        sync_db_session.delete(stock)
        sync_db_session.commit()


def test_downgrade_guard_blocks_when_zero_quantity_stock_exists(sync_db_session: Session, inventory_setup):
    """Test that downgrade raises RuntimeError when a zero-quantity stock row exists (correction verification)."""
    env = inventory_setup
    stock = MaterialStock(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        quantity=Decimal("0.00"),
    )
    sync_db_session.add(stock)
    sync_db_session.commit()

    mod = _load_inventory_migration()
    conn = sync_db_session.connection()
    original_get_bind = mod.op.get_bind
    mod.op.get_bind = lambda: conn

    try:
        with pytest.raises(RuntimeError) as exc_info:
            mod.downgrade()
        assert "material inventory or movement records exist in database" in str(exc_info.value)
    finally:
        mod.op.get_bind = original_get_bind
        sync_db_session.delete(stock)
        sync_db_session.commit()


def test_downgrade_guard_blocks_when_movement_row_exists(sync_db_session: Session, inventory_setup):
    """Test that downgrade raises RuntimeError when any movement record exists."""
    env = inventory_setup
    mvt = MaterialStockMovement(
        id=_uuid(),
        site_id=env["site1"].id,
        material_id=env["material1"].id,
        movement_type="inward",
        quantity=Decimal("5.00"),
        balance_after=Decimal("5.00"),
        idempotency_key=f"IDEMP-GUARD-{_uuid()}",
        created_by=env["user"].id,
    )
    sync_db_session.add(mvt)
    sync_db_session.commit()

    mod = _load_inventory_migration()
    conn = sync_db_session.connection()
    original_get_bind = mod.op.get_bind
    mod.op.get_bind = lambda: conn

    try:
        with pytest.raises(RuntimeError) as exc_info:
            mod.downgrade()
        assert "material inventory or movement records exist in database" in str(exc_info.value)
    finally:
        mod.op.get_bind = original_get_bind
        sync_db_session.delete(mvt)
        sync_db_session.commit()


def test_downgrade_guard_passes_when_inventory_tables_are_empty(sync_db_session: Session):
    """Test that downgrade guard passes and allows dropping and re-upgrading tables when inventory tables are empty."""
    from sqlalchemy import inspect, text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    # Ensure inventory tables in test DB are empty
    sync_db_session.execute(text("DELETE FROM material_stock_movements"))
    sync_db_session.execute(text("DELETE FROM material_stocks"))
    sync_db_session.commit()

    conn = sync_db_session.connection()
    has_m = conn.execute(text("SELECT EXISTS (SELECT 1 FROM material_stock_movements LIMIT 1)")).scalar()
    has_s = conn.execute(text("SELECT EXISTS (SELECT 1 FROM material_stocks LIMIT 1)")).scalar()
    assert has_m is False
    assert has_s is False

    mod = _load_inventory_migration()
    ctx = MigrationContext.configure(conn)

    with Operations.context(ctx):
        # Downgrade executes safely when tables are empty
        mod.downgrade()
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        assert "material_stock_movements" not in tables
        assert "material_stocks" not in tables

        # Re-upgrade restores the tables, constraints, and indexes
        mod.upgrade()
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        assert "material_stock_movements" in tables
        assert "material_stocks" in tables


from datetime import date, datetime, timezone
from decimal import Decimal
import asyncio
from unittest.mock import patch
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.material_inventory import MaterialStock, MaterialStockMovement
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
)
from app.models.system import AuditLog
from app.models.workforce import Employee, Role
from app.modules.verification.exceptions import (
    InsufficientMaterialStockError,
    InvalidVerificationStateError,
    MissingCatalogueMaterialError,
)
from app.modules.verification.service import VerificationService
from tests.conftest import TestingSessionLocal


async def setup_batch4_fixtures(session: AsyncSession):
    suffix = str(uuid.uuid4())[:8]

    # Roles
    worker_role = Role(id=uuid.uuid4(), name=f"Worker-{suffix}")
    sup_role = Role(id=uuid.uuid4(), name=f"Supervisor-{suffix}")
    admin_role = Role(id=uuid.uuid4(), name=f"Admin-{suffix}")
    session.add_all([worker_role, sup_role, admin_role])
    await session.flush()

    # Users
    worker_user = User(id=uuid.uuid4(), mobile_id=f"W-{suffix}", role="employee", is_active=True)
    sup_user = User(id=uuid.uuid4(), mobile_id=f"S-{suffix}", role="supervisor", is_active=True)
    admin_user = User(id=uuid.uuid4(), mobile_id=f"A-{suffix}", role="administrator", is_active=True)
    session.add_all([worker_user, sup_user, admin_user])
    await session.flush()

    # Employees
    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        employee_code=f"SUP-{suffix}",
        mobile_id=sup_user.mobile_id,
        name="Site Supervisor",
        is_active=True,
    )
    worker_emp = Employee(
        id=uuid.uuid4(),
        user_id=worker_user.id,
        employee_code=f"EMP-{suffix}",
        mobile_id=worker_user.mobile_id,
        name="Site Worker",
        supervisor_id=sup_emp.id,
        is_active=True,
    )
    session.add_all([sup_emp, worker_emp])
    await session.flush()

    # Client, Project, Site
    client = Client(name=f"Client-{suffix}", is_active=True)
    session.add(client)
    await session.flush()

    project = Project(client_id=client.id, name=f"Project-{suffix}", status="active")
    session.add(project)
    await session.flush()

    site = Site(
        project_id=project.id,
        name=f"Site-{suffix}",
        supervisor_id=sup_emp.id,
        permitted_radius_m=500.0,
    )
    session.add(site)
    await session.flush()

    assignment = EmployeeSiteAssignment(
        employee_id=worker_emp.id,
        site_id=site.id,
        is_active=True,
    )
    session.add(assignment)

    activity = Activity(
        name="Cable Pulling",
        unit_of_measure="metre",
        approved_rate=15.0,
        category="cable",
    )
    session.add(activity)
    await session.flush()

    # Active Material
    material = Material(
        material_code=f"MAT-{suffix}",
        name=f"Cat6 UTP Cable Box-{suffix}",
        description="305m Cat6 Cable Box",
        unit_of_measure="box",
        category="cable",
        purchase_approval_limit=5000.0,
        is_active=True,
    )
    session.add(material)
    await session.flush()

    # Attendance Record
    att = AttendanceRecord(
        employee_id=worker_emp.id,
        site_id=site.id,
        date=date.today(),
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        working_hours=8.0,
        is_within_geofence=True,
        status="draft",
    )
    session.add(att)
    await session.flush()

    # Daily Work Entry
    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=att.id,
        employee_id=worker_emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=date.today(),
        quantity=5.0,
        uom=activity.unit_of_measure,
        status="submitted",
    )
    session.add(dwe)
    await session.flush()

    # Stock of 10 items
    stock = MaterialStock(
        site_id=site.id,
        material_id=material.id,
        quantity=Decimal("10.00"),
    )
    session.add(stock)
    await session.commit()

    return {
        "worker_user": worker_user,
        "worker_emp": worker_emp,
        "sup_user": sup_user,
        "sup_emp": sup_emp,
        "admin_user": admin_user,
        "site": site,
        "material": material,
        "dwe": dwe,
        "stock": stock,
    }


@pytest.mark.asyncio
async def test_approve_consumption_deducts_stock_10_to_8():
    """Approving consumption of 2 items with 10 available results in balance of 8."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-approve-{uuid.uuid4()}"
        vr, status_res, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        assert status_res == "approved"
        assert is_replay is False
        assert vr.action == "approved"

        # Check stock balance
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("8.00")

        # Check transaction status
        stmt_tx = select(MaterialTransaction).where(MaterialTransaction.id == tx.id)
        tx_db = (await session.execute(stmt_tx)).scalars().first()
        assert tx_db.status == "approved"


@pytest.mark.asyncio
async def test_movement_ledger_recorded_accurately():
    """Movement ledger records positive quantity, balance_after, transaction link, and idempotency key."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-movement-{uuid.uuid4()}"
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        # Inspect movement ledger
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id
        )
        mov = (await session.execute(stmt_mov)).scalars().first()
        assert mov is not None
        assert mov.movement_type == "consumed"
        assert mov.quantity == Decimal("2.00")
        assert mov.balance_after == Decimal("8.00")
        assert mov.site_id == f["site"].id
        assert mov.material_id == f["material"].id
        assert mov.created_by == f["sup_user"].id
        assert mov.idempotency_key == f"CONSUME-{idemp}"[:100]


@pytest.mark.asyncio
async def test_missing_catalogue_material_rejected_at_approval():
    """Consumed material without material_id must be rejected at approval and not guessed or deducted."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        # Legacy transaction with no material_id
        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=None,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name="Uncatalogued Screws",
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-missing-{uuid.uuid4()}"
        with pytest.raises(MissingCatalogueMaterialError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="material",
                entity_id=tx.id,
                action="approved",
                idempotency_key=idemp,
                supervisor_user_id=f["sup_user"].id,
                supervisor_emp_id=f["sup_emp"].id,
            )

        assert "valid catalogue material" in exc_info.value.detail.lower()

        # Verify stock and transaction remain unchanged
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("10.00")

        stmt_tx = select(MaterialTransaction).where(MaterialTransaction.id == tx.id)
        tx_db = (await session.execute(stmt_tx)).scalars().first()
        assert tx_db.status == "submitted"


@pytest.mark.asyncio
async def test_invalid_or_nonexistent_catalogue_material_rejected():
    """Consumed material with nonexistent material_id in materials catalogue is rejected."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name="Valid Material",
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        fake_mat_id = uuid.uuid4()
        orig_fetch = VerificationService._fetch_target_entity

        async def mock_fetch(sess, entity_type, entity_id):
            obj, emp_id, site_id = await orig_fetch(sess, entity_type, entity_id)
            # Expunge to prevent autoflush on query
            sess.expunge(obj)
            # Simulate a target_obj referencing a catalogue ID that does not exist in materials
            obj.material_id = fake_mat_id
            return obj, emp_id, site_id

        idemp = f"test-nonexistent-{uuid.uuid4()}"
        with patch.object(VerificationService, "_fetch_target_entity", side_effect=mock_fetch):
            with pytest.raises(MissingCatalogueMaterialError) as exc_info:
                await VerificationService.verify_entity(
                    session=session,
                    entity_type="material",
                    entity_id=tx.id,
                    action="approved",
                    idempotency_key=idemp,
                    supervisor_user_id=f["sup_user"].id,
                    supervisor_emp_id=f["sup_emp"].id,
                )

        assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_inactive_catalogue_material_rejected_at_approval():
    """Inactive catalogue material cannot be approved for consumption."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        # Deactivate material
        stmt_mat = select(Material).where(Material.id == f["material"].id)
        mat = (await session.execute(stmt_mat)).scalars().first()
        mat.is_active = False
        await session.commit()

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-inactive-{uuid.uuid4()}"
        with pytest.raises(InvalidVerificationStateError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="material",
                entity_id=tx.id,
                action="approved",
                idempotency_key=idemp,
                supervisor_user_id=f["sup_user"].id,
                supervisor_emp_id=f["sup_emp"].id,
            )

        assert "inactive" in exc_info.value.detail.lower()

        # Stock remains 10.00
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("10.00")


@pytest.mark.asyncio
async def test_insufficient_stock_prevents_approval():
    """Insufficient stock blocks approval and leaves stock, status, verification, and audit unchanged."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        # Set stock to 1.00
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_obj = (await session.execute(stmt_stock)).scalars().first()
        stock_obj.quantity = Decimal("1.00")
        await session.commit()

        # Transaction requires 2.00
        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-insufficient-{uuid.uuid4()}"
        with pytest.raises(InsufficientMaterialStockError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="material",
                entity_id=tx.id,
                action="approved",
                idempotency_key=idemp,
                supervisor_user_id=f["sup_user"].id,
                supervisor_emp_id=f["sup_emp"].id,
            )

        assert "insufficient stock" in exc_info.value.detail.lower()

        # Stock unchanged at 1.00
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        qty = (await session.execute(stmt_s)).scalar()
        assert qty == Decimal("1.00")

        # Transaction status unchanged
        stmt_tx = select(MaterialTransaction.status).where(MaterialTransaction.id == tx.id)
        st = (await session.execute(stmt_tx)).scalar()
        assert st == "submitted"

        # No movement ledger recorded
        stmt_m = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id
        )
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 0

        # No verification record
        stmt_vr = select(VerificationRecord).where(VerificationRecord.idempotency_key == idemp)
        vr = (await session.execute(stmt_vr)).scalars().first()
        assert vr is None


@pytest.mark.asyncio
async def test_repeated_approval_does_not_deduct_twice():
    """Identical idempotency key replay or re-approval does not deduct stock twice."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"test-idemp-{uuid.uuid4()}"

        # 1. First approval
        vr1, st1, rep1 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert st1 == "approved"
        assert rep1 is False

        # Stock is 8.00
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        assert (await session.execute(stmt_s)).scalar() == Decimal("8.00")

        # 2. Replay with identical idempotency key
        vr2, st2, rep2 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert rep2 is True
        assert vr2.id == vr1.id
        assert (await session.execute(stmt_s)).scalar() == Decimal("8.00")

        # 3. New idempotency key on already approved record
        new_idemp = f"test-new-idemp-{uuid.uuid4()}"
        vr3, st3, rep3 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=new_idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert rep3 is True
        assert (await session.execute(stmt_s)).scalar() == Decimal("8.00")

        # Exactly 1 movement exists
        stmt_m = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id
        )
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 1


@pytest.mark.asyncio
async def test_concurrent_approvals_cannot_produce_negative_stock():
    """Two concurrent approvals competing for remaining stock cannot make balance negative."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        # Set stock to 3.00
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_obj = (await session.execute(stmt_stock)).scalars().first()
        stock_obj.quantity = Decimal("3.00")
        await session.commit()

        # Two transactions each requiring 2.00 (sum 4.00 > 3.00)
        tx1 = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        tx2 = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add_all([tx1, tx2])
        await session.commit()

        tx1_id = tx1.id
        tx2_id = tx2.id
        site_id = f["site"].id
        mat_id = f["material"].id
        sup_user_id = f["sup_user"].id
        sup_emp_id = f["sup_emp"].id

    # Run approvals concurrently in distinct sessions
    async def try_approve(target_id: uuid.UUID):
        async with TestingSessionLocal() as s:
            return await VerificationService.verify_entity(
                session=s,
                entity_type="material",
                entity_id=target_id,
                action="approved",
                idempotency_key=f"concurrent-{target_id}",
                supervisor_user_id=sup_user_id,
                supervisor_emp_id=sup_emp_id,
            )

    results = await asyncio.gather(
        try_approve(tx1_id),
        try_approve(tx2_id),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"
    assert isinstance(failures[0], InsufficientMaterialStockError)

    # Check final stock is 1.00 (3.00 - 2.00), not negative!
    async with TestingSessionLocal() as s:
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == site_id,
            MaterialStock.material_id == mat_id,
        )
        final_qty = (await s.execute(stmt_s)).scalar()
        assert final_qty == Decimal("1.00")


@pytest.mark.asyncio
async def test_reopening_reverses_consumption_atomically():
    """Admin reopening an approved consumed transaction reverses the deduction and records returned movement."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        # 1. Approve
        idemp_app = f"app-{uuid.uuid4()}"
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp_app,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        assert (await session.execute(stmt_s)).scalar() == Decimal("8.00")

        # 2. Admin Reopens with correction_required
        idemp_reopen = f"reopen-{uuid.uuid4()}"
        vr_reopen, st_reopen, rep_reopen = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="correction_required",
            idempotency_key=idemp_reopen,
            supervisor_user_id=f["admin_user"].id,
            remarks="Reopening material transaction for quantity correction",
            is_admin=True,
        )

        assert st_reopen == "correction_required"
        assert rep_reopen is False

        # Stock is restored back to 10.00
        assert (await session.execute(stmt_s)).scalar() == Decimal("10.00")

        # Verify movements: 1 consumed + 1 returned
        stmt_m = (
            select(MaterialStockMovement)
            .where(MaterialStockMovement.material_transaction_id == tx.id)
            .order_by(MaterialStockMovement.created_at.asc())
        )
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 2

        assert movs[0].movement_type == "consumed"
        assert movs[0].quantity == Decimal("2.00")
        assert movs[0].balance_after == Decimal("8.00")

        assert movs[1].movement_type == "returned"
        assert movs[1].quantity == Decimal("2.00")
        assert movs[1].balance_after == Decimal("10.00")
        assert movs[1].idempotency_key == f"RETURN-{idemp_reopen}"[:100]


@pytest.mark.asyncio
async def test_reapproval_after_reversal_deducts_correctly():
    """Reapproving a reopened transaction deducts stock again without key conflict."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        # Step 1: Initial approval (10 -> 8)
        idemp1 = f"app-1-{uuid.uuid4()}"
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp1,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        # Step 2: Reopen (8 -> 10)
        idemp_reopen = f"reopen-{uuid.uuid4()}"
        await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="correction_required",
            idempotency_key=idemp_reopen,
            supervisor_user_id=f["admin_user"].id,
            remarks="Reopening transaction for verification test",
            is_admin=True,
        )

        # Simulate correction and resubmission after reopening
        tx.status = "submitted"
        await session.commit()

        # Step 3: Re-approve (10 -> 8)
        idemp2 = f"app-2-{uuid.uuid4()}"
        vr2, st2, rep2 = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx.id,
            action="approved",
            idempotency_key=idemp2,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        assert st2 == "approved"
        assert rep2 is False

        # Final stock is 8.00
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        assert (await session.execute(stmt_s)).scalar() == Decimal("8.00")

        # 3 distinct movements recorded
        stmt_m = (
            select(MaterialStockMovement)
            .where(MaterialStockMovement.material_transaction_id == tx.id)
            .order_by(MaterialStockMovement.created_at.asc())
        )
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 3
        assert [m.movement_type for m in movs] == ["consumed", "returned", "consumed"]
        assert [m.balance_after for m in movs] == [Decimal("8.00"), Decimal("10.00"), Decimal("8.00")]


@pytest.mark.asyncio
async def test_purchased_transactions_not_deducted_or_added_to_stock():
    """Purchased material transactions are not deducted or added to stock by this batch."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx_purchased = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="purchased",
            item_name="Purchased Cable Reel",
            quantity=5.0,
            amount=500.0,
            status="submitted",
        )
        session.add(tx_purchased)
        await session.commit()

        # Approve purchased transaction
        idemp = f"purchased-app-{uuid.uuid4()}"
        vr, st, rep = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx_purchased.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        assert st == "approved"
        assert rep is False

        # Stock remains strictly 10.00 (not 15.00, not 5.00)
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        assert (await session.execute(stmt_s)).scalar() == Decimal("10.00")

        # Zero stock movements
        stmt_m = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx_purchased.id
        )
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 0

        # Reopen purchased transaction
        idemp_reopen = f"purchased-reopen-{uuid.uuid4()}"
        vr_reopen, st_reopen, _ = await VerificationService.verify_entity(
            session=session,
            entity_type="material",
            entity_id=tx_purchased.id,
            action="correction_required",
            idempotency_key=idemp_reopen,
            supervisor_user_id=f["admin_user"].id,
            remarks="Reopening purchased transaction test remarks",
            is_admin=True,
        )

        assert st_reopen == "correction_required"
        # Stock still strictly 10.00
        assert (await session.execute(stmt_s)).scalar() == Decimal("10.00")


@pytest.mark.asyncio
async def test_audit_or_database_failure_rolls_back_entire_operation():
    """If database commit fails, stock deduction, movement, status and verification record roll back."""
    async with TestingSessionLocal() as session:
        f = await setup_batch4_fixtures(session)

        tx = MaterialTransaction(
            daily_work_entry_id=f["dwe"].id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=2.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        tx_id = tx.id
        site_id = f["site"].id
        mat_id = f["material"].id
        sup_user_id = f["sup_user"].id
        sup_emp_id = f["sup_emp"].id
        idemp = f"rollback-test-{uuid.uuid4()}"

    # In a fresh session, patch commit to raise an exception
    async with TestingSessionLocal() as session:
        with patch.object(session, "commit", side_effect=Exception("Simulated commit/audit failure")):
            with pytest.raises(Exception) as exc_info:
                await VerificationService.verify_entity(
                    session=session,
                    entity_type="material",
                    entity_id=tx_id,
                    action="approved",
                    idempotency_key=idemp,
                    supervisor_user_id=sup_user_id,
                    supervisor_emp_id=sup_emp_id,
                )
            assert "Simulated commit/audit failure" in str(exc_info.value)

    # In another fresh session, confirm database state is untouched
    async with TestingSessionLocal() as session:
        # Stock remains 10.00
        stmt_s = select(MaterialStock.quantity).where(
            MaterialStock.site_id == site_id,
            MaterialStock.material_id == mat_id,
        )
        assert (await session.execute(stmt_s)).scalar() == Decimal("10.00")

        # Transaction status remains submitted
        stmt_tx = select(MaterialTransaction.status).where(MaterialTransaction.id == tx_id)
        assert (await session.execute(stmt_tx)).scalar() == "submitted"

        # No movement ledger
        stmt_m = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx_id
        )
        assert len((await session.execute(stmt_m)).scalars().all()) == 0

        # No verification record
        stmt_vr = select(VerificationRecord).where(VerificationRecord.idempotency_key == idemp)
        assert (await session.execute(stmt_vr)).scalars().first() is None

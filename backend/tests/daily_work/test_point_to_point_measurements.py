import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi import HTTPException
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
    WorkOrder,
)
from app.models.workforce import Employee
from app.modules.daily_work.schemas import DailyWorkEntryCreate, DailyWorkEntryUpdate, WorkMeasurementItem
from app.modules.daily_work.service import DailyWorkService
from app.modules.daily_work.material_service import MaterialTransactionService
from app.modules.verification.service import VerificationService
from tests.conftest import TestingSessionLocal


async def setup_measurement_fixtures(session: AsyncSession):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # Users
    worker_user = User(id=uuid.uuid4(), mobile_id=f"W-{suffix}", role="employee", is_active=True)
    sup_user = User(id=uuid.uuid4(), mobile_id=f"S-{suffix}", role="supervisor", is_active=True)
    session.add_all([worker_user, sup_user])
    await session.commit()

    # Employees
    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        name=f"Supervisor {suffix}",
        employee_code=f"SUP-{suffix}",
        mobile_id=sup_user.mobile_id,
        is_active=True,
    )
    worker_emp = Employee(
        id=uuid.uuid4(),
        user_id=worker_user.id,
        name=f"Worker {suffix}",
        employee_code=f"EMP-{suffix}",
        mobile_id=worker_user.mobile_id,
        supervisor_id=sup_emp.id,
        is_active=True,
    )
    session.add_all([sup_emp, worker_emp])
    await session.commit()

    # Project and Site
    client = Client(name=f"Client {suffix}", is_active=True)
    session.add(client)
    await session.commit()

    project = Project(client_id=client.id, name=f"Project {suffix}", status="active")
    session.add(project)
    await session.commit()

    site = Site(
        name=f"Site {suffix}",
        project_id=project.id,
        supervisor_id=sup_emp.id,
        location="POINT(77.5946 12.9716)",
        permitted_radius_m=500.0,
    )
    session.add(site)
    await session.commit()

    assignment = EmployeeSiteAssignment(
        employee_id=worker_emp.id,
        site_id=site.id,
        is_active=True,
    )
    session.add(assignment)

    activity = Activity(
        name=f"Fibre Cabling {suffix}",
        unit_of_measure="metre",
        approved_rate=15.00,
        category="cable",
        is_active=True,
    )
    session.add(activity)

    material = Material(
        material_code=f"MAT-CABLE-{suffix}",
        name=f"Armoured Fibre Cable {suffix}",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=5000.0,
        is_active=True,
    )
    session.add(material)
    await session.flush()

    stock = MaterialStock(
        site_id=site.id,
        material_id=material.id,
        quantity=Decimal("100.00"),
    )
    session.add(stock)

    att_record = AttendanceRecord(
        employee_id=worker_emp.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        check_out_time=None,
        status="draft",
        is_within_geofence=True,
    )
    session.add(att_record)
    await session.commit()

    return {
        "worker_user": worker_user,
        "sup_user": sup_user,
        "worker_emp": worker_emp,
        "sup_emp": sup_emp,
        "site": site,
        "activity": activity,
        "material": material,
        "stock": stock,
        "att_record": att_record,
        "today": today,
    }


# ==============================================================================
# 1. MEASUREMENT ROWS & QUANTITY DERIVATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_entry_with_multiple_measurements_derives_total_quantity():
    """Point-to-point measurement rows automatically sum to total quantity."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        measurements = [
            WorkMeasurementItem(start_point="P1", end_point="P2", distance=50.0),
            WorkMeasurementItem(start_point="P2", end_point="P3", distance=20.0),
            WorkMeasurementItem(start_point="P3", end_point="P4", distance=30.0),
        ]

        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=measurements,
            remarks="Recorded 3 spans",
        )

        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )

        # Quantity must be automatically derived as 50 + 20 + 30 = 100.0
        assert float(entry.quantity) == 100.0
        assert entry.measurements is not None
        assert len(entry.measurements) == 3
        assert entry.measurements[0]["start_point"] == "P1"
        assert entry.measurements[0]["end_point"] == "P2"
        assert entry.measurements[0]["distance"] == 50.0
        assert entry.measurements[1]["distance"] == 20.0
        assert entry.measurements[2]["distance"] == 30.0


@pytest.mark.asyncio
async def test_measurement_validation_errors():
    """Validates missing start_point, end_point, and non-positive distance."""
    # 1. Empty start_point
    with pytest.raises(Exception):
        WorkMeasurementItem(start_point="", end_point="P2", distance=50.0)

    # 2. Whitespace-only end_point
    with pytest.raises(Exception):
        WorkMeasurementItem(start_point="P1", end_point="   ", distance=50.0)

    # 3. Non-positive distance (0)
    with pytest.raises(Exception):
        WorkMeasurementItem(start_point="P1", end_point="P2", distance=0.0)

    # 4. Negative distance
    with pytest.raises(Exception):
        WorkMeasurementItem(start_point="P1", end_point="P2", distance=-10.0)


@pytest.mark.asyncio
async def test_update_measurements_rederives_quantity_and_syncs_material():
    """Updating measurements re-sums quantity and synchronizes linked consumed material transaction."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # 1. Create initial entry with 40m
        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=40.0),
            ],
            remarks="Initial 40m",
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )
        assert float(entry.quantity) == 40.0

        # Create linked consumed material transaction
        tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=40.0,
            amount=0.0,
            status="draft",
        )
        session.add(tx)
        await session.commit()

        # 2. Update with additional span: 40m + 30m = 70m
        update_payload = DailyWorkEntryUpdate(
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=40.0),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=30.0),
            ],
            remarks="Extended to 70m",
        )
        updated_entry = await DailyWorkService.update_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
            data=update_payload,
        )

        assert float(updated_entry.quantity) == 70.0
        assert len(updated_entry.measurements) == 2

        # 3. Verify linked material transaction quantity was synchronized to 70.0
        stmt_tx = select(MaterialTransaction).where(MaterialTransaction.id == tx.id)
        tx_db = (await session.execute(stmt_tx)).scalars().first()
        assert float(tx_db.quantity) == 70.0


# ==============================================================================
# 2. SUPERVISOR APPROVAL & INVENTORY INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_supervisor_approval_deducts_exact_measured_stock():
    """Supervisor approval deducts exactly the summed measurement distance from stock."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # 1. Create entry with P1->P2: 45m, P2->P3: 25m = 70m
        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=45.0),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=25.0),
            ],
            remarks="Cable pulling 70m",
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )
        assert float(entry.quantity) == 70.0

        # Submit the work entry
        await DailyWorkService.submit_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
        )

        # Linked consumed material transaction (quantity=70)
        tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=70.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        # 2. Supervisor approves the daily work entry
        idemp = f"APPR-{uuid.uuid4()}"
        vr, status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        assert status == "approved"
        assert is_replay is False

        # 3. Check MaterialStock deduction: 100.00 - 70.00 = 30.00
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("30.00")

        # 4. Check MaterialStockMovement record
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id
        )
        mov = (await session.execute(stmt_mov)).scalars().first()
        assert mov is not None
        assert mov.movement_type == "consumed"
        assert mov.quantity == Decimal("70.00")
        assert mov.balance_after == Decimal("30.00")


@pytest.mark.asyncio
async def test_supervisor_rejection_leaves_stock_untouched():
    """Supervisor rejection does not deduct any material stock."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # 1. Create entry with 50m
        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=50.0),
            ],
            remarks="Cabling 50m",
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )

        await DailyWorkService.submit_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
        )

        tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=50.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        # 2. Supervisor rejects
        idemp = f"REJ-{uuid.uuid4()}"
        vr, status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="rejected",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
            remarks="Work rejected: faulty installation",
        )

        assert status == "rejected"

        # 3. Stock remains 100.00
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("100.00")

        # No consumption movement created
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id
        )
        mov = (await session.execute(stmt_mov)).scalars().first()
        assert mov is None


@pytest.mark.asyncio
async def test_reopen_correction_reverses_deduction_idempotently():
    """Reopening an approved entry returns deducted stock and logs returned movement."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # 1. Create entry with 60m
        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=30.0),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=30.0),
            ],
            remarks="Cabling 60m",
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )

        await DailyWorkService.submit_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
        )

        tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=60.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        # Approve: stock 100 -> 40
        appr_idemp = f"APPR-{uuid.uuid4()}"
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="approved",
            idempotency_key=appr_idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )

        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("40.00")

        # 2. Reopen for corrections: stock 40 -> 100
        reopen_idemp = f"REOPEN-{uuid.uuid4()}"
        vr, status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="correction_required",
            idempotency_key=reopen_idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
            remarks="Measurement needs re-checking",
            is_admin=True,
        )

        assert status == "correction_required"

        # Check stock returned
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("100.00")

        # Check return movement
        stmt_ret = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx.id,
            MaterialStockMovement.movement_type == "returned",
        )
        ret_mov = (await session.execute(stmt_ret)).scalars().first()
        assert ret_mov is not None
        assert ret_mov.quantity == Decimal("60.00")
        assert ret_mov.balance_after == Decimal("100.00")


@pytest.mark.asyncio
async def test_idempotent_approval_does_not_double_deduct():
    """Replaying approval with the same idempotency_key returns cached result without double-deduction."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        payload = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=25.0),
            ],
            remarks="Cabling 25m",
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )

        await DailyWorkService.submit_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
        )

        tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=f["material"].id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name=f["material"].name,
            quantity=25.0,
            amount=0.0,
            status="submitted",
        )
        session.add(tx)
        await session.commit()

        idemp = f"REPLAY-IDEMP-{uuid.uuid4()}"

        # First approval
        vr1, status1, is_replay1 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert status1 == "approved"
        assert is_replay1 is False

        # Stock is 100 - 25 = 75
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("75.00")

        # Second approval with identical idempotency key (replay)
        vr2, status2, is_replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="approved",
            idempotency_key=idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert is_replay2 is True
        assert status2 == "approved"

        # Stock must remain 75.00 (NOT 50.00)
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        assert stock_db.quantity == Decimal("75.00")


@pytest.mark.asyncio
async def test_auto_sync_measurement_to_mapped_material_on_create_and_update():
    """Test required behavior 1, 2, 3:
    P1 -> P2 = 100m, P2 -> P3 = 50m. Total = 150m.
    The linked Cable material transaction must automatically show 150 metres, not 1.00.
    """
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        measurements = [
            WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("100.00")),
            WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("50.00")),
        ]
        payload = DailyWorkEntryCreate(
            idempotency_key=f"AUTO-SYNC-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=measurements,
            material_id=f["material"].id,
        )

        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )

        assert entry.quantity == Decimal("150.00")

        # Verify linked material transaction has synchronized to 150.00, not 1.00
        stmt = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == entry.id)
        txs = (await session.execute(stmt)).scalars().all()
        assert len(txs) == 1
        assert txs[0].quantity == Decimal("150.00")
        assert txs[0].transaction_type == "consumed"
        assert txs[0].material_id == f["material"].id


@pytest.mark.asyncio
async def test_measurement_changes_immediately_sync_quantity():
    """Test required behavior 4:
    Update quantity immediately when measurement rows are added, edited, or removed.
    """
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # Initial: 100m + 50m = 150m
        payload = DailyWorkEntryCreate(
            idempotency_key=f"IMMEDIATE-SYNC-{uuid.uuid4()}",
            activity_id=f["activity"].id,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("100.00")),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("50.00")),
            ],
            material_id=f["material"].id,
        )
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=payload,
        )
        assert entry.quantity == Decimal("150.00")

        # Edit measurement row (P1 -> P2 = 80m, remove P2 -> P3): total = 80m
        update_payload1 = DailyWorkEntryUpdate(
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("80.00")),
            ]
        )
        updated_entry1 = await DailyWorkService.update_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
            data=update_payload1,
        )
        assert updated_entry1.quantity == Decimal("80.00")

        stmt = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == entry.id)
        txs = (await session.execute(stmt)).scalars().all()
        assert len(txs) == 1
        assert txs[0].quantity == Decimal("80.00")

        # Add measurement row (P1 -> P2 = 80m, P2 -> P3 = 120m): total = 200m
        update_payload2 = DailyWorkEntryUpdate(
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("80.00")),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("120.00")),
            ]
        )
        updated_entry2 = await DailyWorkService.update_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
            data=update_payload2,
        )
        assert updated_entry2.quantity == Decimal("200.00")

        stmt = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == entry.id)
        txs = (await session.execute(stmt)).scalars().all()
        assert len(txs) == 1
        assert txs[0].quantity == Decimal("200.00")


@pytest.mark.asyncio
async def test_unrelated_and_purchased_materials_not_synchronized():
    """Test required behavior 7:
    Do not automatically apply a distance total to unrelated materials or purchased-locally transactions.
    Inspect existing activity-to-material mappings and only synchronize the appropriate consumed material.
    """
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # Create unrelated consumable material (RJ45 Connectors in pcs, category=consumable)
        rj45_mat = Material(
            material_code=f"MAT-RJ45-{uuid.uuid4().hex[:6]}",
            name="RJ45 Connectors",
            unit_of_measure="pcs",
            category="consumable",
            purchase_approval_limit=50.00,
            is_active=True,
        )
        session.add(rj45_mat)
        await session.commit()

        # Create entry with cable measurements = 150m
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=DailyWorkEntryCreate(
                idempotency_key=f"UNRELATED-MAT-{uuid.uuid4()}",
                activity_id=f["activity"].id,
                measurements=[
                    WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("100.00")),
                    WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("50.00")),
                ],
                material_id=f["material"].id,
            ),
        )

        # Add unrelated consumed material transaction (RJ45 = 10 pcs)
        rj45_tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            material_id=rj45_mat.id,
            site_id=f["site"].id,
            transaction_type="consumed",
            item_name="RJ45 Connectors",
            quantity=10.0,
            amount=0.0,
            status="draft",
        )
        # Add purchased-locally transaction (PVC Tape = 5 units)
        purchased_tx = MaterialTransaction(
            daily_work_entry_id=entry.id,
            site_id=f["site"].id,
            transaction_type="purchased",
            item_name="PVC Insulation Tape",
            quantity=5.0,
            amount=50.0,
            status="draft",
        )
        session.add_all([rj45_tx, purchased_tx])
        await session.commit()

        # Update cable measurements to 300m
        await DailyWorkService.update_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
            data=DailyWorkEntryUpdate(
                measurements=[
                    WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("200.00")),
                    WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("100.00")),
                ]
            ),
        )

        # Refresh transactions
        stmt = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == entry.id)
        all_txs = (await session.execute(stmt)).scalars().all()
        assert len(all_txs) == 3

        cable_tx = next(t for t in all_txs if t.material_id == f["material"].id)
        rj45_tx_db = next(t for t in all_txs if t.material_id == rj45_mat.id)
        tape_tx_db = next(t for t in all_txs if t.transaction_type == "purchased")

        # Matching consumed cable was synchronized to 300.00
        assert cable_tx.quantity == Decimal("300.00")
        # Unrelated consumable RJ45 Connectors remains 10.00
        assert rj45_tx_db.quantity == Decimal("10.00")
        # Purchased-locally tape remains 5.00
        assert tape_tx_db.quantity == Decimal("5.00")


@pytest.mark.asyncio
async def test_explain_missing_configuration_when_unmapped_or_ambiguous():
    """Test required behavior 8:
    If no reliable mapping exists, explain the missing configuration instead of guessing.
    """
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # 1. Unmapped category activity (drilling has no matching material category)
        unmapped_act = Activity(
            name=f"Core Drilling {uuid.uuid4().hex[:6]}",
            unit_of_measure="metre",
            approved_rate=20.00,
            category="drilling",
            is_active=True,
        )
        session.add(unmapped_act)
        await session.commit()

        res1 = await DailyWorkService.explain_activity_material_mapping(session=session, activity_id=unmapped_act.id)
        assert res1["is_mapped"] is False
        assert "No active inventory material found in catalogue for category 'drilling'" in res1["reason"]

        # 2. Reliably mapped activity (cable -> cable in metre)
        # Ensure only f["material"] is active for category="cable" in this test
        stmt_other = select(Material).where(Material.category == "cable", Material.id != f["material"].id)
        other_mats = (await session.execute(stmt_other)).scalars().all()
        for m in other_mats:
            m.is_active = False
        await session.commit()

        res2 = await DailyWorkService.explain_activity_material_mapping(session=session, activity_id=f["activity"].id)
        assert res2["is_mapped"] is True
        assert res2["mapped_material_id"] == str(f["material"].id)
        assert res2["mapped_material_name"] == f["material"].name

        # 3. Ambiguous mapping (multiple materials in same category with compatible UOM)
        second_cable = Material(
            material_code=f"MAT-CABLE2-{uuid.uuid4().hex[:6]}",
            name="24-Core Single Mode Fibre Cable",
            unit_of_measure="metre",
            category="cable",
            purchase_approval_limit=500.00,
            is_active=True,
        )
        session.add(second_cable)
        await session.commit()

        res3 = await DailyWorkService.explain_activity_material_mapping(session=session, activity_id=f["activity"].id)
        assert res3["is_mapped"] is False
        assert "Multiple inventory materials match" in res3["reason"]


@pytest.mark.asyncio
async def test_avoid_duplicate_material_transactions_and_duplicate_stock_deduction():
    """Test required behavior 5 & 6:
    Avoid creating duplicate material transactions or duplicate stock deductions.
    Preserve existing material selection, stock validation, supervisor approval,
    inventory audit trail, rejection, and correction/reversal workflows.
    """
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)

        # Create entry with 150m measurement total
        entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=DailyWorkEntryCreate(
                idempotency_key=f"NO-DUP-{uuid.uuid4()}",
                activity_id=f["activity"].id,
                measurements=[
                    WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("100.00")),
                    WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("50.00")),
                ],
            ),
        )

        # Call MaterialTransactionService.create_material_transaction for consumed cable
        tx1 = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={
                "transaction_type": "consumed",
                "material_id": str(f["material"].id),
                "item_name": f["material"].name,
                "quantity": 150.0,
                "amount": 0.0,
            },
            employee_id=f["worker_emp"].id,
        )
        assert tx1.quantity == Decimal("150.00")

        # Second create_material_transaction call with updated quantity 160.0
        tx2 = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={
                "transaction_type": "consumed",
                "material_id": str(f["material"].id),
                "item_name": f["material"].name,
                "quantity": 160.0,
                "amount": 0.0,
            },
            employee_id=f["worker_emp"].id,
        )
        assert tx2.id == tx1.id
        assert tx2.quantity == Decimal("160.00")

        # Verify only 1 material transaction exists (no duplicate records)
        stmt_count = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id == entry.id)
        all_txs = (await session.execute(stmt_count)).scalars().all()
        assert len(all_txs) == 1

        # Submit work entry
        await DailyWorkService.submit_work_entry(
            session=session,
            entry_id=entry.id,
            employee_id=f["worker_emp"].id,
        )

        # Supervisor Approval deducts stock
        stmt_stock = select(MaterialStock).where(
            MaterialStock.site_id == f["site"].id,
            MaterialStock.material_id == f["material"].id,
        )
        stock_db = (await session.execute(stmt_stock)).scalars().first()
        stock_db.quantity = Decimal("500.00")
        await session.commit()

        approval_idemp = f"APPR-IDEMP-{uuid.uuid4()}"
        vr, st, is_rep = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="approved",
            idempotency_key=approval_idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
        )
        assert st == "approved"
        assert is_rep is False

        # Stock deducted: 500 - 160 = 340
        await session.refresh(stock_db)
        assert stock_db.quantity == Decimal("340.00")

        # Verify movements audit trail
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == tx1.id
        )
        movs = (await session.execute(stmt_mov)).scalars().all()
        assert len(movs) == 1
        assert movs[0].quantity == Decimal("160.00")
        assert movs[0].movement_type == "consumed"

        # Reopen / correction_required reverses the stock deduction cleanly
        reopen_idemp = f"REOPEN-IDEMP-{uuid.uuid4()}"
        vr2, st2, is_rep2 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=entry.id,
            action="correction_required",
            idempotency_key=reopen_idemp,
            supervisor_user_id=f["sup_user"].id,
            supervisor_emp_id=f["sup_emp"].id,
            remarks="Fix cable type",
            is_admin=True,
        )
        assert st2 == "correction_required"

        # Stock restored: 340 + 160 = 500
        await session.refresh(stock_db)
        assert stock_db.quantity == Decimal("500.00")


@pytest.mark.asyncio
async def test_measurement_unit_preservation_for_pcs_and_metre_activities():
    """Verify backend preserves both pcs and metre activity units when deriving total quantity from measurements."""
    async with TestingSessionLocal() as session:
        f = await setup_measurement_fixtures(session)
        suffix = uuid.uuid4().hex[:8]

        # 1. Activity with unit_of_measure="pcs" (e.g. CCTV installation - DEVICE)
        cctv_activity = Activity(
            name=f"CCTV Installation {suffix}",
            unit_of_measure="pcs",
            approved_rate=45.00,
            category="device",
            is_active=True,
        )
        session.add(cctv_activity)

        # 2. Activity with unit_of_measure="metres" (e.g. Cat 6 cable laying - CABLE)
        cable_activity = Activity(
            name=f"Cat 6 Cable Laying {suffix}",
            unit_of_measure="metres",
            approved_rate=15.00,
            category="cable",
            is_active=True,
        )
        session.add(cable_activity)
        await session.commit()

        # Create entry for CCTV (pcs) with measurements P1->P2 = 60, P2->P3 = 40 (total 100)
        cctv_entry_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-CCTV-{suffix}",
            activity_id=cctv_activity.id,
            work_date=f["att_record"].date,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("60")),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("40")),
            ],
        )
        cctv_entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=cctv_entry_data,
        )
        assert cctv_entry.quantity == Decimal("100")
        assert cctv_entry.uom == "pcs"
        assert len(cctv_entry.measurements) == 2

        # Create entry for Cable (metres) with measurements P1->P2 = 70, P2->P3 = 30 (total 100)
        cable_entry_data = DailyWorkEntryCreate(
            idempotency_key=f"IDEMP-CABLE-{suffix}",
            activity_id=cable_activity.id,
            work_date=f["att_record"].date,
            measurements=[
                WorkMeasurementItem(start_point="P1", end_point="P2", distance=Decimal("70")),
                WorkMeasurementItem(start_point="P2", end_point="P3", distance=Decimal("30")),
            ],
        )
        cable_entry = await DailyWorkService.create_work_entry(
            session=session,
            employee_id=f["worker_emp"].id,
            data=cable_entry_data,
        )
        assert cable_entry.quantity == Decimal("100")
        assert cable_entry.uom == "metres"
        assert len(cable_entry.measurements) == 2

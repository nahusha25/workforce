from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import tempfile
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
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
from app.models.workforce import Employee, Role
from app.modules.daily_work.photo_service import WorkPhotoService
from app.modules.verification.exceptions import (
    InsufficientMaterialStockError,
    InvalidVerificationStateError,
)
from app.modules.verification.service import VerificationService
from app.shared.file_storage import LocalFileStorage
from tests.conftest import TestingSessionLocal

VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"A" * 100)
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"B" * 100)


async def setup_test_env(session: AsyncSession):
    suffix = str(uuid.uuid4())[:8]

    worker_user = User(id=uuid.uuid4(), mobile_id=f"W-{suffix}", role="employee", is_active=True)
    sup_user = User(id=uuid.uuid4(), mobile_id=f"S-{suffix}", role="supervisor", is_active=True)
    admin_user = User(id=uuid.uuid4(), mobile_id=f"A-{suffix}", role="administrator", is_active=True)
    session.add_all([worker_user, sup_user, admin_user])
    await session.flush()

    sup_emp = Employee(
        id=uuid.uuid4(),
        user_id=sup_user.id,
        employee_code=f"SUP-{suffix}",
        name="Cable Supervisor",
        mobile_id=f"S-{suffix}",
        is_active=True,
    )
    session.add(sup_emp)
    await session.flush()

    worker_emp = Employee(
        id=uuid.uuid4(),
        user_id=worker_user.id,
        employee_code=f"W-{suffix}",
        name="Cable Technician",
        mobile_id=f"W-{suffix}",
        supervisor_id=sup_emp.id,
        is_active=True,
    )
    session.add(worker_emp)

    client = Client(name=f"Client {suffix}", is_active=True)
    session.add(client)
    await session.flush()

    project = Project(name=f"Project {suffix}", client_id=client.id, status="active")
    session.add(project)
    await session.flush()

    site = Site(
        name=f"Site {suffix}",
        project_id=project.id,
        supervisor_id=sup_emp.id,
        permitted_radius_m=500.0,
        is_active=True,
    )
    session.add(site)
    await session.flush()

    activity = Activity(
        name="Cable Laying 11kV",
        unit_of_measure="metres",
        approved_rate=50.0,
        category="cable",
    )
    material = Material(
        material_code=f"CBL-{suffix}",
        name="11kV XLPE Cable",
        unit_of_measure="metres",
        category="cable",
        purchase_approval_limit=50000.0,
        is_active=True,
    )
    session.add_all([activity, material])
    await session.flush()

    today = date.today()
    att = AttendanceRecord(
        employee_id=worker_emp.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc) - timedelta(hours=8),
        check_in_distance_m=10.0,
        check_out_time=datetime.now(timezone.utc),
        check_out_distance_m=15.0,
        working_hours=8.0,
        is_within_geofence=True,
        status="draft",
    )
    session.add(att)
    await session.flush()

    # Initial stock: 500 metres of cable at site
    stock = MaterialStock(
        site_id=site.id,
        material_id=material.id,
        quantity=Decimal("500.00"),
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
        "activity": activity,
        "material": material,
        "attendance": att,
        "stock": stock,
        "today": today,
    }


@pytest.mark.asyncio
async def test_start_and_end_photos_storage_and_supervisor_visibility():
    """Verify employee can attach start-point and end-point photos, and supervisor sees both with reported quantity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileStorage(base_dir=tmpdir, base_url="/uploads")
        async with TestingSessionLocal() as session:
            env = await setup_test_env(session)
            worker_emp = env["worker_emp"]
            site = env["site"]
            act = env["activity"]
            att = env["attendance"]
            sup_emp = env["sup_emp"]
            today = env["today"]

            # Create daily work entry (120 metres cable laying)
            dwe = DailyWorkEntry(
                idempotency_key=str(uuid.uuid4()),
                attendance_record_id=att.id,
                employee_id=worker_emp.id,
                site_id=site.id,
                activity_id=act.id,
                work_date=today,
                quantity=Decimal("120.00"),
                uom="metres",
                status="draft",
                remarks="Laying 11kV cable along trench A-B",
            )
            session.add(dwe)
            await session.commit()

            # 1. Upload start-point photo
            photo_start = await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=dwe.id,
                file_data=VALID_JPEG_BYTES,
                filename="start_point.jpg",
                content_type="image/jpeg",
                employee_id=worker_emp.id,
                storage=storage,
                photo_type="start_point",
            )
            assert photo_start.photo_type == "start_point"

            # 2. Upload end-point photo
            photo_end = await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=dwe.id,
                file_data=VALID_PNG_BYTES,
                filename="end_point.png",
                content_type="image/png",
                employee_id=worker_emp.id,
                storage=storage,
                photo_type="end_point",
            )
            assert photo_end.photo_type == "end_point"

            # 3. Retake start-point photo -> old start photo is replaced
            photo_start_retake = await WorkPhotoService.upload_photo(
                session=session,
                daily_work_entry_id=dwe.id,
                file_data=VALID_JPEG_BYTES,
                filename="start_retake.jpg",
                content_type="image/jpeg",
                employee_id=worker_emp.id,
                storage=storage,
                photo_type="start_point",
            )
            assert photo_start_retake.photo_type == "start_point"
            assert photo_start_retake.id != photo_start.id

            # Verify only 2 photos exist now: 1 start_point and 1 end_point
            photos = await WorkPhotoService.list_photos(
                session=session,
                daily_work_entry_id=dwe.id,
                employee_id=worker_emp.id,
            )
            assert len(photos) == 2
            types = {p.photo_type for p in photos}
            assert types == {"start_point", "end_point"}

            # Transition work entry to submitted
            dwe.status = "submitted"
            await session.commit()

            # 4. Supervisor views employee day detail
            detail = await VerificationService.get_employee_detail(
                session=session,
                supervisor_emp_id=sup_emp.id,
                employee_id=worker_emp.id,
                review_date=today,
            )
            assert len(detail.work_entries) == 1
            entry_detail = detail.work_entries[0]

            # Verify reported quantity and unit
            assert entry_detail.quantity == Decimal("120.00")
            assert entry_detail.uom == "metres"

            # Verify photos visible to supervisor with photo_type
            assert len(entry_detail.photos) == 2
            photo_types_seen = {p.photo_type for p in entry_detail.photos}
            assert photo_types_seen == {"start_point", "end_point"}


@pytest.mark.asyncio
async def test_supervisor_approval_deducts_inventory_stock():
    """Verify approving a daily work entry with 120m cable deducts stock from 500m to 380m."""
    async with TestingSessionLocal() as session:
        env = await setup_test_env(session)
        worker_emp = env["worker_emp"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        site = env["site"]
        act = env["activity"]
        mat = env["material"]
        att = env["attendance"]
        today = env["today"]

        # Create daily work entry (120 metres)
        dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=today,
            quantity=Decimal("120.00"),
            uom="metres",
            status="submitted",
        )
        session.add(dwe)
        await session.flush()

        # Consumed material transaction (120 metres cable) linked to work entry
        mat_tx = MaterialTransaction(
            daily_work_entry_id=dwe.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=Decimal("120.00"),
            amount=Decimal("0.00"),
            status="submitted",
        )
        session.add(mat_tx)
        await session.commit()

        # Initial stock check: 500.00
        stmt_stk = select(MaterialStock).where(
            MaterialStock.site_id == site.id,
            MaterialStock.material_id == mat.id,
        )
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("500.00")

        # Supervisor approves the daily work entry
        idemp_key = f"APP-DWE-{uuid.uuid4().hex[:12]}"
        vr, target_status, is_replay = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=idemp_key,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        assert target_status == "approved"
        assert is_replay is False

        # Verify stock decreased to 380.00
        res_stk = await session.execute(stmt_stk)
        stock_row = res_stk.scalars().first()
        assert stock_row.quantity == Decimal("380.00")

        # Verify MaterialStockMovement created
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == mat_tx.id
        )
        res_mov = await session.execute(stmt_mov)
        movement = res_mov.scalars().first()
        assert movement is not None
        assert movement.movement_type == "consumed"
        assert movement.quantity == Decimal("120.00")
        assert movement.balance_after == Decimal("380.00")
        assert movement.site_id == site.id
        assert movement.material_id == mat.id

        # Verify MaterialTransaction status is approved
        stmt_mat = select(MaterialTransaction).where(MaterialTransaction.id == mat_tx.id)
        res_mat = await session.execute(stmt_mat)
        assert res_mat.scalars().first().status == "approved"


@pytest.mark.asyncio
async def test_rejection_does_not_deduct_stock():
    """Verify rejecting a work entry does not deduct stock, stock remains 500m."""
    async with TestingSessionLocal() as session:
        env = await setup_test_env(session)
        worker_emp = env["worker_emp"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        site = env["site"]
        act = env["activity"]
        mat = env["material"]
        att = env["attendance"]
        today = env["today"]

        dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=today,
            quantity=Decimal("120.00"),
            uom="metres",
            status="submitted",
        )
        session.add(dwe)
        await session.flush()

        mat_tx = MaterialTransaction(
            daily_work_entry_id=dwe.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=Decimal("120.00"),
            amount=Decimal("0.00"),
            status="submitted",
        )
        session.add(mat_tx)
        await session.commit()

        # Reject work entry
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="rejected",
            idempotency_key=f"REJ-{uuid.uuid4().hex[:12]}",
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
            remarks="Work failed visual inspection along the trench",
        )

        # Stock remains 500.00
        stmt_stk = select(MaterialStock).where(
            MaterialStock.site_id == site.id,
            MaterialStock.material_id == mat.id,
        )
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("500.00")

        # No movement created
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == mat_tx.id
        )
        res_mov = await session.execute(stmt_mov)
        assert res_mov.scalars().first() is None

        # MaterialTransaction status is rejected
        stmt_mat = select(MaterialTransaction).where(MaterialTransaction.id == mat_tx.id)
        res_mat = await session.execute(stmt_mat)
        assert res_mat.scalars().first().status == "rejected"


@pytest.mark.asyncio
async def test_repeated_approval_does_not_deduct_twice():
    """Verify repeated approval (retry or replay) does not deduct stock a second time."""
    async with TestingSessionLocal() as session:
        env = await setup_test_env(session)
        worker_emp = env["worker_emp"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        site = env["site"]
        act = env["activity"]
        mat = env["material"]
        att = env["attendance"]
        today = env["today"]

        dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=today,
            quantity=Decimal("120.00"),
            uom="metres",
            status="submitted",
        )
        session.add(dwe)
        await session.flush()

        mat_tx = MaterialTransaction(
            daily_work_entry_id=dwe.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=Decimal("120.00"),
            amount=Decimal("0.00"),
            status="submitted",
        )
        session.add(mat_tx)
        await session.commit()

        idemp_key = f"APP-REP-{uuid.uuid4().hex[:12]}"
        # First approval
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=idemp_key,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )

        stmt_stk = select(MaterialStock).where(
            MaterialStock.site_id == site.id,
            MaterialStock.material_id == mat.id,
        )
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("380.00")

        # Second approval: same idempotency key (idempotent replay)
        vr2, status2, replay2 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=idemp_key,
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        assert replay2 is True
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("380.00")

        # Third approval: different idempotency key on already approved entry
        vr3, status3, replay3 = await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=f"APP-NEW-{uuid.uuid4().hex[:12]}",
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )
        assert replay3 is True
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("380.00")

        # Exactly 1 movement created
        stmt_mov = select(MaterialStockMovement).where(
            MaterialStockMovement.material_transaction_id == mat_tx.id
        )
        res_mov = await session.execute(stmt_mov)
        movements = list(res_mov.scalars().all())
        assert len(movements) == 1


@pytest.mark.asyncio
async def test_insufficient_stock_fails_atomically():
    """Verify insufficient stock raises error and leaves work entry submitted (not approved)."""
    async with TestingSessionLocal() as session:
        env = await setup_test_env(session)
        worker_emp = env["worker_emp"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        site = env["site"]
        act = env["activity"]
        mat = env["material"]
        att = env["attendance"]
        today = env["today"]

        # Request 600 metres when stock is only 500 metres
        dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=today,
            quantity=Decimal("600.00"),
            uom="metres",
            status="submitted",
        )
        session.add(dwe)
        await session.flush()

        mat_tx = MaterialTransaction(
            daily_work_entry_id=dwe.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=Decimal("600.00"),
            amount=Decimal("0.00"),
            status="submitted",
        )
        session.add(mat_tx)
        await session.commit()

        # Attempt supervisor approval -> raises InsufficientMaterialStockError
        with pytest.raises(InsufficientMaterialStockError) as exc_info:
            await VerificationService.verify_entity(
                session=session,
                entity_type="daily_work",
                entity_id=dwe.id,
                action="approved",
                idempotency_key=f"APP-FAIL-{uuid.uuid4().hex[:12]}",
                supervisor_user_id=sup_user.id,
                supervisor_emp_id=sup_emp.id,
            )
        assert "Insufficient stock" in str(exc_info.value)

        # Fresh query to check transactional state
        async with TestingSessionLocal() as verify_session:
            stmt_dwe = select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id)
            res_dwe = await verify_session.execute(stmt_dwe)
            assert res_dwe.scalars().first().status == "submitted"

            stmt_stk = select(MaterialStock).where(
                MaterialStock.site_id == site.id,
                MaterialStock.material_id == mat.id,
            )
            res_stk = await verify_session.execute(stmt_stk)
            assert res_stk.scalars().first().quantity == Decimal("500.00")

            stmt_mov = select(MaterialStockMovement).where(
                MaterialStockMovement.material_transaction_id == mat_tx.id
            )
            res_mov = await verify_session.execute(stmt_mov)
            assert res_mov.scalars().first() is None


@pytest.mark.asyncio
async def test_reopen_and_reapproval_cycle():
    """Verify admin reopening reverses stock deduction, and subsequent approval re-deducts cleanly."""
    async with TestingSessionLocal() as session:
        env = await setup_test_env(session)
        worker_emp = env["worker_emp"]
        sup_user = env["sup_user"]
        sup_emp = env["sup_emp"]
        admin_user = env["admin_user"]
        site = env["site"]
        act = env["activity"]
        mat = env["material"]
        att = env["attendance"]
        today = env["today"]

        dwe = DailyWorkEntry(
            idempotency_key=str(uuid.uuid4()),
            attendance_record_id=att.id,
            employee_id=worker_emp.id,
            site_id=site.id,
            activity_id=act.id,
            work_date=today,
            quantity=Decimal("120.00"),
            uom="metres",
            status="submitted",
        )
        session.add(dwe)
        await session.flush()

        mat_tx = MaterialTransaction(
            daily_work_entry_id=dwe.id,
            material_id=mat.id,
            site_id=site.id,
            transaction_type="consumed",
            item_name=mat.name,
            quantity=Decimal("120.00"),
            amount=Decimal("0.00"),
            status="submitted",
        )
        session.add(mat_tx)
        await session.commit()

        # 1. Approve
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=f"APP-1-{uuid.uuid4().hex[:12]}",
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )

        stmt_stk = select(MaterialStock).where(
            MaterialStock.site_id == site.id,
            MaterialStock.material_id == mat.id,
        )
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("380.00")

        # 2. Admin reopens for correction
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="correction_required",
            idempotency_key=f"REOPEN-{uuid.uuid4().hex[:12]}",
            supervisor_user_id=admin_user.id,
            remarks="Reopening to verify cable drum serial number",
            is_admin=True,
        )

        # Stock restored back to 500.00
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("500.00")

        # MaterialTransaction is correction_required
        stmt_mat = select(MaterialTransaction).where(MaterialTransaction.id == mat_tx.id)
        res_mat = await session.execute(stmt_mat)
        assert res_mat.scalars().first().status == "correction_required"

        # Worker resubmits
        dwe_obj = (await session.execute(select(DailyWorkEntry).where(DailyWorkEntry.id == dwe.id))).scalars().first()
        dwe_obj.status = "submitted"
        mat_obj = (await session.execute(select(MaterialTransaction).where(MaterialTransaction.id == mat_tx.id))).scalars().first()
        mat_obj.status = "submitted"
        await session.commit()

        # 3. Supervisor re-approves
        await VerificationService.verify_entity(
            session=session,
            entity_type="daily_work",
            entity_id=dwe.id,
            action="approved",
            idempotency_key=f"APP-2-{uuid.uuid4().hex[:12]}",
            supervisor_user_id=sup_user.id,
            supervisor_emp_id=sup_emp.id,
        )

        # Stock deducted back to 380.00 cleanly
        res_stk = await session.execute(stmt_stk)
        assert res_stk.scalars().first().quantity == Decimal("380.00")

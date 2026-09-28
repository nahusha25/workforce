import tempfile
import uuid
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
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
)
from app.models.workforce import Employee
from app.modules.daily_work.material_service import MaterialTransactionService
from app.modules.daily_work.schemas import MaterialTransactionCreate
from app.shared.file_storage import FileNotFoundStorageError, LocalFileStorage
from tests.conftest import TestingSessionLocal

VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"A" * 100)


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalFileStorage(base_dir=tmpdir, base_url="/uploads")


async def setup_material_fixtures(session: AsyncSession):
    suffix = uuid.uuid4().hex[:8]
    today = datetime.now(timezone.utc).date()

    # Users
    user1 = User(id=uuid.uuid4(), mobile_id=f"M-M1-{suffix}", role="employee", is_active=True)
    user2 = User(id=uuid.uuid4(), mobile_id=f"M-M2-{suffix}", role="employee", is_active=True)
    user_sup = User(id=uuid.uuid4(), mobile_id=f"M-MS-{suffix}", role="supervisor", is_active=True)
    user_sup2 = User(id=uuid.uuid4(), mobile_id=f"M-MS2-{suffix}", role="supervisor", is_active=True)
    session.add_all([user1, user2, user_sup, user_sup2])
    await session.commit()

    # Supervisors
    sup = Employee(
        id=uuid.uuid4(),
        user_id=user_sup.id,
        name=f"Sup {suffix}",
        employee_code=f"SUP-{suffix}",
        mobile_id=f"M-MS-{suffix}",
        is_active=True,
    )
    sup2 = Employee(
        id=uuid.uuid4(),
        user_id=user_sup2.id,
        name=f"Other Sup {suffix}",
        employee_code=f"SUP2-{suffix}",
        mobile_id=f"M-MS2-{suffix}",
        is_active=True,
    )
    session.add_all([sup, sup2])
    await session.commit()

    # Employees: emp1 reports to sup; emp2 reports to sup2
    emp1 = Employee(
        id=uuid.uuid4(),
        user_id=user1.id,
        name=f"Worker One {suffix}",
        employee_code=f"W1-{suffix}",
        mobile_id=f"M-M1-{suffix}",
        supervisor_id=sup.id,
        is_active=True,
    )
    emp2 = Employee(
        id=uuid.uuid4(),
        user_id=user2.id,
        name=f"Worker Two {suffix}",
        employee_code=f"W2-{suffix}",
        mobile_id=f"M-M2-{suffix}",
        supervisor_id=sup2.id,
        is_active=True,
    )
    session.add_all([emp1, emp2])
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
        supervisor_id=sup.id,
        location="POINT(77.5946 12.9716)",
        permitted_radius_m=500.0,
    )
    session.add(site)
    await session.commit()

    assign1 = EmployeeSiteAssignment(employee_id=emp1.id, site_id=site.id, is_active=True)
    session.add(assign1)

    activity = Activity(name=f"Act {suffix}", unit_of_measure="m", approved_rate=10.0, category="cable")
    session.add(activity)
    await session.commit()

    # Material Master: limit = 5000.00
    material = Material(
        name=f"Standard Cable {suffix}",
        material_code=f"MAT-{suffix}",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=5000.00,
        is_active=True,
    )
    session.add(material)
    await session.commit()

    att = AttendanceRecord(
        employee_id=emp1.id,
        site_id=site.id,
        date=today,
        session_number=1,
        check_in_time=datetime.now(timezone.utc),
        status="draft",
    )
    session.add(att)
    await session.commit()

    entry = DailyWorkEntry(
        idempotency_key=f"IDEMP-{uuid.uuid4()}",
        attendance_record_id=att.id,
        employee_id=emp1.id,
        site_id=site.id,
        activity_id=activity.id,
        work_date=today,
        quantity=1.0,
        uom=activity.unit_of_measure,
        status="draft",
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return {
        "emp1": emp1,
        "emp2": emp2,
        "sup": sup,
        "sup2": sup2,
        "site": site,
        "entry": entry,
        "material": material,
        "today": today,
    }


# ==============================================================================
# 1. IS_HIGH_VALUE COMPUTATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_is_high_value_above_threshold():
    """amount > purchase_approval_limit produces is_high_value = True."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        material = data["material"]  # limit = 5000.00

        is_high, mat = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=5000.01,
            material_id=material.id,
        )
        assert is_high is True
        assert mat.id == material.id


@pytest.mark.asyncio
async def test_is_high_value_at_threshold():
    """amount == purchase_approval_limit produces is_high_value = False (not strictly greater)."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        material = data["material"]  # limit = 5000.00

        is_high, _ = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=5000.00,
            material_id=material.id,
        )
        assert is_high is False


@pytest.mark.asyncio
async def test_is_high_value_below_threshold():
    """amount < purchase_approval_limit produces is_high_value = False."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        material = data["material"]  # limit = 5000.00

        is_high, _ = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=4999.99,
            material_id=material.id,
        )
        assert is_high is False


@pytest.mark.asyncio
async def test_is_high_value_no_matching_material_purchased():
    """Uncataloged purchase (item_name not in master data) with amount > 0 defaults to is_high_value = True."""
    async with TestingSessionLocal() as session:
        is_high, mat = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=150.00,
            material_id=None,
            item_name="Nonexistent Custom Drill Bit",
        )
        assert is_high is True
        assert mat is None


@pytest.mark.asyncio
async def test_is_high_value_no_matching_material_zero_amount():
    """Uncataloged purchase with amount = 0 produces is_high_value = False."""
    async with TestingSessionLocal() as session:
        is_high, _ = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=0.0,
            material_id=None,
            item_name="Free Sample Screws",
        )
        assert is_high is False


@pytest.mark.asyncio
async def test_is_high_value_no_matching_material_consumed():
    """Consumed material not in master data produces is_high_value = False."""
    async with TestingSessionLocal() as session:
        is_high, _ = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="consumed",
            amount=0.0,
            material_id=None,
            item_name="Generic Tape",
        )
        assert is_high is False


@pytest.mark.asyncio
async def test_is_high_value_by_item_name_match():
    """Matches master data by item_name when material_id is omitted."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        material = data["material"]

        # amount > limit
        is_high, mat = await MaterialTransactionService.compute_high_value(
            session=session,
            transaction_type="purchased",
            amount=6000.0,
            item_name=material.name.lower(),  # Case-insensitive
        )
        assert is_high is True
        assert mat.id == material.id


@pytest.mark.asyncio
async def test_is_high_value_invalid_material_id():
    """Providing a nonexistent material_id raises 404."""
    async with TestingSessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            await MaterialTransactionService.compute_high_value(
                session=session,
                transaction_type="purchased",
                amount=100.0,
                material_id=uuid.uuid4(),
            )
        assert exc_info.value.status_code == 404


# ==============================================================================
# 2. CREATE TRANSACTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_consumed_transaction_success():
    """Successfully records consumed material transaction without bill."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]
        material = data["material"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data=MaterialTransactionCreate(
                transaction_type="consumed",
                item_name=material.name,
                quantity=50.0,
                amount=0.0,
                material_id=material.id,
            ),
            employee_id=emp1.id,
        )

        assert tx.id is not None
        assert tx.daily_work_entry_id == entry.id
        assert tx.site_id == entry.site_id
        assert tx.transaction_type == "consumed"
        assert tx.item_name == material.name
        assert float(tx.quantity) == 50.0
        assert float(tx.amount) == 0.0
        assert tx.is_high_value is False
        assert tx.bill_image_url is None
        assert tx.status == "draft"


@pytest.mark.asyncio
async def test_create_purchased_transaction_with_bill_upload(temp_storage):
    """Successfully records purchased material transaction with bill photo upload."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]
        material = data["material"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={
                "transaction_type": "purchased",
                "item_name": material.name,
                "quantity": 10.0,
                "amount": 7500.0,  # > limit (5000)
                "material_id": str(material.id),
            },
            bill_file=VALID_JPEG_BYTES,
            bill_filename="receipt.jpg",
            employee_id=emp1.id,
            storage=temp_storage,
        )

        assert tx.id is not None
        assert tx.transaction_type == "purchased"
        assert float(tx.amount) == 7500.0
        assert tx.is_high_value is True
        assert tx.bill_image_url is not None
        assert tx.bill_image_url.startswith("/uploads/materials/")

        # Verify file exists on disk
        clean_path = tx.bill_image_url.replace("/uploads/", "")
        assert await temp_storage.file_exists(clean_path)


@pytest.mark.asyncio
async def test_create_transaction_correction_required():
    """Allows recording transaction when entry status is 'correction_required'."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        entry.status = "correction_required"
        await session.commit()

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={
                "transaction_type": "consumed",
                "item_name": "Screws",
                "quantity": 25.0,
            },
            employee_id=emp1.id,
        )
        assert tx.id is not None


@pytest.mark.asyncio
async def test_create_transaction_rejects_disallowed_statuses():
    """Rejects recording transactions when entry is in submitted, approved, or rejected status."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        for blocked_status in ["submitted", "approved", "rejected"]:
            entry.status = blocked_status
            await session.commit()

            with pytest.raises(HTTPException) as exc_info:
                await MaterialTransactionService.create_material_transaction(
                    session=session,
                    daily_work_entry_id=entry.id,
                    data={"transaction_type": "consumed", "item_name": "Nails", "quantity": 10},
                    employee_id=emp1.id,
                )
            assert exc_info.value.status_code == 400
            assert blocked_status in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_transaction_rejects_unauthorized_employee():
    """Employee B cannot record transactions on Employee A's work entry."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp2 = data["emp2"]
        entry = data["entry"]

        with pytest.raises(HTTPException) as exc_info:
            await MaterialTransactionService.create_material_transaction(
                session=session,
                daily_work_entry_id=entry.id,
                data={"transaction_type": "consumed", "item_name": "Nails", "quantity": 10},
                employee_id=emp2.id,
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_transaction_validations():
    """Validates transaction_type, quantity > 0, amount >= 0, item_name not empty."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        # Invalid type
        with pytest.raises(HTTPException) as exc1:
            await MaterialTransactionService.create_material_transaction(
                session=session,
                daily_work_entry_id=entry.id,
                data={"transaction_type": "borrowed", "item_name": "Tool", "quantity": 1},
                employee_id=emp1.id,
            )
        assert exc1.value.status_code == 400

        # Zero quantity
        with pytest.raises(HTTPException) as exc2:
            await MaterialTransactionService.create_material_transaction(
                session=session,
                daily_work_entry_id=entry.id,
                data={"transaction_type": "consumed", "item_name": "Tool", "quantity": 0},
                employee_id=emp1.id,
            )
        assert exc2.value.status_code == 400

        # Negative amount
        with pytest.raises(HTTPException) as exc3:
            await MaterialTransactionService.create_material_transaction(
                session=session,
                daily_work_entry_id=entry.id,
                data={"transaction_type": "purchased", "item_name": "Tool", "quantity": 1, "amount": -10},
                employee_id=emp1.id,
            )
        assert exc3.value.status_code == 400

        # Empty item_name
        with pytest.raises(HTTPException) as exc4:
            await MaterialTransactionService.create_material_transaction(
                session=session,
                daily_work_entry_id=entry.id,
                data={"transaction_type": "consumed", "item_name": "   ", "quantity": 1},
                employee_id=emp1.id,
            )
        assert exc4.value.status_code == 400


# ==============================================================================
# 3. LIST TRANSACTIONS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_list_material_transactions_self_and_supervisor():
    """Employee and direct supervisor can list transactions of the entry."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        sup = data["sup"]
        entry = data["entry"]

        tx1 = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "consumed", "item_name": "Item A", "quantity": 5},
            employee_id=emp1.id,
        )
        tx2 = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "purchased", "item_name": "Item B", "quantity": 2, "amount": 50},
            employee_id=emp1.id,
        )

        # 1. Employee lists
        items_emp = await MaterialTransactionService.list_material_transactions(
            session=session,
            daily_work_entry_id=entry.id,
            user_role="employee",
            employee_id=emp1.id,
        )
        assert len(items_emp) == 2
        tx_ids = [t.id for t in items_emp]
        assert tx1.id in tx_ids
        assert tx2.id in tx_ids

        # 2. Supervisor lists
        items_sup = await MaterialTransactionService.list_material_transactions(
            session=session,
            daily_work_entry_id=entry.id,
            user_role="supervisor",
            employee_id=sup.id,
        )
        assert len(items_sup) == 2


@pytest.mark.asyncio
async def test_list_material_transactions_rejects_unauthorized():
    """Other employee or unrelated supervisor cannot list transactions."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp2 = data["emp2"]
        sup2 = data["sup2"]
        entry = data["entry"]

        with pytest.raises(HTTPException) as exc1:
            await MaterialTransactionService.list_material_transactions(
                session=session,
                daily_work_entry_id=entry.id,
                user_role="employee",
                employee_id=emp2.id,
            )
        assert exc1.value.status_code == 403

        with pytest.raises(HTTPException) as exc2:
            await MaterialTransactionService.list_material_transactions(
                session=session,
                daily_work_entry_id=entry.id,
                user_role="supervisor",
                employee_id=sup2.id,
            )
        assert exc2.value.status_code == 403


# ==============================================================================
# 4. DELETE TRANSACTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_delete_material_transaction_success(temp_storage):
    """Owner employee can delete transaction while entry is draft; cleans up stored bill image."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "purchased", "item_name": "Drill", "quantity": 1, "amount": 100},
            bill_file=VALID_JPEG_BYTES,
            employee_id=emp1.id,
            storage=temp_storage,
        )

        clean_path = tx.bill_image_url.replace("/uploads/", "")
        assert await temp_storage.file_exists(clean_path)

        deleted = await MaterialTransactionService.delete_material_transaction(
            session=session,
            transaction_id=tx.id,
            employee_id=emp1.id,
            storage=temp_storage,
        )
        assert deleted is True

        # DB row deleted
        with pytest.raises(HTTPException) as exc_info:
            await MaterialTransactionService.get_material_transaction(session, tx.id)
        assert exc_info.value.status_code == 404

        # Stored bill image deleted from disk
        assert not await temp_storage.file_exists(clean_path)


@pytest.mark.asyncio
async def test_delete_material_transaction_rejects_when_entry_submitted():
    """Cannot delete transaction if entry has been submitted, approved, or rejected."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "consumed", "item_name": "Conduit", "quantity": 10},
            employee_id=emp1.id,
        )

        entry.status = "submitted"
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await MaterialTransactionService.delete_material_transaction(
                session=session,
                transaction_id=tx.id,
                employee_id=emp1.id,
            )
        assert exc_info.value.status_code == 400
        assert "submitted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_material_transaction_rejects_unauthorized_employee():
    """Employee B cannot delete material transaction recorded on Employee A's entry."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        emp2 = data["emp2"]
        entry = data["entry"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "consumed", "item_name": "Conduit", "quantity": 10},
            employee_id=emp1.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await MaterialTransactionService.delete_material_transaction(
                session=session,
                transaction_id=tx.id,
                employee_id=emp2.id,
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_transaction_admin_access():
    """Admin can delete a material transaction while entry is still in draft."""
    async with TestingSessionLocal() as session:
        data = await setup_material_fixtures(session)
        emp1 = data["emp1"]
        entry = data["entry"]

        tx = await MaterialTransactionService.create_material_transaction(
            session=session,
            daily_work_entry_id=entry.id,
            data={"transaction_type": "consumed", "item_name": "Glue", "quantity": 2},
            employee_id=emp1.id,
        )

        deleted = await MaterialTransactionService.delete_material_transaction(
            session=session,
            transaction_id=tx.id,
            is_admin=True,
        )
        assert deleted is True

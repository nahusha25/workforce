import uuid
from datetime import date, datetime
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    Material,
    MaterialTransaction,
    Project,
    Site,
    WorkOrder,
)
from app.models.workforce import Employee


def create_dependencies(sync_db_session: Session):
    unique_suffix = str(uuid.uuid4())[:8]

    user = User(mobile_id=f"M-{unique_suffix}", role="employee", is_active=True)
    sync_db_session.add(user)
    sync_db_session.flush()

    client = Client(name=f"Client-{unique_suffix}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.flush()

    project = Project(client_id=client.id, name=f"Project-{unique_suffix}", status="active")
    sync_db_session.add(project)
    sync_db_session.flush()

    emp = Employee(
        user_id=user.id,
        employee_code=f"E-{unique_suffix}",
        mobile_id=f"M-{unique_suffix}",
        name="John Doe",
        is_active=True,
    )
    site = Site(project_id=project.id, name=f"Site-{unique_suffix}")
    activity = Activity(
        name=f"Activity-{unique_suffix}",
        unit_of_measure="metre",
        approved_rate=15.00,
        category="cable",
    )
    material = Material(
        material_code=f"MAT-{unique_suffix}",
        name="Cat6 Ethernet Cable",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=1000.00,
    )
    sync_db_session.add_all([emp, site, activity, material])
    sync_db_session.flush()

    work_order = WorkOrder(
        order_number=f"WO-MT-{unique_suffix}",
        project_id=project.id,
        site_id=site.id,
        status="open",
        is_active=True,
    )
    attendance = AttendanceRecord(
        employee_id=emp.id, site_id=site.id, date=date.today(), status="present"
    )
    sync_db_session.add_all([work_order, attendance])
    sync_db_session.flush()

    dwe = DailyWorkEntry(
        idempotency_key=str(uuid.uuid4()),
        attendance_record_id=attendance.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=activity.id,
        work_order_id=work_order.id,
        work_date=date.today(),
        quantity=50.0,
        uom=activity.unit_of_measure,
        status="draft",
    )
    sync_db_session.add(dwe)
    sync_db_session.flush()

    return dwe, site, material


def test_valid_material_transaction_consumed(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Cat6 Ethernet Cable",
        quantity=50.00,
        amount=0.00,
        bill_image_url=None,
        is_high_value=False,
        status="draft",
    )
    sync_db_session.add(tx)
    sync_db_session.commit()

    assert tx.id is not None
    assert isinstance(tx.id, uuid.UUID)
    assert tx.daily_work_entry_id == dwe.id
    assert tx.material_id == material.id
    assert tx.site_id == site.id
    assert tx.transaction_type == "consumed"
    assert tx.item_name == "Cat6 Ethernet Cable"
    assert float(tx.quantity) == 50.00
    assert float(tx.amount) == 0.00
    assert tx.bill_image_url is None
    assert tx.is_high_value is False
    assert tx.status == "draft"
    assert isinstance(tx.created_at, datetime)
    assert isinstance(tx.updated_at, datetime)


def test_valid_material_transaction_purchased(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Conduit Pipes",
        quantity=10.00,
        amount=2500.50,
        bill_image_url="https://example.com/bills/invoice_001.jpg",
        is_high_value=True,
        status="submitted",
    )
    sync_db_session.add(tx)
    sync_db_session.commit()

    assert tx.id is not None
    assert tx.transaction_type == "purchased"
    assert float(tx.amount) == 2500.50
    assert tx.bill_image_url == "https://example.com/bills/invoice_001.jpg"
    assert tx.is_high_value is True
    assert tx.status == "submitted"


def test_nullable_material_id(sync_db_session: Session):
    dwe, site, _ = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=None,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Ad-hoc screws and bolts",
        quantity=100.00,
        amount=150.00,
        status="draft",
    )
    sync_db_session.add(tx)
    sync_db_session.commit()

    assert tx.material_id is None
    assert tx.item_name == "Ad-hoc screws and bolts"


@pytest.mark.parametrize("tx_type", ["consumed", "purchased"])
def test_valid_transaction_types(sync_db_session: Session, tx_type: str):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type=tx_type,
        item_name="Test Item",
        quantity=5.00,
        amount=10.00,
        status="draft",
    )
    sync_db_session.add(tx)
    sync_db_session.commit()
    assert tx.transaction_type == tx_type


def test_invalid_transaction_type_rejected(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="transferred",
        item_name="Test Item",
        quantity=5.00,
        amount=10.00,
        status="draft",
    )
    sync_db_session.add(tx)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


def test_quantity_zero_rejected(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Zero Qty Item",
        quantity=0.00,
        amount=0.00,
        status="draft",
    )
    sync_db_session.add(tx)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


def test_quantity_negative_rejected(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Negative Qty Item",
        quantity=-5.00,
        amount=0.00,
        status="draft",
    )
    sync_db_session.add(tx)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


def test_amount_negative_rejected(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="purchased",
        item_name="Negative Cost Item",
        quantity=1.00,
        amount=-50.00,
        status="draft",
    )
    sync_db_session.add(tx)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


@pytest.mark.parametrize("status", ["draft", "submitted", "approved", "rejected", "correction_required"])
def test_valid_statuses(sync_db_session: Session, status: str):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Status Check Item",
        quantity=1.00,
        amount=0.00,
        status=status,
    )
    sync_db_session.add(tx)
    sync_db_session.commit()
    assert tx.status == status


def test_invalid_status_rejected(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)

    tx = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Invalid Status Item",
        quantity=1.00,
        amount=0.00,
        status="archived",
    )
    sync_db_session.add(tx)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


def test_foreign_key_constraints(sync_db_session: Session):
    dwe, site, material = create_dependencies(sync_db_session)
    fake_id = uuid.uuid4()

    # Invalid daily_work_entry_id
    tx_invalid_dwe = MaterialTransaction(
        daily_work_entry_id=fake_id,
        material_id=material.id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Invalid DWE",
        quantity=1.0,
        amount=0.0,
    )
    sync_db_session.add(tx_invalid_dwe)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Invalid site_id
    tx_invalid_site = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=material.id,
        site_id=fake_id,
        transaction_type="consumed",
        item_name="Invalid Site",
        quantity=1.0,
        amount=0.0,
    )
    sync_db_session.add(tx_invalid_site)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

    # Invalid material_id
    tx_invalid_mat = MaterialTransaction(
        daily_work_entry_id=dwe.id,
        material_id=fake_id,
        site_id=site.id,
        transaction_type="consumed",
        item_name="Invalid Material",
        quantity=1.0,
        amount=0.0,
    )
    sync_db_session.add(tx_invalid_mat)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

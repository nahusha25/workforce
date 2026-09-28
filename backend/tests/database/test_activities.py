import uuid
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.operations import Activity

def test_valid_activity(sync_db_session: Session):
    activity = Activity(
        name="Cable Laying",
        unit_of_measure="metre",
        approved_rate=125.50,
        category="cable"
    )
    sync_db_session.add(activity)
    sync_db_session.commit()
    
    assert activity.id is not None
    assert isinstance(activity.id, uuid.UUID)
    assert activity.name == "Cable Laying"
    assert activity.unit_of_measure == "metre"
    assert float(activity.approved_rate) == 125.50
    assert activity.category == "cable"
    assert activity.is_active is True
    assert isinstance(activity.created_at, datetime)
    assert isinstance(activity.updated_at, datetime)

def test_approved_rate_zero(sync_db_session: Session):
    activity = Activity(
        name="Free Work",
        unit_of_measure="hour",
        approved_rate=0.00,
        category="testing"
    )
    sync_db_session.add(activity)
    sync_db_session.commit()
    assert float(activity.approved_rate) == 0.00

def test_approved_rate_negative(sync_db_session: Session):
    activity = Activity(
        name="Negative Rate",
        unit_of_measure="unit",
        approved_rate=-10.00,
        category="device"
    )
    sync_db_session.add(activity)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_approved_rate_precision(sync_db_session: Session):
    activity = Activity(
        name="Precision Check",
        unit_of_measure="unit",
        approved_rate=12.345, # PostgreSQL NUMERIC(12,2) will round this
        category="device"
    )
    sync_db_session.add(activity)
    sync_db_session.commit()
    
    # Reload from DB to verify precision
    sync_db_session.refresh(activity)
    # 12.345 rounds to 12.35
    assert float(activity.approved_rate) == 12.35

@pytest.mark.parametrize("category", [
    "cable",
    "device",
    "drilling",
    "mounting",
    "testing",
    "commissioning"
])
def test_valid_categories(sync_db_session: Session, category: str):
    activity = Activity(
        name=f"{category} Activity",
        unit_of_measure="unit",
        approved_rate=10.00,
        category=category
    )
    sync_db_session.add(activity)
    sync_db_session.commit()
    assert activity.category == category

def test_invalid_category(sync_db_session: Session):
    activity = Activity(
        name="Invalid Category",
        unit_of_measure="unit",
        approved_rate=10.00,
        category="invalid_category"
    )
    sync_db_session.add(activity)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

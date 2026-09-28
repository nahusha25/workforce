import uuid
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.operations import Material

def test_valid_material(sync_db_session: Session):
    material = Material(
        material_code="CAB-001",
        name="Fiber Optic Cable",
        description="High speed fiber",
        unit_of_measure="metre",
        category="cable",
        purchase_approval_limit=5000.00
    )
    sync_db_session.add(material)
    sync_db_session.commit()
    
    assert material.id is not None
    assert isinstance(material.id, uuid.UUID)
    assert material.material_code == "CAB-001"
    assert material.name == "Fiber Optic Cable"
    assert material.description == "High speed fiber"
    assert material.unit_of_measure == "metre"
    assert material.category == "cable"
    assert float(material.purchase_approval_limit) == 5000.00
    assert material.is_active is True
    assert isinstance(material.created_at, datetime)
    assert isinstance(material.updated_at, datetime)

def test_material_nullable_code_description(sync_db_session: Session):
    material = Material(
        name="Simple Material",
        unit_of_measure="each",
        category="device",
        purchase_approval_limit=100.00
    )
    sync_db_session.add(material)
    sync_db_session.commit()
    assert material.material_code is None
    assert material.description is None

def test_no_name_unique_constraint(sync_db_session: Session):
    # Testing that two materials can have the same name without breaking unique constraints.
    m1 = Material(name="Duplicate", unit_of_measure="m", category="tool", purchase_approval_limit=0)
    m2 = Material(name="Duplicate", unit_of_measure="m", category="tool", purchase_approval_limit=0)
    sync_db_session.add_all([m1, m2])
    sync_db_session.commit()
    assert m1.id != m2.id
    assert m1.name == m2.name

def test_purchase_approval_limit_zero(sync_db_session: Session):
    material = Material(
        name="Zero Limit",
        unit_of_measure="unit",
        category="consumable",
        purchase_approval_limit=0.00
    )
    sync_db_session.add(material)
    sync_db_session.commit()
    assert float(material.purchase_approval_limit) == 0.00

def test_purchase_approval_limit_negative(sync_db_session: Session):
    material = Material(
        name="Negative Limit",
        unit_of_measure="unit",
        category="tool",
        purchase_approval_limit=-10.00
    )
    sync_db_session.add(material)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_purchase_approval_limit_precision(sync_db_session: Session):
    material = Material(
        name="Precision Limit",
        unit_of_measure="unit",
        category="device",
        purchase_approval_limit=12.345 # Should round to 12.35 based on NUMERIC(12,2)
    )
    sync_db_session.add(material)
    sync_db_session.commit()
    
    sync_db_session.refresh(material)
    assert float(material.purchase_approval_limit) == 12.35

@pytest.mark.parametrize("category", [
    "cable",
    "device",
    "tool",
    "consumable"
])
def test_valid_categories(sync_db_session: Session, category: str):
    material = Material(
        name=f"{category} material",
        unit_of_measure="unit",
        category=category,
        purchase_approval_limit=10.00
    )
    sync_db_session.add(material)
    sync_db_session.commit()
    assert material.category == category

def test_invalid_category(sync_db_session: Session):
    material = Material(
        name="Invalid Category",
        unit_of_measure="unit",
        category="invalid_category",
        purchase_approval_limit=10.00
    )
    sync_db_session.add(material)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

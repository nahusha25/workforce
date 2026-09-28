import uuid
from datetime import date, datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.operations import Client, Project, Site, WorkOrder

def create_base_data(sync_db_session: Session):
    client = Client(name="Test Client")
    sync_db_session.add(client)
    sync_db_session.flush()

    project = Project(client_id=client.id, name="Test Project", status="open")
    sync_db_session.add(project)
    sync_db_session.flush()

    site = Site(project_id=project.id, name="Test Site")
    sync_db_session.add(site)
    sync_db_session.flush()

    return project, site

def test_valid_work_order(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(
        order_number="WO-001",
        project_id=project.id,
        site_id=site.id,
        description="Test description",
        target_quantities={"cable_length_metres": 100},
        start_date=date.today(),
        end_date=date.today() + timedelta(days=5),
        billing_basis="per_metre",
        status="draft"
    )
    sync_db_session.add(wo)
    sync_db_session.commit()
    
    assert wo.id is not None
    assert wo.is_active is True
    assert wo.created_at is not None
    assert wo.updated_at is not None
    assert wo.target_quantities == {"cable_length_metres": 100}

def test_duplicate_order_number(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo1 = WorkOrder(order_number="WO-DUP", project_id=project.id, site_id=site.id, status="draft")
    sync_db_session.add(wo1)
    sync_db_session.commit()
    
    wo2 = WorkOrder(order_number="WO-DUP", project_id=project.id, site_id=site.id, status="draft")
    sync_db_session.add(wo2)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_invalid_status(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(order_number="WO-STAT", project_id=project.id, site_id=site.id, status="invalid_status")
    sync_db_session.add(wo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_invalid_billing_basis(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(order_number="WO-BILL", project_id=project.id, site_id=site.id, status="draft", billing_basis="hourly")
    sync_db_session.add(wo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_end_date_before_start_date(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(
        order_number="WO-DATE1",
        project_id=project.id,
        site_id=site.id,
        status="draft",
        start_date=date.today(),
        end_date=date.today() - timedelta(days=1)
    )
    sync_db_session.add(wo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_end_date_equals_start_date(sync_db_session: Session):
    project, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(
        order_number="WO-DATE2",
        project_id=project.id,
        site_id=site.id,
        status="draft",
        start_date=date.today(),
        end_date=date.today()
    )
    sync_db_session.add(wo)
    sync_db_session.commit()
    assert wo.id is not None

def test_invalid_project_id(sync_db_session: Session):
    _, site = create_base_data(sync_db_session)
    
    wo = WorkOrder(order_number="WO-PROJ", project_id=uuid.uuid4(), site_id=site.id, status="draft")
    sync_db_session.add(wo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

def test_invalid_site_id(sync_db_session: Session):
    project, _ = create_base_data(sync_db_session)
    
    wo = WorkOrder(order_number="WO-SITE", project_id=project.id, site_id=uuid.uuid4(), status="draft")
    sync_db_session.add(wo)
    
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()

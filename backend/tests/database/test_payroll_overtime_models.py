from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.employee_payments import EmployeePayment, EmployeePaymentLine
from app.models.operations import AttendanceRecord, DailyWorkEntry, Project, Site, Client, Activity
from app.models.payroll_settings import PayrollOvertimeSettings
from app.models.workforce import Employee, EmployeeRateHistory


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# 1. PayrollOvertimeSettings: Model Defaults & Custom Values
# ---------------------------------------------------------------------------

def test_payroll_overtime_settings_defaults(sync_db_session: Session):
    setting = PayrollOvertimeSettings(
        id=_uuid(),
        effective_from=date(2026, 1, 1),
    )
    sync_db_session.add(setting)
    sync_db_session.commit()
    sync_db_session.refresh(setting)

    assert setting.standard_workday_hours == Decimal("7.00")
    assert setting.overtime_multiplier == Decimal("1.50")
    assert setting.effective_from == date(2026, 1, 1)
    assert setting.effective_to is None
    assert setting.description is None
    assert setting.created_at is not None


def test_payroll_overtime_settings_custom_values_and_creator(sync_db_session: Session):
    admin_user = User(id=_uuid(), mobile_id=f"+9198{str(_uuid())[:8]}", role="administrator")
    sync_db_session.add(admin_user)
    sync_db_session.commit()

    setting = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=Decimal("8.00"),
        overtime_multiplier=Decimal("2.00"),
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 12, 31),
        description="Q4 Festive Season overtime policy",
        created_by=admin_user.id,
    )
    sync_db_session.add(setting)
    sync_db_session.commit()
    sync_db_session.refresh(setting)

    assert setting.standard_workday_hours == Decimal("8.00")
    assert setting.overtime_multiplier == Decimal("2.00")
    assert setting.effective_from == date(2026, 10, 1)
    assert setting.effective_to == date(2026, 12, 31)
    assert setting.description == "Q4 Festive Season overtime policy"
    assert setting.created_by == admin_user.id


# ---------------------------------------------------------------------------
# 2. PayrollOvertimeSettings: Database Constraints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_hours", [Decimal("0.00"), Decimal("-1.00"), Decimal("25.00")])
def test_payroll_overtime_settings_invalid_standard_hours_constraint(sync_db_session: Session, invalid_hours: Decimal):
    setting = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=invalid_hours,
        overtime_multiplier=Decimal("1.50"),
        effective_from=date(2026, 1, 1),
    )
    sync_db_session.add(setting)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


@pytest.mark.parametrize("invalid_multiplier", [Decimal("0.50"), Decimal("0.99"), Decimal("5.01"), Decimal("6.00")])
def test_payroll_overtime_settings_invalid_multiplier_constraint(sync_db_session: Session, invalid_multiplier: Decimal):
    setting = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=Decimal("7.00"),
        overtime_multiplier=invalid_multiplier,
        effective_from=date(2026, 1, 1),
    )
    sync_db_session.add(setting)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


def test_payroll_overtime_settings_invalid_effective_dates_constraint(sync_db_session: Session):
    # effective_to is strictly earlier than effective_from
    setting = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=Decimal("7.00"),
        overtime_multiplier=Decimal("1.50"),
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 9, 30),
    )
    sync_db_session.add(setting)
    with pytest.raises(IntegrityError):
        sync_db_session.commit()
    sync_db_session.rollback()


# ---------------------------------------------------------------------------
# 3. PayrollOvertimeSettings: Date-Effective Revisions
# ---------------------------------------------------------------------------

def test_payroll_overtime_settings_effective_date_lookup(sync_db_session: Session):
    sfx = str(_uuid())[:8]
    # Revision 1: 2026-01-01 to 2026-09-30 (8.00h, 1.50x)
    s1 = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=Decimal("8.00"),
        overtime_multiplier=Decimal("1.50"),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 9, 30),
        description=f"Policy Phase 1 {sfx}",
    )
    # Revision 2: 2026-10-01 onwards (7.00h, 1.75x)
    s2 = PayrollOvertimeSettings(
        id=_uuid(),
        standard_workday_hours=Decimal("7.00"),
        overtime_multiplier=Decimal("1.75"),
        effective_from=date(2026, 10, 1),
        effective_to=None,
        description=f"Policy Phase 2 {sfx}",
    )
    sync_db_session.add_all([s1, s2])
    sync_db_session.commit()

    def find_active_setting(d: date) -> PayrollOvertimeSettings | None:
        stmt = (
            select(PayrollOvertimeSettings)
            .where(
                PayrollOvertimeSettings.effective_from <= d,
                (PayrollOvertimeSettings.effective_to.is_(None)) | (PayrollOvertimeSettings.effective_to >= d),
                PayrollOvertimeSettings.description.like(f"%{sfx}%"),
            )
            .order_by(PayrollOvertimeSettings.effective_from.desc())
        )
        return sync_db_session.execute(stmt).scalars().first()

    # Query in August 2026 -> returns s1
    res_august = find_active_setting(date(2026, 8, 15))
    assert res_august is not None
    assert res_august.id == s1.id
    assert res_august.standard_workday_hours == Decimal("8.00")
    assert res_august.overtime_multiplier == Decimal("1.50")

    # Query in October 2026 -> returns s2
    res_october = find_active_setting(date(2026, 10, 15))
    assert res_october is not None
    assert res_october.id == s2.id
    assert res_october.standard_workday_hours == Decimal("7.00")
    assert res_october.overtime_multiplier == Decimal("1.75")


# ---------------------------------------------------------------------------
# 4. EmployeePayment & Line: Overtime Snapshot Fields & Defaults
# ---------------------------------------------------------------------------

def test_employee_payment_overtime_snapshot_defaults_and_fields(sync_db_session: Session):
    sfx = str(_uuid())[:8]
    u = User(id=_uuid(), mobile_id=f"+9197{sfx[:6]}1", role="employee")
    sync_db_session.add(u)
    sync_db_session.commit()

    emp = Employee(id=_uuid(), user_id=u.id, employee_code=f"EMP-{sfx}", mobile_id=u.mobile_id, name="Test Worker")
    sync_db_session.add(emp)
    sync_db_session.commit()

    # 1. Test defaults when omitted
    pay1 = EmployeePayment(
        id=_uuid(),
        payment_number=f"PAY-{sfx}-0001",
        idempotency_key=f"idemp-{sfx}-0001",
        employee_id=emp.id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 7),
        status="draft",
        total_amount=Decimal("500.00"),
        total_days=Decimal("1.00"),
        total_quantity=Decimal("0.00"),
    )
    sync_db_session.add(pay1)
    sync_db_session.commit()
    sync_db_session.refresh(pay1)

    assert pay1.total_regular_amount == Decimal("0.00")
    assert pay1.total_overtime_hours == Decimal("0.00")
    assert pay1.total_overtime_amount == Decimal("0.00")

    # 2. Test explicit snapshot values
    pay2 = EmployeePayment(
        id=_uuid(),
        payment_number=f"PAY-{sfx}-0002",
        idempotency_key=f"idemp-{sfx}-0002",
        employee_id=emp.id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 7),
        status="draft",
        total_amount=Decimal("660.72"),
        total_regular_amount=Decimal("500.00"),
        total_overtime_hours=Decimal("1.50"),
        total_overtime_amount=Decimal("160.72"),
        total_days=Decimal("1.00"),
        total_quantity=Decimal("0.00"),
    )
    sync_db_session.add(pay2)
    sync_db_session.commit()
    sync_db_session.refresh(pay2)

    assert pay2.total_amount == Decimal("660.72")
    assert pay2.total_regular_amount == Decimal("500.00")
    assert pay2.total_overtime_hours == Decimal("1.50")
    assert pay2.total_overtime_amount == Decimal("160.72")


def test_employee_payment_line_overtime_snapshot_fields(sync_db_session: Session):
    sfx = str(_uuid())[:8]
    u = User(id=_uuid(), mobile_id=f"+9196{sfx[:6]}1", role="employee")
    client = Client(id=_uuid(), name=f"Client_{sfx}")
    sync_db_session.add_all([u, client])
    sync_db_session.commit()

    proj = Project(id=_uuid(), client_id=client.id, name=f"Proj_{sfx}", status="in_progress")
    sync_db_session.add(proj)
    sync_db_session.commit()

    site = Site(id=_uuid(), project_id=proj.id, name=f"Site_{sfx}")
    emp = Employee(id=_uuid(), user_id=u.id, employee_code=f"EMP-LN-{sfx}", mobile_id=u.mobile_id, name="Line Worker")
    rate_h = EmployeeRateHistory(
        id=_uuid(),
        employee_id=emp.id,
        rate_type="daily",
        rate_amount=Decimal("500.00"),
        effective_from=date(2026, 10, 1),
        effective_to=None,
        changed_by=emp.id,
    )
    sync_db_session.add_all([site, emp, rate_h])
    sync_db_session.commit()

    att = AttendanceRecord(id=_uuid(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 1), status="approved")
    sync_db_session.add(att)
    sync_db_session.commit()

    pay = EmployeePayment(
        id=_uuid(),
        payment_number=f"PAY-LN-{sfx}",
        idempotency_key=f"idemp-ln-{sfx}",
        employee_id=emp.id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 7),
        status="draft",
        total_amount=Decimal("660.72"),
        total_regular_amount=Decimal("500.00"),
        total_overtime_hours=Decimal("1.50"),
        total_overtime_amount=Decimal("160.72"),
        total_days=Decimal("1.00"),
        total_quantity=Decimal("0.00"),
    )
    sync_db_session.add(pay)
    sync_db_session.commit()

    # Create line with full overtime snapshot metadata
    line = EmployeePaymentLine(
        id=_uuid(),
        payment_id=pay.id,
        source_attendance_id=att.id,
        source_daily_work_entry_id=None,
        source_date=date(2026, 10, 1),
        rate_type="daily",
        rate_amount=Decimal("500.00"),
        rate_effective_from=date(2026, 10, 1),
        rate_effective_to=None,
        days=Decimal("1.00"),
        quantity=Decimal("0.00"),
        regular_hours=Decimal("7.00"),
        overtime_hours=Decimal("1.50"),
        standard_day_hours=Decimal("7.00"),
        hourly_equivalent_rate=Decimal("71.43"),
        overtime_multiplier=Decimal("1.50"),
        regular_amount=Decimal("500.00"),
        overtime_amount=Decimal("160.72"),
        amount=Decimal("660.72"),
        is_active=True,
    )
    sync_db_session.add(line)
    sync_db_session.commit()
    sync_db_session.refresh(line)

    assert line.regular_hours == Decimal("7.00")
    assert line.overtime_hours == Decimal("1.50")
    assert line.standard_day_hours == Decimal("7.00")
    assert line.hourly_equivalent_rate == Decimal("71.43")
    assert line.overtime_multiplier == Decimal("1.50")
    assert line.regular_amount == Decimal("500.00")
    assert line.overtime_amount == Decimal("160.72")
    assert line.amount == Decimal("660.72")


def test_employee_payment_line_legacy_and_piece_rate_nullable_compatibility(sync_db_session: Session):
    sfx = str(_uuid())[:8]
    u = User(id=_uuid(), mobile_id=f"+9195{sfx[:6]}1", role="employee")
    client = Client(id=_uuid(), name=f"Client_P_{sfx}")
    sync_db_session.add_all([u, client])
    sync_db_session.commit()

    proj = Project(id=_uuid(), client_id=client.id, name=f"Proj_P_{sfx}", status="in_progress")
    sync_db_session.add(proj)
    sync_db_session.commit()

    site = Site(id=_uuid(), project_id=proj.id, name=f"Site_P_{sfx}")
    emp = Employee(id=_uuid(), user_id=u.id, employee_code=f"EMP-P-{sfx}", mobile_id=u.mobile_id, name="Piece Worker")
    act = Activity(id=_uuid(), name=f"Activity_{sfx}", unit_of_measure="metres", approved_rate=Decimal("20.00"), category="cable")
    rate_h = EmployeeRateHistory(
        id=_uuid(),
        employee_id=emp.id,
        rate_type="piece",
        rate_amount=Decimal("20.00"),
        effective_from=date(2026, 10, 1),
        effective_to=None,
        changed_by=emp.id,
    )
    sync_db_session.add_all([site, emp, act, rate_h])
    sync_db_session.commit()

    att = AttendanceRecord(id=_uuid(), employee_id=emp.id, site_id=site.id, date=date(2026, 10, 1), status="approved")
    sync_db_session.add(att)
    sync_db_session.commit()

    dwe = DailyWorkEntry(
        id=_uuid(),
        idempotency_key=f"idemp-dwe-{sfx}",
        attendance_record_id=att.id,
        employee_id=emp.id,
        site_id=site.id,
        activity_id=act.id,
        work_date=date(2026, 10, 1),
        quantity=50,
        uom="metres",
        status="approved",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()

    pay = EmployeePayment(
        id=_uuid(),
        payment_number=f"PAY-P-{sfx}",
        idempotency_key=f"idemp-p-{sfx}",
        employee_id=emp.id,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 7),
        status="draft",
        total_amount=Decimal("1000.00"),
        total_regular_amount=Decimal("1000.00"),
        total_overtime_hours=Decimal("0.00"),
        total_overtime_amount=Decimal("0.00"),
        total_days=Decimal("0.00"),
        total_quantity=Decimal("50.00"),
    )
    sync_db_session.add(pay)
    sync_db_session.commit()

    # Piece rate line: has no standard workday, no overtime rate
    piece_line = EmployeePaymentLine(
        id=_uuid(),
        payment_id=pay.id,
        source_attendance_id=None,
        source_daily_work_entry_id=dwe.id,
        source_date=date(2026, 10, 1),
        rate_type="piece",
        rate_amount=Decimal("20.00"),
        rate_effective_from=date(2026, 10, 1),
        rate_effective_to=None,
        days=Decimal("0.00"),
        quantity=Decimal("50.00"),
        regular_hours=None,
        overtime_hours=Decimal("0.00"),
        standard_day_hours=None,
        hourly_equivalent_rate=None,
        overtime_multiplier=None,
        regular_amount=Decimal("1000.00"),
        overtime_amount=Decimal("0.00"),
        amount=Decimal("1000.00"),
        is_active=True,
    )
    sync_db_session.add(piece_line)
    sync_db_session.commit()
    sync_db_session.refresh(piece_line)

    assert piece_line.rate_type == "piece"
    assert piece_line.standard_day_hours is None
    assert piece_line.overtime_multiplier is None
    assert piece_line.hourly_equivalent_rate is None
    assert piece_line.regular_amount == Decimal("1000.00")
    assert piece_line.overtime_amount == Decimal("0.00")
    assert piece_line.amount == Decimal("1000.00")

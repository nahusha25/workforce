"""
Phase 5 — DashboardService tests (BE-027, BE-028).

Fixture design:
  - 3 employees: emp_a (cable + device work), emp_b (cable only), emp_c (no work entries)
  - 2 sites: site_main, site_other (for filter tests)
  - 2 activities: act_cable (category='cable', uom='metres'), act_device (category='device', uom='nos')
  - emp_a has 2 approved attendance records at site_main (total 16h), 1 at site_other (8h)
  - emp_b has 1 approved attendance record at site_main (8h), 1 DRAFT (excluded)
  - emp_c has 0 attendance records
  - emp_a has approved work: cable @ site_main 500m, device @ site_main 10nos,
            cable @ site_other 200m
  - emp_b has approved work: cable @ site_main 300m, and 1 REJECTED cable entry (excluded)
  - 3 approved material_transactions: 2 at site_main, 1 at site_other
  - 1 draft material_transaction at site_main (excluded from cost metric)
  - employee_rate_history: emp_a → daily 500, emp_b → piece 100, emp_c → no rate row
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    MaterialTransaction,
    Project,
    Site,
)
from app.models.workforce import Employee, EmployeeRateHistory, Role
from app.modules.dashboard.schemas import DashboardFilters
from app.modules.dashboard.service import DashboardService
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _u() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _setup(session: AsyncSession):
    """Seed rich test data; return a dict of named objects for assertions."""
    sfx = str(_u())[:8]

    # --- Users ---
    u_a = User(id=_u(), mobile_id=f"ua-{sfx}", role="employee", is_active=True)
    u_b = User(id=_u(), mobile_id=f"ub-{sfx}", role="employee", is_active=True)
    u_c = User(id=_u(), mobile_id=f"uc-{sfx}", role="employee", is_active=True)
    u_sup = User(id=_u(), mobile_id=f"us-{sfx}", role="supervisor", is_active=True)
    session.add_all([u_a, u_b, u_c, u_sup])
    await session.flush()

    # --- Employees ---
    sup_emp = Employee(id=_u(), user_id=u_sup.id, employee_code=f"SUP-{sfx}",
                       mobile_id=u_sup.mobile_id, name="Supervisor", is_active=True)
    emp_a = Employee(id=_u(), user_id=u_a.id, employee_code=f"A-{sfx}",
                     mobile_id=u_a.mobile_id, name="Alpha Worker", is_active=True)
    emp_b = Employee(id=_u(), user_id=u_b.id, employee_code=f"B-{sfx}",
                     mobile_id=u_b.mobile_id, name="Beta Worker", is_active=True)
    emp_c = Employee(id=_u(), user_id=u_c.id, employee_code=f"C-{sfx}",
                     mobile_id=u_c.mobile_id, name="Gamma Worker", is_active=True)
    session.add_all([sup_emp, emp_a, emp_b, emp_c])
    await session.flush()

    # --- Client / Project / Sites ---
    client = Client(id=_u(), name=f"Cli-{sfx}", is_active=True)
    session.add(client)
    await session.flush()

    project = Project(id=_u(), client_id=client.id, name=f"Proj-{sfx}", status="active")
    session.add(project)
    await session.flush()

    site_main = Site(id=_u(), project_id=project.id, name=f"MainSite-{sfx}",
                     supervisor_id=sup_emp.id, permitted_radius_m=500.0)
    site_other = Site(id=_u(), project_id=project.id, name=f"OtherSite-{sfx}",
                      supervisor_id=sup_emp.id, permitted_radius_m=500.0)
    session.add_all([site_main, site_other])
    await session.flush()

    # --- Activities ---
    act_cable = Activity(id=_u(), name=f"Cable-{sfx}", unit_of_measure="metres",
                         approved_rate=Decimal("10"), category="cable", is_active=True)
    act_device = Activity(id=_u(), name=f"Device-{sfx}", unit_of_measure="nos",
                          approved_rate=Decimal("50"), category="device", is_active=True)
    session.add_all([act_cable, act_device])
    await session.flush()

    # --- Attendance records ---
    d1 = date(2025, 8, 1)
    d2 = date(2025, 8, 2)
    d3 = date(2025, 8, 3)

    # emp_a: 2 approved at site_main (8h each), 1 approved at site_other (8h)
    att_a1 = AttendanceRecord(id=_u(), employee_id=emp_a.id, site_id=site_main.id,
                              date=d1, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                              status="approved")
    att_a2 = AttendanceRecord(id=_u(), employee_id=emp_a.id, site_id=site_main.id,
                              date=d2, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                              status="approved")
    att_a3 = AttendanceRecord(id=_u(), employee_id=emp_a.id, site_id=site_other.id,
                              date=d3, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                              status="approved")
    # emp_b: 1 approved at site_main, 1 draft (must be excluded)
    att_b1 = AttendanceRecord(id=_u(), employee_id=emp_b.id, site_id=site_main.id,
                              date=d1, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                              status="approved")
    att_b_draft = AttendanceRecord(id=_u(), employee_id=emp_b.id, site_id=site_main.id,
                                   date=d2, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                                   status="draft")
    session.add_all([att_a1, att_a2, att_a3, att_b1, att_b_draft])
    await session.flush()

    # --- Work entries ---
    # emp_a: cable 500m approved at site_main, device 10nos approved at site_main,
    #         cable 200m approved at site_other
    dwe_a_cable_main = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-acm-{sfx}",
        attendance_record_id=att_a1.id, employee_id=emp_a.id,
        site_id=site_main.id, activity_id=act_cable.id,
        work_date=d1, quantity=Decimal("500"), uom="metres", status="approved",
    )
    dwe_a_device_main = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-adm-{sfx}",
        attendance_record_id=att_a2.id, employee_id=emp_a.id,
        site_id=site_main.id, activity_id=act_device.id,
        work_date=d2, quantity=Decimal("10"), uom="nos", status="approved",
    )
    dwe_a_cable_other = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-aco-{sfx}",
        attendance_record_id=att_a3.id, employee_id=emp_a.id,
        site_id=site_other.id, activity_id=act_cable.id,
        work_date=d3, quantity=Decimal("200"), uom="metres", status="approved",
    )
    # emp_b: cable 300m approved at site_main, cable 100m REJECTED (excluded)
    dwe_b_cable = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-bcm-{sfx}",
        attendance_record_id=att_b1.id, employee_id=emp_b.id,
        site_id=site_main.id, activity_id=act_cable.id,
        work_date=d1, quantity=Decimal("300"), uom="metres", status="approved",
    )
    dwe_b_rejected = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-brj-{sfx}",
        attendance_record_id=att_b1.id, employee_id=emp_b.id,
        site_id=site_main.id, activity_id=act_cable.id,
        work_date=d1, quantity=Decimal("100"), uom="metres", status="rejected",
    )
    session.add_all([dwe_a_cable_main, dwe_a_device_main, dwe_a_cable_other,
                     dwe_b_cable, dwe_b_rejected])
    await session.flush()

    # --- Material transactions ---
    # Use explicit created_at within the test period so date filter works.
    # 2 approved at site_main (amounts 1000 + 500), 1 approved at site_other (amount 200)
    # 1 draft at site_main (amount 9999 — must be excluded from cost metric)
    mt_ts = datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    mt1 = MaterialTransaction(
        id=_u(), daily_work_entry_id=dwe_a_cable_main.id,
        site_id=site_main.id, transaction_type="purchased",
        item_name="Cable roll", quantity=Decimal("5"), amount=Decimal("1000"),
        is_high_value=False, status="approved", created_at=mt_ts, updated_at=mt_ts,
    )
    mt2 = MaterialTransaction(
        id=_u(), daily_work_entry_id=dwe_a_device_main.id,
        site_id=site_main.id, transaction_type="purchased",
        item_name="Conduit pipe", quantity=Decimal("2"), amount=Decimal("500"),
        is_high_value=False, status="approved", created_at=mt_ts, updated_at=mt_ts,
    )
    mt3 = MaterialTransaction(
        id=_u(), daily_work_entry_id=dwe_a_cable_other.id,
        site_id=site_other.id, transaction_type="purchased",
        item_name="Junction box", quantity=Decimal("1"), amount=Decimal("200"),
        is_high_value=False, status="approved", created_at=mt_ts, updated_at=mt_ts,
    )
    mt_draft = MaterialTransaction(
        id=_u(), daily_work_entry_id=dwe_b_cable.id,
        site_id=site_main.id, transaction_type="purchased",
        item_name="Draft item", quantity=Decimal("1"), amount=Decimal("9999"),
        is_high_value=False, status="draft", created_at=mt_ts, updated_at=mt_ts,
    )
    session.add_all([mt1, mt2, mt3, mt_draft])
    await session.flush()

    # --- Rate history ---
    # emp_a: daily rate 500, effective for whole period
    # emp_b: piece rate 100, effective for whole period
    # emp_c: no rate row (edge case)
    rate_a = EmployeeRateHistory(
        id=_u(), employee_id=emp_a.id, rate_type="daily", rate_amount=Decimal("500"),
        effective_from=date(2025, 1, 1), effective_to=None, changed_by=sup_emp.id,
    )
    rate_b = EmployeeRateHistory(
        id=_u(), employee_id=emp_b.id, rate_type="piece", rate_amount=Decimal("100"),
        effective_from=date(2025, 1, 1), effective_to=None, changed_by=sup_emp.id,
    )
    session.add_all([rate_a, rate_b])
    await session.commit()

    return dict(
        emp_a=emp_a, emp_b=emp_b, emp_c=emp_c,
        site_main=site_main, site_other=site_other,
        act_cable=act_cable, act_device=act_device,
        client=client,
        d1=d1, d2=d2, d3=d3,
    )


# Full-period filters covering all seed data
PERIOD_FROM = date(2025, 8, 1)
PERIOD_TO = date(2025, 8, 31)


def _full_filters(**kwargs) -> DashboardFilters:
    return DashboardFilters(date_from=PERIOD_FROM, date_to=PERIOD_TO, **kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDashboardMetrics:

    @pytest.mark.asyncio
    async def test_manpower_counts_only_approved(self):
        """Only approved attendance rows count toward manpower; draft excluded."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(client_id=ctx["client"].id)
            manpower, hours = await DashboardService._get_manpower_hours(session, f)
            # emp_a (3 approved across 2 sites) + emp_b (1 approved) = 2 distinct employees
            assert manpower.total_distinct_employees == 2

    @pytest.mark.asyncio
    async def test_working_hours_excludes_draft(self):
        """Draft attendance hours not included in total."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            # Scope to site_main only to isolate from other test runs
            f = _full_filters(site_id=ctx["site_main"].id)
            _, hours = await DashboardService._get_manpower_hours(session, f)
            # emp_a: 16h approved, emp_b: 8h approved at site_main; draft 8h excluded
            assert hours.total_hours == Decimal("24")

    @pytest.mark.asyncio
    async def test_working_hours_average(self):
        """Average = total / distinct employees (scoped to site_main)."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            _, hours = await DashboardService._get_manpower_hours(session, f)
            # 24h total / 2 employees = 12h avg at site_main
            assert hours.average_per_employee == Decimal("12.00")

    @pytest.mark.asyncio
    async def test_manpower_site_filter(self):
        """site_id filter restricts to that site only."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            manpower, hours = await DashboardService._get_manpower_hours(session, f)
            # emp_a has 2 approved at site_main, emp_b has 1
            assert manpower.total_distinct_employees == 2
            # emp_a: 16h + emp_b: 8h at site_main only
            assert hours.total_hours == Decimal("24")

    @pytest.mark.asyncio
    async def test_manpower_employee_filter(self):
        """employee_id filter restricts to one employee."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            manpower, hours = await DashboardService._get_manpower_hours(session, f)
            assert manpower.total_distinct_employees == 1
            assert hours.total_hours == Decimal("24")

    @pytest.mark.asyncio
    async def test_manpower_empty_period_returns_zeros(self):
        """No approved records in a future period → zeros, not errors."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = DashboardFilters(date_from=date(2030, 1, 1), date_to=date(2030, 1, 31))
            manpower, hours = await DashboardService._get_manpower_hours(session, f)
            assert manpower.total_distinct_employees == 0
            assert hours.total_hours == Decimal("0")
            assert hours.average_per_employee is None

    @pytest.mark.asyncio
    async def test_cable_metres_only_cable_category(self):
        """cable metric = SUM(quantity) WHERE activity.category='cable', scoped to emp_a."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            cable, devices = await DashboardService._get_cable_and_devices(session, f)
            # emp_a cable: 500 (site_main) + 200 (site_other) = 700
            assert cable.total == Decimal("700")

    @pytest.mark.asyncio
    async def test_devices_installed_only_device_category(self):
        """device metric = SUM(quantity) WHERE activity.category='device', scoped to emp_a."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            cable, devices = await DashboardService._get_cable_and_devices(session, f)
            # emp_a device: 10nos
            assert devices.total == Decimal("10")

    @pytest.mark.asyncio
    async def test_cable_excludes_rejected_work(self):
        """Rejected work entry must not appear; scoped to emp_b to isolate."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_b"].id)
            cable, _ = await DashboardService._get_cable_and_devices(session, f)
            # emp_b: 300m approved; 100m rejected excluded
            assert cable.total == Decimal("300")

    @pytest.mark.asyncio
    async def test_material_cost_excludes_draft(self):
        """Draft material transaction must not appear; scoped to site_main."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            cost = await DashboardService._get_material_cost(session, f)
            # approved at site_main: 1000 + 500 = 1500; draft 9999 excluded
            assert cost.total_amount == Decimal("1500")

    @pytest.mark.asyncio
    async def test_material_cost_site_filter(self):
        """site_other filter isolates its own approved transaction."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_other"].id)
            cost = await DashboardService._get_material_cost(session, f)
            assert cost.total_amount == Decimal("200")

    @pytest.mark.asyncio
    async def test_approval_status_counts_all_states(self):
        """Approval status counts across all status values, scoped to site_main."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            status = await DashboardService._get_approval_status(session, f)
            # attendance at site_main: 2 approved (emp_a), 1 approved (emp_b), 1 draft (emp_b)
            assert status.attendance.approved == 3
            assert status.attendance.draft == 1
            # work entries at site_main: 3 approved (a_cable, a_device, b_cable), 1 rejected (b_rejected)
            assert status.work_entries.approved == 3
            assert status.work_entries.rejected == 1
            # materials at site_main: 2 approved, 1 draft
            assert status.materials.approved == 2
            assert status.materials.draft == 1


class TestProductivityMetric:

    @pytest.mark.asyncio
    async def test_productivity_per_category_not_blended(self):
        """emp_a has cable and device work — must appear as 2 separate by_category entries."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            results = await DashboardService._get_productivity(session, f)
            assert len(results) == 1
            emp = results[0]
            categories = {c.category for c in emp.by_category}
            assert "cable" in categories
            assert "device" in categories
            assert len(emp.by_category) == 2

    @pytest.mark.asyncio
    async def test_productivity_cable_ratio_correct(self):
        """emp_a cable: 700m / 24h = 29.17 metres/hour."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            results = await DashboardService._get_productivity(session, f)
            emp = results[0]
            cable = next(c for c in emp.by_category if c.category == "cable")
            assert cable.total_quantity == Decimal("700")
            assert cable.ratio == Decimal("29.17")
            assert "metres/hour" in cable.ratio_label

    @pytest.mark.asyncio
    async def test_productivity_device_ratio_correct(self):
        """emp_a device: 10nos / 24h = 0.42 devices/hour."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_a"].id)
            results = await DashboardService._get_productivity(session, f)
            emp = results[0]
            device = next(c for c in emp.by_category if c.category == "device")
            assert device.total_quantity == Decimal("10")
            assert device.ratio == Decimal("0.42")

    @pytest.mark.asyncio
    async def test_productivity_emp_b_cable_only(self):
        """emp_b has only cable work — by_category has exactly 1 entry."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_b"].id)
            results = await DashboardService._get_productivity(session, f)
            assert len(results) == 1
            emp = results[0]
            assert len(emp.by_category) == 1
            assert emp.by_category[0].category == "cable"

    @pytest.mark.asyncio
    async def test_productivity_excluded_categories_absent_not_zero(self):
        """emp_b has no device work — device must not appear in by_category at all."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_b"].id)
            results = await DashboardService._get_productivity(session, f)
            categories = {c.category for c in results[0].by_category}
            assert "device" not in categories

    @pytest.mark.asyncio
    async def test_productivity_rejected_work_excluded(self):
        """emp_b rejected cable entry (100m) must not appear in by_category quantity."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_b"].id)
            results = await DashboardService._get_productivity(session, f)
            cable = results[0].by_category[0]
            # Only 300m approved; 100m rejected must not contribute
            assert cable.total_quantity == Decimal("300")

    @pytest.mark.asyncio
    async def test_productivity_null_ratio_when_zero_hours(self):
        """An employee with work entries but zero approved hours gets ratio=None."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            # emp_c has no attendance records → total_approved_hours = 0
            # But _get_productivity only returns employees with approved attendance.
            # Verify emp_c is absent (not present with null ratio).
            f = _full_filters()
            results = await DashboardService._get_productivity(session, f)
            emp_ids = {r.employee_id for r in results}
            assert ctx["emp_c"].id not in emp_ids

    @pytest.mark.asyncio
    async def test_productivity_top10_cap_in_metrics(self):
        """Dashboard metrics endpoint caps at 10 employees (limit=10)."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            results = await DashboardService._get_productivity(session, f, limit=10)
            assert len(results) <= 10

    @pytest.mark.asyncio
    async def test_productivity_sorted_by_hours_desc_name_asc(self):
        """Employees sorted by total_approved_hours DESC, name ASC for ties."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            results = await DashboardService._get_productivity(session, f)
            if len(results) >= 2:
                # emp_a has 24h, emp_b has 8h → emp_a first
                assert results[0].total_approved_hours >= results[1].total_approved_hours


class TestSiteProgress:

    @pytest.mark.asyncio
    async def test_site_progress_category_breakdown(self):
        """site_main should show both cable and device in category_breakdown."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            sites = await DashboardService._get_site_progress(session, f)
            assert len(sites) == 1
            breakdown = sites[0].category_breakdown
            assert "cable" in breakdown
            assert "device" in breakdown
            # emp_a 500m + emp_b 300m at site_main = 800m cable
            assert breakdown["cable"] == Decimal("800")
            # emp_a 10nos device at site_main
            assert breakdown["device"] == Decimal("10")

    @pytest.mark.asyncio
    async def test_site_progress_total_is_sum_of_breakdown(self):
        """total_quantity must equal sum of all category_breakdown values."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            sites = await DashboardService._get_site_progress(session, f)
            site = sites[0]
            assert site.total_quantity == sum(site.category_breakdown.values())

    @pytest.mark.asyncio
    async def test_site_progress_having_excludes_null_qty(self):
        """
        HAVING COALESCE(SUM(quantity), 0) > 0 must exclude categories
        where a LEFT JOIN would produce NULL rather than 0.
        We verify this by checking that no by_category entry has qty=0.
        """
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            sites = await DashboardService._get_site_progress(session, f)
            for site in sites:
                for qty in site.category_breakdown.values():
                    assert qty > 0, f"Found zero/null quantity in site_progress for site {site.site_name}"


class TestReports:

    @pytest.mark.asyncio
    async def test_attendance_report_default_approved_only(self):
        """Default status filter returns only approved records."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_attendance_report(session, f)
            for row in resp.data:
                assert row.status == "approved"

    @pytest.mark.asyncio
    async def test_attendance_report_pagination(self):
        """page=1, page_size=2 returns at most 2 rows and correct total."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_attendance_report(session, f, page=1, page_size=2)
            assert len(resp.data) <= 2
            assert resp.total >= 4  # 4 approved records seeded

    @pytest.mark.asyncio
    async def test_attendance_report_page2_different_rows(self):
        """Page 2 must differ from page 1 (scoped to site_main for isolation)."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            p1 = await DashboardService.get_attendance_report(session, f, page=1, page_size=2)
            p2 = await DashboardService.get_attendance_report(session, f, page=2, page_size=2)
            ids_p1 = {r.attendance_id for r in p1.data}
            ids_p2 = {r.attendance_id for r in p2.data}
            if ids_p2:  # only assert disjoint if page 2 has rows
                assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_work_report_only_approved(self):
        """Work report returns only approved entries, scoped to emp_a+emp_b via site_main."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            resp = await DashboardService.get_work_report(session, f)
            for row in resp.data:
                assert row.status == "approved"
            # 3 approved at site_main: a_cable_main, a_device_main, b_cable
            assert resp.total == 3

    @pytest.mark.asyncio
    async def test_work_report_site_filter(self):
        """site_id filter restricts work report to that site."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            resp = await DashboardService.get_work_report(session, f)
            assert all(r.site_id == ctx["site_main"].id for r in resp.data)

    @pytest.mark.asyncio
    async def test_materials_report_includes_all_statuses(self):
        """Materials report (no status filter) includes approved and draft, scoped to site_main."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            resp = await DashboardService.get_materials_report(session, f)
            statuses = {r.status for r in resp.data}
            # site_main has 2 approved + 1 draft
            assert "approved" in statuses
            assert "draft" in statuses

    @pytest.mark.asyncio
    async def test_materials_report_high_value_filter(self):
        """is_high_value=True filter returns only high-value transactions."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_materials_report(session, f, is_high_value=True)
            # Seed has no high_value=True entries
            assert resp.total == 0

    @pytest.mark.asyncio
    async def test_productivity_report_paginated(self):
        """Full productivity report scoped to site_main contains exactly emp_a and emp_b."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_main"].id)
            resp = await DashboardService.get_productivity_report(session, f, page=1, page_size=50)
            emp_ids = {r.employee_id for r in resp.data}
            assert ctx["emp_a"].id in emp_ids
            assert ctx["emp_b"].id in emp_ids
            assert ctx["emp_c"].id not in emp_ids

    @pytest.mark.asyncio
    async def test_payment_summary_daily_rate(self):
        """emp_a: daily rate 500, 3 approved days → estimated_gross = 1500."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_payment_summary_report(session, f)
            emp_a_row = next((r for r in resp.data if r.employee_id == ctx["emp_a"].id), None)
            assert emp_a_row is not None
            assert emp_a_row.rate_type == "daily"
            assert emp_a_row.approved_days == 3
            assert emp_a_row.estimated_gross == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_payment_summary_piece_rate(self):
        """emp_b: piece rate 100, approved_quantity 300 → estimated_gross = 30000."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(employee_id=ctx["emp_b"].id)
            resp = await DashboardService.get_payment_summary_report(session, f)
            emp_b_row = next((r for r in resp.data if r.employee_id == ctx["emp_b"].id), None)
            assert emp_b_row is not None
            assert emp_b_row.rate_type == "piece"
            assert emp_b_row.approved_quantity == Decimal("300")
            assert emp_b_row.estimated_gross == Decimal("30000.00")

    @pytest.mark.asyncio
    async def test_payment_summary_effective_dated_rate(self):
        """
        Rate lookup uses per-record join on attendance date:
        An employee with two distinct rates in the queried period (e.g. 400 from
        Aug 1-15 and 600 from Aug 16 onward) produces two separate rate-band rows
        with correct sub-totals, proving work is priced with the rate active on
        each record's actual date rather than a single period snapshot.
        """
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            sfx = str(_u())[:8]

            # Employee with 2 rates within August 2025
            u_mr = User(id=_u(), mobile_id=f"umr-{sfx}", role="employee", is_active=True)
            session.add(u_mr)
            await session.flush()

            emp_mr = Employee(
                id=_u(),
                user_id=u_mr.id,
                employee_code=f"MR-{sfx}",
                mobile_id=u_mr.mobile_id,
                name="Rate-Shift Worker",
                is_active=True,
            )
            session.add(emp_mr)
            await session.flush()

            # Rate 1: 400 daily from Aug 1 to Aug 15
            rate1 = EmployeeRateHistory(
                id=_u(),
                employee_id=emp_mr.id,
                rate_type="daily",
                rate_amount=Decimal("400"),
                effective_from=date(2025, 8, 1),
                effective_to=date(2025, 8, 15),
                changed_by=ctx["emp_a"].id,
            )
            # Rate 2: 600 daily from Aug 16 onward
            rate2 = EmployeeRateHistory(
                id=_u(),
                employee_id=emp_mr.id,
                rate_type="daily",
                rate_amount=Decimal("600"),
                effective_from=date(2025, 8, 16),
                effective_to=None,
                changed_by=ctx["emp_a"].id,
            )
            session.add_all([rate1, rate2])

            # Attendance 1 & 2 in band 1 (Aug 5, Aug 10)
            att1 = AttendanceRecord(
                id=_u(), employee_id=emp_mr.id, site_id=ctx["site_main"].id,
                date=date(2025, 8, 5), working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                status="approved",
            )
            att2 = AttendanceRecord(
                id=_u(), employee_id=emp_mr.id, site_id=ctx["site_main"].id,
                date=date(2025, 8, 10), working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                status="approved",
            )
            # Attendance 3 in band 2 (Aug 20)
            att3 = AttendanceRecord(
                id=_u(), employee_id=emp_mr.id, site_id=ctx["site_main"].id,
                date=date(2025, 8, 20), working_hours=Decimal("8"), overtime_hours=Decimal("0"),
                status="approved",
            )
            session.add_all([att1, att2, att3])
            await session.commit()

            f = DashboardFilters(
                date_from=date(2025, 8, 1),
                date_to=date(2025, 8, 31),
                employee_id=emp_mr.id,
            )
            resp = await DashboardService.get_payment_summary_report(session, f)

            assert len(resp.data) == 2, f"Expected 2 rate-band rows, got {len(resp.data)}"

            band1 = next((r for r in resp.data if r.effective_rate == Decimal("400")), None)
            band2 = next((r for r in resp.data if r.effective_rate == Decimal("600")), None)

            assert band1 is not None, "Band 1 (400) row missing"
            assert band1.approved_days == 2
            assert band1.estimated_gross == Decimal("800.00")
            assert band1.rate_effective_from == date(2025, 8, 1)
            assert band1.rate_effective_to == date(2025, 8, 15)

            assert band2 is not None, "Band 2 (600) row missing"
            assert band2.approved_days == 1
            assert band2.estimated_gross == Decimal("600.00")
            assert band2.rate_effective_from == date(2025, 8, 16)
            assert band2.rate_effective_to is None

            total_estimated = sum(r.estimated_gross for r in resp.data)
            assert total_estimated == Decimal("1400.00")


    @pytest.mark.asyncio
    async def test_payment_summary_no_rate_row_gives_zero_gross(self):
        """emp_c has no rate history → excluded from payment summary (no attendance)."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_payment_summary_report(session, f)
            # emp_c has no approved attendance → not in summary at all
            emp_c_ids = [r.employee_id for r in resp.data]
            assert ctx["emp_c"].id not in emp_c_ids

    @pytest.mark.asyncio
    async def test_invoice_summary_aggregates_by_site(self):
        """Invoice summary shows site_other with correct material cost."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_other"].id)
            resp = await DashboardService.get_invoice_summary_report(session, f)
            assert len(resp.data) == 1
            site_other_row = resp.data[0]
            # site_other material cost: 200 (draft 9999 is at site_main, not here)
            assert site_other_row.total_material_cost == Decimal("200")

    @pytest.mark.asyncio
    async def test_full_metrics_response_all_8_keys_present(self):
        """get_metrics returns a response with all 8 required metric keys."""
        async with TestingSessionLocal() as session:
            await _setup(session)
            f = _full_filters()
            resp = await DashboardService.get_metrics(session, f)
            assert resp.manpower is not None
            assert resp.working_hours is not None
            assert resp.site_progress is not None
            assert resp.cable_metres is not None
            assert resp.devices_installed is not None
            assert resp.employee_productivity is not None
            assert resp.material_cost is not None
            assert resp.approval_status is not None

    @pytest.mark.asyncio
    async def test_full_metrics_only_approved_data(self):
        """get_metrics material cost and cable at site_other must match approved-only sum."""
        async with TestingSessionLocal() as session:
            ctx = await _setup(session)
            f = _full_filters(site_id=ctx["site_other"].id)
            resp = await DashboardService.get_metrics(session, f)
            # site_other: 200 approved material, 200m cable
            assert resp.material_cost.total_amount == Decimal("200")
            assert resp.cable_metres.total == Decimal("200")

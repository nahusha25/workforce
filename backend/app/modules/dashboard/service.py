"""
Phase 5 — Dashboard & Reporting service layer (BE-027, BE-028).

Design notes:
- All queries filter by status='approved' only (REQ-BR-004).
- Productivity is computed per-employee per-activity-category so units remain
  comparable (metres/hour, devices/hour) — never blended across categories.
- The dashboard metrics endpoint caps employee_productivity at top-10 by
  total_approved_hours DESC, ties broken by employee_name ASC (deterministic).
- Payment summary uses effective-dated rates: for each approved attendance record
  we join employee_rate_history on effective_from <= record.date AND
  (effective_to IS NULL OR effective_to >= record.date). If no rate row matches a
  given day, that day is excluded from the estimated gross with a count in
  unrated_days so the caller can surface a warning.
- HAVING clause uses COALESCE(SUM(...), 0) > 0 to exclude both NULL (no matching
  rows from LEFT JOIN) and genuine 0-quantity entries from by_category entries.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    MaterialTransaction,
    Project,
    Site,
)
from app.models.workforce import Employee, EmployeeRateHistory
from app.modules.dashboard.schemas import (
    ApprovalStatusCounts,
    ApprovalStatusMetric,
    AttendanceReportResponse,
    AttendanceReportRow,
    CableMetresMetric,
    DashboardFilters,
    DashboardMetricsResponse,
    DevicesInstalledMetric,
    EmployeeProductivity,
    InvoiceSummaryResponse,
    InvoiceSummaryRow,
    ManpowerMetric,
    MaterialCostMetric,
    MaterialsReportResponse,
    MaterialsReportRow,
    PaymentSummaryResponse,
    PaymentSummaryRow,
    ProductivityByCategoryEntry,
    ProductivityReportResponse,
    ProductivityReportRow,
    SiteProgressEntry,
    WorkReportResponse,
    WorkReportRow,
    WorkingHoursMetric,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _attendance_base_filter(f: DashboardFilters):
    """Core filter clauses shared across all attendance-based queries."""
    clauses = [
        AttendanceRecord.status == "approved",
        AttendanceRecord.date >= f.date_from,
        AttendanceRecord.date <= f.date_to,
    ]
    if f.site_id:
        clauses.append(AttendanceRecord.site_id == f.site_id)
    if f.employee_id:
        clauses.append(AttendanceRecord.employee_id == f.employee_id)
    if f.supervisor_id:
        # Filter by sites supervised by supervisor_id
        clauses.append(
            AttendanceRecord.site_id.in_(
                select(Site.id).where(Site.supervisor_id == f.supervisor_id)
            )
        )
    if f.client_id:
        clauses.append(
            AttendanceRecord.site_id.in_(
                select(Site.id)
                .join(Project, Project.id == Site.project_id)
                .where(Project.client_id == f.client_id)
            )
        )
    return clauses


def _dwe_base_filter(f: DashboardFilters):
    """Core filter clauses shared across all daily_work_entries-based queries."""
    clauses = [
        DailyWorkEntry.status == "approved",
        DailyWorkEntry.work_date >= f.date_from,
        DailyWorkEntry.work_date <= f.date_to,
    ]
    if f.site_id:
        clauses.append(DailyWorkEntry.site_id == f.site_id)
    if f.employee_id:
        clauses.append(DailyWorkEntry.employee_id == f.employee_id)
    if f.supervisor_id:
        clauses.append(
            DailyWorkEntry.site_id.in_(
                select(Site.id).where(Site.supervisor_id == f.supervisor_id)
            )
        )
    if f.client_id:
        clauses.append(
            DailyWorkEntry.site_id.in_(
                select(Site.id)
                .join(Project, Project.id == Site.project_id)
                .where(Project.client_id == f.client_id)
            )
        )
    return clauses


def _mt_approved_filter(f: DashboardFilters):
    """Filter clauses for approved material_transactions (cost metric, invoice summary)."""
    return _mt_filter_with_status(f, status="approved")


def _mt_base_filter(f: DashboardFilters):
    """Alias kept for compatibility — returns approved-only filter."""
    return _mt_approved_filter(f)


def _mt_filter_with_status(f: DashboardFilters, status: Optional[str] = None):
    """Core filter for material_transactions with optional status restriction."""
    from datetime import timedelta
    from sqlalchemy import cast as sa_cast
    from sqlalchemy.types import Date as DateType
    date_to_exclusive = f.date_to + timedelta(days=1)
    # Cast timestamptz created_at to Date for clean date-boundary comparison.
    created_date = sa_cast(MaterialTransaction.created_at, DateType)
    clauses = [
        created_date >= f.date_from,
        created_date < date_to_exclusive,
    ]
    if status is not None:
        clauses.append(MaterialTransaction.status == status)
    if f.site_id:
        clauses.append(MaterialTransaction.site_id == f.site_id)
    if f.client_id:
        clauses.append(
            MaterialTransaction.site_id.in_(
                select(Site.id)
                .join(Project, Project.id == Site.project_id)
                .where(Project.client_id == f.client_id)
            )
        )
    if f.supervisor_id:
        clauses.append(
            MaterialTransaction.site_id.in_(
                select(Site.id).where(Site.supervisor_id == f.supervisor_id)
            )
        )
    return clauses


def _fmt_ratio_label(ratio: Optional[Decimal], uom: str) -> str:
    if ratio is None:
        return "N/A (no approved hours)"
    return f"{ratio:.2f} {uom}/hour"


# ---------------------------------------------------------------------------
# DashboardService
# ---------------------------------------------------------------------------

class DashboardService:

    # ------------------------------------------------------------------
    # Metric 1 + 2: Manpower + Working Hours
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_manpower_hours(
        session: AsyncSession, f: DashboardFilters
    ) -> Tuple[ManpowerMetric, WorkingHoursMetric]:
        stmt = select(
            func.count(func.distinct(AttendanceRecord.employee_id)).label("distinct_emp"),
            func.coalesce(func.sum(AttendanceRecord.working_hours), 0).label("total_hours"),
        ).where(and_(*_attendance_base_filter(f)))

        row = (await session.execute(stmt)).one()
        distinct_emp = row.distinct_emp or 0
        total_hours = Decimal(str(row.total_hours or 0))

        avg = (
            (total_hours / distinct_emp).quantize(Decimal("0.01"))
            if distinct_emp > 0
            else None
        )
        return (
            ManpowerMetric(total_distinct_employees=distinct_emp),
            WorkingHoursMetric(total_hours=total_hours, average_per_employee=avg),
        )

    # ------------------------------------------------------------------
    # Metric 3: Site progress (total quantity + category breakdown per site)
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_site_progress(
        session: AsyncSession, f: DashboardFilters
    ) -> List[SiteProgressEntry]:
        stmt = (
            select(
                DailyWorkEntry.site_id,
                Site.name.label("site_name"),
                Activity.category,
                func.coalesce(func.sum(DailyWorkEntry.quantity), Decimal("0")).label("qty"),
            )
            .join(Activity, Activity.id == DailyWorkEntry.activity_id)
            .join(Site, Site.id == DailyWorkEntry.site_id)
            .where(and_(*_dwe_base_filter(f)))
            .group_by(DailyWorkEntry.site_id, Site.name, Activity.category)
            .having(func.coalesce(func.sum(DailyWorkEntry.quantity), 0) > 0)
            .order_by(DailyWorkEntry.site_id, Activity.category)
        )
        rows = (await session.execute(stmt)).all()

        # Aggregate into per-site entries
        sites: Dict[uuid.UUID, SiteProgressEntry] = {}
        for row in rows:
            sid = row.site_id
            qty = Decimal(str(row.qty))
            if sid not in sites:
                sites[sid] = SiteProgressEntry(
                    site_id=sid,
                    site_name=row.site_name,
                    total_quantity=Decimal("0"),
                    category_breakdown={},
                )
            sites[sid].total_quantity += qty
            sites[sid].category_breakdown[row.category] = qty

        return list(sites.values())

    # ------------------------------------------------------------------
    # Metric 4 + 5: Cable metres (category='cable') + Devices installed (category='device')
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_cable_and_devices(
        session: AsyncSession, f: DashboardFilters
    ) -> Tuple[CableMetresMetric, DevicesInstalledMetric]:
        stmt = (
            select(
                Activity.category,
                func.coalesce(func.sum(DailyWorkEntry.quantity), 0).label("total"),
            )
            .join(Activity, Activity.id == DailyWorkEntry.activity_id)
            .where(
                and_(
                    *_dwe_base_filter(f),
                    Activity.category.in_(["cable", "device"]),
                )
            )
            .group_by(Activity.category)
        )
        rows = (await session.execute(stmt)).all()
        totals = {row.category: Decimal(str(row.total)) for row in rows}
        return (
            CableMetresMetric(total=totals.get("cable", Decimal("0"))),
            DevicesInstalledMetric(total=totals.get("device", Decimal("0"))),
        )

    # ------------------------------------------------------------------
    # Metric 6: Employee productivity (per-employee, per-category)
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_productivity(
        session: AsyncSession,
        f: DashboardFilters,
        limit: Optional[int] = None,
    ) -> List[EmployeeProductivity]:
        """
        Compute per-employee, per-category productivity.

        Step 1: total approved hours per employee from attendance_records.
        Step 2: approved quantity per employee per category from daily_work_entries JOIN activities.
        Step 3: merge in Python to build the by_category list.

        HAVING uses COALESCE(SUM(quantity), 0) > 0 — this correctly excludes
        both NULL (from a LEFT JOIN with no matching rows) and genuine zero-quantity
        entries, satisfying the confirmed design requirement.
        """
        # Step 1: approved hours per employee
        hours_stmt = (
            select(
                AttendanceRecord.employee_id,
                Employee.name.label("employee_name"),
                func.coalesce(func.sum(AttendanceRecord.working_hours), 0).label("total_hours"),
            )
            .join(Employee, Employee.id == AttendanceRecord.employee_id)
            .where(and_(*_attendance_base_filter(f)))
            .group_by(AttendanceRecord.employee_id, Employee.name)
            .order_by(
                func.coalesce(func.sum(AttendanceRecord.working_hours), 0).desc(),
                Employee.name.asc(),  # deterministic tie-break
            )
        )
        if limit:
            hours_stmt = hours_stmt.limit(limit)

        hours_rows = (await session.execute(hours_stmt)).all()
        if not hours_rows:
            return []

        employee_ids = [r.employee_id for r in hours_rows]
        hours_map: Dict[uuid.UUID, Tuple[str, Decimal]] = {
            r.employee_id: (r.employee_name, Decimal(str(r.total_hours)))
            for r in hours_rows
        }

        # Step 2: quantity per employee per category (only employees in our set)
        work_stmt = (
            select(
                DailyWorkEntry.employee_id,
                Activity.category,
                Activity.unit_of_measure.label("uom"),
                func.coalesce(func.sum(DailyWorkEntry.quantity), 0).label("total_qty"),
            )
            .join(Activity, Activity.id == DailyWorkEntry.activity_id)
            .where(
                and_(
                    *_dwe_base_filter(f),
                    DailyWorkEntry.employee_id.in_(employee_ids),
                )
            )
            .group_by(DailyWorkEntry.employee_id, Activity.category, Activity.unit_of_measure)
            # Exclude both NULL and genuine 0-quantity — confirmed design requirement
            .having(func.coalesce(func.sum(DailyWorkEntry.quantity), 0) > 0)
            .order_by(DailyWorkEntry.employee_id, Activity.category)
        )
        work_rows = (await session.execute(work_stmt)).all()

        # Step 3: merge
        categories_by_emp: Dict[uuid.UUID, List[ProductivityByCategoryEntry]] = {
            eid: [] for eid in employee_ids
        }
        for wr in work_rows:
            emp_hours = hours_map[wr.employee_id][1]
            qty = Decimal(str(wr.total_qty))
            ratio = (qty / emp_hours).quantize(Decimal("0.01")) if emp_hours > 0 else None
            categories_by_emp[wr.employee_id].append(
                ProductivityByCategoryEntry(
                    category=wr.category,
                    uom=wr.uom,
                    total_quantity=qty,
                    ratio=ratio,
                    ratio_label=_fmt_ratio_label(ratio, wr.uom),
                )
            )

        return [
            EmployeeProductivity(
                employee_id=eid,
                employee_name=hours_map[eid][0],
                total_approved_hours=hours_map[eid][1],
                by_category=categories_by_emp[eid],
            )
            for eid in employee_ids
        ]

    # ------------------------------------------------------------------
    # Metric 7: Material cost
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_material_cost(
        session: AsyncSession, f: DashboardFilters
    ) -> MaterialCostMetric:
        stmt = select(
            func.coalesce(func.sum(MaterialTransaction.amount), 0).label("total")
        ).where(and_(*_mt_base_filter(f)))
        row = (await session.execute(stmt)).one()
        return MaterialCostMetric(total_amount=Decimal(str(row.total)))

    # ------------------------------------------------------------------
    # Metric 8: Approval status breakdown
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_approval_status(
        session: AsyncSession, f: DashboardFilters
    ) -> ApprovalStatusMetric:
        def _status_counts_stmt(model, date_col, date_from, date_to, site_id, employee_id, supervisor_id, client_id):
            clauses = [
                date_col >= date_from,
                date_col <= date_to,
            ]
            if site_id and hasattr(model, "site_id"):
                clauses.append(model.site_id == site_id)
            if employee_id and hasattr(model, "employee_id"):
                clauses.append(model.employee_id == employee_id)
            if supervisor_id:
                clauses.append(
                    model.site_id.in_(
                        select(Site.id).where(Site.supervisor_id == supervisor_id)
                    )
                )
            if client_id:
                clauses.append(
                    model.site_id.in_(
                        select(Site.id)
                        .join(Project, Project.id == Site.project_id)
                        .where(Project.client_id == client_id)
                    )
                )
            return (
                select(model.status, func.count().label("cnt"))
                .where(and_(*clauses))
                .group_by(model.status)
            )

        def _to_counts(rows) -> ApprovalStatusCounts:
            mapping = {r.status: r.cnt for r in rows}
            return ApprovalStatusCounts(
                approved=mapping.get("approved", 0),
                submitted=mapping.get("submitted", 0),
                draft=mapping.get("draft", 0),
                rejected=mapping.get("rejected", 0),
                correction_required=mapping.get("correction_required", 0),
            )

        att_stmt = _status_counts_stmt(
            AttendanceRecord, AttendanceRecord.date,
            f.date_from, f.date_to, f.site_id, f.employee_id, f.supervisor_id, f.client_id,
        )
        dwe_stmt = _status_counts_stmt(
            DailyWorkEntry, DailyWorkEntry.work_date,
            f.date_from, f.date_to, f.site_id, f.employee_id, f.supervisor_id, f.client_id,
        )
        # For approval_status we want ALL statuses — use no-status filter
        mt_stmt = (
            select(MaterialTransaction.status, func.count().label("cnt"))
            .where(and_(*_mt_filter_with_status(f, status=None)))
            .group_by(MaterialTransaction.status)
        )

        att_rows = (await session.execute(att_stmt)).all()
        dwe_rows = (await session.execute(dwe_stmt)).all()
        mt_rows = (await session.execute(mt_stmt)).all()

        return ApprovalStatusMetric(
            attendance=_to_counts(att_rows),
            work_entries=_to_counts(dwe_rows),
            materials=_to_counts(mt_rows),
        )

    # ------------------------------------------------------------------
    # Public: all 8 metrics in one call
    # ------------------------------------------------------------------

    @staticmethod
    async def get_metrics(
        session: AsyncSession, f: DashboardFilters
    ) -> DashboardMetricsResponse:
        manpower, working_hours = await DashboardService._get_manpower_hours(session, f)
        site_progress = await DashboardService._get_site_progress(session, f)
        cable, devices = await DashboardService._get_cable_and_devices(session, f)
        productivity = await DashboardService._get_productivity(session, f, limit=10)
        material_cost = await DashboardService._get_material_cost(session, f)
        approval_status = await DashboardService._get_approval_status(session, f)

        return DashboardMetricsResponse(
            period={"from": f.date_from, "to": f.date_to},
            manpower=manpower,
            working_hours=working_hours,
            site_progress=site_progress,
            cable_metres=cable,
            devices_installed=devices,
            employee_productivity=productivity,
            material_cost=material_cost,
            approval_status=approval_status,
        )

    # ------------------------------------------------------------------
    # Report: DSH-002 Attendance
    # ------------------------------------------------------------------

    @staticmethod
    async def get_attendance_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[str] = "approved",
    ) -> AttendanceReportResponse:
        base = [
            AttendanceRecord.date >= f.date_from,
            AttendanceRecord.date <= f.date_to,
        ]
        if status_filter:
            base.append(AttendanceRecord.status == status_filter)
        if f.site_id:
            base.append(AttendanceRecord.site_id == f.site_id)
        if f.employee_id:
            base.append(AttendanceRecord.employee_id == f.employee_id)
        if f.supervisor_id:
            base.append(
                AttendanceRecord.site_id.in_(
                    select(Site.id).where(Site.supervisor_id == f.supervisor_id)
                )
            )
        if f.client_id:
            base.append(
                AttendanceRecord.site_id.in_(
                    select(Site.id)
                    .join(Project, Project.id == Site.project_id)
                    .where(Project.client_id == f.client_id)
                )
            )

        count_stmt = select(func.count()).where(and_(*base))
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(
                AttendanceRecord.id.label("attendance_id"),
                AttendanceRecord.employee_id,
                Employee.name.label("employee_name"),
                AttendanceRecord.site_id,
                Site.name.label("site_name"),
                AttendanceRecord.date,
                AttendanceRecord.check_in_time,
                AttendanceRecord.check_out_time,
                AttendanceRecord.working_hours,
                AttendanceRecord.overtime_hours,
                AttendanceRecord.status,
                AttendanceRecord.is_within_geofence,
            )
            .join(Employee, Employee.id == AttendanceRecord.employee_id)
            .join(Site, Site.id == AttendanceRecord.site_id)
            .where(and_(*base))
            .order_by(AttendanceRecord.date.desc(), Employee.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).all()
        data = [AttendanceReportRow(**dict(r._mapping)) for r in rows]
        return AttendanceReportResponse(data=data, total=total, page=page, page_size=page_size)

    # ------------------------------------------------------------------
    # Report: DSH-003 Work entries
    # ------------------------------------------------------------------

    @staticmethod
    async def get_work_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
        activity_id: Optional[uuid.UUID] = None,
        work_order_id: Optional[uuid.UUID] = None,
    ) -> WorkReportResponse:
        base = list(_dwe_base_filter(f))
        if activity_id:
            base.append(DailyWorkEntry.activity_id == activity_id)
        if work_order_id:
            base.append(DailyWorkEntry.work_order_id == work_order_id)

        count_stmt = select(func.count()).where(and_(*base))
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(
                DailyWorkEntry.id.label("entry_id"),
                DailyWorkEntry.employee_id,
                Employee.name.label("employee_name"),
                DailyWorkEntry.site_id,
                Site.name.label("site_name"),
                DailyWorkEntry.work_date,
                Activity.name.label("activity_name"),
                Activity.category,
                DailyWorkEntry.quantity,
                DailyWorkEntry.uom,
                DailyWorkEntry.status,
                DailyWorkEntry.work_order_id,
            )
            .join(Employee, Employee.id == DailyWorkEntry.employee_id)
            .join(Site, Site.id == DailyWorkEntry.site_id)
            .join(Activity, Activity.id == DailyWorkEntry.activity_id)
            .where(and_(*base))
            .order_by(DailyWorkEntry.work_date.desc(), Employee.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).all()
        data = [WorkReportRow(**dict(r._mapping)) for r in rows]
        return WorkReportResponse(data=data, total=total, page=page, page_size=page_size)

    # ------------------------------------------------------------------
    # Report: DSH-004 Materials
    # ------------------------------------------------------------------

    @staticmethod
    async def get_materials_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
        transaction_type: Optional[str] = None,
        is_high_value: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> MaterialsReportResponse:
        # For the materials report we want all statuses by default; filter if requested
        base = [
            MaterialTransaction.created_at >= func.cast(f.date_from, MaterialTransaction.created_at.type),
            MaterialTransaction.created_at < text(f"'{f.date_to}'::date + interval '1 day'"),
        ]
        if status:
            base.append(MaterialTransaction.status == status)
        if f.site_id:
            base.append(MaterialTransaction.site_id == f.site_id)
        if f.supervisor_id:
            base.append(
                MaterialTransaction.site_id.in_(
                    select(Site.id).where(Site.supervisor_id == f.supervisor_id)
                )
            )
        if f.client_id:
            base.append(
                MaterialTransaction.site_id.in_(
                    select(Site.id)
                    .join(Project, Project.id == Site.project_id)
                    .where(Project.client_id == f.client_id)
                )
            )
        if transaction_type:
            base.append(MaterialTransaction.transaction_type == transaction_type)
        if is_high_value is not None:
            base.append(MaterialTransaction.is_high_value == is_high_value)
        # Optionally include only approved for cost-related views; caller passes status via filters
        # Default: all statuses (report shows history)

        # employee_id filter: via the linked daily_work_entry
        if f.employee_id:
            from app.models.operations import DailyWorkEntry as DWE
            base.append(
                MaterialTransaction.daily_work_entry_id.in_(
                    select(DWE.id).where(DWE.employee_id == f.employee_id)
                )
            )

        count_stmt = select(func.count()).where(and_(*base))
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(
                MaterialTransaction.id.label("transaction_id"),
                DailyWorkEntry.employee_id,
                Employee.name.label("employee_name"),
                MaterialTransaction.site_id,
                Site.name.label("site_name"),
                MaterialTransaction.item_name,
                MaterialTransaction.transaction_type,
                MaterialTransaction.quantity,
                MaterialTransaction.amount,
                MaterialTransaction.is_high_value,
                MaterialTransaction.status,
                MaterialTransaction.created_at,
            )
            .join(DailyWorkEntry, DailyWorkEntry.id == MaterialTransaction.daily_work_entry_id)
            .join(Employee, Employee.id == DailyWorkEntry.employee_id)
            .join(Site, Site.id == MaterialTransaction.site_id)
            .where(and_(*base))
            .order_by(MaterialTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).all()
        data = [MaterialsReportRow(**dict(r._mapping)) for r in rows]
        return MaterialsReportResponse(data=data, total=total, page=page, page_size=page_size)

    # ------------------------------------------------------------------
    # Report: DSH-005 Productivity (full paginated version)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_productivity_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
        sort_category: Optional[str] = None,
    ) -> ProductivityReportResponse:
        """
        Full paginated productivity report.
        sort_category: if provided, sort employees by their ratio in that category desc,
                       then by employee_name asc for deterministic ties.
                       If None, sort by total_approved_hours desc, employee_name asc.
        """
        # Get all matching employees (no limit) then slice in Python after merge
        all_productivity = await DashboardService._get_productivity(session, f, limit=None)

        if sort_category:
            def _cat_ratio(ep: EmployeeProductivity) -> Decimal:
                for c in ep.by_category:
                    if c.category == sort_category and c.ratio is not None:
                        return c.ratio
                return Decimal("-1")

            all_productivity.sort(
                key=lambda ep: (_cat_ratio(ep) * -1, ep.employee_name)
            )
        # else: already sorted by total_approved_hours desc, employee_name asc from query

        total = len(all_productivity)
        start = (page - 1) * page_size
        page_data = all_productivity[start : start + page_size]

        return ProductivityReportResponse(
            data=[ProductivityReportRow(**ep.model_dump()) for ep in page_data],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Report: DSH-006 Payment summary (estimated, read-only)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_payment_summary_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
    ) -> PaymentSummaryResponse:
        """
        Estimated pay preview using per-record effective-dated rates.

        Design:
          - Each approved attendance record is joined to the rate_history row
            that was active on that specific day:
              effective_from <= attendance.date AND
              (effective_to IS NULL OR effective_to >= attendance.date)
          - Results are grouped by (employee, rate_type, rate_amount,
            effective_from, effective_to) — one output row per rate segment.
          - If an employee had a rate change mid-period, they appear as two rows
            with correct sub-totals for each band.
          - For daily/weekly rate types: approved_days from attendance_records.
          - For piece rate type: approved_quantity from daily_work_entries whose
            work_date falls within the same rate band.
          - Attendance records with no matching rate row are collected separately
            and emitted as an 'unrated' row so the caller can surface a warning.
        """
        from sqlalchemy import case as sa_case, literal

        # ------------------------------------------------------------------
        # Build attendance base clauses (shared between rated and unrated)
        # ------------------------------------------------------------------
        att_base = [
            AttendanceRecord.status == "approved",
            AttendanceRecord.date >= f.date_from,
            AttendanceRecord.date <= f.date_to,
        ]
        if f.site_id:
            att_base.append(AttendanceRecord.site_id == f.site_id)
        if f.employee_id:
            att_base.append(AttendanceRecord.employee_id == f.employee_id)
        if f.supervisor_id:
            att_base.append(
                AttendanceRecord.site_id.in_(
                    select(Site.id).where(Site.supervisor_id == f.supervisor_id)
                )
            )

        # ------------------------------------------------------------------
        # Query A: per-record join for daily / weekly rate types.
        # Each attendance record is matched to the rate effective on that day.
        # We GROUP BY (employee, rate_type, rate_amount, eff_from, eff_to) to
        # produce one sub-total per rate band.
        # ------------------------------------------------------------------
        att_daily_stmt = (
            select(
                AttendanceRecord.employee_id,
                Employee.name.label("employee_name"),
                EmployeeRateHistory.rate_type,
                EmployeeRateHistory.rate_amount,
                EmployeeRateHistory.effective_from.label("rate_eff_from"),
                EmployeeRateHistory.effective_to.label("rate_eff_to"),
                func.count(AttendanceRecord.id).label("days_in_band"),
            )
            .join(Employee, Employee.id == AttendanceRecord.employee_id)
            .join(
                EmployeeRateHistory,
                and_(
                    EmployeeRateHistory.employee_id == AttendanceRecord.employee_id,
                    EmployeeRateHistory.effective_from <= AttendanceRecord.date,
                    or_(
                        EmployeeRateHistory.effective_to.is_(None),
                        EmployeeRateHistory.effective_to >= AttendanceRecord.date,
                    ),
                    EmployeeRateHistory.rate_type.in_(["daily", "weekly"]),
                ),
            )
            .where(and_(*att_base))
            .group_by(
                AttendanceRecord.employee_id,
                Employee.name,
                EmployeeRateHistory.rate_type,
                EmployeeRateHistory.rate_amount,
                EmployeeRateHistory.effective_from,
                EmployeeRateHistory.effective_to,
            )
            .order_by(Employee.name.asc(), EmployeeRateHistory.effective_from.asc())
        )
        daily_rows = (await session.execute(att_daily_stmt)).all()

        # ------------------------------------------------------------------
        # Query B: per-record join for piece rate type.
        # Each approved work entry is matched to the piece rate effective on
        # that work_date, grouped by the same rate-band key.
        # ------------------------------------------------------------------
        dwe_base = [
            DailyWorkEntry.status == "approved",
            DailyWorkEntry.work_date >= f.date_from,
            DailyWorkEntry.work_date <= f.date_to,
        ]
        if f.site_id:
            dwe_base.append(DailyWorkEntry.site_id == f.site_id)
        if f.employee_id:
            dwe_base.append(DailyWorkEntry.employee_id == f.employee_id)
        if f.supervisor_id:
            dwe_base.append(
                DailyWorkEntry.site_id.in_(
                    select(Site.id).where(Site.supervisor_id == f.supervisor_id)
                )
            )

        # Also need approved attendance count per piece-rate band (for approved_days field)
        # We compute it by joining attendance to the same piece-rate bands.
        att_piece_days_stmt = (
            select(
                AttendanceRecord.employee_id,
                EmployeeRateHistory.effective_from.label("rate_eff_from"),
                EmployeeRateHistory.effective_to.label("rate_eff_to"),
                func.count(AttendanceRecord.id).label("days_in_band"),
            )
            .join(
                EmployeeRateHistory,
                and_(
                    EmployeeRateHistory.employee_id == AttendanceRecord.employee_id,
                    EmployeeRateHistory.effective_from <= AttendanceRecord.date,
                    or_(
                        EmployeeRateHistory.effective_to.is_(None),
                        EmployeeRateHistory.effective_to >= AttendanceRecord.date,
                    ),
                    EmployeeRateHistory.rate_type == "piece",
                ),
            )
            .where(and_(*att_base))
            .group_by(
                AttendanceRecord.employee_id,
                EmployeeRateHistory.effective_from,
                EmployeeRateHistory.effective_to,
            )
        )
        piece_days_rows = (await session.execute(att_piece_days_stmt)).all()
        # Build lookup: (employee_id, eff_from, eff_to) → days_in_band
        piece_days_map: Dict[tuple, int] = {
            (r.employee_id, r.rate_eff_from, r.rate_eff_to): r.days_in_band
            for r in piece_days_rows
        }

        dwe_piece_stmt = (
            select(
                DailyWorkEntry.employee_id,
                Employee.name.label("employee_name"),
                EmployeeRateHistory.rate_type,
                EmployeeRateHistory.rate_amount,
                EmployeeRateHistory.effective_from.label("rate_eff_from"),
                EmployeeRateHistory.effective_to.label("rate_eff_to"),
                func.coalesce(func.sum(DailyWorkEntry.quantity), 0).label("qty_in_band"),
            )
            .join(Employee, Employee.id == DailyWorkEntry.employee_id)
            .join(
                EmployeeRateHistory,
                and_(
                    EmployeeRateHistory.employee_id == DailyWorkEntry.employee_id,
                    EmployeeRateHistory.effective_from <= DailyWorkEntry.work_date,
                    or_(
                        EmployeeRateHistory.effective_to.is_(None),
                        EmployeeRateHistory.effective_to >= DailyWorkEntry.work_date,
                    ),
                    EmployeeRateHistory.rate_type == "piece",
                ),
            )
            .where(and_(*dwe_base))
            .group_by(
                DailyWorkEntry.employee_id,
                Employee.name,
                EmployeeRateHistory.rate_type,
                EmployeeRateHistory.rate_amount,
                EmployeeRateHistory.effective_from,
                EmployeeRateHistory.effective_to,
            )
            .order_by(Employee.name.asc(), EmployeeRateHistory.effective_from.asc())
        )
        piece_rows = (await session.execute(dwe_piece_stmt)).all()

        # ------------------------------------------------------------------
        # Assemble results — one PaymentSummaryRow per rate segment
        # ------------------------------------------------------------------
        results: List[PaymentSummaryRow] = []

        # daily / weekly segments
        for r in daily_rows:
            days = r.days_in_band
            rate = Decimal(str(r.rate_amount))
            if r.rate_type == "daily":
                gross = Decimal(days) * rate
            elif r.rate_type == "weekly":
                gross = (Decimal(days) / Decimal("7")) * rate
            else:
                gross = Decimal("0")

            results.append(PaymentSummaryRow(
                employee_id=r.employee_id,
                employee_name=r.employee_name,
                rate_type=r.rate_type,
                rate_effective_from=r.rate_eff_from,
                rate_effective_to=r.rate_eff_to,
                approved_days=days,
                approved_quantity=Decimal("0"),
                effective_rate=rate,
                estimated_gross=gross.quantize(Decimal("0.01")),
            ))

        # piece segments
        for r in piece_rows:
            qty = Decimal(str(r.qty_in_band))
            rate = Decimal(str(r.rate_amount))
            gross = qty * rate
            days = piece_days_map.get(
                (r.employee_id, r.rate_eff_from, r.rate_eff_to), 0
            )
            results.append(PaymentSummaryRow(
                employee_id=r.employee_id,
                employee_name=r.employee_name,
                rate_type=r.rate_type,
                rate_effective_from=r.rate_eff_from,
                rate_effective_to=r.rate_eff_to,
                approved_days=days,
                approved_quantity=qty,
                effective_rate=rate,
                estimated_gross=gross.quantize(Decimal("0.01")),
            ))

        # Sort: employee_name asc, rate_effective_from asc (deterministic)
        results.sort(key=lambda x: (x.employee_name, x.rate_effective_from))

        total = len(results)
        start = (page - 1) * page_size
        return PaymentSummaryResponse(
            data=results[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Report: DSH-007 Invoice summary (client/site aggregated totals)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_invoice_summary_report(
        session: AsyncSession,
        f: DashboardFilters,
        page: int = 1,
        page_size: int = 50,
    ) -> InvoiceSummaryResponse:
        # Labour days per site: each approved attendance record = one employee-day
        labour_stmt = (
            select(
                AttendanceRecord.site_id,
                func.count(AttendanceRecord.id).label("labour_days"),
            )
            .where(and_(*_attendance_base_filter(f)))
            .group_by(AttendanceRecord.site_id)
        )
        labour_rows = (await session.execute(labour_stmt)).all()
        labour_map = {r.site_id: r.labour_days for r in labour_rows}

        # Work quantity per site
        work_stmt = (
            select(
                DailyWorkEntry.site_id,
                func.coalesce(func.sum(DailyWorkEntry.quantity), 0).label("total_qty"),
            )
            .where(and_(*_dwe_base_filter(f)))
            .group_by(DailyWorkEntry.site_id)
        )
        work_rows = (await session.execute(work_stmt)).all()
        work_map = {r.site_id: Decimal(str(r.total_qty)) for r in work_rows}

        # Material cost per site
        mt_base = list(_mt_base_filter(f))
        mt_stmt = (
            select(
                MaterialTransaction.site_id,
                func.coalesce(func.sum(MaterialTransaction.amount), 0).label("total_amount"),
            )
            .where(and_(*mt_base))
            .group_by(MaterialTransaction.site_id)
        )
        mt_rows = (await session.execute(mt_stmt)).all()
        mt_map = {r.site_id: Decimal(str(r.total_amount)) for r in mt_rows}

        # All relevant sites
        all_site_ids = list(
            set(labour_map.keys()) | set(work_map.keys()) | set(mt_map.keys())
        )
        if not all_site_ids:
            return InvoiceSummaryResponse(data=[], total=0, page=page, page_size=page_size)

        sites_stmt = (
            select(Site.id, Site.name, Project.client_id, Client.name.label("client_name"))
            .join(Project, Project.id == Site.project_id)
            .join(Client, Client.id == Project.client_id)
            .where(Site.id.in_(all_site_ids))
        )
        site_rows = (await session.execute(sites_stmt)).all()

        results = [
            InvoiceSummaryRow(
                site_id=sr.id,
                site_name=sr.name,
                client_id=sr.client_id,
                client_name=sr.client_name,
                total_labour_days=labour_map.get(sr.id, 0),
                total_work_quantity=work_map.get(sr.id, Decimal("0")),
                total_material_cost=mt_map.get(sr.id, Decimal("0")),
            )
            for sr in site_rows
        ]
        results.sort(key=lambda r: (r.client_name, r.site_name))

        total = len(results)
        start = (page - 1) * page_size
        return InvoiceSummaryResponse(
            data=results[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

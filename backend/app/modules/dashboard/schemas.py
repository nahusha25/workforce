"""
Phase 5 — Dashboard & Reporting Pydantic schemas.
All response models are derived from the approved productivity shape
and metric definitions in docs/05-director-dashboard-invoicing/requirements.md.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Shared filter / pagination
# ---------------------------------------------------------------------------

class DashboardFilters(BaseModel):
    """Shared filter parameters for all dashboard and report endpoints."""
    date_from: date
    date_to: date
    client_id: Optional[uuid.UUID] = None
    site_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None
    supervisor_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_date_range(self) -> DashboardFilters:
        if self.date_from > self.date_to:
            raise ValueError("date_from must not be greater than date_to")
        if (self.date_to - self.date_from).days > 365:
            raise ValueError("date range cannot exceed 365 days")
        return self



class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Dashboard metrics — DSH-001
# ---------------------------------------------------------------------------

class ManpowerMetric(BaseModel):
    total_distinct_employees: int


class WorkingHoursMetric(BaseModel):
    total_hours: Decimal
    average_per_employee: Optional[Decimal]  # None when total_distinct_employees == 0


class SiteProgressEntry(BaseModel):
    site_id: uuid.UUID
    site_name: str
    total_quantity: Decimal
    # breakdown by activity category (e.g. {"cable": 500.0, "device": 12.0})
    category_breakdown: Dict[str, Decimal]


class CableMetresMetric(BaseModel):
    total: Decimal


class DevicesInstalledMetric(BaseModel):
    total: Decimal


class ProductivityByCategoryEntry(BaseModel):
    category: str          # one of the 6 confirmed categories
    uom: str               # from activities.unit_of_measure
    total_quantity: Decimal
    ratio: Optional[Decimal]  # None when total_approved_hours == 0
    ratio_label: str       # always a human-readable string, never None


class EmployeeProductivity(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    total_approved_hours: Decimal
    by_category: List[ProductivityByCategoryEntry]


class MaterialCostMetric(BaseModel):
    total_amount: Decimal
    currency: str = "INR"


class ApprovalStatusCounts(BaseModel):
    approved: int = 0
    submitted: int = 0
    draft: int = 0
    rejected: int = 0
    correction_required: int = 0


class ApprovalStatusMetric(BaseModel):
    attendance: ApprovalStatusCounts
    work_entries: ApprovalStatusCounts
    materials: ApprovalStatusCounts


class DashboardMetricsResponse(BaseModel):
    period: Dict[str, date]   # {"from": date, "to": date}
    manpower: ManpowerMetric
    working_hours: WorkingHoursMetric
    site_progress: List[SiteProgressEntry]
    cable_metres: CableMetresMetric
    devices_installed: DevicesInstalledMetric
    # top 10 by total_approved_hours desc, ties broken by employee_name asc
    employee_productivity: List[EmployeeProductivity]
    material_cost: MaterialCostMetric
    approval_status: ApprovalStatusMetric


# ---------------------------------------------------------------------------
# Report rows — DSH-002 through DSH-007
# ---------------------------------------------------------------------------

class AttendanceReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attendance_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    site_id: uuid.UUID
    site_name: str
    date: date
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    working_hours: Optional[Decimal]
    overtime_hours: Optional[Decimal]
    status: str
    is_within_geofence: Optional[bool]


class WorkReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    site_id: uuid.UUID
    site_name: str
    work_date: date
    activity_name: str
    category: str
    quantity: Decimal
    uom: str
    status: str
    work_order_id: Optional[uuid.UUID]


class MaterialsReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    site_id: uuid.UUID
    site_name: str
    item_name: str
    transaction_type: str
    quantity: Decimal
    amount: Decimal
    is_high_value: bool
    status: str
    created_at: datetime


class ProductivityReportRow(BaseModel):
    """One row per employee in the productivity report, full by_category breakdown."""
    employee_id: uuid.UUID
    employee_name: str
    total_approved_hours: Decimal
    by_category: List[ProductivityByCategoryEntry]


class PaymentSummaryRow(BaseModel):
    """
    Read-only estimated pay per employee using effective-dated rates.
    No payment records are created — this is a preview only.

    One row is produced per (employee, rate_segment): if an employee had a rate
    change within the filtered period they will appear as multiple rows — one per
    effective rate band — so the caller can show itemised sub-totals.
    """
    employee_id: uuid.UUID
    employee_name: str
    rate_type: str                        # 'daily' | 'weekly' | 'piece'
    rate_effective_from: date             # start of this rate band
    rate_effective_to: Optional[date]     # end of this rate band (None = open-ended)
    approved_days: int                    # approved attendance days falling in this rate band
    approved_quantity: Decimal            # sum of approved work quantity in this rate band
    effective_rate: Decimal               # rate_amount from employee_rate_history for this band
    estimated_gross: Decimal


class InvoiceSummaryRow(BaseModel):
    """Client/site aggregated totals for the period."""
    site_id: uuid.UUID
    site_name: str
    client_id: uuid.UUID
    client_name: str
    total_labour_days: int
    total_work_quantity: Decimal
    total_material_cost: Decimal


# ---------------------------------------------------------------------------
# Paginated wrappers for report endpoints
# ---------------------------------------------------------------------------

class AttendanceReportResponse(BaseModel):
    data: List[AttendanceReportRow]
    total: int
    page: int
    page_size: int


class WorkReportResponse(BaseModel):
    data: List[WorkReportRow]
    total: int
    page: int
    page_size: int


class MaterialsReportResponse(BaseModel):
    data: List[MaterialsReportRow]
    total: int
    page: int
    page_size: int


class ProductivityReportResponse(BaseModel):
    data: List[ProductivityReportRow]
    total: int
    page: int
    page_size: int


class PaymentSummaryResponse(BaseModel):
    data: List[PaymentSummaryRow]
    total: int
    page: int
    page_size: int
    note: str = (
        "This is an estimated preview only. "
        "No payment records have been created. "
        "Rates reflect effective_dated values from employee_rate_history."
    )


class InvoiceSummaryResponse(BaseModel):
    data: List[InvoiceSummaryRow]
    total: int
    page: int
    page_size: int

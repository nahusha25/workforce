"""
Phase 5 — Dashboard & Reports API Tests (BE-029, BE-030, BE-031).
Verifies:
  - RBAC: Director required (200), non-director forbidden (403), unauth (401)
  - Date validation: date_from > date_to (422), date range > 365 days (422)
  - All 8 metrics present in GET /api/v1/dashboard/metrics
  - All 6 report endpoints return 200 and paginated structure
  - Export: xlsx and pdf formats, proper Content-Type, Content-Disposition, and binary content
  - Invalid export report_type and invalid format produce 422
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
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


def _u() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def api_setup(sync_db_session: Session):
    sfx = uuid.uuid4().hex[:8]

    # Users
    u_dir = User(id=_u(), mobile_id=f"dir-{sfx}", role="director", is_active=True)
    u_admin = User(id=_u(), mobile_id=f"adm-{sfx}", role="administrator", is_active=True)
    u_sup = User(id=_u(), mobile_id=f"sup-{sfx}", role="supervisor", is_active=True)
    u_emp = User(id=_u(), mobile_id=f"emp-{sfx}", role="employee", is_active=True)
    sync_db_session.add_all([u_dir, u_admin, u_sup, u_emp])
    sync_db_session.commit()

    # Employees
    dir_emp = Employee(id=_u(), user_id=u_dir.id, employee_code=f"DIR-{sfx}",
                       mobile_id=u_dir.mobile_id, name="Director Boss", is_active=True)
    admin_emp = Employee(id=_u(), user_id=u_admin.id, employee_code=f"ADM-{sfx}",
                         mobile_id=u_admin.mobile_id, name="System Admin", is_active=True)
    sup_emp = Employee(id=_u(), user_id=u_sup.id, employee_code=f"SUP-{sfx}",
                       mobile_id=u_sup.mobile_id, name="Site Supervisor", is_active=True)
    emp_worker = Employee(id=_u(), user_id=u_emp.id, employee_code=f"WRK-{sfx}",
                          mobile_id=u_emp.mobile_id, name="Field Worker", is_active=True)
    sync_db_session.add_all([dir_emp, admin_emp, sup_emp, emp_worker])
    sync_db_session.commit()

    # Client, Project, Site
    client = Client(id=_u(), name=f"Client-{sfx}", is_active=True)
    sync_db_session.add(client)
    sync_db_session.commit()

    project = Project(id=_u(), client_id=client.id, name=f"Project-{sfx}", status="active")
    sync_db_session.add(project)
    sync_db_session.commit()

    site = Site(
        id=_u(),
        project_id=project.id,
        name=f"SiteAlpha-{sfx}",
        supervisor_id=sup_emp.id,
        permitted_radius_m=500.0,
    )
    sync_db_session.add(site)
    sync_db_session.commit()

    # Activities (cable and device)
    act_cable = Activity(id=_u(), name=f"Cabling-{sfx}", unit_of_measure="metres",
                         approved_rate=Decimal("15"), category="cable", is_active=True)
    act_device = Activity(id=_u(), name=f"DeviceMount-{sfx}", unit_of_measure="nos",
                          approved_rate=Decimal("100"), category="device", is_active=True)
    sync_db_session.add_all([act_cable, act_device])
    sync_db_session.commit()

    # Dates
    d1 = date(2025, 8, 1)
    d2 = date(2025, 8, 2)

    # Attendance
    att1 = AttendanceRecord(
        id=_u(), employee_id=emp_worker.id, site_id=site.id,
        date=d1, working_hours=Decimal("8.5"), overtime_hours=Decimal("0.5"),
        status="approved", is_within_geofence=True,
    )
    att_draft = AttendanceRecord(
        id=_u(), employee_id=emp_worker.id, site_id=site.id,
        date=d2, working_hours=Decimal("8"), overtime_hours=Decimal("0"),
        status="draft", is_within_geofence=True,
    )
    sync_db_session.add_all([att1, att_draft])
    sync_db_session.commit()

    # Daily work entry
    dwe = DailyWorkEntry(
        id=_u(), idempotency_key=f"ik-dwe-{sfx}",
        attendance_record_id=att1.id, employee_id=emp_worker.id,
        site_id=site.id, activity_id=act_cable.id,
        work_date=d1, quantity=Decimal("450"), uom="metres", status="approved",
    )
    sync_db_session.add(dwe)
    sync_db_session.commit()

    # Material transaction
    mt_ts = datetime(2025, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    mt = MaterialTransaction(
        id=_u(), daily_work_entry_id=dwe.id,
        site_id=site.id, transaction_type="purchased",
        item_name="Cat6 Cable", quantity=Decimal("2"), amount=Decimal("2400.00"),
        is_high_value=False, status="approved", created_at=mt_ts, updated_at=mt_ts,
    )
    sync_db_session.add(mt)
    sync_db_session.commit()

    # Rate history
    rate = EmployeeRateHistory(
        id=_u(), employee_id=emp_worker.id, rate_type="daily", rate_amount=Decimal("600"),
        effective_from=date(2025, 1, 1), effective_to=None, changed_by=dir_emp.id,
    )
    sync_db_session.add(rate)
    sync_db_session.commit()

    # Tokens
    dir_token = create_access_token(subject=str(u_dir.id), role="director")
    admin_token = create_access_token(subject=str(u_admin.id), role="administrator")
    sup_token = create_access_token(subject=str(u_sup.id), role="supervisor")
    emp_token = create_access_token(subject=str(u_emp.id), role="employee")

    return {
        "dir_token": dir_token,
        "admin_token": admin_token,
        "sup_token": sup_token,
        "emp_token": emp_token,
        "dir_headers": {"Authorization": f"Bearer {dir_token}"},
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "sup_headers": {"Authorization": f"Bearer {sup_token}"},
        "emp_headers": {"Authorization": f"Bearer {emp_token}"},
        "site": site,
        "client": client,
        "employee": emp_worker,
    }


# ---------------------------------------------------------------------------
# Auth / RBAC tests
# ---------------------------------------------------------------------------

class TestDashboardAuthAndRBAC:

    def test_unauthenticated_returns_401(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/dashboard/metrics")
        assert resp.status_code == 401

    def test_director_allowed_on_metrics(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/dashboard/metrics", headers=api_setup["dir_headers"])
        assert resp.status_code == 200

    def test_administrator_allowed_on_metrics(self, client: TestClient, api_setup):
        """Administrator role explicitly permitted on dashboard metrics (matching security-plan.md)."""
        resp = client.get("/api/v1/dashboard/metrics", headers=api_setup["admin_headers"])
        assert resp.status_code == 200

    def test_administrator_allowed_on_reports(self, client: TestClient, api_setup):
        """Administrator role explicitly permitted on report endpoints."""
        resp = client.get("/api/v1/reports/attendance", headers=api_setup["admin_headers"])
        assert resp.status_code == 200

    def test_administrator_allowed_on_export(self, client: TestClient, api_setup):
        """Administrator role explicitly permitted on report export."""
        resp = client.get(
            "/api/v1/reports/attendance/export?format=xlsx",
            headers=api_setup["admin_headers"],
        )
        assert resp.status_code == 200

    def test_supervisor_forbidden_on_metrics(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/dashboard/metrics", headers=api_setup["sup_headers"])
        assert resp.status_code == 403

    def test_employee_forbidden_on_metrics(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/dashboard/metrics", headers=api_setup["emp_headers"])
        assert resp.status_code == 403

    def test_supervisor_forbidden_on_reports(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/reports/attendance", headers=api_setup["sup_headers"])
        assert resp.status_code == 403

    def test_employee_forbidden_on_export(self, client: TestClient, api_setup):
        resp = client.get("/api/v1/reports/attendance/export?format=xlsx", headers=api_setup["emp_headers"])
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Date filter validation tests
# ---------------------------------------------------------------------------

class TestDateFilterValidation:

    def test_date_from_greater_than_date_to_returns_422(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/dashboard/metrics?date_from=2025-08-31&date_to=2025-08-01",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 422
        assert "date_from must not be greater than date_to" in resp.text

    def test_date_range_exceeding_365_days_returns_422(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/dashboard/metrics?date_from=2024-01-01&date_to=2025-06-01",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 422
        assert "date range cannot exceed 365 days" in resp.text

    def test_invalid_date_format_returns_422(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/dashboard/metrics?date_from=invalid-date",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard Metrics API tests (DSH-001)
# ---------------------------------------------------------------------------

class TestDashboardMetricsAPI:

    def test_get_metrics_200_all_8_keys_present(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/dashboard/metrics?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "period" in data
        assert "manpower" in data
        assert "working_hours" in data
        assert "site_progress" in data
        assert "cable_metres" in data
        assert "devices_installed" in data
        assert "employee_productivity" in data
        assert "material_cost" in data
        assert "approval_status" in data

        assert data["manpower"]["total_distinct_employees"] >= 1
        assert float(data["material_cost"]["total_amount"]) >= 2400.0

    def test_get_metrics_defaults_to_last_30_days_when_params_omitted(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/dashboard/metrics",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "period" in data
        assert "from" in data["period"]
        assert "to" in data["period"]

    def test_get_metrics_scoped_by_site_id(self, client: TestClient, api_setup):
        site_id = str(api_setup["site"].id)
        resp = client.get(
            f"/api/v1/dashboard/metrics?date_from=2025-08-01&date_to=2025-08-31&site_id={site_id}",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["site_progress"]) == 1
        assert data["site_progress"][0]["site_id"] == site_id


# ---------------------------------------------------------------------------
# Report Endpoints API tests (DSH-002 through DSH-007)
# ---------------------------------------------------------------------------

class TestReportEndpointsAPI:

    def test_get_attendance_report_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/attendance?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert all(r["status"] == "approved" for r in data["data"])

    def test_get_attendance_report_all_statuses(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/attendance?date_from=2025-08-01&date_to=2025-08-31&status=draft",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["status"] == "draft" for r in data["data"])

    def test_get_work_report_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/work?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] >= 1
        row = data["data"][0]
        assert "activity_name" in row
        assert "category" in row
        assert "quantity" in row

    def test_get_materials_report_200(self, client: TestClient, api_setup):
        site_id = str(api_setup["site"].id)
        resp = client.get(
            f"/api/v1/reports/materials?date_from=2025-08-01&date_to=2025-08-31&site_id={site_id}",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] >= 1
        item_names = [r["item_name"] for r in data["data"]]
        assert "Cat6 Cable" in item_names

    def test_get_productivity_report_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/productivity?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        if data["data"]:
            first = data["data"][0]
            assert "employee_name" in first
            assert "by_category" in first

    def test_get_payment_summary_report_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/payment-summary?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "note" in data
        assert "preview" in data["note"].lower()
        if data["data"]:
            row = data["data"][0]
            assert "rate_effective_from" in row
            assert "estimated_gross" in row

    def test_get_payment_summary_alias_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/payment?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_get_invoice_summary_report_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/invoice-summary?date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        if data["data"]:
            row = data["data"][0]
            assert "site_name" in row
            assert "total_labour_days" in row
            assert "total_material_cost" in row


# ---------------------------------------------------------------------------
# Export Endpoint API tests (DSH-008)
# ---------------------------------------------------------------------------

class TestReportExportAPI:

    def test_export_attendance_excel_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/attendance/export?format=xlsx&date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
        assert 'attachment; filename="attendance_2025-08-01_2025-08-31.xlsx"' in resp.headers["content-disposition"]
        assert len(resp.content) > 1000

    def test_export_attendance_pdf_200(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/attendance/export?format=pdf&date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        assert 'attachment; filename="attendance_2025-08-01_2025-08-31.pdf"' in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 500

    @pytest.mark.parametrize(
        "report_type",
        [
            "attendance",
            "work",
            "materials",
            "productivity",
            "payment-summary",
            "invoice-summary",
        ],
    )
    def test_export_all_report_types_excel(self, client: TestClient, api_setup, report_type):
        resp = client.get(
            f"/api/v1/reports/{report_type}/export?format=xlsx&date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
        assert len(resp.content) > 1000

    @pytest.mark.parametrize(
        "report_type",
        [
            "attendance",
            "work",
            "materials",
            "productivity",
            "payment-summary",
            "invoice-summary",
        ],
    )
    def test_export_all_report_types_pdf(self, client: TestClient, api_setup, report_type):
        resp = client.get(
            f"/api/v1/reports/{report_type}/export?format=pdf&date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 500

    def test_export_invalid_report_type_returns_422(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/nonexistent-report/export?format=xlsx",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 422
        assert "Unsupported report_type" in resp.text

    def test_export_invalid_format_returns_422(self, client: TestClient, api_setup):
        resp = client.get(
            "/api/v1/reports/attendance/export?format=csv",
            headers=api_setup["dir_headers"],
        )
        assert resp.status_code == 422
        assert "Invalid format" in resp.text

    def test_export_currency_formatting_two_decimal_places(self, client: TestClient, api_setup):
        """
        Confirms currency values in Excel exports use consistent 2-decimal-place precision
        matching the formatDecimal standard (e.g. 2400.00, 600.00).
        """
        import io
        import re
        import openpyxl

        site_id = str(api_setup["site"].id)
        # 1. Materials export
        resp_mat = client.get(
            f"/api/v1/reports/materials/export?format=xlsx&date_from=2025-08-01&date_to=2025-08-31&site_id={site_id}",
            headers=api_setup["dir_headers"],
        )
        assert resp_mat.status_code == 200
        wb_mat = openpyxl.load_workbook(io.BytesIO(resp_mat.content))
        ws_mat = wb_mat.active
        # Header: Date, Item, Emp, Site, Type, Quantity, Amount (INR), High Value, Status
        # Col 7 is Amount (INR)
        amount_found = False
        for row in ws_mat.iter_rows(min_row=5, values_only=True):
            if row and row[6] is not None:
                val = str(row[6])
                assert re.match(r"^\d+\.\d{2}$", val), f"Amount '{val}' does not match 2 decimal places"
                amount_found = True
        assert amount_found, "Seeded material transaction amount was not found in export"

        # 2. Payment summary export
        resp_pay = client.get(
            "/api/v1/reports/payment-summary/export?format=xlsx&date_from=2025-08-01&date_to=2025-08-31",
            headers=api_setup["dir_headers"],
        )
        assert resp_pay.status_code == 200
        wb_pay = openpyxl.load_workbook(io.BytesIO(resp_pay.content))
        ws_pay = wb_pay.active
        # Col 7 is Effective Rate (INR), Col 8 is Estimated Gross (INR)
        rate_found = False
        for row in ws_pay.iter_rows(min_row=5, values_only=True):
            if row and row[6] is not None and row[7] is not None:
                rate_val = str(row[6])
                gross_val = str(row[7])
                assert re.match(r"^\d+\.\d{2}$", rate_val), f"Rate '{rate_val}' does not match 2 decimal places"
                assert re.match(r"^\d+\.\d{2}$", gross_val), f"Gross '{gross_val}' does not match 2 decimal places"
                rate_found = True
        assert rate_found, "Payment summary rate/gross was not found in export"


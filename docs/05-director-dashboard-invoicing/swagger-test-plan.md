# Phase 5 — Director Dashboard & Invoicing — Swagger Test Plan

> Execute all tests via Swagger UI at `/api/docs`. Each test case must be executed and result recorded.

---

## DSH-001: GET /api/v1/dashboard/metrics

| # | Test Case | Query Params | Expected Status | Expected Response | Verified |
|---|-----------|-------------|----------------|-------------------|----------|
| 1 | Valid request | None | 200 | All 8 metrics populated | ☐ |
| 2 | Filter by date | `?date_from=X&date_to=Y` | 200 | Metrics updated based on dates | ☐ |
| 3 | Filter by site | `?site_id=Z` | 200 | Metrics updated for site | ☐ |
| 4 | RBAC Check | Employee token | 403 | Forbidden | ☐ |

## DSH-002 to DSH-007: Reports

| # | Test Case | Endpoint & Request | Expected Status | Expected Response | Verified |
|---|-----------|--------------------|----------------|-------------------|----------|
| 1 | Attendance | GET `/api/v1/reports/attendance` | 200 | Paginated attendance | ☐ |
| 2 | Work | GET `/api/v1/reports/work` | 200 | Paginated work quantities | ☐ |
| 3 | Materials | GET `/api/v1/reports/materials` | 200 | Paginated materials | ☐ |
| 4 | Productivity | GET `/api/v1/reports/productivity` | 200 | Productivity ranking | ☐ |
| 5 | Verify only approved | All endpoints | 200 | Check response contains NO draft/submitted records | ☐ |

## DSH-008: Export Report

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Export XLSX | GET `/api/v1/reports/work/export?format=xlsx` | 200 | Excel file download | ☐ |
| 2 | Export PDF | GET `/api/v1/reports/work/export?format=pdf` | 200 | PDF file download | ☐ |
| 3 | Invalid format | GET `?format=csv` | 422 | Validation error | ☐ |

## DSH-009: POST /api/v1/invoices/generate

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid generation | Valid client/period | 201 | Invoice created, `status=draft` | ☐ |
| 2 | Missing client | | 422 | Validation error | ☐ |
| 3 | Date mismatch | end < start | 422 | Validation error | ☐ |
| 4 | RBAC Check | Supervisor token | 403 | Forbidden | ☐ |

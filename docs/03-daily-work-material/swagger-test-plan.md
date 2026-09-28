# Phase 3 — Daily Work & Material Update — Swagger Test Plan

> Execute all tests via Swagger UI at `/api/docs`. Each test case must be executed and result recorded.

---

## WRK-001: POST /api/v1/daily-work

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid work entry creation | `{ "activity_id": "valid_uuid", "cable_runs": 5, "cable_length_metres": 100 }` | 201 | Record created, `status=draft`, `cable_runs=5` | ☐ |
| 2 | No active attendance | Request from employee without active check-in | 422 | "Must be checked in to create work entry" | ☐ |
| 3 | Invalid activity_id | `{ "activity_id": "non_existent_uuid" }` | 404 | "Activity not found" | ☐ |
| 4 | Negative quantities | `{ "cable_runs": -1 }` | 422 | Validation error: must be >= 0 | ☐ |
| 5 | Missing required fields | `{ "cable_runs": 5 }` (no activity_id) | 422 | Validation error: activity_id required | ☐ |
| 6 | No auth | No Authorization header | 401 | Unauthorized | ☐ |
| 7 | Non-employee role | Supervisor token | 403 | Forbidden | ☐ |

## WRK-002: GET /api/v1/daily-work

| # | Test Case | Query Params | Expected Status | Expected Response | Verified |
|---|-----------|-------------|----------------|-------------------|----------|
| 1 | Employee sees own entries | None | 200 | Only own entries | ☐ |
| 2 | Supervisor sees assigned | `?employee_id=<assigned_uuid>` | 200 | Assigned employee entries | ☐ |
| 3 | Supervisor tries unassigned | `?employee_id=<unassigned_uuid>` | 403 | "Not authorised for this employee" | ☐ |
| 4 | Filter by status | `?status=draft` | 200 | Only draft entries | ☐ |
| 5 | Pagination | `?page=1&page_size=5` | 200 | Paginated list | ☐ |

## WRK-003: GET /api/v1/daily-work/{id}

| # | Test Case | Path | Expected Status | Expected Response | Verified |
|---|-----------|------|----------------|-------------------|----------|
| 1 | Employee views own entry | Own entry ID | 200 | Full entry with nested photos/materials | ☐ |
| 2 | Employee views other's entry| Other's entry ID | 403 | Forbidden | ☐ |
| 3 | Non-existent ID | Random UUID | 404 | Not found | ☐ |

## WRK-004: PUT /api/v1/daily-work/{id}

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid update | `{ "cable_runs": 10 }` (on draft entry) | 200 | Updated record | ☐ |
| 2 | Update submitted entry | Request on 'submitted' entry | 409 | "Cannot edit submitted entry" | ☐ |
| 3 | Update approved entry | Request on 'approved' entry | 409 | "Cannot edit approved entry" | ☐ |
| 4 | Employee updates other's entry| Request on other's entry | 403 | Forbidden | ☐ |
| 5 | Negative quantities | `{ "cable_length_metres": -5 }` | 422 | Validation error | ☐ |

## WRK-005: POST /api/v1/daily-work/{id}/submit

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid submission | `{}` on draft entry | 200 | `status=submitted` | ☐ |
| 2 | Already submitted | `{}` on submitted entry | 409 | "Entry already submitted" | ☐ |
| 3 | Non-owner submission | `{}` on other's entry | 403 | Forbidden | ☐ |
| 4 | Verify audit log created | After successful submission | N/A | Check audit_logs table | ☐ |

## WRK-006: POST /api/v1/daily-work/{id}/photos

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid image upload | Valid JPEG file | 201 | Photo record with signed URLs | ☐ |
| 2 | Invalid file type | PDF file | 422 | "Invalid file type. Only JPEG/PNG/WEBP allowed." | ☐ |
| 3 | File too large | 15MB file | 422 | "File size exceeds 10MB limit" | ☐ |
| 4 | Upload to submitted entry | Valid file on submitted entry | 409 | "Cannot add photos to submitted entry" | ☐ |
| 5 | Non-owner upload | Valid file on other's entry | 403 | Forbidden | ☐ |

## WRK-007: POST /api/v1/daily-work/{id}/materials

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid material | `{ "item_name": "Cable", "quantity": 10, "amount": 100, "transaction_type": "purchased" }` | 201 | Material record created | ☐ |
| 2 | High-value purchase | Amount > material limit | 201 | `is_high_value=true` | ☐ |
| 3 | Normal purchase | Amount <= material limit | 201 | `is_high_value=false` | ☐ |
| 4 | Zero/negative quantity | `{ "quantity": 0 }` | 422 | "Quantity must be > 0" | ☐ |
| 5 | Negative amount | `{ "amount": -10 }` | 422 | "Amount must be >= 0" | ☐ |
| 6 | Invalid transaction type | `{ "transaction_type": "invalid" }` | 422 | Validation error | ☐ |
| 7 | Add to submitted entry | Valid payload on submitted entry | 409 | "Cannot add materials to submitted entry" | ☐ |

## ADM-007 to ADM-015: Admin Endpoints

| # | Test Case | Endpoint & Request | Expected Status | Expected Response | Verified |
|---|-----------|--------------------|----------------|-------------------|----------|
| 1 | Create valid activity | POST `/api/v1/admin/activities` `{ "name": "Test", "unit_of_measure": "m", "category": "cable", "approved_rate": 10 }` | 201 | Activity created | ☐ |
| 2 | Create negative rate activity | POST `/api/v1/admin/activities` with negative rate | 422 | Validation error | ☐ |
| 3 | Non-admin tries create | POST with Employee token | 403 | Forbidden | ☐ |
| 4 | Create valid material | POST `/api/v1/admin/materials` `{ "name": "Test", "unit_of_measure": "m", "category": "cable", "purchase_approval_limit": 1000 }` | 201 | Material created | ☐ |
| 5 | Create negative limit material | POST `/api/v1/admin/materials` with negative limit | 422 | Validation error | ☐ |
| 6 | Create valid work order | POST `/api/v1/admin/work-orders` with valid payload | 201 | Work order created | ☐ |
| 7 | Create duplicate work order | POST with existing order_number | 409 | "Work order number already exists" | ☐ |
| 8 | Invalid dates work order | POST with end_date < start_date | 422 | Validation error | ☐ |

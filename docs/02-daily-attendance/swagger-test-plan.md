# Phase 2 — Daily Attendance — Swagger Test Plan

> Execute all tests via Swagger UI at `/api/docs`. Each test case must be executed and result recorded.

---

## ATT-001: POST /api/v1/attendance/check-in

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid check-in within geo-fence | `{ "latitude": 12.9716, "longitude": 77.5946 }` with employee token | 201 | Record created, `is_within_geofence=true` | ☐ |
| 2 | Check-in outside geo-fence | GPS coordinates >500m from site | 422 | Geo-fence violation error with distance info | ☐ |
| 3 | Duplicate check-in same day | Same employee, same day | 409 | "Already checked in today" | ☐ |
| 4 | Missing latitude | `{ "longitude": 77.5946 }` | 422 | Validation error: latitude required | ☐ |
| 5 | Missing longitude | `{ "latitude": 12.9716 }` | 422 | Validation error: longitude required | ☐ |
| 6 | Latitude out of range | `{ "latitude": -91, "longitude": 77 }` | 422 | Validation error: latitude range | ☐ |
| 7 | Longitude out of range | `{ "latitude": 12, "longitude": 181 }` | 422 | Validation error: longitude range | ☐ |
| 8 | Employee not assigned to any site | Employee without site assignment | 403 | "No active site assignment" | ☐ |
| 9 | No auth token | Request without Authorization header | 401 | Unauthorized | ☐ |
| 10 | Non-employee role (supervisor) | Supervisor token | 403 | Forbidden | ☐ |
| 11 | Expired token | Expired JWT | 401 | Token expired | ☐ |
| 12 | Verify server timestamp used | Check response `check_in_time` is server-generated | 201 | Timestamp matches server time (not client) | ☐ |
| 13 | Verify employee auto-identified | Check response `employee_id` matches token | 201 | Employee ID from token | ☐ |
| 14 | Verify site auto-assigned | Check response `site_id` matches assignment | 201 | Site from assignment | ☐ |

## ATT-002: POST /api/v1/attendance/check-out

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid check-out | GPS coordinates with active check-in | 200 | Record updated, `working_hours` calculated | ☐ |
| 2 | No active check-in | Employee who hasn't checked in today | 404 | "No active check-in today" | ☐ |
| 3 | Already checked out | Employee who already checked out | 409 | "Already checked out" | ☐ |
| 4 | Check-out with unsubmitted work | Work entries in draft status | 200 | Response includes `work_submission_warning` | ☐ |
| 5 | Check-out with all work submitted | Work entries in submitted status | 200 | `work_submission_warning` is null | ☐ |
| 6 | Verify working hours calculation | Check-out 8.5 hours after check-in | 200 | `working_hours` ≈ 8.5 | ☐ |
| 7 | No auth | No Authorization header | 401 | Unauthorized | ☐ |
| 8 | Missing GPS | Empty request body | 422 | Validation error | ☐ |

## ATT-003: GET /api/v1/attendance

| # | Test Case | Query Params | Expected Status | Expected Response | Verified |
|---|-----------|-------------|----------------|-------------------|----------|
| 1 | Employee sees own records | None (defaults) | 200 | Only own attendance records | ☐ |
| 2 | Supervisor sees assigned employees | None (defaults) | 200 | Assigned employees only, not others | ☐ |
| 3 | Director sees all records | None (defaults) | 200 | All attendance records | ☐ |
| 4 | Date range filter | `?date_from=2025-08-01&date_to=2025-08-07` | 200 | Only records within date range | ☐ |
| 5 | Site filter | `?site_id=<uuid>` | 200 | Only records for specified site | ☐ |
| 6 | Status filter | `?status=approved` | 200 | Only approved records | ☐ |
| 7 | Pagination page 1 | `?page=1&page_size=5` | 200 | First 5 records, correct total | ☐ |
| 8 | Pagination page 2 | `?page=2&page_size=5` | 200 | Next 5 records | ☐ |
| 9 | Employee tries to filter other employee | `?employee_id=<other_uuid>` | 200 | Returns empty (isolation enforced) or own data | ☐ |
| 10 | Invalid date format | `?date_from=not-a-date` | 422 | Validation error | ☐ |
| 11 | No auth | No Authorization header | 401 | Unauthorized | ☐ |

## ATT-004: GET /api/v1/attendance/{id}

| # | Test Case | Path | Expected Status | Expected Response | Verified |
|---|-----------|------|----------------|-------------------|----------|
| 1 | Employee views own record | Own attendance ID | 200 | Full attendance detail | ☐ |
| 2 | Supervisor views assigned employee | Assigned employee's attendance ID | 200 | Full attendance detail | ☐ |
| 3 | Employee views someone else's record | Another employee's attendance ID | 403 | Forbidden | ☐ |
| 4 | Non-existent ID | Random UUID | 404 | Not found | ☐ |
| 5 | Invalid UUID format | `abc123` | 422 | Validation error | ☐ |
| 6 | No auth | No Authorization header | 401 | Unauthorized | ☐ |

## ATT-005: POST /api/v1/attendance/{id}/override

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid override with reason | `{ "reason": "Employee at adjacent building within client campus" }` | 200 | Override recorded, `override_by` set | ☐ |
| 2 | Missing reason | `{}` | 422 | "reason is required" | ☐ |
| 3 | Reason too short | `{ "reason": "ok" }` (< 10 chars) | 422 | "reason must be at least 10 characters" | ☐ |
| 4 | Employee tries override | Employee token | 403 | "Supervisor role required" | ☐ |
| 5 | Supervisor not assigned to employee | Supervisor for different team | 403 | "Not authorised for this employee" | ☐ |
| 6 | Non-existent record | Random UUID | 404 | Not found | ☐ |
| 7 | No auth | No Authorization header | 401 | Unauthorized | ☐ |
| 8 | Verify audit log created | After successful override | 200 | Check audit_logs table for entry | ☐ |
| 9 | Verify override_by populated | After successful override | 200 | `override_by` = supervisor's user ID | ☐ |

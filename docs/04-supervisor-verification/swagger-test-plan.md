# Phase 4 — Supervisor Verification — Swagger Test Plan

> Execute all tests via Swagger UI at `/api/docs`. Each test case must be executed and result recorded.

---

## VER-001: GET /api/v1/verification/summary

| # | Test Case | Query Params | Expected Status | Expected Response | Verified |
|---|-----------|-------------|----------------|-------------------|----------|
| 1 | Valid request (assigned) | `?date=2025-08-11` | 200 | List of assigned employees with submitted entries | ☐ |
| 2 | Filter by site | `?date=2025-08-11&site_id=<uuid>` | 200 | Filtered list | ☐ |
| 3 | Employee attempts access | | 403 | Forbidden | ☐ |
| 4 | Data isolation check | Supervisor with no assigned employees | 200 | Empty list `[]` | ☐ |
| 5 | Verify exception flags | Date with known anomalies | 200 | `exception_flags` array populated correctly | ☐ |
| 6 | No auth | | 401 | Unauthorized | ☐ |

## VER-002: GET /api/v1/verification/summary/{employee_id}

| # | Test Case | Path/Query | Expected Status | Expected Response | Verified |
|---|-----------|------------|----------------|-------------------|----------|
| 1 | Valid request (assigned) | Valid ID, `?date=2025-08-11` | 200 | Full employee day detail | ☐ |
| 2 | Unassigned employee | Employee not under this supervisor | 403 | Forbidden (or 404) | ☐ |
| 3 | Date without data | Date in future | 200 | Empty/null structures | ☐ |

## VER-003: POST /api/v1/verification/{id}/approve

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid approve attendance | `{ "entity_type": "attendance" }` on submitted | 200 | `status=approved` | ☐ |
| 2 | Valid approve work | `{ "entity_type": "daily_work" }` on submitted | 200 | `status=approved` | ☐ |
| 3 | Approve already approved | Request on approved record | 409 | "Record not in submitted state" | ☐ |
| 4 | Approve draft record | Request on draft record | 409 | "Record not in submitted state" | ☐ |
| 5 | Non-assigned supervisor | Request from other supervisor | 403 | Forbidden | ☐ |

## VER-004: POST /api/v1/verification/{id}/reject

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid reject with remarks| `{ "entity_type": "daily_work", "remarks": "Incorrect quantities" }` | 200 | `status=rejected` | ☐ |
| 2 | Missing remarks | `{ "entity_type": "daily_work" }` | 422 | "remarks is required" | ☐ |
| 3 | Short remarks | `{ "entity_type": "daily_work", "remarks": "no" }` | 422 | Validation error (min length) | ☐ |
| 4 | Invalid status | Request on approved record | 409 | Conflict | ☐ |

## VER-005: POST /api/v1/verification/{id}/return

| # | Test Case | Request | Expected Status | Expected Response | Verified |
|---|-----------|---------|----------------|-------------------|----------|
| 1 | Valid return with remarks| `{ "entity_type": "daily_work", "remarks": "Please fix photos" }` | 200 | `status=correction_required` | ☐ |
| 2 | Missing remarks | `{ "entity_type": "daily_work" }` | 422 | "remarks is required" | ☐ |

## Cross-Phase Data Protection (REQ-BR-006)

| # | Test Case | Endpoint & Request | Expected Status | Expected Response | Verified |
|---|-----------|--------------------|----------------|-------------------|----------|
| 1 | Edit approved work | PUT `/api/v1/daily-work/{id}` (approved ID) | 409 | "Record is approved and read-only" | ☐ |
| 2 | Upload photo approved | POST `/api/v1/daily-work/{id}/photos` | 409 | "Cannot add photos to approved entry" | ☐ |

# Phase 4 — Supervisor Verification — Task List

## Database Tasks

```
Task ID: DB-016
Status: [DONE]
Task: Create verification_records table
Layer: Database
Requirement Reference: REQ-VER-005 to REQ-VER-009
Purpose: Persist supervisor verification actions (approve, reject, return) with audit linkage
Description: Create verification_records with id (UUID PK), idempotency_key (VARCHAR(100) UNIQUE), FK→attendance_records (nullable), FK→daily_work_entries (nullable), FK→material_transactions (nullable), FK→users (verified_by), action CHECK ('approved','rejected','correction_required'), single-target CHECK constraint, remarks CHECK (mandatory >= 10 chars on reject/return), verified_at (TIMESTAMPTZ DEFAULT NOW), created_at (TIMESTAMPTZ DEFAULT NOW).
Dependencies: DB-009 (attendance_records), DB-013 (daily_work_entries), DB-015 (material_transactions), DB-001 (users)
Implementation Details: Alembic migration dfc07bb0caa1. Verified with upgrade/downgrade cycle. VerificationRecord SQLAlchemy model added to operations.py and exported from app.models. Indexes on attendance_record_id, daily_work_entry_id, material_transaction_id, verified_by, idempotency_key, and verified_at.
Expected Output: Migration file, verification_records table created
Validation: Valid verification record creates; invalid action rejected; single-target violation rejected; short/missing remarks on reject/return rejected; duplicate idempotency_key rejected; FK constraints enforced; 16/16 pytest tests passing.
Acceptance Criteria: Verification records persistable with action constraint, single-target constraint, mandatory remarks constraint, and audit linkage
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-016B-DECISION
Status: [DONE]
Task: Add exception_flags JSONB column to attendance_records and daily_work_entries
Layer: Database
Requirement Reference: REQ-BR-005
Purpose: Store computed exception flags for supervisor attention (missing checkout, no photo, etc.)
Description: If not already present, ensure attendance_records and daily_work_entries have an exception_flags JSONB column (array of flag strings).
Implementation Details: In Phase 4, the architectural decision was made to compute exception flags dynamically on the fly via `compute_exception_flags` in `backend/app/modules/verification/service.py` to prevent state staleness between live attendance/work edits and denormalized columns. Attendance records retain the existing JSONB column from Phase 2, while dynamic computation covers the consolidated employee day.
Validation: Computed dynamically across all summary and detail endpoints.
Acceptance Criteria: Exception flag data is persistable or dynamically computable for supervisor review
Definition of Done: Flags computed dynamically and verified across 317 backend tests
```

## Backend Tasks

```
Task ID: BE-023
Status: [DONE]
Task: Create verification service (EOD summary, approve, reject, return)
Layer: Backend / Verification Module
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: Business logic for supervisor end-of-day verification workflow
Description: Implement modules/verification/service.py with:
  - get_eod_summary(supervisor_id, date, site_id)
  - get_employee_detail(supervisor_id, employee_id, date)
  - approve(supervisor_id, entity_type, entity_id, idempotency_key, remarks)
  - reject(supervisor_id, entity_type, entity_id, idempotency_key, remarks)
  - return_for_correction(supervisor_id, entity_type, entity_id, idempotency_key, remarks)
  - compute_exception_flags(...)
Dependencies: DB-016, BE-014 (attendance), BE-017 (daily work)
Implementation Details: Implemented in `backend/app/modules/verification/service.py`. Handles entity types 'attendance', 'daily_work', 'material'. Enforces status transitions, single-target verification records, immutable audit logs, supervisor hierarchy isolation, and admin/director reopen permissions.
Validation: 100% passing service tests in `tests/unit/test_verification_service.py`.
Acceptance Criteria: Supervisor can view, approve, reject, and return submitted work with full audit trail
Definition of Done: Service tests pass, business rules verified, >90% service coverage
```

```
Task ID: BE-024
Status: [DONE]
Task: Create verification API endpoints (VER-001 through VER-005)
Layer: Backend / API
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: REST endpoints for supervisor verification operations
Description: Implement api/v1/verification.py with 5 endpoints:
  - VER-001: GET /api/v1/verification/summary?date=&site_id= — EOD summary list
  - VER-002: GET /api/v1/verification/summary/{employee_id}?date= — Employee detail
  - VER-003: POST /api/v1/verification/{id}/approve — Approve entry
  - VER-004: POST /api/v1/verification/{id}/reject — Reject with remarks
  - VER-005: POST /api/v1/verification/{id}/return — Return for correction / reopen with remarks
Dependencies: BE-023
Implementation Details: Implemented in `backend/app/api/v1/verification.py`. Supports supervisor RBAC, Director/Admin global oversight, SEC-004-A unified-404 anti-enumeration on out-of-scope targets, idempotency keys, and nested audit history.
Validation: Integration tests in `tests/api/test_verification_api.py`.
Acceptance Criteria: Complete verification API functional with proper authorization
Definition of Done: API tests pass, Swagger verified, RBAC confirmed
```

```
Task ID: BE-025
Status: [DONE]
Task: Implement approved-record protection (read-only after approval)
Layer: Backend / Shared
Requirement Reference: REQ-BR-006
Purpose: Prevent modification of approved attendance records and work entries
Description: Add approval protection logic to attendance and daily work services.
Implementation Details: Enforced in service layer for attendance records, daily work entries, and material transactions. Modifications to records in 'approved' status reject with HTTP 409 Conflict. Reopening approved records requires Admin or Director role via VER-005 `POST /verification/{id}/return`.
Validation: Unit and API tests assert 409 Conflict when attempting updates on approved records.
Acceptance Criteria: Approved records are read-only; reopening requires authorisation and produces audit trail
Definition of Done: Protection verified across all update endpoints, audit trail confirmed
```

```
Task ID: BE-026
Status: [DONE]
Task: Add exception flag generation
Layer: Backend / Verification Module
Requirement Reference: REQ-BR-005
Purpose: Automatically compute and store exception flags for supervisor review
Description: Implement exception flag computation in the verification service. Flags to detect:
  - missing_checkout: attendance with check_in_time but no check_out_time by EOD
  - attendance_without_work: attendance record exists but no daily_work_entries
  - work_without_attendance: daily_work_entries exist but no attendance record
  - no_photograph: scoped strictly to submitted daily_work_entries with zero photos
  - out_of_location: attendance where is_within_geofence=false
  - high_value_material: material_transactions where is_high_value=true
Dependencies: BE-023, DB-016B
Implementation Details: Implemented in `compute_exception_flags` in `backend/app/modules/verification/service.py`. Refined so that `no_photograph` does not prematurely flag draft entries.
Validation: Unit tests in `tests/unit/test_verification_service.py` test all flag variations.
Acceptance Criteria: Supervisor sees relevant exception indicators when reviewing employee work
Definition of Done: All flag types tested, flags displayed in API response
```

## Swagger Tasks

```
Task ID: SWG-004
Status: [DONE]
Task: Execute Phase 4 Swagger test plan
Layer: Swagger
Requirement Reference: All Phase 4 requirements
Purpose: Manual API verification of all Phase 4 endpoints via Swagger UI
Description: Execute all test cases defined in swagger-test-plan.md for VER-001 through VER-005.
Implementation Details: Verified via OpenAPI docs at `/docs` and automated integration tests in `tests/api/test_verification_api.py`.
Validation: All endpoints return expected schemas and error codes across supervisor, admin, and employee roles.
Acceptance Criteria: All endpoints behave as specified in the backend API plan
Definition of Done: All test cases executed, results documented, no critical failures
```

## Frontend Tasks

```
Task ID: FE-016
Status: [DONE]
Task: Create verification queue page (EOD summary list)
Layer: Frontend
Requirement Reference: REQ-VER-001 to REQ-VER-004, REQ-UX-002
Purpose: Supervisor's end-of-day verification queue showing all employees with submitted work
Description: Build a verification queue page showing a list of employees who have submitted work for the selected date.
Implementation Details: Implemented in `frontend/src/pages/SupervisorVerificationQueuePage.tsx` with date picker, site filter, exception badges, work/photo/material counts, pending/reviewed state badges, and direct navigation to detail view.
Validation: Unit tests in `SupervisorVerificationQueuePage.test.tsx` and Playwright E2E tests.
Acceptance Criteria: Supervisor sees consolidated EOD summary with visual exception flagging
Definition of Done: Page works on mobile and desktop, exception badges correct, filters functional
```

```
Task ID: FE-017
Status: [DONE]
Task: Create verification detail page (employee day review)
Layer: Frontend
Requirement Reference: REQ-VER-001 to REQ-VER-004
Purpose: Detailed view of a single employee's day for supervisor verification
Description: Build a detail page showing the complete picture of an employee's work day: Attendance, Work Entries, Photos (with lightbox), Materials (with high-value warning), Action Buttons, and Audit History Timelines.
Implementation Details: Implemented in `frontend/src/pages/EmployeeDayVerificationPage.tsx`. Decouples attendance, individual daily work entries, and individual material line items.
Validation: Comprehensive unit tests in `EmployeeDayVerificationPage.test.tsx` and Playwright E2E tests.
Acceptance Criteria: Supervisor can review all aspects of an employee's day from a single page
Definition of Done: Detail page functional, responsive, all data sections populated, accessible
```

```
Task ID: FE-018
Status: [DONE]
Task: Create approve/reject/return action buttons with remarks modal
Layer: Frontend
Requirement Reference: REQ-VER-005 to REQ-VER-008
Purpose: Action buttons for supervisor verification decisions with mandatory remarks for reject/return
Description: Build action button group, confirmation modal, and mandatory remarks modal.
Implementation Details: Implemented `VerificationRemarksModal.tsx` enforcing >= 10 character mandatory remarks for rejection, return for correction, and admin reopening. Added high-value purchase warning confirmation dialog in `EmployeeDayVerificationPage.tsx`.
Validation: Unit tests in `VerificationRemarksModal.test.tsx` and Playwright E2E tests.
Acceptance Criteria: Supervisor can approve, reject, or return entries with appropriate workflow
Definition of Done: All three actions work, remarks validation enforced, status updates displayed
```

```
Task ID: FE-019
Status: [DONE]
Task: Create exception badge component
Layer: Frontend
Requirement Reference: REQ-BR-005
Purpose: Reusable visual component for displaying exception flags
Description: Build a reusable ExceptionBadge component that displays exception flags with colour-coded severity indicators.
Implementation Details: Implemented in `frontend/src/components/verification/ExceptionBadge.tsx` supporting flags `missing_checkout`, `attendance_without_work`, `no_photograph`, `out_of_location`, and `high_value_material`.
Validation: Unit tests in `ExceptionBadge.test.tsx`.
Acceptance Criteria: Exception flags visually communicated to supervisor
Definition of Done: Component renders all flag types correctly, responsive, accessible
```

```
Task ID: FE-020
Status: [DONE]
Task: Create audit history timeline component
Layer: Frontend
Requirement Reference: REQ-VER-009
Purpose: Visual timeline showing the complete change history of a verified record
Description: Build an audit history timeline component showing chronological list of all actions on a record.
Implementation Details: Implemented in `frontend/src/components/verification/AuditHistoryTimeline.tsx`. Displays sorted chronological events, action badges, actor names ("by {name}"), timestamps, and formatted remarks blockquotes.
Validation: Unit tests in `AuditHistoryTimeline.test.tsx` and Playwright E2E test assertion.
Acceptance Criteria: Complete change history visible for any verified record
Definition of Done: Timeline renders correctly, change details expandable, accessible
```

## Testing Tasks

```
Task ID: TEST-009
Status: [DONE]
Task: Database and service tests for verification
Layer: Testing
Requirement Reference: All Phase 4 requirements
Purpose: Unit and integration tests for verification database constraints and service business logic
Implementation Details: Implemented in `backend/tests/database/test_verification_records.py` (16 tests) and `backend/tests/unit/test_verification_service.py`. Enforces action CHECK, single-target CHECK, mandatory remarks CHECK, unique idempotency key, status transitions, and exception flags.
Validation: 317/317 backend pytest suite passing.
Acceptance Criteria: Every verification business rule has a corresponding test
Definition of Done: Tests pass, >90% coverage on verification service
```

```
Task ID: TEST-010
Status: [DONE]
Task: API integration tests for verification endpoints
Layer: Testing
Requirement Reference: All Phase 4 API requirements
Purpose: Integration tests for all 5 verification REST endpoints
Implementation Details: Implemented in `backend/tests/api/test_verification_api.py`. Covers VER-001 through VER-005, RBAC authorization, SEC-004-A anti-enumeration (unified 404), IDOR prevention, and admin reopen permissions.
Validation: 317/317 backend pytest suite passing.
Acceptance Criteria: Every API behaviour has integration test coverage
Definition of Done: All API tests pass, RBAC verified, audit trail confirmed
```

## E2E Tasks

```
Task ID: E2E-005
Status: [DONE]
Task: E2E tests for supervisor approve/reject/return journeys
Layer: E2E
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: End-to-end Playwright tests for the supervisor verification workflow
Description: Test complete lifecycle on mobile viewport (Pixel 5) against real backend and DB without mocking:
  1. Worker submits daily work entry with photo, normal material, and high-value material.
  2. Supervisor views queue with exception badges (`out_of_location`, `high_value_material`).
  3. Supervisor approves attendance, work entry, normal material, and confirms high-value warning modal before approving high-value material.
  4. Card updates to reviewed / nothing pending in queue.
  5. Administrator logs in, reopens approved work entry with mandatory remarks; audit history timeline shows chronological events with actor names.
  6. Supervisor rejects submitted work entry on Worker 2 with mandatory remarks; entry transitions to rejected and action buttons are excluded.
Implementation Details: Implemented in `frontend/e2e/supervisor_verification.spec.ts` with database seeder `backend/e2e_seed_verification.py`.
Validation: 3/3 tests passing in Playwright test runner.
Acceptance Criteria: Complete verification workflow tested end-to-end with multi-user interaction
Definition of Done: E2E tests pass reliably on mobile viewport, multi-user flow verified
```

## Security Tasks

```
Task ID: SEC-004
Status: [DONE]
Task: Security review of supervisor data isolation, audit trail, approved record protection
Layer: Security
Requirement Reference: REQ-VER-001 to REQ-VER-009, REQ-BR-006, REQ-SEC-001
Purpose: Security audit of Phase 4 data access controls and integrity protections
Implementation Details:
  - Enforced SEC-004-A: Unified 404 anti-enumeration for all out-of-scope employee detail and verification action targets.
  - Role hierarchy: Only Admin and Director can reopen approved records; supervisors receive 403 Forbidden.
  - Concurrent rapid idempotency key race condition protection verified with asyncio concurrency test.
  - Read-only protection on approved attendance, work entries, and materials verified.
Validation: 317 backend tests passing including explicit IDOR and concurrency suites.
Acceptance Criteria: Phase 4 passes security review with data isolation and audit integrity confirmed
Definition of Done: Audit complete, findings addressed, re-audit confirms no critical/high issues
```

## Documentation Tasks

```
Task ID: DOC-004
Status: [DONE]
Task: Update Phase 4 documentation after implementation
Layer: Documentation
Requirement Reference: All Phase 4 requirements
Purpose: Ensure Phase 4 documentation matches actual implementation
Description: Review and update all documents in `docs/04-supervisor-verification/*.md` to reflect the final database schema, dynamic exception flag architecture, unified-404 anti-enumeration security, multi-activity line-item verification granularity, test results, and backlog items.
Implementation Details: Synchronized `database-plan.md`, `backend-api-plan.md`, `security-plan.md`, `task-list.md`, `requirements.md`, `testing-plan.md`, `ui-ux-plan.md`, and `frontend-plan.md`.
Validation: Documentation accurately reflects the implemented system.
Acceptance Criteria: No documentation contradicts implementation
Definition of Done: All Phase 4 docs reviewed and updated
```

---

## Backlog Items & Technical Debt

| Item ID | Component | Description | Status |
|---------|-----------|-------------|--------|
| **FE-QUEUE-RACE** | Frontend / `SupervisorVerificationQueuePage` | Stale-response race condition in `SupervisorVerificationQueuePage.test.tsx` when date changes rapidly while prior requests are in-flight. Needs a monotonic request sequence counter or AbortController to discard stale responses. | Tracked in test suite |
| **ERR-CODE** | Backend / API | Standardization of machine-readable `code` error fields in JSON error payloads across verification endpoints to complement HTTP status codes. | Backlog |
| **BE-026B-FOLLOWUP** | Backend / Database | Evaluation of caching or materialized persistence for computed exception flags at massive scale (thousands of daily records). Currently computed dynamically per query to ensure real-time accuracy. | Backlog |
| **PERF-EXC-PHOTO** | Backend / Verification Service | Batch-fetch optimization for work photo counts when computing `no_photograph` exception flags across large batches of daily work entries to avoid N+1 query overhead. | Backlog |
| **OPT-BASE-MODAL** | Frontend / UI Components | Refactor `VerificationRemarksModal`, `ApprovalConfirmModal`, and general UI modals into a unified shared `Modal` primitive with standardized accessibility traps and backdrop styles. | Backlog |
| **DB-016B-DECISION** | Backend / Database | Addressed in implementation as dynamic computation of exception flags on attendance/work summaries rather than static column on `daily_work_entries`. Note: Distinct from Phase 3's `BE-016B` (S3 testing backlog item, which remains open). | Resolved by Design |

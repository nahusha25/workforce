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
Task ID: DB-016B
Task: Add exception_flags JSONB column to attendance_records and daily_work_entries
Layer: Database
Requirement Reference: REQ-BR-005
Purpose: Store computed exception flags for supervisor attention (missing checkout, no photo, etc.)
Description: If not already present, ensure attendance_records and daily_work_entries have an exception_flags JSONB column (array of flag strings). This was defined in the canonical ERD and should already exist on attendance_records. Verify daily_work_entries also supports flagging or handle at application level.
Dependencies: DB-009, DB-013
Implementation Details: Verify columns exist per canonical ERD. If missing on daily_work_entries, add via Alembic migration. Flags are computed server-side, not user-settable.
Expected Output: Exception flags column available on both tables (or application-level flagging confirmed)
Validation: Exception flags can be stored and queried
Acceptance Criteria: Exception flag data is persistable for supervisor review
Definition of Done: Column verified or migration created, tests pass
```

## Backend Tasks

```
Task ID: BE-023
Task: Create verification service (EOD summary, approve, reject, return)
Layer: Backend / Verification Module
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: Business logic for supervisor end-of-day verification workflow
Description: Implement modules/verification/service.py with:
  - get_eod_summary(supervisor_id, date, site_id): Aggregates attendance, work entries, photos, and materials for all assigned employees with submitted status.
  - get_employee_detail(supervisor_id, employee_id, date): Returns full detail view of a single employee's day — attendance record, all work entries with quantities, photos, materials.
  - approve(supervisor_id, entity_type, entity_id): Sets status to 'approved', creates verification_record, creates audit_log entry. Makes record read-only.
  - reject(supervisor_id, entity_type, entity_id, remarks): Validates remarks not empty. Sets status to 'rejected'. Creates verification_record with remarks. Creates audit_log.
  - return_for_correction(supervisor_id, entity_type, entity_id, remarks): Validates remarks not empty. Sets status to 'correction_required'. Employee can re-edit. Creates records.
  - compute_exception_flags(attendance_record): Computes flags like missing_checkout, no_work_submitted, no_photo, out_of_geofence, high_value_material.
Dependencies: DB-016, BE-014 (attendance), BE-017 (daily work)
Implementation Details: Supervisor data isolation — verify supervisor is assigned to the employee via employee.supervisor_id or site.supervisor_id. Status transitions enforced: only 'submitted' entries can be approved/rejected/returned. Approved records protected from further modification at service level. All actions logged to audit_logs.
Expected Output: Complete verification service with EOD aggregation and action processing
Validation: Data isolation enforced; status transitions valid; remarks mandatory for reject/return; audit entries created
Acceptance Criteria: Supervisor can view, approve, reject, and return submitted work with full audit trail
Definition of Done: Service tests pass, business rules verified, >90% service coverage
```

```
Task ID: BE-024
Task: Create verification API endpoints (VER-001 through VER-005)
Layer: Backend / API
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: REST endpoints for supervisor verification operations
Description: Implement api/v1/verification.py with 5 endpoints:
  - VER-001: GET /api/v1/verification/summary?date=&site_id= — EOD summary list
  - VER-002: GET /api/v1/verification/summary/{employee_id}?date= — Employee detail
  - VER-003: POST /api/v1/verification/{id}/approve — Approve entry
  - VER-004: POST /api/v1/verification/{id}/reject — Reject with remarks
  - VER-005: POST /api/v1/verification/{id}/return — Return for correction with remarks
Dependencies: BE-023
Implementation Details: Thin route handlers. Supervisor role required for all endpoints. Data isolation enforced through service layer. Request/response schemas via Pydantic. Consistent error responses.
Expected Output: 5 verification API endpoints with RBAC
Validation: All Swagger test cases pass; supervisor role enforced; data isolation confirmed
Acceptance Criteria: Complete verification API functional with proper authorization
Definition of Done: API tests pass, Swagger verified, RBAC confirmed
```

```
Task ID: BE-025
Task: Implement approved-record protection (read-only after approval)
Layer: Backend / Shared
Requirement Reference: REQ-BR-006
Purpose: Prevent modification of approved attendance records and work entries
Description: Add approval protection logic to attendance and daily work services. When an update is attempted on a record with status='approved': (1) If the request includes authorised reopening (admin/director role), require remarks, create audit trail, change status to 'correction_required'. (2) Otherwise, reject the update with 403/409.
Dependencies: BE-014, BE-017, BE-023
Implementation Details: Add status check to update methods in attendance and daily work services. Approved records return HTTP 409 Conflict with message "Record is approved and read-only." Authorised reopening creates a verification_record with action='correction_required' and full audit entry.
Expected Output: Approved records protected from modification across all services
Validation: Approved records reject updates; authorised reopening works with audit trail
Acceptance Criteria: Approved records are read-only; reopening requires authorisation and produces audit trail
Definition of Done: Protection verified across all update endpoints, audit trail confirmed
```

```
Task ID: BE-026
Task: Add exception flag generation
Layer: Backend / Verification Module
Requirement Reference: REQ-BR-005
Purpose: Automatically compute and store exception flags for supervisor review
Description: Implement exception flag computation in the verification service or as a shared utility. Flags to detect:
  - missing_checkout: attendance with check_in_time but no check_out_time by EOD
  - attendance_without_work: attendance record exists but no daily_work_entries
  - work_without_attendance: daily_work_entries exist but no attendance record (edge case)
  - no_photograph: daily_work_entries with zero work_photos
  - out_of_geofence: attendance where is_within_geofence=false (and no override)
  - high_value_material: material_transactions where is_high_value=true
Dependencies: BE-023, DB-016B
Implementation Details: Compute flags when generating EOD summary. Store computed flags in exception_flags JSONB column. Flags are informational for supervisor — they do not block submission. Include flag descriptions in the EOD summary API response.
Expected Output: Exception flag computation integrated into verification summary
Validation: Each flag type triggers correctly based on test data; flags appear in summary API response
Acceptance Criteria: Supervisor sees relevant exception indicators when reviewing employee work
Definition of Done: All 6 flag types tested, flags displayed in API response
```

## Swagger Tasks

```
Task ID: SWG-004
Task: Execute Phase 4 Swagger test plan
Layer: Swagger
Requirement Reference: All Phase 4 requirements
Purpose: Manual API verification of all Phase 4 endpoints via Swagger UI
Description: Execute all test cases defined in swagger-test-plan.md for VER-001 through VER-005. Test each endpoint with valid and invalid inputs, correct and incorrect roles, edge cases.
Dependencies: BE-024, BE-025, BE-026
Implementation Details: Use Swagger UI at /api/docs. For each test case: send request, verify status code, verify response body, verify side effects (status changes, audit entries).
Expected Output: All Swagger test cases executed and passing
Validation: Every test case in the swagger test plan has a recorded result
Acceptance Criteria: All endpoints behave as specified in the backend API plan
Definition of Done: All test cases executed, results documented, no critical failures
```

## Frontend Tasks

```
Task ID: FE-016
Task: Create verification queue page (EOD summary list)
Layer: Frontend
Requirement Reference: REQ-VER-001 to REQ-VER-004, REQ-UX-002
Purpose: Supervisor's end-of-day verification queue showing all employees with submitted work
Description: Build a verification queue page showing a list of employees who have submitted work for the selected date. Each row shows: employee name, check-in/out times, work entry count, photo count, material count, total material cost, exception flags (visual indicators). Date picker to select day. Site filter. Rows are colour-coded or badged by exception status.
Dependencies: FE-002 (app shell), BE-024 (verification APIs)
Implementation Details: Card-based layout on mobile, table on desktop. Exception badges (red for critical, amber for warning). Tap/click a row to drill into employee detail. Default to today's date. Auto-refresh or pull-to-refresh.
Expected Output: Working verification queue page with exception indicators
Validation: Queue shows correct employees; exception flags visible; date/site filters work; responsive
Acceptance Criteria: Supervisor sees consolidated EOD summary with visual exception flagging
Definition of Done: Page works on mobile and desktop, exception badges correct, filters functional
```

```
Task ID: FE-017
Task: Create verification detail page (employee day review)
Layer: Frontend
Requirement Reference: REQ-VER-001 to REQ-VER-004
Purpose: Detailed view of a single employee's day for supervisor verification
Description: Build a detail page showing the complete picture of an employee's work day: (1) Attendance section — check-in/out times, GPS location, geo-fence status, working hours. (2) Work entries section — activity type, all quantities, status. (3) Photos section — photo gallery with thumbnails, tap to enlarge. (4) Materials section — item list with quantities, amounts, bill images, high-value indicators. (5) Action buttons (approve/reject/return) at bottom.
Dependencies: FE-016, BE-024
Implementation Details: Collapsible sections for each data category. Photo gallery with lightbox zoom. Material list with high-value highlighting. Sticky action bar at bottom on mobile. Data loaded from VER-002 endpoint.
Expected Output: Complete employee day detail view with all data categories
Validation: All data sections display correctly; photos viewable; materials listed; action buttons accessible
Acceptance Criteria: Supervisor can review all aspects of an employee's day from a single page
Definition of Done: Detail page functional, responsive, all data sections populated, accessible
```

```
Task ID: FE-018
Task: Create approve/reject/return action buttons with remarks modal
Layer: Frontend
Requirement Reference: REQ-VER-005 to REQ-VER-008
Purpose: Action buttons for supervisor verification decisions with mandatory remarks for reject/return
Description: Build action button group and remarks modal: (1) Approve button — green, no remarks required (optional). Confirmation dialog before action. (2) Reject button — red, opens modal requiring remarks text. (3) Return for Correction button — amber, opens modal requiring remarks text. After action, show success notification, update record status in UI, disable further actions.
Dependencies: FE-017
Implementation Details: Button group at bottom of detail page (sticky on mobile). Remarks modal with textarea (min 10 characters for reject/return). Loading state during API call. Success/error toast notification. Optimistic UI update on success.
Expected Output: Action buttons with confirmation/remarks flow
Validation: Approve works without remarks; reject/return require remarks; status updates in UI; loading states work
Acceptance Criteria: Supervisor can approve, reject, or return entries with appropriate workflow
Definition of Done: All three actions work, remarks validation enforced, status updates displayed
```

```
Task ID: FE-019
Task: Create exception badge component
Layer: Frontend
Requirement Reference: REQ-BR-005
Purpose: Reusable visual component for displaying exception flags
Description: Build a reusable ExceptionBadge component that displays exception flags with colour-coded severity indicators. Flags: missing_checkout (red), attendance_without_work (amber), no_photograph (amber), out_of_geofence (red), high_value_material (amber). Badge shows count and expands to show details on tap.
Dependencies: FE-001 (design system)
Implementation Details: Compact badge with count for queue view. Expandable detail for verification detail page. Colour coding: red for critical, amber for warning. Icon per flag type. Tooltip on desktop, expandable on mobile.
Expected Output: Reusable exception badge component
Validation: Correct colours for each flag type; expandable detail works; responsive
Acceptance Criteria: Exception flags visually communicated to supervisor
Definition of Done: Component renders all flag types correctly, responsive, accessible
```

```
Task ID: FE-020
Task: Create audit history timeline component
Layer: Frontend
Requirement Reference: REQ-VER-009
Purpose: Visual timeline showing the complete change history of a verified record
Description: Build an audit history timeline component showing chronological list of all actions on a record: creation, edits, submission, verification actions, reopening. Each entry shows: timestamp, actor (who), action (what), old/new values for changes, remarks.
Dependencies: FE-001 (design system), audit_logs API
Implementation Details: Vertical timeline layout. Colour-coded by action type. Expandable change details showing before/after values (from JSONB). Read from audit_logs API filtered by entity type and ID. Pagination for long histories.
Expected Output: Audit history timeline component
Validation: Timeline shows correct chronological order; change details accurate; actor names displayed
Acceptance Criteria: Complete change history visible for any verified record
Definition of Done: Timeline renders correctly, change details expandable, accessible
```

## Testing Tasks

```
Task ID: TEST-009
Task: Database and service tests for verification
Layer: Testing
Requirement Reference: All Phase 4 requirements
Purpose: Unit and integration tests for verification database constraints and service business logic
Description: Test: (1) verification_records — action CHECK constraint, FK constraints, remarks storage. (2) Verification service — EOD summary aggregation returns correct data, approve changes status to 'approved', reject requires remarks and changes status, return changes status to 'correction_required', data isolation (supervisor sees only assigned), approved record protection, exception flag computation. (3) Audit trail — approve/reject/return all create audit_log entries with correct data.
Dependencies: DB-016, BE-023, BE-025, BE-026
Implementation Details: pytest with database fixtures. Mock data for multiple employees, sites, attendance, work entries, materials. Test edge cases: empty summary, all approved, mixed statuses.
Expected Output: Comprehensive test suite for verification database and service
Validation: All business rules verified; data isolation confirmed; audit entries verified
Acceptance Criteria: Every verification business rule has a corresponding test
Definition of Done: Tests pass, >90% coverage on verification service
```

```
Task ID: TEST-010
Task: API integration tests for verification endpoints
Layer: Testing
Requirement Reference: All Phase 4 API requirements
Purpose: Integration tests for all 5 verification REST endpoints
Description: Test all endpoints VER-001 through VER-005 with: (1) Valid supervisor request — correct response data. (2) Non-supervisor role — 403. (3) Supervisor accessing non-assigned employees — 403 or empty result. (4) Approve — status changes, verification_record created. (5) Reject without remarks — 422. (6) Reject with remarks — success. (7) Return without remarks — 422. (8) Return with remarks — success. (9) Already approved record — 409 on approve again. (10) Audit log entries created.
Dependencies: BE-024
Implementation Details: pytest with httpx AsyncClient. Authenticated requests with different roles. Verify response codes, bodies, and database side effects.
Expected Output: API integration test suite for all verification endpoints
Validation: All endpoints return correct status codes; RBAC enforced; side effects verified
Acceptance Criteria: Every API behaviour has integration test coverage
Definition of Done: All API tests pass, RBAC verified, audit trail confirmed
```

## E2E Tasks

```
Task ID: E2E-005
Task: E2E tests for supervisor approve/reject/return journeys
Layer: E2E
Requirement Reference: REQ-VER-001 to REQ-VER-009
Purpose: End-to-end Playwright tests for the supervisor verification workflow
Description: Test journeys: (1) Supervisor opens verification queue → sees employees with submitted work → taps employee → sees detail → approves → status changes to approved. (2) Supervisor rejects with remarks → employee sees rejected status. (3) Supervisor returns for correction → employee can re-edit → re-submit → supervisor sees again. (4) Exception flags visible in queue and detail view. (5) Approved record is read-only. (6) Cross-phase: employee submits work → supervisor approves → data appears in dashboard (Phase 5 prep).
Dependencies: All Phase 4 implementation, E2E-004 (Phase 3 — data to verify)
Implementation Details: Playwright with both mobile and tablet viewports (supervisor may use tablet). Multi-user test: create employee test data, submit work, then switch to supervisor. Verify status transitions across users. Screenshot on failure.
Expected Output: E2E test files covering supervisor verification journeys
Validation: All journeys pass; status transitions verified across users; exception flags visible
Acceptance Criteria: Complete verification workflow tested end-to-end with multi-user interaction
Definition of Done: E2E tests pass reliably, multi-user flow verified, screenshots captured
```

## Security Tasks

```
Task ID: SEC-004
Task: Security review of supervisor data isolation, audit trail, approved record protection
Layer: Security
Requirement Reference: REQ-VER-001 to REQ-VER-009, REQ-BR-006, REQ-SEC-001
Purpose: Security audit of Phase 4 data access controls and integrity protections
Description: Audit: (1) Data isolation — supervisor can ONLY access data for their assigned employees, enforced server-side not just UI. Test by attempting to access non-assigned employee data. (2) Role enforcement — all verification endpoints require supervisor role. Test with employee and director tokens. (3) Approved record protection — approved records cannot be modified via any API (attendance update, work update, direct DB). Test update attempts on approved records. (4) Audit trail integrity — audit_log entries are immutable (append-only, no UPDATE or DELETE). Verify no endpoint allows audit modification. (5) Remarks injection — remarks text is properly sanitised (no XSS if rendered in UI, no SQL injection). (6) Status transition enforcement — only valid transitions allowed (submitted→approved, not draft→approved).
Dependencies: All Phase 4 implementation
Implementation Details: Follow security audit workflow (.ai/workflows/security-audit.md). Report findings before remediation.
Expected Output: Security audit report with findings categorised by severity
Validation: No critical or high-severity findings remain after remediation
Acceptance Criteria: Phase 4 passes security review with data isolation and audit integrity confirmed
Definition of Done: Audit complete, findings addressed, re-audit confirms no critical/high issues
```

## Documentation Tasks

```
Task ID: DOC-004
Task: Update Phase 4 documentation after implementation
Layer: Documentation
Requirement Reference: All Phase 4 requirements
Purpose: Ensure Phase 4 documentation matches actual implementation
Description: Review and update: requirements.md, implementation-plan.md, database-plan.md, backend-api-plan.md, swagger-test-plan.md, frontend-plan.md, ui-ux-plan.md, security-plan.md, testing-plan.md. Add any implementation details discovered during development. Document exception flag types and their trigger conditions.
Dependencies: All Phase 4 tasks complete
Implementation Details: Cross-reference implemented code with documentation. Update API contracts if changed. Document exception flag behaviour. Update task-list.md statuses.
Expected Output: Updated Phase 4 documentation matching implementation
Validation: Documentation accurately reflects the implemented system
Acceptance Criteria: No documentation contradicts implementation
Definition of Done: All Phase 4 docs reviewed and updated
```

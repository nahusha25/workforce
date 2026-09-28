# Phase 2 — Daily Attendance — Task List

## Database Tasks

```
Task ID: DB-009
Task: Create attendance_records table
Layer: Database
Requirement Reference: REQ-ATT-001 to REQ-ATT-009
Purpose: Persist daily attendance with GPS, geo-fence, and override data
Description: Create attendance_records with all columns, constraints, and indexes as defined in database-plan.md.
Dependencies: DB-007 (employees), DB-006 (sites), DB-001 (users for override_by)
Implementation Details: Alembic migration with UNIQUE(employee_id, date), CHECK constraints, FK constraints, indexes.
Expected Output: Migration file, attendance_records table
Validation: Valid record creates; duplicate rejected; invalid times rejected
Acceptance Criteria: Attendance table with all constraints enforced
Definition of Done: Migration exists, constraints verified, tests pass
```

## Backend Tasks

```
Task ID: BE-013
Task: Create geo-fence distance calculation utility
Layer: Backend / Shared
Requirement Reference: REQ-ATT-007
Purpose: Calculate distance between two GPS coordinates for geo-fence validation
Description: Implement shared/geo.py with haversine formula.
Dependencies: None
Implementation Details: Haversine formula returning distance in metres.
Expected Output: is_within_geofence(lat1, lng1, lat2, lng2, radius_metres) → bool
Validation: Known GPS coordinates return correct distances
Acceptance Criteria: Geo-fence calculation accurate to within 10 metres
Definition of Done: Unit tests with known coordinates pass
```

```
Task ID: BE-014
Task: Create attendance service
Layer: Backend / Attendance Module
Requirement Reference: REQ-ATT-001 to REQ-ATT-009
Purpose: Check-in, check-out, override, list attendance with business rules
Description: Implement attendance/service.py with check_in, check_out, override_geofence, list_attendance.
Dependencies: BE-013, DB-009, BE-006
Implementation Details: Validate site assignment, generate server timestamps, calculate geo-fence, generate exception flags.
Expected Output: Working attendance service with all business rules
Validation: All business rules enforced
Acceptance Criteria: Full attendance lifecycle managed
Definition of Done: Service tests pass, business rules verified
```

```
Task ID: BE-015
Task: Create attendance API endpoints
Layer: Backend / API
Requirement Reference: REQ-ATT-001 to REQ-ATT-009
Purpose: REST endpoints for attendance operations
Description: Implement api/v1/attendance.py with check-in, check-out, list, get, override.
Dependencies: BE-014, BE-006
Implementation Details: Thin route handlers with role-based authorization.
Expected Output: 5 attendance endpoints
Validation: All Swagger tests pass
Acceptance Criteria: Attendance API functional with RBAC
Definition of Done: API tests pass, Swagger verified
```

## Swagger Tasks

```
Task ID: SWG-002
Task: Execute Phase 2 Swagger test plan
Layer: Swagger
Requirement Reference: All Phase 2 requirements
Purpose: Manual API verification
Dependencies: BE-015
Expected Output: All test cases pass
Definition of Done: All cases executed and passing
```

## Frontend Tasks

```
Task ID: FE-008
Task: Create useGeolocation hook
Layer: Frontend
Requirement Reference: REQ-ATT-006
Purpose: Browser Geolocation API wrapper with error handling
Description: Hook that requests GPS, handles permissions, provides coordinates and status.
Dependencies: FE-001
Expected Output: useGeolocation hook returning { latitude, longitude, status, error }
Validation: GPS acquired on permission grant; error on deny
Definition of Done: Hook works on mobile browsers
```

```
Task ID: FE-009
Task: Create attendance page
Layer: Frontend
Requirement Reference: REQ-ATT-001, REQ-ATT-002
Purpose: One-touch check-in/out experience
Description: Build mobile-first attendance page with large buttons, GPS indicator, auto-filled context.
Dependencies: FE-002, FE-008
Expected Output: Working attendance page
Validation: Check-in/out works; GPS captured; responsive
Acceptance Criteria: Employee can check in/out with one touch on mobile
Definition of Done: Page works, responsive, accessible, tested
```

## Testing Tasks

```
Task ID: TEST-004
Task: Write attendance database and service tests
Layer: Testing
Requirement Reference: All Phase 2 requirements
Dependencies: DB-009, BE-013, BE-014
Expected Output: Test suite for geo-fence calculation, attendance service, DB constraints
Definition of Done: Tests pass with >90% coverage on service
```

```
Task ID: TEST-005
Task: Write attendance API integration tests
Layer: Testing
Dependencies: BE-015
Expected Output: API test suite for all attendance endpoints
Definition of Done: All endpoint behaviours tested
```

## E2E Tasks

```
Task ID: E2E-003
Task: Write daily attendance E2E tests
Layer: E2E
Requirement Reference: REQ-ATT-001 to REQ-ATT-009
Description: Playwright tests for check-in with GPS, geo-fence validation, check-out, supervisor override.
Dependencies: All Phase 2 implementation
Expected Output: E2E test files for journeys E2E-J03, E2E-J04, E2E-J05
Definition of Done: E2E tests pass on mobile viewport
```

## Security Tasks

```
Task ID: SEC-002
Task: Security review of Phase 2 attendance
Layer: Security
Dependencies: All Phase 2 implementation
Description: Audit GPS handling, timestamp immutability, site assignment enforcement, data isolation.
Definition of Done: Audit complete, no critical/high findings
```

## Documentation Tasks

```
Task ID: DOC-002
Task: Update Phase 2 documentation after implementation
Layer: Documentation
Dependencies: All Phase 2 tasks
Definition of Done: Docs match implementation
```

# Phase 2 — Daily Attendance — Backend API Plan

> All APIs use the `/api/v1` prefix. See [`docs/00-phase-0/api-development-standard.md`](../00-phase-0/api-development-standard.md) for conventions.

---

## ATT-001: Check-In

```
API ID: ATT-001
Endpoint: POST /api/v1/attendance/check-in
HTTP Method: POST
Purpose: Record employee check-in with GPS location and geo-fence validation
Requirement Reference: REQ-ATT-001, REQ-ATT-003 to REQ-ATT-007

Request:
{
  "latitude": 12.9716,
  "longitude": 77.5946
}

Response (201 Created):
{
  "status": "success",
  "record_id": "uuid"
}

Validation:
  - latitude: required, numeric, -90 to 90
  - longitude: required, numeric, -180 to 180

Business Rules:
  - Employee identity derived from auth token (REQ-ATT-003)
  - Employee must have an active site assignment (REQ-BR-001)
  - No existing check-in for today for this employee (UNIQUE constraint)
  - Server generates check_in_time (REQ-ATT-004, REQ-BR-002)
  - Site auto-assigned from employee_site_assignments (REQ-ATT-005)
  - Geo-fence calculated: haversine(employee GPS, site GPS) vs permitted_radius
  - If outside geo-fence → reject with 422 (unless supervisor override follows)

Authentication: Required (JWT Bearer token)
Authorization: Employee role

Database Interaction:
  - Read: employee_site_assignments (active assignment), sites (GPS + radius)
  - Write: INSERT attendance_records
  - Write: INSERT audit_logs

Error Cases:
  - 401: No authentication token
  - 403: Not employee role / no active site assignment
  - 409: Already checked in today (duplicate)
  - 422: Missing GPS coordinates / geo-fence violation / validation error

Swagger Test Cases:
  1. Valid check-in within geo-fence → 201, is_within_geofence=true
  2. Check-in outside geo-fence → 422 geo-fence violation
  3. Duplicate check-in same day → 409
  4. Missing latitude → 422 validation
  5. Missing longitude → 422 validation
  6. Employee not assigned to any site → 403
  7. No auth token → 401
  8. Non-employee role → 403
  9. Latitude out of range (-91) → 422
```

---

## ATT-002: Check-Out

```
API ID: ATT-002
Endpoint: POST /api/v1/attendance/check-out
HTTP Method: POST
Purpose: Record employee check-out with GPS, calculate working hours
Requirement Reference: REQ-ATT-002, REQ-BR-003

Request:
{
  "latitude": 12.9716,
  "longitude": 77.5946
}

Response (200 OK):
{
  "status": "success",
  "record_id": "uuid"
}

Validation:
  - latitude: required, numeric, -90 to 90
  - longitude: required, numeric, -180 to 180

Business Rules:
  - Must have active check-in today (check_in_time exists, check_out_time IS NULL)
  - Server generates check_out_time (REQ-BR-002)
  - Calculate working_hours = (check_out_time - check_in_time) in decimal hours
  - Calculate overtime_hours = max(0, working_hours - standard_hours_threshold)
  - REQ-BR-003: Check if daily work entries exist for this attendance. If unsubmitted work exists (status='draft'), include work_submission_warning in response
  - Allow checkout even with warning (business decision pending: warn vs block)

Authentication: Required
Authorization: Employee role (own record only)

Database Interaction:
  - Read: attendance_records (today's active check-in)
  - Read: daily_work_entries (check submission status for REQ-BR-003)
  - Write: UPDATE attendance_records (set check_out fields, working_hours)
  - Write: INSERT audit_logs

Error Cases:
  - 401: No auth
  - 404: No active check-in today
  - 409: Already checked out

Swagger Test Cases:
  1. Valid check-out → 200, working_hours calculated
  2. No active check-in → 404
  3. Already checked out → 409
  4. Check-out with unsubmitted work → 200 with warning
  5. No auth → 401
```

---

## ATT-003: List Attendance

```
API ID: ATT-003
Endpoint: GET /api/v1/attendance
HTTP Method: GET
Purpose: List attendance records with filtering and pagination
Requirement Reference: REQ-ATT-001 to REQ-ATT-009

Query Parameters:
  - date_from: DATE (optional)
  - date_to: DATE (optional)
  - employee_id: UUID (optional, supervisor/director only)
  - site_id: UUID (optional)
  - status: string (optional)
  - page: integer (default 1)
  - page_size: integer (default 20, max 100)

Response (200 OK):
{
  "items": [
    {
      "id": "uuid",
      "employee_id": "uuid",
      "employee_name": "string",
      "site_id": "uuid",
      "site_name": "string",
      "date": "2025-08-11",
      "check_in_time": "timestamp",
      "check_out_time": "timestamp",
      "working_hours": 8.0,
      "is_within_geofence": true,
      "status": "approved",
      "exception_flags": ["no_photograph"]
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}

Authorization:
  - Employee: sees own records only (employee_id filter auto-applied)
  - Supervisor: sees records for assigned employees
  - Director: sees all records
  - Administrator: sees all records

Database Interaction:
  - Read: attendance_records with JOINs to employees, sites
  - Filtered by role-based data isolation

Error Cases:
  - 401: No auth
  - 422: Invalid date format / invalid page

Swagger Test Cases:
  1. Employee sees own records → 200, own data only
  2. Supervisor sees assigned employees → 200, assigned only
  3. Director sees all → 200, all records
  4. Date range filter → 200, filtered
  5. Status filter → 200, filtered
  6. Pagination → 200, correct page/total
  7. No auth → 401
```

---

## ATT-004: Get Attendance Detail

```
API ID: ATT-004
Endpoint: GET /api/v1/attendance/{id}
HTTP Method: GET
Purpose: Retrieve full attendance record detail
Requirement Reference: REQ-ATT-001 to REQ-ATT-009

Path Parameters:
  - id: UUID (attendance record ID)

Response (200 OK):
{
  "id": "uuid",
  "employee_id": "uuid",
  "site_id": "uuid",
  "date": "2025-08-11",
  "session_number": 1,
  "check_in_time": "timestamp",
  "check_out_time": "timestamp",
  "check_in_latitude": 12.9716,
  "check_in_longitude": 77.5946,
  "check_in_distance_m": 15.2,
  "check_out_latitude": 12.9716,
  "check_out_longitude": 77.5946,
  "check_out_distance_m": 15.2,
  "is_within_geofence": true,
  "working_hours": 8.5,
  "overtime_hours": 0.5,
  "override_by": null,
  "status": "draft"
}

Authorization: Own record, supervisor of employee (assigned directly or via site), director, admin

Error Cases:
  - 401: No auth
  - 403: Not authorised to view this record
  - 404: Record not found

Swagger Test Cases:
  1. Employee views own record → 200
  2. Supervisor views assigned employee → 200
  3. Employee views someone else's → 403
  4. Non-existent ID → 404
```

---

## ATT-005: Supervisor Override

```
API ID: ATT-005
Endpoint: POST /api/v1/attendance/{id}/override
HTTP Method: POST
Purpose: Allow supervisor to override geo-fence violation for an attendance record
Requirement Reference: REQ-ATT-008, REQ-ATT-009

Path Parameters:
  - id: UUID (attendance record ID)

Request:
{
  "override_reason": "Employee at adjacent building within client campus"
}

Response (200 OK):
{
  "status": "success",
  "record_id": "uuid"
}

Validation:
  - override_reason: required, string, min 10 characters, max 500 characters

Business Rules:
  - Supervisor role required
  - Supervisor must be assigned to the employee (employee.supervisor_id or site.supervisor_id)
  - Override reason is mandatory (REQ-ATT-009)
  - Records the supervisor's user ID as override_by

Authentication: Required
Authorization: Supervisor role + assigned to employee

Database Interaction:
  - Read: attendance_records, employees (verify assignment)
  - Write: UPDATE attendance_records (override_by, override_reason)
  - Write: INSERT audit_logs

Error Cases:
  - 401: No auth
  - 403: Not supervisor role / not assigned to this employee
  - 404: Attendance record not found
  - 422: Missing or too short reason

Swagger Test Cases:
  1. Valid override with reason → 200, override recorded
  2. Missing reason → 422
  3. Reason too short (<10 chars) → 422
  4. Employee tries override → 403
  5. Supervisor not assigned to this employee → 403
  6. Non-existent record → 404
```

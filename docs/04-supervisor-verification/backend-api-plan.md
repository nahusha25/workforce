# Phase 4 — Supervisor Verification — Backend API Plan

> All APIs use the `/api/v1` prefix. See [`docs/00-phase-0/api-development-standard.md`](../00-phase-0/api-development-standard.md) for conventions.

---

## VER-001: EOD Verification Summary

```
API ID: VER-001
Endpoint: GET /api/v1/verification/summary
HTTP Method: GET
Purpose: Retrieve list of employees with submitted work for supervisor verification
Requirement Reference: REQ-VER-001 to REQ-VER-004

Query Parameters:
  - date: DATE (required, e.g., 2025-08-11)
  - site_id: UUID (optional)

Response (200 OK):
{
  "items": [
    {
      "employee_id": "uuid",
      "employee_name": "string",
      "site_id": "uuid",
      "site_name": "string",
      "attendance_status": "submitted",
      "work_entry_count": 3,
      "photo_count": 5,
      "material_count": 2,
      "total_material_cost": 5000.00,
      "exception_flags": ["missing_checkout", "high_value_material"]
    }
  ]
}

Business Rules:
  - Supervisor sees only assigned employees (employee.supervisor_id or site.supervisor_id matches)
  - Exception flags computed and returned for quick scanning

Auth: Supervisor role
Error Cases: 401, 403, 422
```

---

## VER-002: Employee Detail for Verification

```
API ID: VER-002
Endpoint: GET /api/v1/verification/summary/{employee_id}
HTTP Method: GET
Purpose: Retrieve full detail of an employee's day for verification
Requirement Reference: REQ-VER-001 to REQ-VER-004

Query Parameters:
  - date: DATE (required)

Response (200 OK):
{
  "employee_id": "uuid",
  "employee_name": "string",
  "attendance": {
    "id": "uuid",
    "check_in_time": "timestamp",
    "check_out_time": "timestamp",
    "working_hours": 8.5,
    "status": "submitted",
    "exception_flags": []
  },
  "work_entries": [
    {
      "id": "uuid",
      "activity_name": "Cable Laying",
      "quantities": { "cable_runs": 5, "cable_length_metres": 120.5 },
      "status": "submitted",
      "photos": [ { "thumbnail_url": "url", "image_url": "url" } ],
      "materials": [ { "item_name": "Cable", "amount": 1000, "is_high_value": false } ]
    }
  ]
}

Business Rules:
  - Combines attendance, work entries, photos, and materials into a single comprehensive view.
  - Same data isolation as VER-001.

Auth: Supervisor role
Error Cases: 401, 403, 404
```

---

## VER-003: Approve

```
API ID: VER-003
Endpoint: POST /api/v1/verification/{id}/approve
HTTP Method: POST
Purpose: Approve an attendance record or daily work entry
Requirement Reference: REQ-VER-005, REQ-BR-006

Request:
{
  "entity_type": "attendance|daily_work",
  "remarks": "optional text"
}

Response (200 OK):
{
  "id": "uuid",
  "status": "approved",
  "verification_record_id": "uuid"
}

Business Rules:
  - Target record must be in 'submitted' status.
  - Updates target record status to 'approved'.
  - Creates verification_records entry.
  - Creates audit_logs entry.
  - Approved records become read-only (enforced globally).

Auth: Supervisor role (must be assigned to employee)
Error Cases: 401, 403 (unassigned/wrong role), 404, 409 (not in 'submitted' status), 422
```

---

## VER-004: Reject

```
API ID: VER-004
Endpoint: POST /api/v1/verification/{id}/reject
HTTP Method: POST
Purpose: Reject an attendance record or daily work entry
Requirement Reference: REQ-VER-006, REQ-VER-008

Request:
{
  "entity_type": "attendance|daily_work",
  "remarks": "Reject reason text"
}

Response (200 OK):
{
  "id": "uuid",
  "status": "rejected",
  "verification_record_id": "uuid"
}

Business Rules:
  - Target record must be in 'submitted' status.
  - remarks field is MANDATORY (min 10 chars).
  - Updates target status to 'rejected'.
  - Creates verification_records and audit_logs entries.

Auth: Supervisor role (must be assigned to employee)
Error Cases: 401, 403, 404, 409, 422 (missing/short remarks)
```

---

## VER-005: Return for Correction

```
API ID: VER-005
Endpoint: POST /api/v1/verification/{id}/return
HTTP Method: POST
Purpose: Return an attendance record or daily work entry for correction
Requirement Reference: REQ-VER-007, REQ-VER-008

Request:
{
  "entity_type": "attendance|daily_work",
  "remarks": "Correction instructions text"
}

Response (200 OK):
{
  "id": "uuid",
  "status": "correction_required",
  "verification_record_id": "uuid"
}

Business Rules:
  - Target record must be in 'submitted' status (or 'approved' for authorised reopen).
  - remarks field is MANDATORY (min 10 chars).
  - Updates target status to 'correction_required'.
  - Creates verification_records and audit_logs entries.

Auth: Supervisor role (must be assigned to employee)
Error Cases: 401, 403, 404, 409, 422 (missing/short remarks)
```

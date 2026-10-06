# Phase 4 — Supervisor Verification — Backend API Plan

> All APIs use the `/api/v1` prefix. See [`docs/00-phase-0/api-development-standard.md`](../00-phase-0/api-development-standard.md) for conventions.

---

## VER-001: EOD Verification Summary

```
API ID: VER-001
Endpoint: GET /api/v1/verification/summary
HTTP Method: GET
Purpose: Retrieve list of employees with attendance and work for supervisor verification
Requirement Reference: REQ-VER-001 to REQ-VER-004

Query Parameters:
  - date: DATE (required, YYYY-MM-DD)
  - site_id: UUID (optional)

Response (200 OK):
{
  "date": "2026-09-29",
  "site_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": [
    {
      "employee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "employee_name": "Rajesh Kumar",
      "employee_code": "EMP-001",
      "site_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "site_name": "Site Alpha",
      "attendance_record_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "attendance_status": "submitted",
      "check_in_time": "2026-09-29T08:15:00Z",
      "check_out_time": "2026-09-29T17:30:00Z",
      "working_hours": 9.25,
      "work_entry_count": 2,
      "photo_count": 3,
      "material_count": 2,
      "total_material_cost": 4650.00,
      "exception_flags": ["out_of_location", "high_value_material"],
      "has_pending_verification": true
    }
  ],
  "total_employees": 1,
  "pending_verification_count": 1
}

Business Rules:
  - Supervisor sees only assigned employees (employee.supervisor_id or site assignment). Directors and Admins see all.
  - Exception flags dynamically computed per employee day (out_of_location, missing_checkout, no_photograph, high_value_material, attendance_without_work).
  - has_pending_verification is true if attendance or any work entry or material is in 'submitted' status.

Auth: Supervisor, Director, Admin roles
Error Cases: 401 (unauthenticated), 403 (unauthorized role e.g. employee), 422 (validation error)
```

---

## VER-002: Employee Detail for Verification

```
API ID: VER-002
Endpoint: GET /api/v1/verification/summary/{employee_id}
HTTP Method: GET
Purpose: Retrieve full day details of an employee for verification
Requirement Reference: REQ-VER-001 to REQ-VER-004

Path Parameters:
  - employee_id: UUID (required)

Query Parameters:
  - date: DATE (required, YYYY-MM-DD)

Response (200 OK):
{
  "employee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_name": "Rajesh Kumar",
  "employee_code": "EMP-001",
  "date": "2026-09-29",
  "site_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "site_name": "Site Alpha",
  "attendance": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "date": "2026-09-29",
    "session_number": 1,
    "check_in_time": "2026-09-29T08:15:00Z",
    "check_in_distance_m": 12.5,
    "check_out_time": "2026-09-29T17:30:00Z",
    "check_out_distance_m": 14.2,
    "is_within_geofence": false,
    "working_hours": 9.25,
    "overtime_hours": 1.25,
    "status": "submitted",
    "override_by": null,
    "verification_record_id": null,
    "verification_action": null,
    "verification_remarks": null,
    "history": [
      {
        "id": "uuid",
        "action": "approved",
        "remarks": null,
        "verified_by": "uuid",
        "verified_by_name": "E2E Supervisor",
        "verified_at": "2026-09-29T17:30:00Z"
      }
    ]
  },
  "work_entries": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "idempotency_key": "dwe-idemp-1",
      "activity_id": "uuid",
      "activity_name": "Cable Pulling & Laying",
      "activity_category": "Electrical",
      "work_order_id": "uuid",
      "work_order_number": "WO-2026-001",
      "work_date": "2026-09-29",
      "quantity": 120.5,
      "uom": "meters",
      "status": "submitted",
      "remarks": "Standard run completed",
      "verification_record_id": null,
      "verification_action": null,
      "verification_remarks": null,
      "history": [],
      "photos": [
        {
          "id": "uuid",
          "daily_work_entry_id": "uuid",
          "image_url": "/uploads/photos/photo1.jpg",
          "thumbnail_url": null,
          "file_size_bytes": 102400,
          "uploaded_at": "2026-09-29T12:00:00Z"
        }
      ],
      "materials": [
        {
          "id": "uuid",
          "daily_work_entry_id": "uuid",
          "material_id": "uuid",
          "site_id": "uuid",
          "transaction_type": "consumed",
          "item_name": "Heat Shrink Sleeve",
          "quantity": 25.0,
          "amount": 150.0,
          "bill_image_url": null,
          "is_high_value": false,
          "status": "submitted",
          "verification_record_id": null,
          "verification_action": null,
          "verification_remarks": null,
          "history": []
        }
      ]
    }
  ],
  "exception_flags": ["out_of_location"],
  "all_verified": false
}

Business Rules:
  - Combines attendance, work entries, photos, and materials into a unified day inspection view.
  - Returns historical audit events array (`history`) on attendance, work entries, and materials for chronological timeline rendering.
  - SEC-004-A Anti-Enumeration: If employee does not exist OR is outside the authenticated supervisor's scope, returns unified 404 Not Found ("Employee record not found").

Auth: Supervisor (assigned), Director, Admin
Error Cases: 401, 403 (unauthorized role), 404 (non-existent OR out-of-scope employee)
```

---

## VER-003: Approve

```
API ID: VER-003
Endpoint: POST /api/v1/verification/{id}/approve
HTTP Method: POST
Purpose: Approve an attendance record, daily work entry, or material transaction
Requirement Reference: REQ-VER-005, REQ-BR-006

Path Parameters:
  - id: UUID (ID of attendance_record, daily_work_entry, or material_transaction)

Request:
{
  "entity_type": "attendance" | "daily_work" | "material",
  "idempotency_key": "unique-uuid-key",
  "remarks": "Optional remarks"
}

Response (200 OK):
{
  "id": "uuid",
  "verification_record_id": "uuid",
  "idempotency_key": "unique-uuid-key",
  "target_id": "uuid",
  "entity_type": "daily_work",
  "action": "approved",
  "status": "approved",
  "is_replay": false
}

Business Rules:
  - Target entity must be in 'submitted' status.
  - Supports material transactions independently of parent daily work entries.
  - Updates target record status to 'approved'.
  - Creates verification_records entry and immutable audit_logs entry.
  - Idempotency key prevents duplicate verification records on concurrent/rapid requests.
  - SEC-004-A Anti-Enumeration: Accessing an out-of-scope employee's record returns unified 404 Not Found.

Auth: Supervisor (assigned), Director, Admin
Error Cases: 401, 403 (wrong role), 404 (non-existent OR out-of-scope), 409 (target not in submitted status), 422
```

---

## VER-004: Reject

```
API ID: VER-004
Endpoint: POST /api/v1/verification/{id}/reject
HTTP Method: POST
Purpose: Reject an attendance record, daily work entry, or material transaction
Requirement Reference: REQ-VER-006, REQ-VER-008

Request:
{
  "entity_type": "attendance" | "daily_work" | "material",
  "idempotency_key": "unique-uuid-key",
  "remarks": "Mandatory rejection reason (min 10 characters)"
}

Response (200 OK):
{
  "id": "uuid",
  "verification_record_id": "uuid",
  "idempotency_key": "unique-uuid-key",
  "target_id": "uuid",
  "entity_type": "daily_work",
  "action": "rejected",
  "status": "rejected",
  "is_replay": false
}

Business Rules:
  - Target entity must be in 'submitted' status.
  - remarks field is MANDATORY (trimmed length >= 10 chars).
  - Updates target status to 'rejected'.
  - Creates verification_records and audit_logs entries.
  - SEC-004-A Anti-Enumeration: Unified 404 Not Found on out-of-scope targets.

Auth: Supervisor (assigned), Director, Admin
Error Cases: 401, 403, 404, 409, 422 (missing or < 10 char remarks)
```

---

## VER-005: Return for Correction / Reopen

```
API ID: VER-005
Endpoint: POST /api/v1/verification/{id}/return
HTTP Method: POST
Purpose: Return a submitted item for correction, OR reopen an approved item (Admin/Director only)
Requirement Reference: REQ-VER-007, REQ-VER-008, REQ-BR-006

Request:
{
  "entity_type": "attendance" | "daily_work" | "material",
  "idempotency_key": "unique-uuid-key",
  "remarks": "Mandatory correction / reopening instructions (min 10 characters)"
}

Response (200 OK):
{
  "id": "uuid",
  "verification_record_id": "uuid",
  "idempotency_key": "unique-uuid-key",
  "target_id": "uuid",
  "entity_type": "daily_work",
  "action": "correction_required",
  "status": "correction_required",
  "is_replay": false
}

Business Rules:
  - If target status is 'submitted': Any authorized supervisor, director, or admin can return it.
  - If target status is 'approved' (Reopen Workflow):
    - ONLY users with 'administrator' or 'director' roles are authorized to reopen.
    - Supervisors attempting to reopen approved records receive HTTP 403 Forbidden.
  - remarks field is MANDATORY (trimmed length >= 10 chars).
  - Target status transitions to 'correction_required'.
  - Records verification_records entry with action='correction_required' and audit_logs entry.
  - SEC-004-A Anti-Enumeration: Unified 404 Not Found on out-of-scope targets.

Auth: Supervisor (for submitted items), Director / Admin (for submitted items and approved reopens)
Error Cases: 401, 403 (supervisor attempting reopen on approved item), 404, 409, 422 (remarks validation)
```

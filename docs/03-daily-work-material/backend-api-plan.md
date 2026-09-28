# Phase 3 — Daily Work & Material — Backend API Plan

> All APIs use the `/api/v1` prefix. Full conventions in [`docs/00-phase-0/api-development-standard.md`](../00-phase-0/api-development-standard.md).

---

## WRK-001: Create Work Entry (Realigned per DB-ALIGN / FE-ALIGN)

```
API ID: WRK-001
Endpoint: POST /api/v1/daily-work
HTTP Method: POST
Purpose: Create a new daily work entry line item linked to employee's active attendance session
Requirement Reference: REQ-WRK-001 to REQ-WRK-008

Request:
{
  "activity_id": "uuid",
  "work_order_id": "uuid (optional)",
  "quantity": 45.0,
  "uom": "metres",
  "idempotency_key": "c3f9b2d1-e231-419b-bc3e-001122334455",
  "work_date": "2026-09-26 (optional, defaults to active session date)",
  "remarks": "optional notes"
}

Response (201 Created):
{
  "id": "uuid",
  "idempotency_key": "c3f9b2d1-e231-419b-bc3e-001122334455",
  "attendance_record_id": "uuid",
  "employee_id": "uuid",
  "site_id": "uuid",
  "work_date": "2026-09-26",
  "activity_id": "uuid",
  "activity_name": "Cable Pulling",
  "work_order_id": "uuid",
  "quantity": 45.0,
  "uom": "metres",
  "status": "draft",
  "remarks": "optional notes",
  "photos": [],
  "materials": [],
  "created_at": "2026-09-26T10:00:00Z",
  "updated_at": "2026-09-26T10:00:00Z"
}

Validation:
  - activity_id: required UUID, must exist in activities table
  - work_order_id: optional UUID, if provided must exist in work_orders table
  - quantity: numeric >= 0
  - uom: string (auto-derived from activity master)
  - idempotency_key: non-empty string <= 100 chars, unique across entries
  - work_date: optional DATE

Business Rules:
  - Employee must have an active unclosed attendance session (check_out_time IS NULL)
  - attendance_record_id and site_id auto-linked from the active session
  - employee_id derived from auth token
  - Idempotent: duplicate submissions with same idempotency_key return existing entry
  - Initial status = 'draft'

Auth: Employee role only
Error Cases: 401, 403, 404 (activity/work_order), 422 (validation, no active attendance session)
```

---

## WRK-002: List Work Entries

```
API ID: WRK-002
Endpoint: GET /api/v1/daily-work
HTTP Method: GET
Purpose: List daily work entries with filters and pagination

Query Parameters:
  - date_from, date_to: DATE (optional)
  - employee_id: UUID (supervisor/director only)
  - site_id: UUID (optional)
  - activity_id: UUID (optional)
  - status: string (optional)
  - page: integer (default 1)
  - page_size: integer (default 20, max 100)

Response (200): Paginated list of work entries with summary fields, photos, and materials

Auth: Employee (own), Supervisor (assigned), Director (all)
```

---

## WRK-003: Get Work Entry Detail

```
API ID: WRK-003
Endpoint: GET /api/v1/daily-work/{id}
HTTP Method: GET
Purpose: Get full work entry detail including photos and materials

Response (200): Full work entry with nested photos array and materials array

Auth: Own record, supervisor of employee, director, admin
Error Cases: 401, 403, 404
```

---

## WRK-004: Update Work Entry

```
API ID: WRK-004
Endpoint: PUT /api/v1/daily-work/{id}
HTTP Method: PUT
Purpose: Update work entry quantities (draft or correction_required status only)

Request:
{
  "activity_id": "uuid (optional)",
  "work_order_id": "uuid (optional)",
  "quantity": 50.0,
  "uom": "metres",
  "remarks": "updated notes"
}

Business Rules:
  - Only editable in 'draft' or 'correction_required' status
  - Submitted/approved entries return 400/409 Conflict
  - Employee can only update own entries

Auth: Employee (own, draft/correction only)
Error Cases: 401, 403, 404, 400/409 (wrong status), 422
```

---

## WRK-005: Submit Work

```
API ID: WRK-005
Endpoint: POST /api/v1/daily-work/{id}/submit
HTTP Method: POST
Purpose: Change work entry status from draft to submitted

Response (200):
{
  "id": "uuid",
  "status": "submitted",
  "submitted_at": "timestamp"
}

Business Rules:
  - Only from 'draft' status
  - Changes status to 'submitted'
  - Sends entry to supervisor's EOD verification queue
  - Creates audit_log entry

Auth: Employee (own, draft only)
Error Cases: 401, 403, 404, 409 (already submitted/approved)
```

---

## WRK-006: Upload Photo

```
API ID: WRK-006
Endpoint: POST /api/v1/daily-work/{id}/photos
HTTP Method: POST
Content-Type: multipart/form-data
Purpose: Upload work progress photo for a work entry

Request: multipart/form-data with 'file' field

Response (201):
{
  "id": "uuid",
  "daily_work_entry_id": "uuid",
  "image_url": "signed_url",
  "thumbnail_url": "signed_url",
  "file_size_bytes": 245000,
  "uploaded_at": "timestamp"
}

Business Rules:
  - Work entry must be in 'draft' or 'correction_required' status
  - File type: image/jpeg, image/png, image/webp (validated server-side via magic bytes)
  - Max file size: 10MB
  - Thumbnail generated server-side (200px max dimension)
  - File stored via FileStorageService with UUID-based name
  - Multiple photos per work entry supported

Auth: Employee (own entry, draft/correction only)
Error Cases: 401, 403, 404, 409 (wrong status), 422 (invalid file type/size)
```

---

## WRK-007: Add Material Transaction

```
API ID: WRK-007
Endpoint: POST /api/v1/daily-work/{id}/materials
HTTP Method: POST
Purpose: Record material consumption or purchase

Request:
{
  "material_id": "uuid (optional — null for free-text)",
  "transaction_type": "purchased",
  "item_name": "Cat6 Cable",
  "quantity": 100,
  "amount": 5000.00
}

Response (201):
{
  "id": "uuid",
  "daily_work_entry_id": "uuid",
  "material_id": "uuid",
  "transaction_type": "purchased",
  "item_name": "Cat6 Cable",
  "quantity": 100,
  "amount": 5000.00,
  "is_high_value": true,
  "status": "draft"
}

Business Rules:
  - If material_id provided, validate exists in materials table
  - item_name required (auto-filled from material if material_id provided)
  - transaction_type: 'consumed' or 'purchased'
  - Auto-flag is_high_value if amount > material.purchase_approval_limit (REQ-BR-005)
  - Quantity must be > 0, amount must be >= 0

Auth: Employee (own entry, draft/correction only)
Error Cases: 401, 403, 404, 409, 422
```

---

## WRK-008: Update Material Transaction

```
API ID: WRK-008
Endpoint: PUT /api/v1/daily-work/{id}/materials/{mid}
HTTP Method: PUT
Purpose: Update material transaction details

Request: Same fields as create (partial update)

Business Rules: Same status restrictions as WRK-007. Re-calculate is_high_value on update.

Auth: Employee (own, draft/correction only)
Error Cases: 401, 403, 404, 409, 422
```

---

## WRK-009: Upload Bill Image

```
API ID: WRK-009
Endpoint: POST /api/v1/daily-work/{id}/materials/{mid}/bill
HTTP Method: POST
Content-Type: multipart/form-data
Purpose: Upload receipt/bill image for a material purchase

Request: multipart/form-data with 'file' field

Response (200):
{
  "id": "uuid",
  "bill_image_url": "signed_url"
}

Business Rules: Same file validation as WRK-006. Store via FileStorageService.

Auth: Employee (own, draft/correction only)
Error Cases: 401, 403, 404, 409, 422
```

---

## Admin APIs (ADM-007 to ADM-015)

### Work Orders Admin
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| ADM-007 | POST | /api/v1/admin/work-orders | Create work order |
| ADM-008 | GET | /api/v1/admin/work-orders | List work orders (paginated, filterable) |
| ADM-009 | GET | /api/v1/admin/work-orders/{id} | Get work order detail |
| ADM-010 | PUT | /api/v1/admin/work-orders/{id} | Update work order |

### Activities Admin
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| ADM-011 | POST | /api/v1/admin/activities | Create activity |
| ADM-012 | GET | /api/v1/admin/activities | List activities |
| ADM-013 | PUT | /api/v1/admin/activities/{id} | Update activity |

### Materials Admin
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| ADM-014 | POST | /api/v1/admin/materials | Create material |
| ADM-015 | GET | /api/v1/admin/materials | List materials |
| ADM-016 | PUT | /api/v1/admin/materials/{id} | Update material |

**Auth**: Administrator role required for all admin endpoints. Soft delete via `is_active` toggle.

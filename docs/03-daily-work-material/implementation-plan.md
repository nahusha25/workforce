# Phase 3 — Daily Work & Material — Implementation Plan

## Requirement Scope
Enable employees to select activities, enter work quantities, upload progress photos, and record material consumption/purchases. Work must be submitted before check-out. Support draft save for weak-network tolerance.

## Requirement Traceability
| Req ID | Requirement | Feature |
|--------|-------------|---------|
| REQ-WRK-001 | Select activity type | Activity dropdown |
| REQ-WRK-002–008 | Enter quantities (cable, devices, drilling, mounting, testing, commissioning) | Quantity fields |
| REQ-WRK-009 | Upload work-progress photos | Photo capture |
| REQ-WRK-010–012 | Record material (item, quantity, amount) | Material form |
| REQ-WRK-013 | Upload bill image | Bill capture |
| REQ-MD-003 | Work order master data | Admin CRUD |
| REQ-MD-004 | Activity & Material master data | Admin CRUD |
| REQ-BR-003 | Work submitted before check-out | Submit + checkout integration |
| REQ-BR-005 | High-value material flagging | Auto-flag |
| REQ-UX-004 | Camera-first, compression, draft, offline | Photo component, draft save |

---

## Database

### New Tables (6 total)
1. **work_orders** — project/site-linked work orders (master data)
2. **activities** — activity type master data with rates
3. **materials** — material master data with approval limits
4. **daily_work_entries** — daily work quantities per employee per activity
5. **work_photos** — progress photo metadata
6. **material_transactions** — material consumption/purchase records

Full schemas in [`database-plan.md`](./database-plan.md).

### Migration Sequence
```
009_create_work_orders → 010_create_activities → 011_create_materials →
012_create_daily_work_entries → 013_create_work_photos → 014_create_material_transactions
```

---

## Backend

### Module Structure
```
backend/app/modules/daily_work/
├── __init__.py
├── models.py          — DailyWorkEntry, WorkPhoto, MaterialTransaction
├── schemas.py         — Create/Update/Response schemas for all entities
├── service.py         — Work entry lifecycle, submission, photo/material handling
├── repository.py      — CRUD operations for all 3 business tables
└── exceptions.py      — NoActiveAttendance, InvalidWorkStatus

backend/app/modules/admin/
├── work_orders.py     — Work order admin service + routes
├── activities.py      — Activity admin service + routes
└── materials.py       — Material admin service + routes

backend/app/shared/
└── file_storage.py    — FileStorageService (local + S3), upload, signed URLs
```

### Service Layer Logic

1. **create_work_entry(employee_id, data)**:
   - Verify active attendance (checked in, not checked out)
   - Validate activity_id exists and is_active
   - Link to today's attendance_record_id
   - Set employee_id, site_id from attendance
   - Status = 'draft'

2. **submit_work_entry(employee_id, entry_id)**:
   - Verify ownership (employee_id matches)
   - Verify status = 'draft'
   - Change status to 'submitted'
   - Also submits linked material_transactions
   - Create audit_log entry

3. **upload_photo(employee_id, entry_id, file)**:
   - Verify ownership and status (draft/correction_required)
   - Validate file (MIME, size, magic bytes)
   - Generate UUID filename
   - Compress/generate thumbnail (Pillow)
   - Upload original + thumbnail to storage
   - Create work_photos record

4. **add_material(employee_id, entry_id, data)**:
   - Verify ownership and status
   - If material_id provided, lookup approval_limit
   - Calculate is_high_value = (amount > approval_limit)
   - Create material_transactions record

---

## API Endpoints

| API ID | Method | Endpoint | Auth | Purpose |
|--------|--------|----------|------|---------|
| WRK-001 | POST | /api/v1/daily-work | Employee | Create work entry |
| WRK-002 | GET | /api/v1/daily-work | Employee/Supervisor | List entries |
| WRK-003 | GET | /api/v1/daily-work/{id} | Employee/Supervisor | Entry detail |
| WRK-004 | PUT | /api/v1/daily-work/{id} | Employee (draft only) | Update entry |
| WRK-005 | POST | /api/v1/daily-work/{id}/submit | Employee | Submit entry |
| WRK-006 | POST | /api/v1/daily-work/{id}/photos | Employee (draft only) | Upload photo |
| WRK-007 | POST | /api/v1/daily-work/{id}/materials | Employee (draft only) | Add material |
| WRK-008 | PUT | /api/v1/daily-work/{id}/materials/{mid} | Employee (draft only) | Update material |
| WRK-009 | POST | /api/v1/daily-work/{id}/materials/{mid}/bill | Employee (draft only) | Upload bill image |
| ADM-007–016 | Various | /api/v1/admin/... | Administrator | Work order, activity, material CRUD |

Full contracts in [`backend-api-plan.md`](./backend-api-plan.md).

---

## Frontend

### Pages
1. **Work Entry Page** (`/work/new`): Activity selection + quantity fields
2. **Work History Page** (`/work`): List of today's/past work entries
3. **Admin: Work Orders** (`/admin/work-orders`): CRUD management
4. **Admin: Activities** (`/admin/activities`): CRUD management
5. **Admin: Materials** (`/admin/materials`): CRUD management

### Key Components
- **ActivityDropdown**: Fetches activities, shows by category
- **QuantityFields**: Conditionally shows relevant fields based on activity category
- **PhotoCapture**: Camera-first, client-side compression, gallery, upload
- **MaterialForm**: Material selection/free-text, quantity, amount, bill image
- **DraftIndicator**: "Draft saved" / "Saving..." status
- **SubmitFlow**: Confirmation dialog → submit → read-only mode

### Design Decisions
- **Camera-first** (REQ-UX-004): `<input capture="environment">` opens camera directly
- **Client-side compression**: Target ~500KB using canvas/browser-image-compression before upload
- **Activity-based fields**: Only show quantity fields relevant to selected activity category (cable activities show cable fields, device activities show device fields, etc.)
- **Large numeric inputs** (REQ-UX-002): `inputMode="numeric"` for mobile numeric keypad

---

## Key Implementation Notes
1. Image compression on client side (~500KB target) before upload
2. Draft auto-save via debounced API call + localStorage fallback
3. Pre-checkout check: API validates work is submitted before allowing checkout (Phase 2 integration)
4. High-value flag calculated server-side on every material create/update
5. Bill images stored alongside work photos in FileStorageService
6. Admin pages follow standard CRUD pattern with search, sort, paginate

---

## Dependencies
| Dependency | Source | Required For |
|-----------|--------|-------------|
| Active attendance session | Phase 2 | Work entry creation |
| Employee authentication | Phase 1 | All operations |
| Site assignment | Phase 1 | Auto-fill site |
| File storage service | New (shared) | Photo and bill image storage |
| Activity master data | New (admin) | Activity selection |
| Material master data | New (admin) | Material selection, high-value calculation |

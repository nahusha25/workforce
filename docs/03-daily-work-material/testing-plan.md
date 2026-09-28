# Phase 3 — Testing Plan (Complete & Verified)

## Database Tests (`tests/database/`)
- [x] daily_work_entries: generic quantity column ≥ 0 (`test_daily_work_entries.py`)
- [x] daily_work_entries: status CHECK ('draft','submitted','approved','rejected','correction_required')
- [x] daily_work_entries: FK attendance_records, FK employees, FK sites, FK activities
- [x] daily_work_entries: idempotency_key UNIQUE constraint & conflict handling
- [x] material_transactions: quantity > 0 and amount ≥ 0 CHECK constraints (`test_material_transactions.py`)
- [x] material_transactions: status CHECK and transaction_type CHECK
- [x] work_photos: FK daily_work_entries cascade and file_path not null
- [x] work_orders: end_date ≥ start_date and order_number UNIQUE (`test_work_orders.py`)

## Service Tests (`tests/daily_work/`)
- [x] Work entry requires active unclosed attendance session (`test_service.py`)
- [x] Work entry linked to active attendance record and authenticated employee
- [x] Multi-line draft save and idempotency deduplication
- [x] Submission changes status from draft to submitted and locks edits
- [x] Only draft/correction_required entries are editable
- [x] Photo upload validates MIME magic bytes (JPEG/PNG/WEBP) and 10MB size limit (`test_photo_service.py`)
- [x] Photo thumbnail generation via Pillow and storage key isolation
- [x] High-value material flag calculated server-side against approval limits (`test_material_service.py`)
- [x] Pre-checkout validation soft check warns/requires confirmation (`test_attendance.py`)

## API Integration Tests (`tests/api/`)
- [x] POST /daily-work — valid single-activity line entry → 201 (`test_daily_work.py`)
- [x] POST /daily-work — no active attendance → 422
- [x] POST /daily-work/{id}/submit — valid transition → 200 (submits entry & linked materials)
- [x] POST /daily-work/{id}/photos — valid image → 201
- [x] POST /daily-work/{id}/photos — invalid MIME/magic byte → 422
- [x] POST /daily-work/{id}/materials — valid consumed/purchased → 201
- [x] POST /daily-work/{id}/materials — amount > approval_limit auto-flags high-value
- [x] Multi-tenant IDOR security suite: Employee B strictly blocked from accessing Employee A's photos, foreign photo IDs, or materials

## E2E Tests (`frontend/e2e/daily_work.spec.ts`)
- [x] E2E-J06: Complete Daily Work Multi-Activity Capture Journey (Lines → Attachments → Submit Modal → Read-only)
- [x] E2E-J07: Cross-Day Checkout Scenario (unclosed prior-day session checkout without 422 error)

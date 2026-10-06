# Phase 4 — Testing Plan

## Database Tests (`tests/database/test_verification_records.py` - 16/16 Passed)
- [x] `verification_records`: action CHECK constraint ('approved', 'rejected', 'correction_required')
- [x] `verification_records`: single-target CHECK constraint (exactly one of attendance_record_id, daily_work_entry_id, material_transaction_id)
- [x] `verification_records`: mandatory remarks CHECK constraint (action = 'approved' OR length(trim(remarks)) >= 10)
- [x] `verification_records`: unique idempotency_key constraint
- [x] `verification_records`: FK constraints to users and operational entity tables

## Service Tests (`tests/unit/test_verification_service.py` - 100% Passed)
- [x] Summary aggregates correct data per employee/date (work, photo, material counts, costs)
- [x] Approve changes status to approved and generates verification_record and audit_log
- [x] Reject requires remarks >= 10 chars, changes status to rejected
- [x] Return requires remarks >= 10 chars, changes status to correction_required
- [x] Approved records become read-only (rejects mutations with 409 Conflict)
- [x] Audit entries created for all verification actions
- [x] Dynamic exception flag computation: out_of_location, missing_checkout, no_photograph (scoped to submitted entries), high_value_material, attendance_without_work
- [x] Supervisor can only access assigned employees

## API Tests (`tests/api/test_verification_api.py` - 317/317 Full Suite)
- [x] GET /summary (VER-001) — supervisor sees assigned only → 200
- [x] GET /summary (VER-001) — employee access → 403
- [x] GET /summary/{employee_id} (VER-002) — full day details with history → 200
- [x] GET /summary/{employee_id} (VER-002) — out-of-scope employee returns unified 404 (SEC-004-A)
- [x] POST /approve (VER-003) — valid → 200
- [x] POST /approve (VER-003) — already approved target → 409
- [x] POST /approve (VER-003) — out-of-scope target returns unified 404 (SEC-004-A)
- [x] POST /reject (VER-004) — with remarks >= 10 chars → 200
- [x] POST /reject (VER-004) — without remarks / < 10 chars → 422
- [x] POST /return (VER-005) — submitted target with remarks → 200
- [x] POST /return (VER-005) — approved target reopened by Admin/Director → 200
- [x] POST /return (VER-005) — approved target attempted by Supervisor → 403
- [x] Concurrent rapid requests with same idempotency key resolve gracefully without exceptions

## E2E Tests (`frontend/e2e/supervisor_verification.spec.ts` - 3/3 Passed, Mobile Viewport)
- [x] Step 1-4: Supervisor views queue with exception badges (`out_of_location`, `high_value_material`), drills down, approves attendance, work entry, and normal material, confirms high-value purchase warning modal, and verifies reviewed card in queue.
- [x] Step 5: Administrator logs in, reopens approved work entry with mandatory remarks, and verifies chronological `AuditHistoryTimeline` with actor names and remarks.
- [x] Step 6: Supervisor rejects submitted work entry with mandatory remarks, confirms status is rejected and action buttons are excluded.

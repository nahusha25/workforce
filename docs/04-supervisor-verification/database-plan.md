# Phase 4 — Supervisor Verification — Database Plan

> Derived from `canonical-erd.md` v3.0 and Phase 4 Architecture Decision

## Core Tables (Verification)

### `verification_records`
- `id` (PK, UUID, DEFAULT gen_random_uuid())
- `idempotency_key` (VARCHAR(100), UNIQUE, NOT NULL, INDEX)
- `attendance_record_id` (FK to `attendance_records.id`, ON DELETE SET NULL, NULLABLE, INDEX)
- `daily_work_entry_id` (FK to `daily_work_entries.id`, ON DELETE SET NULL, NULLABLE, INDEX)
- `material_transaction_id` (FK to `material_transactions.id`, ON DELETE SET NULL, NULLABLE, INDEX)
- `verified_by` (FK to `users.id`, NOT NULL, INDEX)
- `action` (VARCHAR(30), NOT NULL)
- `remarks` (TEXT, NULLABLE)
- `verified_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW(), INDEX)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())

#### Database Constraints
1. **`check_verification_action`**:
   `action IN ('approved', 'rejected', 'correction_required')`
2. **`check_verification_single_target`**:
   Exactly one of `attendance_record_id`, `daily_work_entry_id`, or `material_transaction_id` must be populated:
   `(CASE WHEN attendance_record_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN daily_work_entry_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN material_transaction_id IS NOT NULL THEN 1 ELSE 0 END) = 1`
3. **`check_verification_mandatory_remarks`**:
   `action = 'approved' OR (remarks IS NOT NULL AND length(trim(remarks)) >= 10)`
4. **`uq_verification_records_idempotency_key`**:
   `UNIQUE (idempotency_key)`

> Note: Anomaly tracking during verification relies on the existing polymorphic `exception_flags` table (introduced in Phase 2) with expanded flag types (`missing_checkout`, `no_photograph`, `out_of_location`, `high_value_material`, `attendance_without_work`).

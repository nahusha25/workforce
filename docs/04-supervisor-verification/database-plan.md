# Phase 4 — Supervisor Verification — Database Plan

> Derived from `canonical-erd.md` v3.0, Phase 4 Architecture Decisions, and Batch 1 Implementation

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
   Exactly one target FK must be populated:
   `(CASE WHEN attendance_record_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN daily_work_entry_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN material_transaction_id IS NOT NULL THEN 1 ELSE 0 END) = 1`
3. **`check_verification_mandatory_remarks`**:
   `action = 'approved' OR (remarks IS NOT NULL AND length(trim(remarks)) >= 10)`
4. **`uq_verification_records_idempotency_key`**:
   `UNIQUE (idempotency_key)`

---

## Architectural Relationships & Decisions

### 1. Relationship to `audit_logs`
- `verification_records` is an **append-only domain ledger** specifically tracking supervisor and administrator decisions.
- In addition to writing a row to `verification_records`, every verification action writes an immutable event to `audit_logs` with `entity_type`, `entity_id`, `actor_id`, `action`, `remarks`, and metadata.
- When retrieving verification history in `VER-002` (`GET /api/v1/verification/summary/{employee_id}`), the backend queries `verification_records` joined with `users` (to populate `verified_by_name`) for each entity, returning a chronological `history` array displayed in the frontend `AuditHistoryTimeline`.

### 2. Relationship to `exception_flags` (Architectural Decision & DB-016B-DECISION)
- In Phase 2, `exception_flags` existed as a polymorphic table and JSONB column on `attendance_records`.
- During Phase 4 architecture design, rather than coupling daily work entries to a static JSONB column or separate persistence table, `compute_exception_flags` was implemented to **compute flags dynamically** at query time from live operational data:
  - `out_of_location`: `attendance.is_within_geofence == False`
  - `missing_checkout`: Attendance checked in with no checkout time
  - `no_photograph`: Scoped strictly to *submitted* daily work entries with zero uploaded photos (excluding drafts)
  - `high_value_material`: Any submitted material transaction where `is_high_value == True` (amount exceeds material `purchase_approval_limit`)
  - `attendance_without_work`: Checked-in attendance with 0 daily work entries
  - `work_without_attendance`: Work entries present without an attendance record
- Dynamic computation guarantees flags remain strictly synchronized with operational edits without risk of stale denormalized columns. (Tracked under backlog item `BE-026B-FOLLOWUP` for future query-caching at massive scale).

### 3. Multi-Activity Line-Item Model Implications for Verification Granularity
- In Phase 3, materials were modeled as child line items of daily work entries (`material_transactions.daily_work_entry_id`).
- In Phase 4, **verification granularity is decoupled at the individual entity level**:
  - **Attendance Record Independence**: An attendance record can be approved or returned independently of work quantities.
  - **Daily Work Entry Independence**: Each work entry for an activity can be verified on its own merit.
  - **Material Transaction Independence**: Each material transaction (`material_transactions`) has its own `status` (`submitted`, `approved`, `rejected`, `correction_required`) and target FK in `verification_records.material_transaction_id`.
  - **Operational Impact**: A supervisor can approve a worker's physical cable laying daily work entry while rejecting or returning a faulty material receipt line item, or approve normal consumable items while holding high-value items for review.
  - **High-Value Guardrails**: High-value materials trigger warning modals requiring explicit supervisor confirmation before approval can proceed.

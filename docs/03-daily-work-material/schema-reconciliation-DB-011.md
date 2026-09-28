# DB-011 — Schema Reconciliation

## 1. Original Conflict
The `activities` table definition conflicted between the Canonical ERD and the Phase 3 DB-011 task description. Discrepancies included `default_rate` vs `approved_rate`, the missing `category` field, and missing boilerplate fields (`is_active`, `created_at`, `updated_at`).

## 2. Evidence Reviewed
- `docs/00-phase-0/canonical-erd.md` (Canonical ERD)
- `docs/03-daily-work-material/task-list.md` (Phase 3 DB-011)
- `docs/03-daily-work-material/database-plan.md`
- Phase 3 frontend requirements (`docs/03-daily-work-material/implementation-plan.md` requiring dynamic UI based on activity category).
- Phase 5 payroll requirements (`docs/05-director-dashboard-invoicing/task-list.md` utilizing `activity_approved_rate`).
- `backend/app/models/operations.py` (Existing models establishing audit/soft-delete conventions).

## 3. Final Decisions
| Field | Final Decision |
| :--- | :--- |
| `approved_rate` | Adopted. Replaced `default_rate` |
| `category` | Added |
| `is_active` | Added |
| `created_at` / `updated_at` | Added |

## 4. Why decisions were made
- **approved_rate**: Selected because Phase 5 invoicing and payroll logic specifically relies on this term (`activity_approved_rate`) as the authoritative rate for piece-work, avoiding the ambiguous implication of "default" being meaningless.
- **category**: Added because the Phase 3 UI completely relies on the category field to determine which dynamic quantity inputs to display to the employee.
- **is_active and timestamps**: Added to strictly adhere to the established project conventions for master data (requiring soft deletion and audit trailing as seen in `clients`, `sites`, etc.).

## 5. Canonical ERD Changes
- Updated the `activities` table in `docs/00-phase-0/canonical-erd.md` to remove `default_rate` and explicitly add `approved_rate`, `category`, `is_active`, `created_at`, and `updated_at`.

## 6. Database Plan Changes
- Updated `docs/03-daily-work-material/database-plan.md` to exactly match the canonical schema, including the exact CHECK constraints and data types (`NUMERIC(12,2)`).

## 7. Confirmation
- Implementation (SQLAlchemy models, Alembic migrations, or tests) has **NOT** started.
- DB-011 remains **NOT STARTED** in the Phase 3 task list.

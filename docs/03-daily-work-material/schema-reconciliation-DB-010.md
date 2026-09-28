# DB-010 — Schema Reconciliation

## 1. Original Conflict
The `work_orders` table definition conflicted between the Canonical ERD and the Phase 3 DB-010 task description. Discrepancies included `description` vs `scope`, `target_quantity (NUMERIC)` vs `target_quantities (JSONB)`, and missing boilerplate/master-data fields (`billing_basis`, `is_active`, `created_at`, `updated_at`).

## 2. Evidence Reviewed
- `docs/00-phase-0/canonical-erd.md` (Canonical ERD)
- `docs/03-daily-work-material/task-list.md` (Phase 3 DB-010)
- `docs/03-daily-work-material/database-plan.md`
- `backend/app/models/operations.py` (Existing models)
- Phase 3 API/Feature requirements (`REQ-WRK-001` through `REQ-WRK-008` specifying multiple work activity quantities).

## 3. Final Decisions
| Field | Final Decision | Why the decision was made |
| :--- | :--- | :--- |
| `description` | `TEXT` | Canonical ERD explicitly defined `description`. "Scope" was determined to be colloquial wording in the task list. |
| `target_quantity` | Replace with `target_quantities JSONB` | Necessary business refinement. A work order targets multiple diverse quantities (cable runs, devices, drilling), requiring a JSONB structure instead of a single `NUMERIC` value. |
| `billing_basis` | Add | Required for future invoicing features (`per_metre`, `per_device`, `lump_sum`). |
| `is_active` | Add | Existing convention for master-data tables to support soft-deletion (required by BE-021). |
| `created_at` / `updated_at` | Add | Existing convention for master-data tracking in the `operations.py` models. |

## 4. Canonical ERD Changes
- Updated the `work_orders` table in `docs/00-phase-0/canonical-erd.md` to change `target_quantity` to `target_quantities jsonb`.
- Added `billing_basis varchar`, `is_active boolean`, `created_at timestamp`, and `updated_at timestamp` to perfectly align with the intended Phase 3 implementation.

## 5. Phase 3 Documentation Changes
- Updated `docs/03-daily-work-material/database-plan.md` to precisely mirror the canonical schema, removing the old `target_quantity` and reflecting all constraints (UNIQUE, CHECK, JSONB).
- Updated `docs/03-daily-work-material/task-list.md` (DB-010) to replace "scope text" with "description (TEXT)" to eliminate ambiguity, while explicitly retaining `target_quantities (JSONB)`.

## 6. Confirmation
- Implementation (SQLAlchemy models, Alembic migrations, or tests) has **NOT** started.
- DB-010 remains **NOT STARTED** in the Phase 3 task list.

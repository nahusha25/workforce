# DB-012 — Schema Reconciliation

## 1. Original Conflict
The `materials` table definition conflicted between the Canonical ERD and the Phase 3 DB-012 task description. Discrepancies included legacy catalog fields (`material_code` and `description`) present in the ERD but missing in the task, and critical Phase 3 fields (`purchase_approval_limit`, `category`, `is_active`, `created_at`, `updated_at`) present in the task but missing in the ERD.

## 2. Evidence Reviewed
- `docs/00-phase-0/canonical-erd.md` (Canonical ERD)
- `docs/03-daily-work-material/task-list.md` (Phase 3 DB-012)
- `docs/03-daily-work-material/database-plan.md`
- Business requirement `REQ-BR-005` mandating high-value flagging based on `purchase_approval_limit`.
- Phase 3 API logic for `material_transactions` where `is_high_value = (amount > material.purchase_approval_limit)`.

## 3. Final Decisions

| Field | Final Decision |
| :--- | :--- |
| `material_code` | Retained (NULLABLE) |
| `description` | Retained (NULLABLE TEXT) |
| `purchase_approval_limit` | Added (NUMERIC(12,2) CHECK >= 0) |
| `category` | Added (VARCHAR CHECK constraint) |
| `is_active` | Added (BOOLEAN default TRUE) |
| timestamps | Added (created_at, updated_at) |
| `name` | Retained (VARCHAR NOT NULL, no UNIQUE constraint) |

## 4. Why decisions were made
- **material_code & description**: Kept to support legacy ERP compatibility originally envisioned in Phase 0, but explicitly made **NULLABLE** because Phase 3 workflows solely rely on `item_name` and `id`.
- **purchase_approval_limit**: Critically necessary to satisfy `REQ-BR-005` allowing automatic identification of high-value material usage. Zero is considered a valid threshold to flag all purchases of a specific category.
- **category**: Necessary to filter standard inventory, tools, and consumables.
- **is_active and timestamps**: Necessary to enforce the established soft-delete master data convention applied universally to clients, sites, and activities.
- **name uniqueness**: Explicitly decided NOT to enforce a UNIQUE constraint on `name` at the database level, as no authoritative evidence mandated it and it could introduce friction when importing loose ERP data.

## 5. Canonical ERD Changes
- Updated the `materials` table in `docs/00-phase-0/canonical-erd.md` to append `category`, `purchase_approval_limit`, `is_active`, `created_at`, and `updated_at` alongside the existing fields.

## 6. Database Plan Changes
- Updated `docs/03-daily-work-material/database-plan.md` to perfectly match the combined schema, stipulating constraints and types.

## 7. Confirmation
- Implementation (SQLAlchemy models, Alembic migrations, or tests) has **NOT** started.
- DB-012 remains **NOT STARTED** in the Phase 3 task list.

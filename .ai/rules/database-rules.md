# Database Rules

## Migration Strategy

- Use **Alembic** for all database schema changes.
- Every migration must be reversible (include `upgrade` and `downgrade`).
- Never manually alter production schema outside migrations.
- Migration file naming: auto-generated with descriptive revision messages.
- Test migrations in development before applying to staging/production.

## Schema Design

### Naming Conventions
- Tables: `snake_case`, plural (e.g., `employees`, `attendance_records`)
- Columns: `snake_case` (e.g., `employee_id`, `check_in_time`)
- Primary keys: `id` (UUID or auto-increment integer — prefer UUID for distributed safety)
- Foreign keys: `<referenced_table_singular>_id` (e.g., `employee_id`, `site_id`)
- Indexes: `ix_<table>_<column>` (e.g., `ix_employees_mobile`)
- Unique constraints: `uq_<table>_<column>` (e.g., `uq_employees_mobile`)
- Check constraints: `ck_<table>_<description>` (e.g., `ck_attendance_records_valid_times`)

### Required Columns on Business Entities
Every business entity table must include:
- `id` — primary key
- `created_at` — timestamp, server default `now()`
- `updated_at` — timestamp, updated on modification
- `is_active` — boolean, default `true` (for soft-delete support where needed)

### Audit Tables
Entities requiring audit trails (per requirements: attendance corrections, approved record changes) must have:
- `changed_by` — user ID of the person who made the change
- `changed_at` — timestamp of the change
- `change_reason` — text describing why the change was made
- `previous_value` — the value before the change (JSON or dedicated columns)

## Constraint Rules

### Primary Keys
- Every table must have a primary key.
- Prefer single-column primary keys.

### Foreign Keys
- Every relationship must be enforced with a foreign key constraint.
- Define `ON DELETE` behavior explicitly (CASCADE, SET NULL, or RESTRICT based on business rules).
- Never leave orphaned references.

### Not-Null Constraints
- Apply `NOT NULL` to every column that must always have a value per business rules.
- Nullable columns must be explicitly justified.

### Unique Constraints
- Apply unique constraints where the business requires uniqueness (e.g., employee mobile number, employee ID).

### Check Constraints
- Use check constraints for:
  - Allowed status values (e.g., `status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')`)
  - Numeric range validation (e.g., `quantity >= 0`, `amount >= 0`)
  - Date/time validation (e.g., `check_out_time > check_in_time`)

## Indexes

- Index columns used in `WHERE` clauses, `JOIN` conditions, and `ORDER BY` on frequently queried tables.
- Index foreign key columns.
- Create composite indexes for common multi-column query patterns.
- Do not over-index — each index has a write cost.

## Data Types

- Use `TIMESTAMP WITH TIME ZONE` for all timestamps.
- Use `NUMERIC(12, 2)` or `DECIMAL` for monetary amounts — never use `FLOAT`.
- Use `TEXT` for variable-length strings (PostgreSQL treats `TEXT` and `VARCHAR` equivalently).
- Use `BOOLEAN` for true/false flags.
- Use `JSONB` sparingly — only for truly schema-less data.
- Use `UUID` for primary keys if distributed ID generation is needed.

## Query Safety

- Always use parameterized queries through SQLAlchemy — never construct SQL strings manually.
- Limit query results with pagination for list endpoints.
- Use `SELECT` with explicit columns when performance matters — avoid `SELECT *` in production code.
- Use database transactions for multi-step operations.

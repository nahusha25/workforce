# Phase 3 — Daily Work & Material — Database Plan

> Derived from `canonical-erd.md` v3.0

## Core Tables (Work & Inventory)

### `activities`
- `id` (PK, UUID)
- `name` (VARCHAR)
- `unit_of_measure` (VARCHAR)
- `approved_rate` (NUMERIC(12,2), CHECK: approved_rate >= 0)
- `category` (VARCHAR, CHECK: 'cable','device','drilling','mounting','testing','commissioning')
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `materials`
- `id` (PK, UUID)
- `material_code` (VARCHAR, NULLABLE)
- `name` (VARCHAR)
- `description` (TEXT, NULLABLE)
- `unit_of_measure` (VARCHAR)
- `category` (VARCHAR, CHECK: 'cable','device','tool','consumable')
- `purchase_approval_limit` (NUMERIC(12,2), CHECK: purchase_approval_limit >= 0)
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `work_orders`
- `id` (PK, UUID)
- `order_number` (VARCHAR, UNIQUE)
- `project_id` (FK to projects)
- `site_id` (FK to sites)
- `description` (TEXT)
- `target_quantities` (JSONB)
- `start_date` (DATE)
- `end_date` (DATE, CHECK: end_date >= start_date)
- `billing_basis` (VARCHAR, CHECK: 'per_metre','per_device','lump_sum')
- `status` (VARCHAR, CHECK: 'draft','open','in_progress','completed','closed')
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `daily_work_entries` (Realigned per DB-ALIGN / FE-ALIGN)
- `id` (PK, UUID, default uuid4)
- `idempotency_key` (VARCHAR(100), UNIQUE, INDEX, NOT NULL — client-generated UUID for robust offline/retry deduplication)
- `attendance_record_id` (FK to attendance_records.id, INDEX, NOT NULL — linked to active unclosed attendance session)
- `employee_id` (FK to employees.id, NOT NULL)
- `site_id` (FK to sites.id, NOT NULL)
- `activity_id` (FK to activities.id, NOT NULL)
- `work_order_id` (FK to work_orders.id, NULLABLE)
- `work_date` (DATE, NOT NULL)
- `quantity` (NUMERIC(10,2), default 0.0, NOT NULL, CHECK: `quantity >= 0`)
- `uom` (VARCHAR(50), NOT NULL — auto-derived from selected activity)
- `status` (VARCHAR, INDEX, NOT NULL, CHECK: `status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')`)
- `remarks` (TEXT, NULLABLE)
- `created_at` (TIMESTAMP WITH TIME ZONE)
- `updated_at` (TIMESTAMP WITH TIME ZONE)
- Indexes & Constraints:
  - `check_dwe_quantity`: `quantity >= 0`
  - `check_dwe_status`: `status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')`
  - Index: `ix_daily_work_entries_employee_id_work_date` on `(employee_id, work_date)`
  - Unique Index on `idempotency_key`

### `work_photos`
- `id` (PK, UUID, default uuid4)
- `daily_work_entry_id` (FK to daily_work_entries.id, ON DELETE CASCADE, INDEX, NOT NULL)
- `image_url` (TEXT, NOT NULL)
- `thumbnail_url` (TEXT, NULLABLE)
- `file_size_bytes` (INTEGER, NULLABLE, CHECK: `file_size_bytes IS NULL OR file_size_bytes >= 0`)
- `uploaded_at` (TIMESTAMP WITH TIME ZONE, NOT NULL, DEFAULT NOW())

### `material_transactions` (Canonical implementation replacing legacy `material_usage` per DB-015)
- `id` (PK, UUID, default uuid4)
- `daily_work_entry_id` (FK to daily_work_entries.id, INDEX, NOT NULL)
- `material_id` (FK to materials.id, NULLABLE — null for free-text items)
- `site_id` (FK to sites.id, NOT NULL)
- `transaction_type` (VARCHAR, NOT NULL, CHECK: `transaction_type IN ('consumed', 'purchased')`)
- `item_name` (VARCHAR(200), NOT NULL)
- `quantity` (NUMERIC(10,2), NOT NULL, CHECK: `quantity > 0`)
- `amount` (NUMERIC(12,2), default 0.0, NOT NULL, CHECK: `amount >= 0`)
- `bill_image_url` (TEXT, NULLABLE — URL to receipt upload in file storage)
- `is_high_value` (BOOLEAN, default FALSE, NOT NULL — auto-flagged if amount > material.purchase_approval_limit)
- `status` (VARCHAR, INDEX, default 'draft', NOT NULL, CHECK: `status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')`)
- `created_at` (TIMESTAMP WITH TIME ZONE)
- `updated_at` (TIMESTAMP WITH TIME ZONE)
- Constraints:
  - `check_material_transactions_type`: `transaction_type IN ('consumed', 'purchased')`
  - `check_material_transactions_quantity`: `quantity > 0`
  - `check_material_transactions_amount`: `amount >= 0`
  - `check_material_transactions_status`: `status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')`

### `material_stock`
- `id` (PK, UUID)
- `material_id` (FK to materials)
- `site_id` (FK to sites)
- `quantity_available` (NUMERIC)
- `quantity_reserved` (NUMERIC)
- `quantity_consumed` (NUMERIC)
- `quantity_purchased` (NUMERIC)
- `updated_at` (TIMESTAMP)

### `asset_management`
- `id` (PK, UUID)
- `asset_code` (VARCHAR)
- `name` (VARCHAR)
- `current_site_id` (FK to sites)
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)

### `asset_movements`
- `id` (PK, UUID)
- `asset_id` (FK to asset_management)
- `from_site_id` (FK to sites)
- `to_site_id` (FK to sites)
- `moved_by` (UUID)
- `moved_at` (TIMESTAMP)

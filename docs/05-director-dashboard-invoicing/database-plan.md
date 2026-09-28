# Phase 5 — Director Dashboard & Invoicing — Database Plan

> Derived from `canonical-erd.md` v3.0

## Core Tables (Finance & Billing)

### `payments`
- `id` (PK, UUID)
- `payment_type` (VARCHAR)
- `amount` (NUMERIC)
- `currency` (VARCHAR)
- `payment_date` (DATE)
- `method` (VARCHAR)
- `status` (VARCHAR)
- `recorded_by` (UUID)
- `created_at` (TIMESTAMP)

### `payment_source_records`
- `id` (PK, UUID)
- `payment_id` (FK to payments)
- `source_type` (VARCHAR)
- `source_id` (UUID)

### `payment_receipts`
- `id` (PK, UUID)
- `payment_id` (FK to payments)
- `amount` (NUMERIC)
- `receipt_url` (TEXT)
- `recorded_by` (UUID)
- `created_at` (TIMESTAMP)

### `project_revenue`
- `id` (PK, UUID)
- `project_id` (FK to projects)
- `client_id` (FK to clients)
- `received_amount` (NUMERIC)
- `currency` (VARCHAR)
- `period_start` (DATE)
- `period_end` (DATE)

### `expenses`
- `id` (PK, UUID)
- `project_id` (FK to projects)
- `site_id` (FK to sites)
- `category` (VARCHAR)
- `amount` (NUMERIC)
- `expense_date` (DATE)
- `recorded_by` (UUID)
- `created_at` (TIMESTAMP)

### `invoices`
- `id` (PK, UUID)
- `invoice_number` (VARCHAR)
- `client_id` (FK to clients)
- `project_id` (FK to projects)
- `project_revenue_id` (FK to project_revenue)
- `total_amount` (NUMERIC)
- `currency` (VARCHAR)
- `invoice_date` (DATE)
- `due_date` (DATE)
- `status` (VARCHAR)
- `created_at` (TIMESTAMP)

### `invoice_line_items`
- `id` (PK, UUID)
- `invoice_id` (FK to invoices)
- `amount` (NUMERIC)
- `source_type` (VARCHAR)
- `source_id` (UUID)

### `client_payments`
- `id` (PK, UUID)
- `payment_id` (FK to payments)
- `invoice_id` (FK to invoices)

### `employee_payments`
- `id` (PK, UUID)
- `employee_id` (FK to employees)
- `project_id` (FK to projects)
- `site_id` (FK to sites)
- `period_start` (DATE)
- `period_end` (DATE)
- `gross_amount` (NUMERIC)
- `deductions` (NUMERIC)
- `net_amount` (NUMERIC)
- `payment_status` (VARCHAR)

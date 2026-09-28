# Database Architecture

> **⚠️ SUPERSEDED**: This document was the preliminary database design.
> The authoritative database model is now the **[Canonical ER Diagram](canonical-erd.md)**.
> All migrations, models, and APIs must derive from the canonical ERD.
> This document is retained for reference only.

## Entity Overview (Canonical ERD v2.0 — 23 entities)

All entities are derived from the approved requirements document and requirement triangulation. No speculative tables.

```
Phase 0 (Technical Foundation):
  users                  → Authentication and RBAC role management
  otp_tokens             → OTP request/verification tracking
  refresh_tokens         → Session persistence
  audit_logs             → Complete activity audit trail (append-only)

Phase 1 (Employee Onboarding):
  clients                → Client companies
  projects               → Project container (client → project → site hierarchy)
  employees              → Employee master data (1:1 with users)
  employee_rate_history   → Historical rate records for accurate payment calculation
  sites                  → Work sites with GPS (FK → projects, NOT clients)
  employee_site_assignments → Employee ↔ site mapping (M:N with history)

Phase 2 (Attendance):
  attendance_records     → Check-in/out with GPS, multi-session support

Phase 3 (Daily Work & Material):
  work_orders            → Project/work order master (FK → projects + sites)
  activities             → Activity type master
  materials              → Material master
  daily_work_entries     → Daily work quantities (FK → attendance, activities, work_orders)
  work_photos            → Work progress photographs
  material_transactions  → Material consumption/purchase records (renamed from material_purchases)

Phase 4 (Supervisor Verification):
  verification_records   → Supervisor approval/rejection decisions

Phase 5 (Dashboard & Invoicing):
  payroll_periods        → Payment period management
  employee_payments      → Employee payment header (gross, deductions, net)
  employee_payment_lines → Payment detail breakdown
  invoices               → Client-facing invoice records
  invoice_line_items     → Invoice detail lines
```

**Total: 23 entities across 9 domains.**

---

## Normalized Business Hierarchy

```
CLIENT
   │ 1:N
   ▼
PROJECT
   │ 1:N
   ▼
SITE ◄── employee_site_assignments ──► EMPLOYEE
   │
   ├── attendance_records
   ├── daily_work_entries → work_photos, material_transactions
   ├── work_orders (also linked to project)
   └── verification_records (via attendance/work)
```

Project context for any operational record is derived via:
```
attendance / work / material → site → project → client
```

No redundant `project_id` on operational tables.

---

## Key Schema Changes (v1.0 → v2.0)

| Change | Detail |
|--------|--------|
| **ADDED** | `projects` entity — first-class project representation |
| **ADDED** | `employee_rate_history` — temporal rate tracking |
| **ADDED** | `payroll_periods` — payment period management |
| **ADDED** | `employee_payments` — employee payment header |
| **ADDED** | `employee_payment_lines` — payment detail breakdown |
| **MODIFIED** | `sites` — replaced `client_id` with `project_id` (normalized hierarchy) |
| **MODIFIED** | `work_orders` — added `project_id` FK and `status` lifecycle field |
| **RENAMED** | `material_purchases` → `material_transactions` (supports consumed + purchased) |
| **MODIFIED** | `material_transactions` — added `site_id` FK and `transaction_type` field |
| **MODIFIED** | `attendance_records` — added `session_number`, `working_hours`, `overtime_hours` |
| **MODIFIED** | `invoices` — added `client_id`, `work_order_id`, restructured for client billing |

## Corrected FK Relationships

These relationships are confirmed and preserved:

| FK | Target | Notes |
|----|--------|-------|
| `sites.project_id` | `projects.id` | Replaces old `sites.client_id` |
| `daily_work_entries.activity_id` | `activities.id` | Required FK |
| `daily_work_entries.work_order_id` | `work_orders.id` | Optional FK |
| `daily_work_entries.attendance_record_id` | `attendance_records.id` | Required FK |
| `work_photos.daily_work_entry_id` | `daily_work_entries.id` | Required FK |
| `material_transactions.daily_work_entry_id` | `daily_work_entries.id` | Required FK |

---

## Full Relationship Summary (39 FK relationships)

See [canonical-erd.md §5](canonical-erd.md) for the complete relationship matrix.

## Migration Strategy

- Use Alembic for all schema changes.
- Phase 0: Create users, otp_tokens, refresh_tokens, audit_logs.
- Phase 1: Create clients, projects, employees, employee_rate_history, sites, employee_site_assignments.
- Phase 2: Create attendance_records.
- Phase 3: Create work_orders, activities, materials, daily_work_entries, work_photos, material_transactions.
- Phase 4: Create verification_records.
- Phase 5: Create payroll_periods, employee_payments, employee_payment_lines, invoices, invoice_line_items.

Each phase's migration builds on the previous, maintaining referential integrity.

**Total: 23 entities, 39 FK relationships, 6 phases.**

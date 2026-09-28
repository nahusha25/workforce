# Canonical ERD — Visual Summary (v3.0)

> Quick-reference visual of the database structure.
> For the authoritative entity dictionary, constraints, and traceability, see [canonical-erd.md](canonical-erd.md).

---

## Normalized Business Hierarchy

```text
CLIENT
   │
   │ 1:N
   ▼
PROJECT ─── 1:N ───► PROJECT_REVENUE / EXPENSES / INVOICES
   │
   ├── 1:N ──► SITE
   │            │
   │            ├── employee_site_assignments → EMPLOYEE
   │            ├── attendance_records
   │            ├── daily_work_entries → work_photos, material_usage
   │            ├── work_orders (also FK to project)
   │            ├── asset_management
   │            └── material_stock
   │
   └── 1:N ──► WORK_ORDER
                │
                └── daily_work_entries (optional FK)

Project context derivation:
   attendance / work / material / assets → site → project → client
```

---

## Domain Diagrams

### Identity & Workforce (RBAC & Rates)

```text
┌──────────────┐     ┌──────────────┐     ┌────────────────┐
│    roles     │ 1:N │employee_roles│ N:1 │   employees    │
│  PK id       │────▶│ FK employee_id│◀────│  PK id          │
│  name        │     │ FK role_id    │     │  employee_code  │
│  description │     └──────────────┘     │  mobile_id      │
└──────────────┘                          │  name           │
                                          │ FK supervisor_id│──┐ self-ref
                                          │  is_active      │  │
                                          │  created_at     │◄─┘
                                          │  updated_at     │
                                          └─────────────────┘
                                                  │ 1:N
                                                  ▼
                                          ┌─────────────────────┐
                                          │employee_rate_history│
                                          │  PK id              │
                                          │  FK employee_id     │
                                          │  rate_type          │
                                          │  rate_amount        │
                                          │  effective_from     │
                                          │  effective_to       │
                                          │  changed_by         │
                                          └─────────────────────┘
```

### Client → Project → Site Hierarchy

```text
┌────────────────┐
│    clients     │
│  PK id         │
│  name          │
│  contact_person│
│  contact_mobile│
│  is_active     │
│  created_at    │
└───────┬────────┘
        │ 1:N
        ▼
┌────────────────┐
│    projects    │
│  PK id         │
│  FK client_id  │
│  name          │
│  status        │
│  start_date    │
│  end_date      │
└───────┬────────┘
        │ 1:N
        ▼
┌──────────────────────┐
│        sites         │
│  PK id               │
│  FK project_id       │
│  name                │
│  address             │
│  location(geography) │
│  permitted_radius_m  │
│  FK supervisor_id    │
│  is_active           │
└──────────────────────┘
```

### Employee Site Assignments

```text
┌──────────────┐     ┌─────────────────────────┐     ┌──────────────┐
│  employees   │ 1:N │employee_site_assignments│ N:1 │    sites     │
│  PK id       │────▶│ PK id                   │◀────│  PK id       │
│              │     │ FK employee_id          │     │              │
│              │     │ FK site_id              │     │              │
│              │     │ assigned_at             │     │              │
│              │     │ unassigned_at           │     │              │
│              │     │ is_active               │     │              │
└──────────────┘     └─────────────────────────┘     └──────────────┘
```

### Master Data (Activities, Materials, Work Orders)

```text
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   activities   │     │   materials    │     │  work_orders   │
│  PK id         │     │  PK id         │     │  PK id         │
│  name          │     │  material_code │     │  order_number  │
│  default_rate  │     │  name          │     │  FK project_id │
│unit_of_measure │     │  description   │     │  FK site_id    │
└────────────────┘     │unit_of_measure │     │  description   │
                       └────────────────┘     │ target_quantity│
                                              │  start_date    │
                                              │  end_date      │
                                              │  status        │
                                              └────────────────┘
```

### Operations (Attendance & Daily Work)

```text
┌──────────────────────┐  1:N  ┌──────────────────────┐  1:N  ┌─────────────────────┐
│  attendance_records  │──────▶│  daily_work_entries  │──────▶│     work_photos     │
│  PK id               │       │ PK id                │       │ PK id               │
│  FK employee_id      │       │ FK attendance_record_id│       │ FK daily_work_entry_id│
│  FK site_id          │       │ FK employee_id       │       │ photo_url           │
│  date                │       │ FK site_id           │       │ taken_at            │
│  session_number      │       │ FK activity_id       │       │ uploaded_by         │
│  check_in_time       │       │ FK work_order_id     │       └─────────────────────┘
│check_in_location(geo)│       │ work_date            │
│  check_in_distance_m │       │ quantity             │
│  check_out_time      │       │ unit                 │
│check_out_location(geo)│      │ remarks              │
│  check_out_distance_m│       │ status               │
│  is_within_geofence  │       └──────────────────────┘
│  working_hours       │
│  overtime_hours      │
│  status              │
│  override_by         │
└──────────────────────┘
```

### Verification & Exceptions

```text
┌─────────────────────────┐       ┌───────────────────────┐
│  attendance_records     │ 1:N   │ verification_records  │
│  daily_work_entries     │──────▶│ PK id                 │
└─────────────────────────┘       │ FK attendance_record_id│ (nullable)
                                  │ FK daily_work_entry_id │ (nullable)
┌─────────────────────────┐       │ FK verified_by        │
│  entity (polymorphic)   │ 1:N   │ action                │
│  e.g., attendance/work  │──────▶└───────────────────────┘
└─────────────────────────┘
                                  ┌───────────────────────┐
                                  │    exception_flags    │
                                  │ PK id                 │
                                  │ entity_type           │
                                  │ entity_id             │
                                  │ flag_type             │
                                  │ is_resolved           │
                                  │ resolved_by           │
                                  │ created_at            │
                                  └───────────────────────┘
```

### Assets & Inventory

```text
┌──────────────┐  1:N  ┌───────────────────┐  N:1  ┌──────────────┐
│    sites     │──────▶│ asset_management  │◀────│    sites     │ (from/to)
└──────────────┘       │ PK id             │     └──────────────┘
                       │ asset_code        │            │ 1:N
                       │ name              │            ▼
                       │ FK current_site_id│     ┌────────────────┐
                       │ is_active         │     │asset_movements │
                       │ created_at        │◀────│ PK id          │
                       └───────────────────┘ 1:N │ FK asset_id    │
                                                 │ FK from_site_id│
┌──────────────┐  1:N  ┌────────────────────┐    │ FK to_site_id  │
│  materials   │──────▶│   material_stock   │    │ moved_by       │
└──────────────┘       │ PK id              │    │ moved_at       │
                       │ FK material_id     │    └────────────────┘
┌──────────────┐  1:N  │ FK site_id         │
│    sites     │──────▶│ quantity_available │
└──────────────┘       │ quantity_reserved  │
                       │ quantity_consumed  │
                       │ quantity_purchased │
                       │ updated_at         │
                       └────────────────────┘

┌──────────────────┐  1:N  ┌──────────────────────┐  N:1  ┌──────────────┐
│daily_work_entries│──────▶│    material_usage    │◀────│  materials   │
└──────────────────┘       │ PK id                │     └──────────────┘
                           │ FK daily_work_entry_id│
                           │ FK material_id       │
                           │ usage_type           │
                           │ quantity             │
                           │ created_at           │
                           └──────────────────────┘
```

### Finance & Billing

```text
┌──────────────┐ 1:N  ┌──────────────────┐
│   projects   │─────▶│ project_revenue  │
│   clients    │─────▶│ PK id            │
└──────────────┘      │ FK project_id    │
                      │ FK client_id     │
                      │ received_amount  │
                      │ currency         │
                      │ period_start     │
                      │ period_end       │
                      └──────────────────┘

┌──────────────┐ 1:N  ┌──────────────────┐
│   projects   │─────▶│     expenses     │
│   sites      │─────▶│ PK id            │
└──────────────┘      │ FK project_id    │
                      │ FK site_id       │
                      │ category         │
                      │ amount           │
                      │ expense_date     │
                      │ recorded_by      │
                      │ created_at       │
                      └──────────────────┘

┌────────────────┐ 1:N  ┌──────────────────────┐  1:N  ┌──────────────────┐
│    clients     │─────▶│       invoices       │─────▶│invoice_line_items│
│    projects    │─────▶│ PK id                │       │ PK id            │
│project_revenue │─────▶│ invoice_number       │       │ FK invoice_id    │
└────────────────┘      │ FK client_id         │       │ amount           │
                        │ FK project_id        │       │ source_type      │
                        │ FK project_revenue_id│       │ source_id        │
                        │ total_amount         │       └──────────────────┘
                        │ currency             │
                        │ invoice_date         │
                        │ due_date             │
                        │ status               │
                        │ created_at           │
                        └──────────────────────┘

┌──────────────┐ 1:N  ┌──────────────────┐
│  employees   │─────▶│employee_payments │
│  projects    │─────▶│ PK id            │
│  sites       │─────▶│ FK employee_id   │
└──────────────┘      │ FK project_id    │
                      │ FK site_id       │
                      │ period_start     │
                      │ period_end       │
                      │ gross_amount     │
                      │ deductions       │
                      │ net_amount       │
                      │ payment_status   │
                      └──────────────────┘

┌──────────────┐ 1:N  ┌──────────────────────┐  1:N  ┌──────────────────┐
│   payments   │─────▶│payment_source_records│       │ client_payments  │
│ PK id        │      │ PK id                │       │ PK id            │
│ payment_type │      │ FK payment_id        │       │ FK payment_id    │
│ amount       │      │ source_type          │       │ FK invoice_id    │
│ currency     │      │ source_id            │       └──────────────────┘
│ payment_date │      └──────────────────────┘
│ method       │ 1:N  ┌──────────────────────┐
│ status       │─────▶│   payment_receipts   │
│ recorded_by  │      │ PK id                │
│ created_at   │      │ FK payment_id        │
└──────────────┘      │ amount               │
                      │ receipt_url          │
                      │ recorded_by          │
                      │ created_at           │
                      └──────────────────────┘
```

### System & Governance

```text
┌──────────────┐  1:N  ┌───────────────────────┐
│ polymorphic  │──────▶│      audit_logs       │
└──────────────┘       │  PK id                │
                       │  entity_type          │
                       │  entity_id            │
                       │  action               │
                       │  changed_by           │
                       │  created_at           │
                       │  previous_values JSONB│
                       │  new_values JSONB     │
                       └───────────────────────┘
                       APPEND-ONLY

┌──────────────┐  1:N  ┌──────────────────────┐
│  employees   │──────▶│    notifications     │
└──────────────┘       │  PK id               │
                       │  FK employee_id      │
                       │  channel             │
                       │  recipient_mobile    │
                       │  message             │
                       │  status              │
                       │  created_at          │
                       │  sent_at             │
                       └──────────────────────┘
```

---

## Entity Count by Domain

| Domain | Entities | Count |
|--------|----------|-------|
| Core Identity & Workforce | employees, roles, employee_roles, employee_rate_history | 4 |
| Clients & Projects | clients, projects, sites, employee_site_assignments | 4 |
| Master Data | activities, materials, work_orders | 3 |
| Operations | attendance_records, daily_work_entries, work_photos, verification_records, exception_flags | 5 |
| Assets & Inventory | asset_management, asset_movements, material_stock, material_usage | 4 |
| Finance & Billing | payments, payment_source_records, payment_receipts, project_revenue, expenses, invoices, invoice_line_items, client_payments, employee_payments | 9 |
| System | audit_logs, notifications | 2 |
| **TOTAL** | | **31** |

---

## Phase Deployment Order

```text
PHASE 1 (Employee Onboarding)
├── roles
├── employees
├── employee_roles
├── employee_rate_history
├── clients
├── projects
├── sites
└── employee_site_assignments

PHASE 2 (Daily Attendance)
├── attendance_records
├── exception_flags
└── verification_records (partial)

PHASE 3 (Daily Work & Master Data)
├── activities
├── materials
├── work_orders
├── daily_work_entries
├── work_photos
└── verification_records (full)

PHASE 4 (Assets & Inventory)
├── asset_management
├── asset_movements
├── material_stock
└── material_usage

PHASE 5 (Finance, Billing, & System)
├── payments
├── payment_source_records
├── payment_receipts
├── project_revenue
├── expenses
├── invoices
├── invoice_line_items
├── client_payments
├── employee_payments
├── audit_logs
└── notifications
```

---

## Key Relationship Count

| Relationship Type | Count |
|---|---|
| Total Business Entities | 31 |
| Core Architecture Pattern | Hub-and-Spoke (Projects/Sites as Hubs) |
| Polymorphic Relationships | audit_logs, exception_flags, payment_source_records, invoice_line_items |
| Geo-Spatial Tracking | PostGIS geography in `sites` and `attendance_records` |

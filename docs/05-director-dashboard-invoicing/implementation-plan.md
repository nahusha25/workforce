# Phase 5 — Director Dashboard & Invoicing — Implementation Plan

## Requirement Scope
Provide high-level visibility to the Director through dashboard metrics and reports. Automate the generation of employee payments (weekly) and client invoices based on approved work and configurable rate cards. Export reports to Excel and PDF.

## Requirement Traceability
| Req ID | Requirement | Feature |
|--------|-------------|---------|
| REQ-DSH-001 - 008 | Dashboard metrics | Dashboard API & UI |
| REQ-RPT-001 | Filtering | Filter bar component |
| REQ-RPT-002 | Standard reports | Report APIs & Tables |
| REQ-RPT-003 | Integration APIs | OpenAPI definitions |
| REQ-DSH-009 | Invoice generation | Invoice API & UI Flow |
| REQ-DSH-010 | Excel export | Export service |
| REQ-DSH-011 | PDF export | Export service |
| REQ-BR-004 | Approval-gated | Filter all queries `status='approved'` |

---

## Database

### New Tables
1. **payroll_periods**
2. **employee_payments**
3. **employee_payment_lines**
4. **invoices**
5. **invoice_line_items**

Full schemas in [`database-plan.md`](./database-plan.md).

---

## Backend

### Module Structure
```
backend/app/modules/dashboard/
├── __init__.py
├── models.py          — Invoice, Payment SQLAlchemy models
├── schemas.py         — DashboardMetrics, ReportRow, Invoice schemas
├── service.py         — Aggregation logic
├── export_service.py  — Excel/PDF generation (openpyxl, reportlab)
├── invoice_service.py — Invoice generation calculations
└── exceptions.py      
```

### Invoice Calculation Engine (DSH-009)
1. Query `employee_rate_history` for active rates during the period.
2. Query `daily_work_entries` (`status='approved'`) for the period.
3. Calculate line items:
   - Piece rate: quantity * approved_rate
   - Daily rate: active days * daily_rate
4. Query `material_transactions` (`status='approved'`) for the period.
5. Create `invoices` and `invoice_line_items`.

### Export Service (DSH-008)
- **Excel**: Use `openpyxl`. Create headers, append rows, auto-adjust column widths. Yield via `StreamingResponse`.
- **PDF**: Use `weasyprint` (render HTML to PDF). Yield via `StreamingResponse`.

---

## Frontend

### Pages
1. **Dashboard** (`/dashboard`): 8 Metric Cards, 5 Charts (Recharts).
2. **Reports** (`/reports/:type`): Data table with pagination and Export buttons.
3. **Invoicing** (`/invoices`): List and Generation form.

### Key Components
- **FilterBar**: Global date/site/client selector. Syncs to URL params.
- **MetricCard**: Large number display with trend indicator.
- **ReportTable**: Reusable sortable table.
- **InvoicePreview**: Print-friendly view of generated invoices.

---

## Dependencies
| Dependency | Source | Required For |
|-----------|--------|-------------|
| Approved data | Phase 4 | All metrics/invoices |
| Rate configurations | Phase 1 | Invoice calculations |
| Client/Site data | Phase 1 | Filters and Invoice grouping |

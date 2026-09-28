# Phase 5 — Director Dashboard & Invoicing — Requirements

## Source Reference
- Page 5: "Director Dashboard & Invoicing"
- Business Rules: REQ-BR-004 (approval-gated calculations)
- Reporting: REQ-RPT-001, REQ-RPT-002, REQ-RPT-003

## Requirement Scope
Provide directors with a consolidated dashboard showing manpower, progress, productivity, and cost metrics across all sites. Enable weekly employee payment/invoice generation and report export.

## Actors
| Role | Actions |
|------|---------|
| Director | View dashboard, filter data, drill into reports, generate invoices, export reports |

## Functional Requirements
| ID | Requirement |
|----|-------------|
| REQ-DSH-001 | Show date-wise manpower |
| REQ-DSH-002 | Show working hours |
| REQ-DSH-003 | Show client/site progress |
| REQ-DSH-004 | Show cable metres |
| REQ-DSH-005 | Show devices installed |
| REQ-DSH-006 | Show employee productivity |
| REQ-DSH-007 | Show material cost |
| REQ-DSH-008 | Show approval status |
| REQ-DSH-009 | Generate weekly employee payment/invoice based on approved work or attendance and configured rates |
| REQ-DSH-010 | Export to Excel |
| REQ-DSH-011 | Export to PDF |
| REQ-RPT-001 | Dashboard filters: date, client, site, employee, supervisor |
| REQ-RPT-002 | Reports: attendance, approved work, materials, productivity, weekly payment, client/site invoice summary |
| REQ-RPT-003 | APIs for future integration (payroll, accounting, ERP, WhatsApp, billing) |

## Business Rules
1. Only **supervisor-approved** data is used for dashboard metrics, payments, and invoices (REQ-BR-004).
2. Invoice calculation uses employee's configured rate type and rate amount.
3. Daily rate: days worked × daily rate.
4. Weekly rate: weeks (or pro-rata) × weekly rate.
5. Piece rate: approved quantities × piece rate.
6. Material costs are separate from labour costs.
7. Invoice generation is triggered manually by director (not automatic).

## Metric Definitions

| Metric | Calculation | Source |
|--------|-------------|--------|
| Date-wise manpower | COUNT(DISTINCT employee_id) per date WHERE status='approved' | attendance_records |
| Working hours | SUM(check_out_time - check_in_time) WHERE status='approved' | attendance_records |
| Client/site progress | SUM(approved quantities) per site | daily_work_entries |
| Cable metres | SUM(cable_length_metres) WHERE status='approved' | daily_work_entries |
| Devices installed | SUM(devices_installed) WHERE status='approved' | daily_work_entries |
| Employee productivity | (Approved work output) / (Working hours) per employee | derived |
| Material cost | SUM(amount) WHERE status='approved' | material_purchases |
| Approval status | COUNT(*) GROUP BY status | attendance + daily_work |

## State Transitions
### Invoice Status
```
Generated → draft
draft → Finalised
```

## Validation Rules
| Field | Rule |
|-------|------|
| period_start | Required, valid date |
| period_end | Required, ≥ period_start |
| Invoice amounts | Calculated, not user-editable |

## Acceptance Criteria
- [ ] Dashboard shows all 8 metrics (manpower, hours, progress, cable, devices, productivity, material cost, approval status)
- [ ] All metrics use only approved data
- [ ] Dashboard filters work (date range, client, site, employee, supervisor)
- [ ] Director can generate weekly payment/invoice
- [ ] Invoice calculation uses correct rate type and amount
- [ ] Reports exportable to Excel
- [ ] Reports exportable to PDF
- [ ] API contracts documented for future integration

## Dependencies
- Phase 4 complete (approved data must exist)
- All previous phases operational

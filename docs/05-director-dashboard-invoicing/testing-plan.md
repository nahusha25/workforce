# Phase 5 — Testing Plan

## Database Tests
- [ ] invoices: period_end ≥ period_start CHECK
- [ ] invoices: total_amount ≥ 0 CHECK
- [ ] invoices: status CHECK IN ('draft','finalised')
- [ ] invoices: invoice_number UNIQUE
- [ ] invoice_line_items: amount ≥ 0 CHECK
- [ ] invoice_line_items: FK→invoices

## Service Tests
- [ ] Dashboard metrics aggregate only approved data
- [ ] Manpower count is DISTINCT employees per date
- [ ] Working hours calculated correctly from check-in/out
- [ ] Cable metres sum is correct
- [ ] Device count is correct
- [ ] Material cost sum is correct
- [ ] Productivity calculated correctly
- [ ] Approval status counts correct
- [ ] Filters (date, site, client, employee) work correctly
- [ ] Invoice daily rate: approved_days × rate_amount
- [ ] Invoice weekly rate: approved_weeks × rate_amount
- [ ] Invoice piece rate: approved_quantities × rate
- [ ] Invoice total is sum of line items
- [ ] Excel export generates valid .xlsx
- [ ] PDF export generates valid .pdf

## API Tests
- [ ] GET /dashboard/metrics — director → 200
- [ ] GET /dashboard/metrics — non-director → 403
- [ ] GET /dashboard/metrics — filters work
- [ ] GET /reports/attendance — paginated data
- [ ] GET /reports/{type}/export?format=xlsx — file download
- [ ] GET /reports/{type}/export?format=pdf — file download
- [ ] POST /invoices/generate — valid → 201
- [ ] POST /invoices/generate — invalid dates → 422
- [ ] POST /invoices/generate — non-director → 403
- [ ] GET /invoices — list
- [ ] GET /invoices/{id} — detail with line items

## E2E Tests
- [ ] E2E-J13: Director views dashboard with data
- [ ] E2E-J14: Director generates weekly invoice
- [ ] E2E-J15: Director exports report to Excel/PDF
- [ ] E2E-J16: Full flow — employee submits → supervisor approves → director sees in dashboard

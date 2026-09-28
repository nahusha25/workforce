# Phase 5 — Director Dashboard & Invoicing — Task List

## Database Tasks

```
Task ID: DB-017
Task: Create payroll_periods table
Layer: Database
Requirement Reference: REQ-DSH-009
Purpose: Define payroll periods (weekly/monthly) for payment calculation grouping
Description: Create payroll_periods with id (UUID PK), period_type CHECK ('weekly','monthly'), period_start (DATE), period_end (DATE CHECK >= period_start), status CHECK ('open','processing','closed'), created_by FK→users, timestamps.
Dependencies: DB-001 (users)
Implementation Details: Alembic migration. CHECK(period_end >= period_start). CHECK(period_type IN ('weekly','monthly')). CHECK(status IN ('open','processing','closed')). Index on status, period_start.
Expected Output: Migration file, payroll_periods table created
Validation: Valid period creates; end < start rejected; invalid status rejected
Acceptance Criteria: Payroll periods persistable with date and status constraints
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-018
Task: Create employee_payments table
Layer: Database
Requirement Reference: REQ-DSH-009
Purpose: Store calculated employee payment records per payroll period
Description: Create employee_payments with id (UUID PK), FK→payroll_periods, FK→employees, gross_amount (NUMERIC(12,2) CHECK >= 0), deductions (NUMERIC(12,2) CHECK >= 0), net_amount (NUMERIC(12,2) CHECK >= 0), status CHECK ('draft','finalised','paid'), generated_by FK→users, generated_at (TIMESTAMPTZ), timestamps. UNIQUE(payroll_period_id, employee_id).
Dependencies: DB-017 (payroll_periods), DB-007 (employees)
Implementation Details: Alembic migration. UNIQUE constraint prevents duplicate payments per period. All amount fields CHECK >= 0. Index on employee_id, payroll_period_id.
Expected Output: Migration file, employee_payments table created
Validation: Valid payment creates; duplicate period+employee rejected; negative amounts rejected
Acceptance Criteria: Employee payments persistable with amount constraints and uniqueness
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-019
Task: Create employee_payment_lines table
Layer: Database
Requirement Reference: REQ-DSH-009
Purpose: Store individual line items that make up an employee payment (attendance, work, overtime, deductions)
Description: Create employee_payment_lines with id (UUID PK), FK→employee_payments, line_type CHECK ('attendance','work_quantity','overtime','deduction','allowance'), description (TEXT), quantity (NUMERIC(10,2)), rate (NUMERIC(12,2)), amount (NUMERIC(12,2)), source_type CHECK (NULL or 'attendance_record','daily_work_entry'), source_id (UUID nullable — polymorphic reference), timestamps.
Dependencies: DB-018 (employee_payments)
Implementation Details: Alembic migration. Line type determines calculation logic. Source_type + source_id provide traceability back to approved data. Index on employee_payment_id.
Expected Output: Migration file, employee_payment_lines table created
Validation: Valid line creates; invalid line_type rejected; FK constraint enforced
Acceptance Criteria: Payment lines traceable to source records
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-020
Task: Create invoices table
Layer: Database
Requirement Reference: REQ-DSH-009, REQ-DSH-010, REQ-DSH-011
Purpose: Store generated invoices for client billing
Description: Create invoices with id (UUID PK), invoice_number (VARCHAR(50) UNIQUE), FK→clients, FK→sites (nullable), FK→work_orders (nullable), FK→projects (nullable), period_start (DATE), period_end (DATE CHECK >= period_start), total_amount (NUMERIC(12,2) CHECK >= 0), tax_amount (NUMERIC(12,2) DEFAULT 0), status CHECK ('draft','finalised'), generated_by FK→users, timestamps.
Dependencies: DB-005 (clients), DB-006 (sites)
Implementation Details: Alembic migration. Invoice number auto-generated (e.g., INV-YYYYMMDD-NNN). UNIQUE on invoice_number. CHECK(period_end >= period_start). Index on client_id, site_id, period dates.
Expected Output: Migration file, invoices table created
Validation: Valid invoice creates; duplicate number rejected; invalid dates rejected; negative amount rejected
Acceptance Criteria: Invoices persistable with all constraints
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-021
Task: Create invoice_line_items table
Layer: Database
Requirement Reference: REQ-DSH-009
Purpose: Store individual line items that make up an invoice (labour, materials, etc.)
Description: Create invoice_line_items with id (UUID PK), FK→invoices, description (TEXT), quantity (NUMERIC(10,2)), rate (NUMERIC(12,2)), amount (NUMERIC(12,2) CHECK >= 0), source_type CHECK (NULL or 'attendance','daily_work','material'), source_id (UUID nullable), timestamps.
Dependencies: DB-020 (invoices)
Implementation Details: Alembic migration. CHECK(amount >= 0). Index on invoice_id. Source references provide traceability to approved data.
Expected Output: Migration file, invoice_line_items table created
Validation: Valid line creates; negative amount rejected; FK constraint enforced
Acceptance Criteria: Invoice line items traceable to source records
Definition of Done: Migration exists, constraints verified, tests pass
```

## Backend Tasks

```
Task ID: BE-027
Task: Create dashboard metric aggregation service
Layer: Backend / Dashboard Module
Requirement Reference: REQ-DSH-001 to REQ-DSH-008, REQ-BR-004
Purpose: Aggregate approved data into the 8 dashboard metrics
Description: Implement modules/dashboard/service.py with get_dashboard_metrics(filters). Calculate:
  - Manpower: COUNT(DISTINCT employee_id) from attendance_records WHERE status='approved'
  - Working hours: SUM(working_hours) from attendance_records WHERE status='approved'
  - Client/site progress: SUM(quantities) from daily_work_entries WHERE status='approved' GROUP BY site
  - Cable metres: SUM(cable_length_metres) from daily_work_entries WHERE status='approved'
  - Devices installed: SUM(devices_installed) from daily_work_entries WHERE status='approved'
  - Employee productivity: (Approved work output) / (Working hours) per employee
  - Material cost: SUM(amount) from material_transactions WHERE status='approved'
  - Approval status: COUNT(*) GROUP BY status across attendance + work
Dependencies: Phase 4 complete (approved data must exist)
Implementation Details: All queries filter by status='approved' (REQ-BR-004). Support date_from, date_to, client_id, site_id, employee_id, supervisor_id filters. Use SQLAlchemy aggregation queries. Return structured DashboardMetrics Pydantic model.
Expected Output: Dashboard metric aggregation service returning all 8 metrics
Validation: Only approved data included; filters work correctly; calculations verified against test data
Acceptance Criteria: All 8 metrics calculated correctly from approved data only
Definition of Done: Service tests pass with verified calculations, >90% coverage
```

```
Task ID: BE-028
Task: Create report data services
Layer: Backend / Dashboard Module
Requirement Reference: REQ-RPT-002
Purpose: Generate report data for attendance, work, materials, productivity, payment, and invoice summary
Description: Implement report generation for 6 report types:
  - Attendance report: approved attendance records with employee, site, times, hours
  - Approved work report: approved work entries with quantities by activity
  - Materials report: approved material transactions with items, quantities, amounts
  - Productivity report: employee productivity (output/hours) rankings
  - Weekly payment report: payment summary per employee for period
  - Client/site invoice summary: total labour + materials per site for period
Dependencies: BE-027 (shared aggregation patterns)
Implementation Details: Each report returns paginated tabular data. Support same filter parameters as dashboard. Reuse aggregation query patterns from dashboard service. Return structured data suitable for both display and export.
Expected Output: 6 report data services with filtering and pagination
Validation: Reports return correct data; filters work; pagination works
Acceptance Criteria: All 6 report types generate correct data from approved records
Definition of Done: Service tests pass for each report type
```

```
Task ID: BE-029
Task: Create dashboard and report API endpoints (DSH-001 through DSH-007)
Layer: Backend / API
Requirement Reference: REQ-DSH-001 to REQ-DSH-008, REQ-RPT-001, REQ-RPT-002
Purpose: REST endpoints for dashboard metrics and report data
Description: Implement api/v1/dashboard.py and api/v1/reports.py with:
  - DSH-001: GET /api/v1/dashboard/metrics — all 8 metrics with filter support
  - DSH-002: GET /api/v1/reports/attendance — attendance report
  - DSH-003: GET /api/v1/reports/work — approved work report
  - DSH-004: GET /api/v1/reports/materials — materials report
  - DSH-005: GET /api/v1/reports/productivity — productivity report
  - DSH-006: GET /api/v1/reports/payment — weekly payment summary
  - DSH-007: GET /api/v1/reports/invoice-summary — client/site invoice summary
Dependencies: BE-027, BE-028
Implementation Details: Director role required for all endpoints. Filter parameters: date_from, date_to, client_id, site_id, employee_id, supervisor_id. Paginated responses for reports. Thin route handlers calling service layer.
Expected Output: 7 dashboard/report API endpoints with RBAC and filtering
Validation: All endpoints return correct data; filters work; director role enforced
Acceptance Criteria: Dashboard and reports functional with proper authorisation
Definition of Done: API tests pass, Swagger verified, RBAC confirmed
```

```
Task ID: BE-030
Task: Create report export service (Excel via openpyxl, PDF via reportlab/weasyprint)
Layer: Backend / Dashboard Module
Requirement Reference: REQ-DSH-010, REQ-DSH-011
Purpose: Generate downloadable report files in Excel and PDF formats
Description: Implement export functionality that takes report data (from BE-028) and generates formatted files:
  - Excel: Use openpyxl. Create workbook with headers, data rows, summary row, column formatting, auto-width.
  - PDF: Use reportlab or weasyprint. Create formatted report with header, table, totals, page numbers.
Dependencies: BE-028
Implementation Details: Reports generated server-side. Return file as streaming response with correct Content-Type and Content-Disposition. Temporary file generated and cleaned up after response. No employee PII in file names (use report type + date range).
Expected Output: Excel and PDF export for all 6 report types
Validation: Excel opens correctly in Excel/LibreOffice; PDF renders correctly; data matches report API
Acceptance Criteria: Reports downloadable in both Excel and PDF formats
Definition of Done: Both formats generate correctly, data verified, file cleanup confirmed
```

```
Task ID: BE-031
Task: Create export API endpoint (DSH-008)
Layer: Backend / API
Requirement Reference: REQ-DSH-010, REQ-DSH-011
Purpose: REST endpoint for downloading reports as Excel or PDF
Description: Implement: GET /api/v1/reports/{type}/export?format=xlsx|pdf&date_from=&date_to=&... Returns file download with appropriate Content-Type header.
Dependencies: BE-030
Implementation Details: Path parameter {type}: attendance, work, materials, productivity, payment, invoice-summary. Query parameter format: xlsx or pdf. Return StreamingResponse with correct headers. Director role required.
Expected Output: Report export API endpoint
Validation: xlsx and pdf downloads work; invalid format returns 422; director role enforced
Acceptance Criteria: Director can download any report as Excel or PDF
Definition of Done: API tests pass, both formats downloadable, Swagger verified
```

```
Task ID: BE-032
Task: Create invoice generation service
Layer: Backend / Dashboard Module
Requirement Reference: REQ-DSH-009
Purpose: Calculate and generate invoices from approved attendance, work, and material data
Description: Implement invoice generation with calculation logic:
  - Daily rate employees: approved_days × daily_rate_amount
  - Weekly rate employees: (approved_days / 7) × weekly_rate_amount (pro-rata)
  - Piece rate employees: approved_quantities × activity_approved_rate or employee_rate_amount
  - Material costs: SUM of approved material transaction amounts (separate line items)
  - Create invoice record with auto-generated invoice_number
  - Create invoice_line_items for each calculation component
  - Create employee_payment record and employee_payment_lines for each employee
Dependencies: Phase 4 complete, employee_rate_history, approved data
Implementation Details: Lookup employee's effective rate from employee_rate_history (where effective_to IS NULL or effective_to >= period_end). Calculate line items. Sum to total. Invoice number format: INV-YYYYMMDD-NNN (sequential). All amounts from approved data only.
Expected Output: Invoice generation service with correct rate calculations
Validation: Daily rate calculation verified; weekly pro-rata verified; piece rate verified; material costs correct; invoice number unique
Acceptance Criteria: Invoices generated correctly from approved data + configured rates
Definition of Done: Service tests pass with verified calculations for all rate types
```

```
Task ID: BE-033
Task: Create invoice API endpoints (DSH-009 through DSH-011)
Layer: Backend / API
Requirement Reference: REQ-DSH-009
Purpose: REST endpoints for invoice generation, listing, and detail
Description: Implement:
  - DSH-009: POST /api/v1/invoices/generate — generate invoice for period + site/employee
  - DSH-010: GET /api/v1/invoices — paginated invoice list with filters
  - DSH-011: GET /api/v1/invoices/{id} — invoice detail with line items
Dependencies: BE-032
Implementation Details: Director role required. Generate accepts: period_start, period_end, site_id (optional), employee_id (optional). List supports: date range, client, site, status filters. Detail includes all line items with source traceability.
Expected Output: 3 invoice API endpoints with RBAC
Validation: Invoice generation creates correct records; list paginates; detail shows line items
Acceptance Criteria: Director can generate, list, and view invoices
Definition of Done: API tests pass, Swagger verified, calculations confirmed
```

```
Task ID: BE-034
Task: Document future integration API contracts in OpenAPI
Layer: Backend / Documentation
Requirement Reference: REQ-RPT-003
Purpose: Document API contracts for future external system integrations
Description: Create OpenAPI documentation for future integration endpoints: payroll system export, accounting system export, ERP data exchange, WhatsApp notification webhooks, client billing system interface. Document request/response schemas, authentication requirements (API key), and data formats. These APIs are documented but NOT implemented in Phase 5.
Dependencies: BE-029, BE-033 (understand internal API patterns)
Implementation Details: Add integration API specifications to OpenAPI schema as documented-only endpoints. Include authentication scheme (API key header). Define data schemas matching internal models. Mark as "planned — not yet implemented."
Expected Output: OpenAPI documentation for 5 future integration API contracts
Validation: Documentation is clear and complete; schemas are consistent with internal models
Acceptance Criteria: Future integration requirements documented as API contracts
Definition of Done: API contracts documented in OpenAPI spec, reviewed for completeness
```

## Swagger Tasks

```
Task ID: SWG-005
Task: Execute Phase 5 Swagger test plan
Layer: Swagger
Requirement Reference: All Phase 5 requirements
Purpose: Manual API verification of all Phase 5 endpoints via Swagger UI
Description: Execute all test cases defined in swagger-test-plan.md for DSH-001 through DSH-011. Test dashboard metrics, reports, exports, and invoice generation with valid and invalid inputs.
Dependencies: BE-029, BE-031, BE-033
Implementation Details: Use Swagger UI at /api/docs. Test each endpoint with various filter combinations. Verify metric calculations against known test data. Download and open export files. Generate test invoices and verify line items.
Expected Output: All Swagger test cases executed and passing
Validation: Every test case has a recorded result; calculations verified
Acceptance Criteria: All endpoints behave as specified; calculations are correct
Definition of Done: All test cases executed, results documented, no critical failures
```

## Frontend Tasks

```
Task ID: FE-021
Task: Create dashboard overview page with metric cards
Layer: Frontend
Requirement Reference: REQ-DSH-001 to REQ-DSH-008, REQ-UX-005
Purpose: Director dashboard showing all 8 metrics with visual indicators
Description: Build dashboard overview page with metric cards for: manpower count, working hours total, cable metres, devices installed, employee productivity, material cost, approval status breakdown. Each card shows current value, optional trend indicator, and link to detail report. Grid layout (2 cols on mobile, 4 on desktop).
Dependencies: FE-002 (app shell), BE-029 (dashboard APIs)
Implementation Details: Cards with large numbers, descriptive labels, and subtle icons. Loading skeleton states. Error states per card. Auto-refresh every 5 minutes. Colour-coded cards (green for positive trends, amber for attention).
Expected Output: Dashboard overview page with 8 metric cards
Validation: All 8 metrics display correctly; loading states work; responsive layout; auto-refresh
Acceptance Criteria: Director sees all key metrics at a glance
Definition of Done: Page functional, responsive, all metrics populated, accessible
```

```
Task ID: FE-022
Task: Create filter bar component (date, client, site, employee, supervisor)
Layer: Frontend
Requirement Reference: REQ-RPT-001
Purpose: Reusable filter bar for dashboard and report pages
Description: Build a filter bar component with: date range picker (from/to), client dropdown, site dropdown (filtered by selected client), employee dropdown, supervisor dropdown. Filters apply to dashboard metrics and all report views. Support URL query params for shareable filtered views.
Dependencies: FE-001 (design system), admin APIs (for dropdown data)
Implementation Details: Responsive: collapsible on mobile (expandable filter panel), inline on desktop. Dropdowns with search. Clear all button. Apply button (or auto-apply on change). Sync filters to URL params. Remember last-used filters in session.
Expected Output: Reusable filter bar component with all 5 filter types
Validation: Filters apply to data correctly; cascading site filter works; responsive; URL sync works
Acceptance Criteria: Director can filter all dashboard and report data
Definition of Done: Filter bar functional, responsive, all filter types working, URL persistence
```

```
Task ID: FE-023
Task: Integrate chart library and create dashboard charts
Layer: Frontend
Requirement Reference: REQ-DSH-001 to REQ-DSH-008
Purpose: Visual charts for dashboard metrics (trends, breakdowns, comparisons)
Description: Integrate a lightweight chart library (e.g., Recharts or Chart.js) and create: (1) Bar chart — daily manpower trend. (2) Line chart — working hours over time. (3) Stacked bar — work quantities by site. (4) Pie/donut — approval status breakdown. (5) Bar chart — employee productivity ranking. Charts should be interactive (hover tooltips) and responsive.
Dependencies: FE-021, chart library
Implementation Details: Use Recharts (React-native charts) or Chart.js with react-chartjs-2. Responsive container. Consistent colour palette from design tokens. Loading skeletons for chart areas. Mobile: charts full width, scrollable. Empty state when no data.
Expected Output: 5 interactive dashboard charts
Validation: Charts render correct data; responsive; tooltips work; empty states handled
Acceptance Criteria: Director sees visual data trends and breakdowns
Definition of Done: Charts functional, responsive, interactive, consistent styling
```

```
Task ID: FE-024
Task: Create report view pages with sortable tables
Layer: Frontend
Requirement Reference: REQ-RPT-002
Purpose: Detailed report pages for each of the 6 report types
Description: Build report detail pages for: attendance, approved work, materials, productivity, weekly payment, client/site invoice summary. Each page features: filter bar (reused), sortable data table with pagination, column visibility toggle, summary/totals row, export buttons.
Dependencies: FE-022 (filter bar), BE-029 (report APIs)
Implementation Details: Reusable report table component with sorting, pagination, and column toggle. Summary row at bottom with totals. Mobile: horizontal scroll for wide tables, or card-based alternative view. Print-friendly CSS.
Expected Output: 6 report view pages with sortable, paginated tables
Validation: Data displays correctly; sorting works; pagination works; responsive; totals correct
Acceptance Criteria: Director can view detailed reports with sorting and filtering
Definition of Done: All 6 report pages functional, responsive, sortable, paginated
```

```
Task ID: FE-025
Task: Create export buttons with download handling
Layer: Frontend
Requirement Reference: REQ-DSH-010, REQ-DSH-011
Purpose: Export buttons on report pages for downloading Excel and PDF files
Description: Build export button group (Excel, PDF) on each report page. Clicking triggers download from the export API endpoint. Show loading state during generation. Handle errors (empty report, generation failure). Preserve current filter context in export.
Dependencies: FE-024, BE-031 (export API)
Implementation Details: Download via fetch with blob response. Create temporary anchor element for download trigger. Pass current filter params to export API. Loading spinner on button during generation. Toast notification on success/error.
Expected Output: Excel and PDF export buttons on all report pages
Validation: Both formats download correctly; current filters applied; loading state visible; errors handled
Acceptance Criteria: Director can export any report as Excel or PDF
Definition of Done: Both export formats work, filter context preserved, error handling complete
```

```
Task ID: FE-026
Task: Create invoice generation form and preview
Layer: Frontend
Requirement Reference: REQ-DSH-009
Purpose: Form for generating invoices and previewing calculated results before finalisation
Description: Build invoice generation flow: (1) Form: select period start/end, site (optional), employee (optional). (2) Preview: after generation, show invoice with calculated line items — labour lines (by rate type), material cost lines, totals. (3) Finalise button to change status from draft to finalised. (4) Print/export options on preview.
Dependencies: FE-022 (filter components), BE-033 (invoice APIs)
Implementation Details: Step-by-step flow: select parameters → generate (API call) → preview result → finalise or discard. Preview shows: employee name, rate type, quantity, rate, amount for each line. Totals section: gross labour, material cost, total. Print CSS for clean invoice printout.
Expected Output: Invoice generation form with preview and finalisation
Validation: Invoice generates correctly; line items match calculation; finalise changes status; preview is printable
Acceptance Criteria: Director can generate, preview, and finalise invoices
Definition of Done: Generation flow complete, calculations verified, print preview works
```

```
Task ID: FE-027
Task: Create invoice list page
Layer: Frontend
Requirement Reference: REQ-DSH-009
Purpose: Paginated list of all generated invoices with filters and drill-down
Description: Build invoice list page showing: invoice number, client/site, period, total amount, status, generation date. Filters: date range, client, site, status. Sortable columns. Click to view invoice detail with line items. Status badges (draft, finalised).
Dependencies: FE-022, BE-033 (invoice APIs)
Implementation Details: Reuse report table component. Status badge colours (grey=draft, green=finalised). Click row to navigate to invoice detail (reuse preview component in read-only mode). Pagination.
Expected Output: Invoice list page with filtering and drill-down
Validation: List displays correct data; filters work; sorting works; drill-down shows detail
Acceptance Criteria: Director can browse and manage generated invoices
Definition of Done: List page functional, filters work, drill-down works, responsive
```

## Testing Tasks

```
Task ID: TEST-011
Task: Database constraint tests for invoice and payment tables
Layer: Testing
Requirement Reference: All Phase 5 database requirements
Purpose: Verify all constraints on payroll_periods, employee_payments, employee_payment_lines, invoices, invoice_line_items
Description: Test: (1) payroll_periods — date constraint, status CHECK, period_type CHECK. (2) employee_payments — UNIQUE(period, employee), amount >= 0 for all, status CHECK. (3) employee_payment_lines — line_type CHECK, source_type CHECK. (4) invoices — UNIQUE invoice_number, date constraint, amount >= 0, status CHECK. (5) invoice_line_items — amount >= 0.
Dependencies: DB-017 through DB-021
Implementation Details: pytest with database fixtures. Test valid inserts and all constraint violations.
Expected Output: Database constraint test suite for all 5 Phase 5 tables
Validation: All constraints enforced as specified in database plan
Acceptance Criteria: Every constraint has a corresponding test
Definition of Done: All tests pass, constraint coverage complete
```

```
Task ID: TEST-012
Task: Service tests for metrics, reports, and invoice calculation
Layer: Testing
Requirement Reference: REQ-DSH-001 to REQ-DSH-011, REQ-BR-004
Purpose: Unit/integration tests for dashboard metrics, report generation, and invoice calculation logic
Description: Test: (1) Dashboard metrics — each of 8 metrics calculated correctly with known test data; only approved data included; filters work correctly. (2) Report data — each of 6 reports returns correct data structure and values. (3) Invoice calculation — daily rate: days × rate; weekly rate: pro-rata calculation; piece rate: qty × rate; material costs separate; totals correct. (4) Export — Excel and PDF files generated without errors.
Dependencies: BE-027, BE-028, BE-030, BE-032
Implementation Details: pytest with rich test data fixtures covering multiple employees, rate types, sites, and date ranges. Verify calculations against manually computed expected values. Test edge cases: zero approved data, single employee, mixed rate types.
Expected Output: Comprehensive test suite for all Phase 5 services
Validation: All calculations verified against expected values; edge cases handled
Acceptance Criteria: Every metric, report, and calculation has thorough test coverage
Definition of Done: Tests pass, >90% service coverage, calculations verified
```

```
Task ID: TEST-013
Task: API integration tests for all Phase 5 endpoints
Layer: Testing
Requirement Reference: All Phase 5 API requirements
Purpose: Integration tests for all 11 dashboard, report, export, and invoice endpoints
Description: Test all endpoints DSH-001 through DSH-011 with: valid director requests, non-director roles (403), filter combinations, pagination, export downloads, invoice generation with various parameters.
Dependencies: BE-029, BE-031, BE-033
Implementation Details: pytest with httpx AsyncClient. Test each endpoint with authenticated director token. Verify response codes, data structure, and content. Test export file downloads. Verify invoice line items match calculation.
Expected Output: API integration test suite for all Phase 5 endpoints
Validation: All endpoints return correct status codes and data; RBAC enforced
Acceptance Criteria: Every API endpoint has integration tests
Definition of Done: All API tests pass, RBAC verified, calculations confirmed
```

## E2E Tasks

```
Task ID: E2E-006
Task: E2E tests for dashboard, invoice, and export journeys
Layer: E2E
Requirement Reference: REQ-DSH-001 to REQ-DSH-011
Purpose: End-to-end Playwright tests for director dashboard workflows
Description: Test journeys: (1) Director opens dashboard → sees all 8 metric cards with data → applies date filter → metrics update. (2) Director navigates to attendance report → sees data table → exports as Excel → file downloads. (3) Director generates invoice → selects period and site → previews line items → finalises → invoice appears in list. (4) Director exports PDF report → file downloads correctly.
Dependencies: All Phase 5 implementation
Implementation Details: Playwright with desktop viewport (director typically uses desktop). Create test data through API fixtures (approved attendance + work). Verify metric values on screen. Download and verify file existence. Invoice preview content verification.
Expected Output: E2E test files covering dashboard, reporting, and invoicing journeys
Validation: All journeys pass; metrics display correctly; exports download; invoices generate
Acceptance Criteria: Complete dashboard → report → invoice workflow tested end-to-end
Definition of Done: E2E tests pass reliably, screenshots captured, files downloaded
```

```
Task ID: E2E-007
Task: E2E cross-phase test (submit → approve → dashboard)
Layer: E2E
Requirement Reference: REQ-BR-004 (approval-gated calculations)
Purpose: End-to-end test verifying data flows correctly from employee submission through supervisor approval to director dashboard
Description: Full cross-phase journey: (1) Employee checks in → creates work entry → uploads photo → submits work → checks out. (2) Supervisor opens verification queue → reviews employee's day → approves. (3) Director opens dashboard → sees approved data reflected in metrics → generates invoice → verifies line items match approved work + configured rates.
Dependencies: All Phase 1–5 implementation
Implementation Details: Playwright multi-user test across 3 roles. Create employee, supervisor, and director test users. Full workflow from data entry through dashboard. Verify data integrity at each step. This is the most critical E2E test in the system.
Expected Output: Cross-phase E2E test file covering the complete business workflow
Validation: Data flows correctly through all 5 phases; calculations verified end-to-end
Acceptance Criteria: Complete workforce management workflow verified from entry to invoice
Definition of Done: Cross-phase E2E test passes reliably, data integrity confirmed
```

## Security Tasks

```
Task ID: SEC-005
Task: Security review of dashboard data access, export files, and invoice generation
Layer: Security
Requirement Reference: REQ-SEC-001, REQ-DSH-001 to REQ-DSH-011
Purpose: Security audit of Phase 5 data access and file generation
Description: Audit: (1) Role enforcement — all dashboard, report, export, and invoice endpoints require director role. Test with other role tokens. (2) Data scope — director sees all data (not filtered by assignment like supervisor). Verify no data leakage of unapproved records. (3) Export file security — generated files served via temporary URLs or streaming response, not persisted publicly. No employee PII in file names. (4) Invoice integrity — amounts are server-calculated, not user-editable. Invoice numbers are sequential and unique. (5) Report data — only approved data appears in metrics and reports (REQ-BR-004). Test by creating non-approved data and verifying it's excluded. (6) Future integration APIs — when documented, include API key authentication scheme.
Dependencies: All Phase 5 implementation
Implementation Details: Follow security audit workflow (.ai/workflows/security-audit.md). Report findings before remediation.
Expected Output: Security audit report with findings categorised by severity
Validation: No critical or high-severity findings remain after remediation
Acceptance Criteria: Phase 5 passes security review
Definition of Done: Audit complete, findings addressed, re-audit confirms no critical/high issues
```

## Documentation Tasks

```
Task ID: DOC-005
Task: Update Phase 5 documentation after implementation
Layer: Documentation
Requirement Reference: All Phase 5 requirements
Purpose: Ensure Phase 5 documentation matches actual implementation
Description: Review and update all Phase 5 documentation. Ensure metric calculations are accurately documented. Update API contracts with actual request/response schemas. Document invoice number format and generation logic. Update export file formats and content.
Dependencies: All Phase 5 tasks complete
Implementation Details: Cross-reference implemented code with documentation. Document any calculation formula decisions. Update task-list.md statuses.
Expected Output: Updated Phase 5 documentation matching implementation
Validation: Documentation accurately reflects the implemented system
Acceptance Criteria: No documentation contradicts implementation
Definition of Done: All Phase 5 docs reviewed and updated
```

```
Task ID: DOC-006
Task: Document future integration API contracts
Layer: Documentation
Requirement Reference: REQ-RPT-003
Purpose: Create comprehensive API contract documentation for future external integrations
Description: Document API contracts for: (1) Payroll system export — employee payment data in standard format. (2) Accounting system — invoice data export. (3) ERP data exchange — attendance and work data. (4) WhatsApp notifications — webhook format for alerts. (5) Client billing — invoice delivery format. Each contract includes: endpoint, authentication, request/response schema, error codes, rate limits.
Dependencies: BE-034 (OpenAPI documentation)
Implementation Details: Create detailed API contract document or extend OpenAPI spec. Include sequence diagrams for integration flows. Document data mapping between internal and external formats.
Expected Output: Future integration API contracts documentation
Validation: Contracts are clear, complete, and consistent with internal models
Acceptance Criteria: External developer can understand integration requirements from documentation alone
Definition of Done: Contracts documented, schemas defined, reviewed for completeness
```

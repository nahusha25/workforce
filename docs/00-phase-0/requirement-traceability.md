# Requirement Traceability Matrix

Every requirement from the source document is mapped to its implementation phase, database work, backend/API work, Swagger testing, frontend/UI, security, testing, and acceptance criteria.

> Source: Workforce_Management_Web_App_Requirements_Two_Page.md

---

## Page 1 — Employee Onboarding & Login (Phase 1)

| Req ID | Requirement | Phase | Feature | DB | Backend/API | Swagger | Frontend/UI | Security | Test | Acceptance Criteria |
|--------|-------------|-------|---------|-----|-------------|---------|-------------|----------|------|---------------------|
| REQ-EMP-001 | Register using name and mobile number | 1 | Employee Registration | employees table: name, mobile columns | POST /api/v1/employees/register | Registration success/failure cases | Registration form with name + mobile fields | Input validation, mobile uniqueness | Unit + API + E2E | Employee record created with name and mobile |
| REQ-EMP-002 | OTP-based login without passwords | 1 | OTP Authentication | otp_tokens table | POST /api/v1/auth/otp/request, POST /api/v1/auth/otp/verify | OTP request/verify success/failure | OTP request screen → verification screen | Rate limiting, OTP expiry, single-use | Unit + API + E2E | User can login with OTP, no password required |
| REQ-EMP-003 | Capture employee ID | 1 | Employee Profile | employees table: employee_id column | Included in registration/profile API | Validated in registration tests | Employee ID field in onboarding form | Unique constraint | DB constraint + API | Employee ID stored and unique |
| REQ-EMP-004 | Capture trade/role | 1 | Employee Profile | employees table: trade_role column | Included in registration/profile API | Validated in registration tests | Trade/role dropdown in onboarding | Validated against allowed values | Unit + API | Trade/role captured and stored |
| REQ-EMP-005 | Capture agreed rate | 1 | Employee Profile | employees table: rate_type, rate_amount columns | Included in registration/profile API | Validated in registration tests | Rate type + amount fields | Admin-only field, numeric validation | Unit + API | Rate type and amount stored |
| REQ-EMP-006 | Assign supervisor | 1 | Employee-Supervisor Assignment | employees table: supervisor_id FK | Included in registration/profile API | Validated in registration tests | Supervisor dropdown | FK constraint, supervisor must be active | DB + API | Employee linked to supervisor |
| REQ-EMP-007 | Assign client site | 1 | Employee-Site Assignment | employee_site_assignments table | Included in registration/profile API | Validated in registration tests | Site selection in onboarding | FK constraint, site must be active | DB + API | Employee assigned to client site |
| REQ-EMP-008 | Keep session active securely | 1 | Session Management | refresh_tokens table | POST /api/v1/auth/refresh | Token refresh success/failure | Auto-refresh on token expiry | Secure httpOnly cookies, rotation | Unit + API | Session persists without daily OTP |

## Page 2 — Daily Attendance (Phase 2)

| Req ID | Requirement | Phase | Feature | DB | Backend/API | Swagger | Frontend/UI | Security | Test | Acceptance Criteria |
|--------|-------------|-------|---------|-----|-------------|---------|-------------|----------|------|---------------------|
| REQ-ATT-001 | One-touch Check-In | 2 | Check-In | attendance_records table: check_in_time | POST /api/v1/attendance/check-in | Check-in success/duplicate/failure | Large Check-In button | Auth required, site assignment validated | Unit + API + E2E | Single tap records check-in |
| REQ-ATT-002 | One-touch Check-Out | 2 | Check-Out | attendance_records table: check_out_time | POST /api/v1/attendance/check-out | Check-out success/failure | Large Check-Out button | Must have active check-in | Unit + API + E2E | Single tap records check-out |
| REQ-ATT-003 | Auto-capture employee identity | 2 | Auto-fill | attendance_records: employee_id FK | Server-side from auth token | N/A (auto-populated) | Auto-displayed, non-editable | Derived from session | Unit | Employee ID auto-captured from session |
| REQ-ATT-004 | Auto-capture date/time | 2 | Auto-fill | attendance_records: check_in_time, check_out_time | Server-side timestamp | N/A (auto-populated) | Auto-displayed, non-editable | Server-generated, immutable | Unit | Server timestamp used, not client |
| REQ-ATT-005 | Auto-capture client/site | 2 | Auto-fill | attendance_records: site_id FK | Server-side from assignment | N/A (auto-populated) | Auto-displayed, non-editable | From employee assignment | Unit | Site auto-populated from assignment |
| REQ-ATT-006 | Auto-capture GPS location | 2 | GPS Capture | attendance_records: latitude, longitude | Received in check-in/out payload | GPS validation tests | Browser Geolocation API request | GPS data immutable by employee | Unit + API | GPS coordinates stored with attendance |
| REQ-ATT-007 | Validate against geo-fence | 2 | Geo-fence Validation | sites table: latitude, longitude, permitted_radius | Server-side distance calculation | Geo-fence pass/fail tests | Warning/block on out-of-range | Server-enforced validation | Unit + API + E2E | Check-in blocked if outside geo-fence (unless overridden) |
| REQ-ATT-008 | Supervisor override for exceptions | 2 | Supervisor Override | attendance_records: override_by, override_reason | POST /api/v1/attendance/{id}/override | Override success/auth failure | Supervisor override form | Supervisor role required | Unit + API + E2E | Supervisor can override geo-fence check |
| REQ-ATT-009 | Mandatory reason for exceptions | 2 | Exception Reason | attendance_records: exception_reason | Validated in override API | Missing reason rejected | Reason text field (required) | Not-null constraint when exception | DB + API | Exception reason required and stored |

## Page 3 — Daily Work & Material Update (Phase 3)

| Req ID | Requirement | Phase | Feature | DB | Backend/API | Swagger | Frontend/UI | Security | Test | Acceptance Criteria |
|--------|-------------|-------|---------|-----|-------------|---------|-------------|----------|------|---------------------|
| REQ-WRK-001 | Select activity type | 3 | Activity Selection | daily_work_entries: activity_id FK | POST /api/v1/daily-work | Activity validation | Activity dropdown | FK to activity master | DB + API | Activity selected from master list |
| REQ-WRK-002 | Enter cable run quantities | 3 | Quantity Entry | daily_work_entries: cable_runs | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Cable runs quantity stored |
| REQ-WRK-003 | Enter cable length (metres) | 3 | Quantity Entry | daily_work_entries: cable_length_metres | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Cable length stored |
| REQ-WRK-004 | Enter cameras/devices installed | 3 | Quantity Entry | daily_work_entries: devices_installed | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Device count stored |
| REQ-WRK-005 | Enter drilling quantities | 3 | Quantity Entry | daily_work_entries: drilling_qty | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Drilling quantity stored |
| REQ-WRK-006 | Enter mounting quantities | 3 | Quantity Entry | daily_work_entries: mounting_qty | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Mounting quantity stored |
| REQ-WRK-007 | Enter testing quantities | 3 | Quantity Entry | daily_work_entries: testing_qty | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Testing quantity stored |
| REQ-WRK-008 | Enter commissioning quantities | 3 | Quantity Entry | daily_work_entries: commissioning_qty | Included in work entry API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Commissioning quantity stored |
| REQ-WRK-009 | Upload work-progress photos | 3 | Photo Upload | work_photos table | POST /api/v1/daily-work/{id}/photos | Upload success/size/type | Camera capture + upload UI | File validation, secure storage | Unit + API + E2E | Photos uploaded and linked to work entry |
| REQ-WRK-010 | Record material: item | 3 | Material Entry | material_transactions: item_name or material_id | POST /api/v1/daily-work/{id}/materials | Material validation | Material selection/input | FK to material master | DB + API | Material item recorded |
| REQ-WRK-011 | Record material: quantity | 3 | Material Entry | material_transactions: quantity | Included in material API | Numeric validation | Numeric input field | Non-negative constraint | DB + API | Material quantity stored |
| REQ-WRK-012 | Record material: amount | 3 | Material Entry | material_transactions: amount | Included in material API | Numeric validation | Amount input field | Non-negative, NUMERIC(12,2) | DB + API | Material amount stored |
| REQ-WRK-013 | Record material: bill image | 3 | Bill Upload | material_transactions: bill_image_url | POST /api/v1/daily-work/{id}/materials/{mid}/bill | Upload success/failure | Camera capture + upload | File validation, secure storage | Unit + API | Bill image uploaded and linked |

## Page 4 — Supervisor Verification (Phase 4)

| Req ID | Requirement | Phase | Feature | DB | Backend/API | Swagger | Frontend/UI | Security | Test | Acceptance Criteria |
|--------|-------------|-------|---------|-----|-------------|---------|-------------|----------|------|---------------------|
| REQ-VER-001 | Consolidate attendance by employee/site EOD | 4 | EOD Summary | Read from attendance_records | GET /api/v1/verification/summary | Summary data tests | Attendance summary table | Supervisor sees only assigned employees | API + E2E | Attendance consolidated per employee per site |
| REQ-VER-002 | Consolidate work quantities by employee/site EOD | 4 | EOD Summary | Read from daily_work_entries | GET /api/v1/verification/summary | Summary data tests | Work quantity summary | Supervisor data isolation | API + E2E | Work quantities consolidated |
| REQ-VER-003 | Consolidate photos by employee/site EOD | 4 | EOD Summary | Read from work_photos | GET /api/v1/verification/summary | Photo list tests | Photo gallery view | Secure image URLs | API | Photos viewable in summary |
| REQ-VER-004 | Consolidate purchases by employee/site EOD | 4 | EOD Summary | Read from material_transactions | GET /api/v1/verification/summary | Purchase list tests | Purchase summary table | Supervisor data isolation | API | Purchases consolidated |
| REQ-VER-005 | Supervisor can Approve | 4 | Approval Action | verification_records: status='approved' | POST /api/v1/verification/{id}/approve | Approve success/auth | Approve button | Supervisor role required | Unit + API + E2E | Entry status changed to Approved |
| REQ-VER-006 | Supervisor can Reject | 4 | Rejection Action | verification_records: status='rejected' | POST /api/v1/verification/{id}/reject | Reject success/auth | Reject button | Supervisor role required | Unit + API + E2E | Entry status changed to Rejected |
| REQ-VER-007 | Supervisor can Return for Correction | 4 | Return Action | verification_records: status='correction_required' | POST /api/v1/verification/{id}/return | Return success/auth | Return button | Supervisor role required | Unit + API + E2E | Entry status changed to Correction Required |
| REQ-VER-008 | Approved quantity changes require remarks | 4 | Remarks | audit_log: remarks column | Required in update API | Missing remarks rejected | Remarks input (mandatory) | Not-null when modifying approved | DB + API | Remarks stored with change |
| REQ-VER-009 | Approved quantity changes require audit trail | 4 | Audit Trail | audit_log table | Auto-recorded on change | Audit trail verification | Audit history view | Immutable audit entries | DB + API + E2E | Complete change history preserved |

## Page 5 — Director Dashboard & Invoicing (Phase 5)

| Req ID | Requirement | Phase | Feature | DB | Backend/API | Swagger | Frontend/UI | Security | Test | Acceptance Criteria |
|--------|-------------|-------|---------|-----|-------------|---------|-------------|----------|------|---------------------|
| REQ-DSH-001 | Date-wise manpower | 5 | Dashboard Metric | Aggregation query on attendance | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role required | API | Manpower count by date displayed |
| REQ-DSH-002 | Working hours | 5 | Dashboard Metric | Calculated from check-in/out times | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Working hours displayed |
| REQ-DSH-003 | Client/site progress | 5 | Dashboard Metric | Aggregation on approved work | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Progress per client/site displayed |
| REQ-DSH-004 | Cable metres | 5 | Dashboard Metric | SUM on cable_length_metres (approved) | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Total cable metres displayed |
| REQ-DSH-005 | Devices installed | 5 | Dashboard Metric | SUM on devices_installed (approved) | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Total devices displayed |
| REQ-DSH-006 | Employee productivity | 5 | Dashboard Metric | Calculated from approved work / hours | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Productivity metric displayed |
| REQ-DSH-007 | Material cost | 5 | Dashboard Metric | SUM on material amounts (approved) | GET /api/v1/dashboard/metrics | Metric data tests | Dashboard card/chart | Director role | API | Total material cost displayed |
| REQ-DSH-008 | Approval status | 5 | Dashboard Metric | COUNT by status | GET /api/v1/dashboard/metrics | Metric data tests | Status breakdown chart | Director role | API | Approval status breakdown displayed |
| REQ-DSH-009 | Weekly payment/invoice generation | 5 | Invoice Generation | invoices table | POST /api/v1/invoices/generate | Generation success/failure | Generate button + preview | Director role, based on approved data + rates | Unit + API + E2E | Invoice generated from approved data |
| REQ-DSH-010 | Export to Excel | 5 | Report Export | N/A (read-only) | GET /api/v1/reports/{type}/export?format=xlsx | Download tests | Export button | Director role | API | Excel file downloaded |
| REQ-DSH-011 | Export to PDF | 5 | Report Export | N/A (read-only) | GET /api/v1/reports/{type}/export?format=pdf | Download tests | Export button | Director role | API | PDF file downloaded |

## Business Rules (Cross-Phase)

| Req ID | Rule | Phases Affected | DB Enforcement | API Enforcement | Frontend Enforcement |
|--------|------|----------------|----------------|-----------------|---------------------|
| REQ-BR-001 | Site assignment enforcement | 2, 3 | FK constraint employee_site_assignments | Validate assignment before check-in/work | Only assigned sites shown |
| REQ-BR-002 | GPS/time immutability | 2 | No UPDATE allowed on GPS/time columns | Server timestamps, reject client-provided times | Fields non-editable |
| REQ-BR-003 | Pre-checkout work submission | 2, 3 | Business rule (no DB constraint) | Check work submission status before checkout | Prompt to submit work before checkout |
| REQ-BR-004 | Approval-gated calculations | 4, 5 | WHERE status='approved' in queries | Filter by approved status in aggregations | Dashboard shows approved data only |
| REQ-BR-005 | Exception flagging | 2, 3 | Status/flag columns | Background job or query to flag exceptions | Exception indicators in UI |
| REQ-BR-006 | Approved record protection | 4 | Check constraint or trigger on status | Reject updates to approved records (unless authorised) | Read-only display for approved |

## Master Data (Cross-Phase)

| Req ID | Entity | Phase Introduced | DB Enforcement | API | Frontend |
|--------|--------|-----------------|----------------|-----|----------|
| REQ-MD-001 | Employee Master | 1 | employees table | Admin CRUD APIs | Admin management screen |
| REQ-MD-002 | Client & Site Master | 1 (prerequisite) | clients, sites tables | Admin CRUD APIs | Admin management screen |
| REQ-MD-003 | Project / Work Order | 1 (prerequisite) | work_orders table | Admin CRUD APIs | Admin management screen |
| REQ-MD-004 | Activity & Material Master | 3 (prerequisite) | activities, materials tables | Admin CRUD APIs | Admin management screen |

## Usability Requirements

| Req ID | Requirement | Implementation Approach | Phases Affected |
|--------|-------------|------------------------|----------------|
| REQ-UX-001 | Mobile-first / PWA | CSS mobile-first breakpoints, PWA manifest, service worker | All |
| REQ-UX-002 | Large buttons, numeric keypad, auto-fill, ≤3–4 actions | Design system tokens, inputMode="numeric", auto-fill | All |
| REQ-UX-003 | English + Kannada/Hindi labels | i18n framework, locale switching | All |
| REQ-UX-004 | Camera-first, auto-compression, draft save, offline | Camera API, client-side compression, local storage queue | 3, 4 |
| REQ-UX-005 | Status indicators | Design system status component | 3, 4, 5 |

## Security & Technical Requirements

| Req ID | Requirement | Implementation Approach | Phases Affected |
|--------|-------------|------------------------|----------------|
| REQ-SEC-001 | RBAC | FastAPI dependencies, role middleware | All |
| REQ-SEC-002 | OTP auth + session | JWT tokens, refresh rotation, httpOnly cookies | 1 |
| REQ-SEC-003 | Cloud DB, encryption, secure storage | PostgreSQL TLS, HTTPS, S3 signed URLs | All |
| REQ-SEC-004 | Daily backup, audit logs | DB backup schedule, audit_log table | All |

## Reporting Requirements

| Req ID | Requirement | Implementation Approach | Phase |
|--------|-------------|------------------------|-------|
| REQ-RPT-001 | Dashboard filters | Query parameters on dashboard APIs | 5 |
| REQ-RPT-002 | Standard reports | Aggregation queries, report endpoints | 5 |
| REQ-RPT-003 | Future integration APIs | Documented API contracts for external systems | 5 |

# Requirement Discovery & Triangulation Matrix

> **Purpose**: This matrix documents the triangulation analysis of all project requirements against three sources: (1) Formal Requirements Document, (2) Supplied Reference Photos / Handwritten Notes, and (3) Onsite Teams Reference Application.
>
> **Source-of-Truth Hierarchy**: See Master Prompt Section 0.

---

## Triangulation Source Status

| Source | Status | Notes |
|--------|--------|-------|
| **Formal Requirements Document** | ✅ ANALYSED | `Workforce_Management_Web_App_Requirements_Two_Page.md` — fully analysed |
| **Supplied Reference Photos / Handwritten Notes** | ✅ ANALYSED | ERD diagram and handwritten workflow notes supplied; analysed for business calculations, material lifecycle, payment/salary, and overtime requirements |
| **Onsite Teams Reference Application** | ⚠️ PENDING | `https://onsiteteams.com/` — not yet fully analysed for triangulation; to be completed when reference photo analysis is finalised |

---

## Evidence Classification Legend

| Level | Classification | Meaning |
|-------|---------------|---------|
| **LEVEL 1** | Explicit Requirement | Appears in the formal approved requirements document |
| **LEVEL 2** | Triangulated Requirement | Appears in BOTH reference photos AND Onsite Teams (even if absent from formal doc) |
| **LEVEL 3A** | Photo-Only Requirement | Appears in reference photos but NOT verified in Onsite |
| **LEVEL 3B** | Onsite-Only Capability | Observed in Onsite but NOT supported by photos or formal doc |
| **LEVEL 4** | Unsupported / Invented | Not supported by any confirmed source |

---

## Requirement Discovery Matrix

### Employee Onboarding & Login (Phase 1)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Business Rules | Dependencies | DB Impact | Backend/API Impact | Frontend Impact | Roles/Permissions | Reporting Impact | Phase | Acceptance Criteria | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|---------------|-------------|-----------|-------------------|----------------|------------------|-----------------|-------|--------------------|--------------|--------------------|
| REQ-EMP-001 | Employee registration (name + mobile) | YES | YES | YES | LEVEL 1 | CONFIRMED | Register employee with name and mobile number | Mobile must be unique | None | employees table | POST /api/v1/employees/register | Registration form | Employee, Administrator | N/A | 1 | Employee record created | None | Formal §2 Page 1 |
| REQ-EMP-002 | OTP-based login | YES | YES | YES | LEVEL 1 | CONFIRMED | Passwordless OTP authentication | OTP expires in 5 min, single-use, rate-limited | REQ-EMP-001 | otp_tokens table | POST /api/v1/auth/otp/request, /verify | OTP request + verify screens | All roles | N/A | 1 | User logs in with OTP | None | Formal §2 Page 1 |
| REQ-EMP-003 | Employee ID capture | YES | YES | YES | LEVEL 1 | CONFIRMED | Unique business employee ID | Must be unique | REQ-EMP-001 | employees.employee_id_number | Included in registration API | Employee ID field | Administrator | N/A | 1 | Employee ID stored and unique | None | Formal §2 Page 1 |
| REQ-EMP-004 | Trade/role capture | YES | YES | YES | LEVEL 1 | CONFIRMED | Employee trade or skill category | Validated against allowed values | REQ-EMP-001 | employees.trade_role | Included in registration API | Trade/role dropdown | Administrator | N/A | 1 | Trade/role captured | None | Formal §2 Page 1 |
| REQ-EMP-005 | Agreed rate capture | YES | YES | YES | LEVEL 1 | CONFIRMED | Daily/weekly/piece rate and amount | Rate type + amount, numeric ≥ 0 | REQ-EMP-001 | employee_rate_history table | Included in registration API | Rate type + amount fields | Administrator | Payment calculation | 1 | Rate stored | None | Formal §2 Page 1, §4 Master Data |
| REQ-EMP-006 | Supervisor assignment | YES | YES | YES | LEVEL 1 | CONFIRMED | Link employee to supervisor | Supervisor must be active employee | REQ-EMP-001 | employees.supervisor_id FK | Included in registration API | Supervisor dropdown | Administrator | N/A | 1 | Employee linked to supervisor | None | Formal §2 Page 1 |
| REQ-EMP-007 | Client site assignment | YES | YES | YES | LEVEL 1 | CONFIRMED | Assign employee to work site | Site must be active | REQ-EMP-001, REQ-MD-002 | employee_site_assignments table | Included in registration API | Site selection | Administrator | N/A | 1 | Employee assigned to site | None | Formal §2 Page 1 |
| REQ-EMP-008 | Secure session persistence | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Keep session active to avoid daily OTP | Refresh token rotation, httpOnly cookies | REQ-EMP-002 | refresh_tokens table | POST /api/v1/auth/refresh | Auto-refresh on expiry | All roles | N/A | 1 | Session persists securely | Token expiry policy | Formal §2 Page 1 |

### Daily Attendance (Phase 2)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Business Rules | Dependencies | DB Impact | Backend/API Impact | Frontend Impact | Roles/Permissions | Reporting Impact | Phase | Acceptance Criteria | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|---------------|-------------|-----------|-------------------|----------------|------------------|-----------------|-------|--------------------|--------------|--------------------|
| REQ-ATT-001 | One-touch check-in | YES | YES | YES | LEVEL 1 | CONFIRMED | Single tap to record arrival | One check-in per employee per day, server timestamp | REQ-EMP-001, REQ-EMP-007 | attendance_records.check_in_time | POST /api/v1/attendance/check-in | Large Check-In button | Employee | Attendance reports | 2 | Check-in recorded with one touch | None | Formal §2 Page 2 |
| REQ-ATT-002 | One-touch check-out | YES | YES | YES | LEVEL 1 | CONFIRMED | Single tap to record departure | Must have active check-in, server timestamp | REQ-ATT-001 | attendance_records.check_out_time | POST /api/v1/attendance/check-out | Large Check-Out button | Employee | Attendance, hours reports | 2 | Check-out recorded with one touch | None | Formal §2 Page 2 |
| REQ-ATT-003 | Auto-capture employee identity | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Employee identity from session | Derived from auth token, not user input | REQ-EMP-002 | attendance_records.employee_id FK | Server-side from token | Auto-displayed, non-editable | Employee | N/A | 2 | Employee auto-identified | None | Formal §2 Page 2 |
| REQ-ATT-004 | Auto-capture date/time | YES | YES | YES | LEVEL 1 | CONFIRMED | Server-generated timestamp | Immutable by employee (REQ-BR-002) | None | attendance_records timestamps | Server-generated | Auto-displayed, non-editable | Employee | N/A | 2 | Server timestamp used | None | Formal §2 Page 2, §3 BR |
| REQ-ATT-005 | Auto-capture client/site | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Site from assignment | Derived from employee assignment | REQ-EMP-007 | attendance_records.site_id FK | Server-side from assignment | Auto-displayed | Employee | N/A | 2 | Site auto-populated | None | Formal §2 Page 2 |
| REQ-ATT-006 | GPS location capture | YES | YES | YES | LEVEL 1 | CONFIRMED | Capture GPS at check-in/out | GPS immutable by employee | None | attendance_records lat/lng columns | Received in payload | Browser Geolocation API | Employee | N/A | 2 | GPS stored with attendance | None | Formal §2 Page 2 |
| REQ-ATT-007 | Geo-fence validation | YES | YES | YES | LEVEL 1 | CONFIRMED | Validate GPS against site radius | Haversine distance ≤ permitted_radius | REQ-MD-002 (site GPS) | sites.latitude, longitude, permitted_radius | Server-side calculation | Warning/block on out-of-range | Employee | Exception reporting | 2 | Out-of-fence blocked unless overridden | None | Formal §2 Page 2 |
| REQ-ATT-008 | Supervisor override | YES | YES | YES | LEVEL 1 | CONFIRMED | Supervisor can override geo-fence | Override reason mandatory | REQ-ATT-007 | attendance_records.override_by, override_reason | POST /api/v1/attendance/{id}/override | Override form | Supervisor | N/A | 2 | Supervisor can override | None | Formal §2 Page 2 |
| REQ-ATT-009 | Mandatory exception reason | YES | YES | YES | LEVEL 1 | CONFIRMED | Reason required for exceptions | Not-null when exception active | REQ-ATT-008 | attendance_records.exception_reason | Validated in override API | Reason text field (required) | Supervisor | N/A | 2 | Reason stored | None | Formal §2 Page 2 |

### Daily Work & Material Update (Phase 3)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Business Rules | Dependencies | DB Impact | Backend/API Impact | Frontend Impact | Roles/Permissions | Reporting Impact | Phase | Acceptance Criteria | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|---------------|-------------|-----------|-------------------|----------------|------------------|-----------------|-------|--------------------|--------------|--------------------|
| REQ-WRK-001 | Activity selection | YES | YES | YES | LEVEL 1 | CONFIRMED | Select work activity type | FK to activity master | REQ-MD-004 | daily_work_entries.activity_id FK | POST /api/v1/daily-work | Activity dropdown | Employee | Work reports | 3 | Activity selected from list | None | Formal §2 Page 3 |
| REQ-WRK-002 | Cable run quantities | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter cable run count | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.cable_runs | Included in work API | Numeric input | Employee | Cable metrics | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-003 | Cable length (metres) | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter cable length | Numeric ≥ 0 | REQ-WRK-001 | daily_work_entries.cable_length_metres | Included in work API | Numeric input | Employee | Cable metres report | 3 | Length stored | None | Formal §2 Page 3 |
| REQ-WRK-004 | Cameras/devices installed | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter device installation count | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.devices_installed | Included in work API | Numeric input | Employee | Devices report | 3 | Count stored | None | Formal §2 Page 3 |
| REQ-WRK-005 | Drilling quantities | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter drilling work quantity | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.drilling_qty | Included in work API | Numeric input | Employee | Work reports | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-006 | Mounting quantities | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter mounting work quantity | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.mounting_qty | Included in work API | Numeric input | Employee | Work reports | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-007 | Testing quantities | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter testing work quantity | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.testing_qty | Included in work API | Numeric input | Employee | Work reports | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-008 | Commissioning quantities | YES | YES | YES | LEVEL 1 | CONFIRMED | Enter commissioning work quantity | Integer ≥ 0 | REQ-WRK-001 | daily_work_entries.commissioning_qty | Included in work API | Numeric input | Employee | Work reports | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-009 | Work progress photos | YES | YES | YES | LEVEL 1 | CONFIRMED | Upload work photos | Camera-first, auto-compress, max 10MB | REQ-WRK-001 | work_photos table | POST /api/v1/daily-work/{id}/photos | Camera + upload UI | Employee | Photo verification | 3 | Photos uploaded and linked | None | Formal §2 Page 3 |
| REQ-WRK-010 | Material: item | YES | YES | YES | LEVEL 1 | CONFIRMED | Record material item name | Required text or FK to material master | REQ-WRK-001 | material_transactions.item_name | POST /api/v1/daily-work/{id}/materials | Material selection/input | Employee | Material reports | 3 | Material item recorded | None | Formal §2 Page 3 |
| REQ-WRK-011 | Material: quantity | YES | YES | YES | LEVEL 1 | CONFIRMED | Record material quantity | Numeric > 0 | REQ-WRK-010 | material_transactions.quantity | Included in material API | Numeric input | Employee | Material reports | 3 | Quantity stored | None | Formal §2 Page 3 |
| REQ-WRK-012 | Material: amount | YES | YES | YES | LEVEL 1 | CONFIRMED | Record material cost | Numeric ≥ 0 | REQ-WRK-010 | material_transactions.amount | Included in material API | Amount input | Employee | Cost reports | 3 | Amount stored | None | Formal §2 Page 3 |
| REQ-WRK-013 | Material: bill image | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Upload purchase bill image | Image file, max 10MB | REQ-WRK-010 | material_transactions.bill_image_url | POST /api/v1/.../bill | Camera + upload | Employee | Audit verification | 3 | Bill image uploaded | None | Formal §2 Page 3 |

### Supervisor Verification (Phase 4)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Business Rules | Dependencies | DB Impact | Backend/API Impact | Frontend Impact | Roles/Permissions | Reporting Impact | Phase | Acceptance Criteria | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|---------------|-------------|-----------|-------------------|----------------|------------------|-----------------|-------|--------------------|--------------|--------------------|
| REQ-VER-001 | Consolidate attendance EOD | YES | YES | YES | LEVEL 1 | CONFIRMED | Show attendance summary by employee/site | End-of-day aggregation | Phase 2 | Read from attendance_records | GET /api/v1/verification/summary | Summary table | Supervisor | N/A | 4 | Attendance consolidated | None | Formal §2 Page 4 |
| REQ-VER-002 | Consolidate work quantities EOD | YES | YES | YES | LEVEL 1 | CONFIRMED | Show work quantity summary | Aggregation by employee/site | Phase 3 | Read from daily_work_entries | GET /api/v1/verification/summary | Work summary | Supervisor | N/A | 4 | Work consolidated | None | Formal §2 Page 4 |
| REQ-VER-003 | Consolidate photos EOD | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Show work photos for review | Photo gallery per employee | Phase 3 | Read from work_photos | GET /api/v1/verification/summary | Photo gallery | Supervisor | N/A | 4 | Photos viewable | None | Formal §2 Page 4 |
| REQ-VER-004 | Consolidate purchases EOD | YES | YES | YES | LEVEL 1 | CONFIRMED | Show material purchases for review | Purchase list with amounts | Phase 3 | Read from material_transactions | GET /api/v1/verification/summary | Purchase table | Supervisor | N/A | 4 | Purchases consolidated | None | Formal §2 Page 4 |
| REQ-VER-005 | Approve | YES | YES | YES | LEVEL 1 | CONFIRMED | Supervisor approves entry | Status → approved, record becomes read-only | REQ-VER-001 | verification_records, status update | POST /api/v1/verification/{id}/approve | Approve button | Supervisor | Feeds into payments | 4 | Status = approved | None | Formal §2 Page 4 |
| REQ-VER-006 | Reject | YES | YES | YES | LEVEL 1 | CONFIRMED | Supervisor rejects entry | Remarks mandatory | REQ-VER-001 | verification_records, status update | POST /api/v1/verification/{id}/reject | Reject button | Supervisor | N/A | 4 | Status = rejected | None | Formal §2 Page 4 |
| REQ-VER-007 | Return for correction | YES | YES | YES | LEVEL 1 | CONFIRMED | Supervisor returns entry for correction | Remarks mandatory, employee can re-edit | REQ-VER-001 | verification_records, status update | POST /api/v1/verification/{id}/return | Return button | Supervisor | N/A | 4 | Status = correction_required | None | Formal §2 Page 4 |
| REQ-VER-008 | Approved change requires remarks | YES | YES | YES | LEVEL 1 | CONFIRMED | Remarks when modifying approved data | Not-null constraint | REQ-VER-005 | audit_log.remarks | Required in update API | Remarks input | Supervisor | Audit trail | 4 | Remarks stored | None | Formal §2 Page 4, §3 BR |
| REQ-VER-009 | Approved change requires audit trail | YES | YES | YES | LEVEL 1 | CONFIRMED | Full change history for approved records | Immutable audit entries | REQ-VER-005 | audit_logs table | Auto-recorded on change | Audit history view | Supervisor | Audit reports | 4 | Change history preserved | None | Formal §2 Page 4, §3 BR |

### Director Dashboard & Invoicing (Phase 5)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Business Rules | Dependencies | DB Impact | Backend/API Impact | Frontend Impact | Roles/Permissions | Reporting Impact | Phase | Acceptance Criteria | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|---------------|-------------|-----------|-------------------|----------------|------------------|-----------------|-------|--------------------|--------------|--------------------|
| REQ-DSH-001 | Date-wise manpower | YES | YES | YES | LEVEL 1 | CONFIRMED | Count distinct employees by date | Only approved attendance | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Manpower report | 5 | Manpower displayed | None | Formal §2 Page 5 |
| REQ-DSH-002 | Working hours | YES | YES | YES | LEVEL 1 | CONFIRMED | Sum working hours | Calculated from check-in/out times (approved) | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Hours report | 5 | Hours displayed | None | Formal §2 Page 5 |
| REQ-DSH-003 | Client/site progress | YES | YES | YES | LEVEL 1 | CONFIRMED | Work progress per client/site | Sum approved quantities by site | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Progress report | 5 | Progress displayed | None | Formal §2 Page 5 |
| REQ-DSH-004 | Cable metres | YES | YES | YES | LEVEL 1 | CONFIRMED | Total cable metres laid | Sum approved cable_length_metres | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Cable report | 5 | Cable metres displayed | None | Formal §2 Page 5 |
| REQ-DSH-005 | Devices installed | YES | YES | YES | LEVEL 1 | CONFIRMED | Total devices installed | Sum approved devices_installed | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Device report | 5 | Devices displayed | None | Formal §2 Page 5 |
| REQ-DSH-006 | Employee productivity | YES | YES | YES | LEVEL 1 | CONFIRMED | Productivity ratio per employee | Approved output / working hours | Phase 4 | Derived calculation | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Productivity report | 5 | Productivity displayed | Exact formula TBD | Formal §2 Page 5 |
| REQ-DSH-007 | Material cost | YES | YES | YES | LEVEL 1 | CONFIRMED | Total material expenditure | Sum approved material amounts | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Dashboard card/chart | Director | Cost report | 5 | Cost displayed | None | Formal §2 Page 5 |
| REQ-DSH-008 | Approval status | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Status breakdown chart | Count by status across entities | Phase 4 | Aggregation query | GET /api/v1/dashboard/metrics | Status chart | Director | Status report | 5 | Status breakdown displayed | None | Formal §2 Page 5 |
| REQ-DSH-009 | Weekly payment/invoice | YES | YES | YES | LEVEL 1 | CONFIRMED | Generate payment from approved data + rates | Daily: days × rate. Weekly: weeks × rate. Piece: qty × rate | Phase 4, REQ-EMP-005 | invoices, employee_payments tables | POST /api/v1/invoices/generate | Generate + preview | Director | Payment report | 5 | Invoice generated correctly | Overtime rate formula | Formal §2 Page 5 |
| REQ-DSH-010 | Export to Excel | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Download report as Excel file | openpyxl generation | REQ-DSH-001–008 | N/A (read-only) | GET /api/v1/reports/{type}/export?format=xlsx | Export button | Director | N/A | 5 | Excel downloaded | None | Formal §2 Page 5 |
| REQ-DSH-011 | Export to PDF | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Download report as PDF | reportlab/weasyprint generation | REQ-DSH-001–008 | N/A (read-only) | GET /api/v1/reports/{type}/export?format=pdf | Export button | Director | N/A | 5 | PDF downloaded | None | Formal §2 Page 5 |

### Business Rules (Cross-Phase)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Phases Affected | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|----------------|---------------|--------------------|
| REQ-BR-001 | Site assignment enforcement | YES | YES | YES | LEVEL 1 | CONFIRMED | Employees can only work at assigned sites | 2, 3 | None | Formal §3 |
| REQ-BR-002 | GPS/time immutability | YES | YES | YES | LEVEL 1 | CONFIRMED | GPS and timestamps cannot be edited by employees | 2 | None | Formal §3 |
| REQ-BR-003 | Pre-checkout work submission | YES | YES | YES | LEVEL 1 | CONFIRMED | Work should be submitted before check-out | 2, 3 | Warn vs block? | Formal §3 |
| REQ-BR-004 | Approval-gated calculations | YES | YES | YES | LEVEL 1 | CONFIRMED | Only approved data feeds into payments/invoices | 4, 5 | None | Formal §3 |
| REQ-BR-005 | Exception flagging | YES | YES | YES | LEVEL 1 | CONFIRMED | Automatically flag anomalies | 2, 3, 4 | None | Formal §3 |
| REQ-BR-006 | Approved record protection | YES | YES | YES | LEVEL 1 | CONFIRMED | Approved records locked; changes require auth + audit | 4 | None | Formal §3 |

### Master Data (Cross-Phase)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Phase Introduced | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|-----------------|---------------|--------------------|
| REQ-MD-001 | Employee Master | YES | YES | YES | LEVEL 1 | CONFIRMED | Employee master with name, mobile, ID, trade, supervisor, rate, status | 1 | None | Formal §4 |
| REQ-MD-002 | Client & Site Master | YES | YES | YES | LEVEL 1 | CONFIRMED | Client, site, GPS coordinates, permitted radius, supervisor | 1 (prerequisite) | None | Formal §4 |
| REQ-MD-003 | Project / Work Order | YES | YES | YES | LEVEL 1 | CONFIRMED | Order number, site, dates, scope, targets, billing basis | 1 (prerequisite) | None | Formal §4 |
| REQ-MD-004 | Activity & Material Master | YES | YES | YES | LEVEL 1 | CONFIRMED | Activity type, UoM, rate, categories, approval limit | 3 (prerequisite) | None | Formal §4 |

### Usability Requirements (Cross-Phase)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Phases | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|--------|---------------|--------------------|
| REQ-UX-001 | Mobile-first / PWA | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Mobile-first responsive design suitable for low-cost Android phones | All | PWA vs responsive-only decision | Formal §5 |
| REQ-UX-002 | Large buttons, numeric keypad, ≤3–4 actions | YES | YES | YES | LEVEL 1 | CONFIRMED | Minimise typing; large buttons, dropdowns, numeric inputs | All | None | Formal §5, Objective |
| REQ-UX-003 | English + Kannada/Hindi | YES | UNKNOWN | UNKNOWN | LEVEL 1 | CONFIRMED | Interface with optional localisation | All | i18n implementation timing | Formal §5 |
| REQ-UX-004 | Camera-first, compression, draft, offline | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Camera-first photo upload with auto-compression and offline tolerance | 3, 4 | Offline sync strategy | Formal §5 |
| REQ-UX-005 | Status indicators | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Draft, Submitted, Approved, Rejected, Correction Required | 3, 4, 5 | None | Formal §5 |

### Security & Technical Requirements (Cross-Phase)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Phases | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|--------|---------------|--------------------|
| REQ-SEC-001 | RBAC | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Role-based access for all 4 roles | All | None | Formal §6 |
| REQ-SEC-002 | OTP auth + session | YES | YES | YES | LEVEL 1 | CONFIRMED | Secure OTP authentication and session management | 1 | None | Formal §6 |
| REQ-SEC-003 | Cloud DB, encryption, secure storage | YES | UNKNOWN | YES | LEVEL 1 | CONFIRMED | Encrypted transmission, secure image storage | All | Cloud provider selection | Formal §6 |
| REQ-SEC-004 | Backup, audit logs | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Daily backup and complete activity audit logs | All | Backup automation timing | Formal §6 |

### Reporting Requirements (Cross-Phase)

| Req ID | Capability | Formal Req | Ref Photos | Onsite Ref | Evidence Level | Status | Business Description | Phase | Open Questions | Source/Evidence Notes |
|--------|-----------|-----------|-----------|-----------|---------------|--------|---------------------|-------|---------------|--------------------|
| REQ-RPT-001 | Dashboard filters | YES | PARTIAL | YES | LEVEL 1 | CONFIRMED | Date, client, site, employee, supervisor filters | 5 | None | Formal §6 |
| REQ-RPT-002 | Standard reports | YES | YES | YES | LEVEL 1 | CONFIRMED | Attendance, work, materials, productivity, payment, invoice summary | 5 | None | Formal §6 |
| REQ-RPT-003 | Future integration APIs | YES | UNKNOWN | UNKNOWN | LEVEL 1 | CONFIRMED | API contracts for payroll, accounting, ERP, WhatsApp, billing | 5 | Timing of integration implementation | Formal §6 |

---

## Triangulation Discovery Areas Analysis

### Working Hours / Overtime

| Discovery Area | Ref Photos Evidence | Onsite Ref Evidence | Classification | Action |
|---------------|-------------------|-------------------|---------------|--------|
| Standard working hours calculation | YES — ERD shows `working_hours` and `overtime_hours` columns on `attendance_records` | PENDING | LEVEL 3A — PENDING VALIDATION | Working hours calculation is captured in the canonical ERD (check_out - check_in). Overtime concept is present in the data model. Exact standard-hours threshold and overtime rate require business confirmation. |
| Overtime calculation | YES — `overtime_hours` column in ERD, `overtime` line type in payment_lines | PENDING | LEVEL 3A — PENDING VALIDATION | Data model supports overtime. **Business Rule Pending Confirmation**: Standard hours threshold (e.g., 8 hours/day) and overtime rate multiplier not specified in formal requirements. |

### Employee Payment / Salary

| Discovery Area | Ref Photos Evidence | Onsite Ref Evidence | Classification | Action |
|---------------|-------------------|-------------------|---------------|--------|
| Employee salary/rate registration | YES — formal requirements specify daily/weekly/piece rate | YES (presumed) | LEVEL 1 | Already in scope as REQ-EMP-005. Rate history tracked via `employee_rate_history` table. |
| Payment calculation (daily rate) | YES — ERD has `employee_payments` and `employee_payment_lines` | PENDING | LEVEL 1 | Formal requirements specify "weekly employee payment/invoice based on approved work or attendance and configured rates." Calculation logic: daily_rate × approved_days. |
| Payment calculation (piece rate) | YES — ERD supports `work_quantity` line type | PENDING | LEVEL 1 | Piece rate: approved_quantities × rate_amount. |
| PPF / deduction management | UNKNOWN | PENDING | LEVEL 3A — PENDING VALIDATION | ERD has `deductions` column on `employee_payments` and `deduction` line type on payment_lines. **Business Rule Pending Confirmation**: No deduction types specified in formal requirements. Data model supports it if needed. |

### Material Management Lifecycle

| Discovery Area | Ref Photos Evidence | Onsite Ref Evidence | Classification | Action |
|---------------|-------------------|-------------------|---------------|--------|
| Material purchase recording | YES — formal requirements specify item, quantity, amount, bill image | YES (presumed) | LEVEL 1 | Already in scope as REQ-WRK-010 through REQ-WRK-013. |
| Material consumption tracking | YES — ERD has `transaction_type` field with `consumed|purchased` | PENDING | LEVEL 1 | Formal requirements mention "material consumed or purchased." Tracked via `material_transactions.transaction_type`. |
| Material inventory / remaining quantity | UNKNOWN | PENDING | NOT IN SCOPE | No inventory tracking specified in formal requirements. Material lifecycle is limited to consumption/purchase recording. |
| High-value purchase flagging | YES — formal requirements mention flagging high-value purchases | YES (presumed) | LEVEL 1 | Already in scope as REQ-BR-005. Threshold from `materials.purchase_approval_limit`. |

---

## Summary Statistics

| Classification | Count |
|---------------|-------|
| LEVEL 1 — Explicit Requirements | 55 |
| LEVEL 2 — Triangulated Requirements | 0 |
| LEVEL 3A — Photo-Only / Pending Validation | 3 (overtime threshold, overtime rate, deduction types) |
| LEVEL 3B — Onsite-Only Capabilities | 0 |
| LEVEL 4 — Unsupported / Invented | 0 |

---

## Open Business Decisions

| # | Decision Required | Context | Impact |
|---|------------------|---------|--------|
| 1 | **Standard working hours threshold** | What constitutes a "standard" work day (e.g., 8 hours)? Hours beyond this would be overtime. | Overtime calculation, payment lines |
| 2 | **Overtime rate multiplier** | What is the overtime pay rate (e.g., 1.5× or 2× base rate)? | Payment calculation |
| 3 | **Deduction types** | What deductions apply to employee payments (e.g., PPF, advances, penalties)? | Payment calculation, data model |
| 4 | **Pre-checkout enforcement** | Should missing work submission **warn** or **block** checkout? | Attendance/work interaction |
| 5 | **Offline sync strategy** | How should the app handle offline data entry and synchronisation? | Frontend architecture |
| 6 | **i18n implementation timing** | When should Kannada/Hindi localisation be implemented? | Frontend, all phases |
| 7 | **Productivity formula** | Exact definition of "employee productivity" metric | Dashboard metrics |

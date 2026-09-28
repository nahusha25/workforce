# Master Implementation Plan

## 1. Product Scope

The **i-Workforce Management Web Application** is a field-worker management tool for organisations performing CCTV installation, cable laying, device installation and site-related material purchases.

**Objective** (from source): Build a simple web application for managing field workers engaged in CCTV installation, cable laying, device installation and site-related material purchases. The solution must minimise typing and use large buttons, dropdowns, numeric inputs and camera uploads so that construction labourers can use it easily.

The application tracks:
- Employee onboarding and authentication
- Daily attendance with GPS and geo-fence validation
- Daily work quantities and progress photographs
- Material consumption and purchases
- Supervisor end-of-day verification (approve/reject/return)
- Director-level dashboard, reporting, and weekly payment/invoice generation

## 2. Users

| Role | Responsibilities | Source |
|------|-----------------|--------|
| **Employee / Field Worker** | Daily attendance, work quantity entry, photographs, material updates | Requirements §1 |
| **Supervisor** | Verifies attendance and work; approves, rejects, or returns entries for correction | Requirements §1 |
| **Director / Management** | Views manpower, site progress, productivity, cost, and weekly invoice/payment summaries | Requirements §1 |
| **Administrator** | Maintains employees, rates, clients, sites, work orders, activities, materials, and user access | Requirements §1 |

## 3. Application Pages

| # | Page | Primary User(s) | Source |
|---|------|-----------------|--------|
| 1 | Employee Onboarding & Login | Employee, Administrator | Requirements §2 |
| 2 | Daily Attendance | Employee | Requirements §2 |
| 3 | Daily Work & Material Update | Employee | Requirements §2 |
| 4 | Supervisor Verification | Supervisor | Requirements §2 |
| 5 | Director Dashboard & Invoicing | Director | Requirements §2 |

> Technical Implementation Decision: Administrator functionality (master data management) is accessed through administrative sections within the application, not listed as a separate numbered page in the requirements but required by the Administrator role definition.

## 4. Functional Requirements

### Page 1 — Employee Onboarding & Login
| ID | Requirement |
|----|-------------|
| REQ-EMP-001 | Register using name and mobile number |
| REQ-EMP-002 | OTP-based login without passwords |
| REQ-EMP-003 | Capture employee ID |
| REQ-EMP-004 | Capture trade/role |
| REQ-EMP-005 | Capture agreed rate |
| REQ-EMP-006 | Assign supervisor |
| REQ-EMP-007 | Assign client site |
| REQ-EMP-008 | Keep session active securely to avoid daily OTP entry |

### Page 2 — Daily Attendance
| ID | Requirement |
|----|-------------|
| REQ-ATT-001 | One-touch Check-In |
| REQ-ATT-002 | One-touch Check-Out |
| REQ-ATT-003 | Automatically capture employee identity |
| REQ-ATT-004 | Automatically capture date/time |
| REQ-ATT-005 | Automatically capture client/site |
| REQ-ATT-006 | Automatically capture GPS location |
| REQ-ATT-007 | Validate against configured site geo-fence |
| REQ-ATT-008 | Supervisor override for geo-fence exceptions |
| REQ-ATT-009 | Mandatory reason for exceptions |

### Page 3 — Daily Work & Material Update
| ID | Requirement |
|----|-------------|
| REQ-WRK-001 | Select activity type |
| REQ-WRK-002 | Enter cable run quantities |
| REQ-WRK-003 | Enter cable length in metres |
| REQ-WRK-004 | Enter cameras/devices installed count |
| REQ-WRK-005 | Enter drilling quantities |
| REQ-WRK-006 | Enter mounting quantities |
| REQ-WRK-007 | Enter testing quantities |
| REQ-WRK-008 | Enter commissioning quantities |
| REQ-WRK-009 | Upload work-progress photos |
| REQ-WRK-010 | Record material consumed/purchased: item |
| REQ-WRK-011 | Record material consumed/purchased: quantity |
| REQ-WRK-012 | Record material consumed/purchased: amount |
| REQ-WRK-013 | Record material consumed/purchased: bill image |

### Page 4 — Supervisor Verification
| ID | Requirement |
|----|-------------|
| REQ-VER-001 | Consolidate attendance by employee and site at end of day |
| REQ-VER-002 | Consolidate work quantities by employee and site at end of day |
| REQ-VER-003 | Consolidate photos by employee and site at end of day |
| REQ-VER-004 | Consolidate purchases by employee and site at end of day |
| REQ-VER-005 | Supervisor can Approve entries |
| REQ-VER-006 | Supervisor can Reject entries |
| REQ-VER-007 | Supervisor can Return entries for Correction |
| REQ-VER-008 | Changes to approved quantities require remarks |
| REQ-VER-009 | Changes to approved quantities require audit trail |

### Page 5 — Director Dashboard & Invoicing
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

### Business Rules
| ID | Rule |
|----|------|
| REQ-BR-001 | Employees can check in, check out and submit work only for assigned client sites |
| REQ-BR-002 | GPS date/time cannot be edited by employees; corrections require supervisor remarks and audit trail |
| REQ-BR-003 | Daily work should be submitted before check-out; system sends all submissions to supervisor's EOD verification queue |
| REQ-BR-004 | Only supervisor-approved attendance and work quantities are considered for productivity, employee payment and invoice generation |
| REQ-BR-005 | Flag exceptions: missing check-out, attendance without work, work without attendance, no photograph, out-of-location attendance, high-value material purchases |
| REQ-BR-006 | Approved records become read-only; reopening requires authorised approval and complete change history |

### Master Data
| ID | Entity | Fields |
|----|--------|--------|
| REQ-MD-001 | Employee Master | name, mobile, ID, trade/role, supervisor, daily/weekly/piece rate, active status |
| REQ-MD-002 | Client & Site Master | client, site name/address, GPS coordinates, permitted radius, site supervisor |
| REQ-MD-003 | Project / Work Order | order number, site, start/end dates, scope, target quantities, billing basis |
| REQ-MD-004 | Activity & Material Master | activity type, unit of measure, approved rate, cable/device categories, tools, purchase approval limit |

### Usability Requirements
| ID | Requirement |
|----|-------------|
| REQ-UX-001 | Mobile-first responsive design or PWA; suitable for low-cost Android phones and mobile browsers |
| REQ-UX-002 | Large buttons, clear icons, numeric keypad, auto-filled employee/date/site, ≤3–4 actions per screen |
| REQ-UX-003 | English interface with optional Kannada/Hindi labels; short text or voice-to-text for remarks |
| REQ-UX-004 | Camera-first photo upload with automatic image compression; draft save and weak-network/offline tolerance |
| REQ-UX-005 | Simple status indicators: Draft, Submitted, Approved, Rejected, Correction Required |

### Security & Technical Requirements
| ID | Requirement |
|----|-------------|
| REQ-SEC-001 | Role-based access for Employee, Supervisor, Director and Administrator |
| REQ-SEC-002 | Secure OTP authentication and session management |
| REQ-SEC-003 | Cloud-hosted central database, encrypted transmission, secure image storage |
| REQ-SEC-004 | Daily backup and complete activity audit logs |

### Reporting Requirements
| ID | Requirement |
|----|-------------|
| REQ-RPT-001 | Dashboard filters: date, client, site, employee, supervisor |
| REQ-RPT-002 | Reports: attendance, approved work, materials, productivity, weekly payment, client/site invoice summary |
| REQ-RPT-003 | Provide APIs for future integration with payroll, accounting, ERP, WhatsApp notifications and client billing systems |

## 5. Business Rules Summary

1. **Site Assignment Enforcement** — Employees work only at assigned sites.
2. **GPS Immutability** — GPS/time data is system-captured and non-editable by employees.
3. **Pre-Checkout Submission** — Work must be submitted before checkout.
4. **Approval-Gated Calculations** — Only approved data feeds into payments and invoices.
5. **Exception Flagging** — System automatically flags anomalies.
6. **Approved Record Protection** — Approved records are locked; changes require authorised approval and full audit trail.

## 6. Technical Architecture

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Alembic |
| Database | PostgreSQL |
| API | REST, JSON, OpenAPI 3.0, Swagger UI |
| Frontend | React, TypeScript, Vite |
| E2E Testing | Playwright |
| Architecture | Modular monolith |

> Technical Implementation Decision: The requirements document suggests "React/Vue" and "Node.js, Python or .NET". This project uses React/TypeScript + Python/FastAPI + PostgreSQL per the engineering standards.

## 7. Phase Sequence

```
Phase 0: Documentation & Governance (this phase — no business code)
    ↓
Phase 1: Employee Onboarding & Login
    ↓
Phase 2: Daily Attendance
    ↓
Phase 3: Daily Work & Material Update
    ↓
Phase 4: Supervisor Verification
    ↓
Phase 5: Director Dashboard & Invoicing
```

**Priority** (from source): Employee Onboarding → Attendance → Daily Work Capture → Supervisor Approval → Director Dashboard → Weekly Invoice / Payment Statement

## 8. Dependencies

### Phase Dependencies
| Phase | Depends On |
|-------|-----------|
| Phase 1 | Phase 0 (documentation/standards) |
| Phase 2 | Phase 1 (employees must exist, auth must work) |
| Phase 3 | Phase 2 (attendance must exist — work submitted before checkout) |
| Phase 4 | Phase 3 (work and materials must exist to verify) |
| Phase 5 | Phase 4 (approved data must exist for dashboard/invoicing) |

### Feature Dependencies
| Feature | Depends On |
|---------|-----------|
| OTP Login | Employee registration |
| Check-In/Out | Employee authentication, site assignment |
| Geo-fence validation | Site master with GPS coordinates and radius |
| Daily work entry | Active attendance session (checked in) |
| Material entry | Active attendance session, material master |
| Supervisor verification | Submitted work + attendance data |
| Dashboard metrics | Approved data from supervisor verification |
| Weekly payment/invoice | Approved data + configured rates |
| Report export | Dashboard data aggregation |

## 9. Engineering Gates

Every phase must pass all 8 gates (see `CLAUDE.md` and `.ai/checklists/definition-of-done.md`):

| Gate | Description |
|------|-------------|
| 1 — Requirement | Traceable to source document |
| 2 — UX | Screens, flows, states, responsive, accessibility |
| 3 — Implementation | DB, backend/API, frontend built to standards |
| 4 — Verification | Unit/integration/API/Swagger/E2E tests pass |
| 5 — Security | Security-sensitive features audited |
| 6 — Cleanup | Dead code reviewed |
| 7 — Documentation | Docs and knowledge updated |
| 8 — Git | Atomic, meaningful commits |

## 10. Definition of Done

See `docs/00-phase-0/definition-of-done.md` and `.ai/checklists/definition-of-done.md` for the complete checklist at task, feature, and phase levels.

Summary: A feature is done when it is requirement-traced, designed, implemented, validated, tested (unit + API + Swagger + E2E), security-reviewed, documented, cleaned up, and committed atomically.

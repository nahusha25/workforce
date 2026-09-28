# Phase Dependencies

## Phase-Level Dependencies

```
Phase 0: Documentation & Governance
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

Each phase depends on the completion of all previous phases.

## Feature-Level Dependencies

```
Employee Registration (Phase 1)
    ↓
OTP Authentication (Phase 1)
    ↓
Employee-Site Assignment (Phase 1)
    ↓
Client & Site Master Data (Phase 1 prerequisite)
    ↓
Daily Check-In with GPS (Phase 2)
    ↓
Geo-Fence Validation (Phase 2)
    ↓
Daily Check-Out (Phase 2)
    ↓
Activity & Material Master Data (Phase 3 prerequisite)
    ↓
Work Entry with Quantities (Phase 3)
    ↓
Work Photo Upload (Phase 3)
    ↓
Material Purchase Recording (Phase 3)
    ↓
Work Submission (Phase 3)
    ↓
Supervisor EOD Summary (Phase 4)
    ↓
Supervisor Approve / Reject / Return (Phase 4)
    ↓
Approved Data Aggregation (Phase 5)
    ↓
Director Dashboard Metrics (Phase 5)
    ↓
Weekly Payment / Invoice Generation (Phase 5)
    ↓
Report Export (Phase 5)
```

## Master Data Prerequisites

Master data must be created before the features that depend on it:

| Master Data | Required Before | Managed By |
|-------------|----------------|------------|
| Clients | Site creation | Administrator |
| Sites (with GPS/radius) | Employee site assignment, attendance | Administrator |
| Employees | Attendance, work entries | Administrator |
| Work Orders | Work entry context (optional) | Administrator |
| Activities | Daily work entry | Administrator |
| Materials | Material purchase recording | Administrator |

## Cross-Phase Data Flow

```
Phase 1 (Employee)
  └──▶ employees, users, clients, sites, employee_site_assignments
           │
Phase 2 (Attendance)
  └──▶ attendance_records (references employees, sites)
           │
Phase 3 (Daily Work)
  └──▶ daily_work_entries, work_photos, material_transactions
       (references attendance_records, activities, materials)
           │
Phase 4 (Verification)
  └──▶ verification_records (references attendance, work entries)
       Status changes: draft → submitted → approved/rejected/correction_required
           │
Phase 5 (Dashboard)
  └──▶ Aggregation queries on approved data
       invoices, invoice_line_items (generated from approved records + rates)
```

## Technical Foundation Dependencies

These must be established before any business phase:

| Component | Purpose | When |
|-----------|---------|------|
| Database setup (PostgreSQL) | Data persistence | Before Phase 1 |
| Alembic migrations | Schema management | Before Phase 1 |
| FastAPI application skeleton | API framework | Before Phase 1 |
| Authentication system (OTP + JWT) | User login | Phase 1 |
| RBAC middleware | Permission enforcement | Phase 1 |
| Error handling framework | Consistent errors | Before Phase 1 |
| Audit logging system | Change tracking | Before Phase 1 |
| File storage integration | Image uploads | Before Phase 3 |
| React application skeleton | Frontend framework | Before Phase 1 |
| API client module | Frontend-backend communication | Before Phase 1 |
| Design system foundation | UI components | Before Phase 1 |

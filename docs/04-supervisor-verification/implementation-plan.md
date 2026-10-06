# Phase 4 — Supervisor Verification — Implementation Plan

## Requirement Scope
Enable supervisors to review, approve, reject, or return end-of-day consolidated attendance, work quantities, photos, and material purchases for their assigned employees. Enforce read-only protection for approved records. Compute exception flags.

## Requirement Traceability
| Req ID | Requirement | Feature |
|--------|-------------|---------|
| REQ-VER-001 | Consolidate attendance | EOD Summary Queue |
| REQ-VER-002 | Consolidate work quantities | Detail View |
| REQ-VER-003 | Consolidate photos | Detail View Gallery |
| REQ-VER-004 | Consolidate purchases | Detail View Materials |
| REQ-VER-005 | Approve | Action Buttons |
| REQ-VER-006 | Reject | Action Buttons + Remarks Modal |
| REQ-VER-007 | Return for Correction | Action Buttons + Remarks Modal |
| REQ-VER-008 | Changes require remarks | API Validation |
| REQ-VER-009 | Changes require audit trail | Audit Logging & Timeline |
| REQ-BR-004 | Approval-gated calculations | Status transitions |
| REQ-BR-005 | Exception flagging | Badge Components & API Logic |
| REQ-BR-006 | Approved record protection | Global Read-Only Enforcement |

---

## Database

### New Tables
1. **verification_records** — Audit linkage for supervisor actions

### Schema Updates
- Ensure `exception_flags` JSONB exists on attendance_records and daily_work_entries.

Full schema in [`database-plan.md`](./database-plan.md).

---

## Backend

### Module Structure
```
backend/app/modules/verification/
├── __init__.py
├── models.py          — VerificationRecord SQLAlchemy model
├── schemas.py         — SummaryResponse, DetailResponse, ActionRequest
├── service.py         — Aggregation logic, approve/reject/return actions, exception computation
├── repository.py      — Verification CRUD
└── exceptions.py      — InvalidVerificationState
```

### Service Layer Logic

1. **get_eod_summary**:
   - Query all assigned employees (or all if Director/Admin).
   - For a given date, aggregate attendance status, count work entries, count photos, sum material cost.
   - Compute `exception_flags` for each row dynamically.
   - Return list with `has_pending_verification` flag.

2. **approve / reject / return**:
   - Validate `entity_type` ('attendance', 'daily_work', or 'material').
   - Validate current status == 'submitted' (or 'approved' for authorized reopen by Admin/Director).
   - If reject/return, validate `remarks` trimmed length >= 10 chars.
   - Enforce SEC-004-A: Return generic 404 Not Found if target employee/record is unassigned or non-existent.
   - Update target entity status.
   - Insert `verification_records` with `verified_by` = current_user.
   - Insert immutable `audit_logs` record.

3. **Global Protection (REQ-BR-006)**:
   - Modifications to `attendance_records`, `daily_work_entries`, or `material_transactions` where `status == 'approved'` return HTTP 409 Conflict.
   - Reopening an approved record creates a new `verification_record` with `action='correction_required'` and transitions status to `correction_required` (restricted to Admin/Director).

---

## API Endpoints

| API ID | Method | Endpoint | Auth | Purpose |
|--------|--------|----------|------|---------|
| VER-001 | GET | /api/v1/verification/summary | Supervisor, Admin, Director | EOD summary queue |
| VER-002 | GET | /api/v1/verification/summary/{emp_id} | Supervisor (assigned), Admin, Director | Employee detail with audit history |
| VER-003 | POST | /api/v1/verification/{id}/approve | Supervisor (assigned), Admin, Director | Approve attendance, work, or material |
| VER-004 | POST | /api/v1/verification/{id}/reject | Supervisor (assigned), Admin, Director | Reject attendance, work, or material |
| VER-005 | POST | /api/v1/verification/{id}/return | Supervisor (return submitted) / Admin, Director (reopen approved) | Return for correction or reopen |

Full contracts in [`backend-api-plan.md`](./backend-api-plan.md).

---

## Frontend

### Pages
1. **Verification Queue** (`/verification`): List of employees pending verification for selected date.
2. **Verification Detail** (`/verification/:employeeId`): Comprehensive view of the employee's day.

### Key Components
- **ExceptionBadge**: Visual indicator for anomalies (red/amber)
- **PhotoLightbox**: Expandable gallery for work photos and bill images
- **ActionActionBar**: Sticky bottom bar with Approve (green), Reject (red), Return (amber) buttons
- **RemarksModal**: Dialog for capturing mandatory remarks
- **AuditTimeline**: Visual history of changes

### Design Decisions
- **Mobile & Tablet Focus**: Supervisors will likely use tablets. Queue view adapts from cards (mobile) to table (tablet/desktop).
- **Consolidated View**: Supervisor must not need to navigate between multiple pages to verify one employee's day. All info (attendance, work, photos, materials) is in one scrolling view.
- **Optimistic UI**: Upon approval, update UI immediately to remove item from queue while API call completes.

---

## Dependencies
| Dependency | Source | Required For |
|-----------|--------|-------------|
| Attendance records | Phase 2 | Verification target |
| Daily work entries | Phase 3 | Verification target |
| Photos & Materials | Phase 3 | Context for verification |
| Audit Logging system | Phase 1 | REQ-VER-009 |

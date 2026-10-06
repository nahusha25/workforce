# Phase 4 — Frontend Plan

## Pages
- **Supervisor Verification Queue** (`SupervisorVerificationQueuePage.tsx`, `/verification`):
  - List of employees with attendance and work for the selected date.
  - Controls: Date picker, Site filter.
  - Card elements: Employee name & code, site name, check-in/out times, working hours, work entry count, photo count, material count, total material cost, exception badges (`ExceptionBadge`), and pending/reviewed state badges (`pending-badge`, `nothing-pending-badge`, `reviewed-badge`).
  - Stale-response race condition tracked under backlog item `FE-QUEUE-RACE`.

- **Employee Day Verification Detail** (`EmployeeDayVerificationPage.tsx`, `/verification/:employeeId`):
  - Comprehensive drill-down inspection of an employee's full day.
  - Sections:
    1. Employee Header & Date selector with back link to queue.
    2. Attendance Card: check-in/out times, distance (m), GPS coordinates, working & overtime hours, geofence status badge, attendance audit history timeline, and Approve/Reject/Return actions.
    3. Multi-Activity Work Entry Cards: activity name, category, work order info, quantity + UOM, status badge, draft note ("Not submitted yet"), photos with lightbox zoom, nested materials list, work entry audit history timeline, and Approve/Reject/Return/Reopen action buttons.
    4. Material Transaction Cards: independent verification actions (Approve, Reject, Return, Reopen), bill image thumbnail/lightbox, high-value badge, and material-specific audit history timeline.

## Components
| Component | File Path | Purpose |
|-----------|-----------|---------|
| `SupervisorVerificationQueuePage` | `frontend/src/pages/SupervisorVerificationQueuePage.tsx` | Verification queue page with date & site filters |
| `EmployeeDayVerificationPage` | `frontend/src/pages/EmployeeDayVerificationPage.tsx` | Full-day verification drill-down with independent line-item actions |
| `ExceptionBadge` | `frontend/src/components/verification/ExceptionBadge.tsx` | Color-coded severity badges for anomalies |
| `VerificationRemarksModal` | `frontend/src/components/verification/VerificationRemarksModal.tsx` | Accessible modal enforcing >= 10 character mandatory remarks for reject/return/reopen |
| `AuditHistoryTimeline` | `frontend/src/components/verification/AuditHistoryTimeline.tsx` | Vertical chronological audit spine with action icons, actor names, timestamps, and remarks |
| Photo Lightbox | Inline in `EmployeeDayVerificationPage.tsx` | Full-screen photo view with keyboard (Escape) dismissal |
| High-Value Warning Modal | Inline in `EmployeeDayVerificationPage.tsx` | Explicit warning dialog requiring confirmation before approving high-value purchases |

## Verification Granularity
- In accordance with the Phase 3 multi-activity line-item data model, verification is decoupled at the individual entity level. Supervisors can approve/reject/return daily work entries and material transactions independently.
- Admin and Director roles can reopen already approved entries via `reopen-work-entry-{id}` or `reopen-material-{id}` buttons, requiring >= 10 character remarks and appending to `AuditHistoryTimeline`.

## Backlog Items & Refactor Opportunities
- `FE-QUEUE-RACE`: Fix rapid date-switch in-flight response race condition in `SupervisorVerificationQueuePage`.
- `OPT-BASE-MODAL`: Extract shared base modal primitives between `VerificationRemarksModal` and approval confirmation dialogs.

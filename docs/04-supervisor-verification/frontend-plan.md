# Phase 4 — Frontend Plan

## Pages
- **4.1 EOD Summary**: List of employees with pending verification, showing: name, check-in/out times, work summary, photo count, material count, exception flags
- **4.2 Employee Detail**: Full view of one employee's day — attendance, work quantities, photos (gallery), materials. Approve/Reject/Return buttons.

## Components
| Component | Purpose |
|-----------|---------|
| VerificationQueue | List of employees pending review |
| VerificationDetail | Full employee day summary |
| ApproveButton | One-touch approve |
| RejectButton | Opens remarks modal, then rejects |
| ReturnButton | Opens remarks modal, then returns |
| RemarksModal | Mandatory text input for reject/return |
| ExceptionBadge | Visual flag for anomalies |
| PhotoGallery | Thumbnail grid with full-size view |
| AuditHistory | Timeline of changes for approved records |

## Mobile Design
- Queue as card list (employee name + summary + exceptions)
- Detail as full-screen card with sections (attendance, work, photos, materials)
- Action buttons fixed at bottom of detail screen
- Swipe between employees (optional enhancement)

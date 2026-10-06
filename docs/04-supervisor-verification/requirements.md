# Phase 4 — Supervisor Verification — Requirements

## Source Reference
- Page 4: "Supervisor Verification"
- Business Rules: REQ-BR-004, REQ-BR-005, REQ-BR-006

## Requirement Scope
Enable supervisors to review, approve, reject, or return end-of-day consolidated attendance, work quantities, photos, and material purchases for their assigned employees.

## Functional Requirements
| ID | Requirement |
|----|-------------|
| REQ-VER-001 | Consolidate attendance by employee/site at EOD |
| REQ-VER-002 | Consolidate work quantities by employee/site at EOD |
| REQ-VER-003 | Consolidate photos by employee/site at EOD |
| REQ-VER-004 | Consolidate purchases by employee/site at EOD |
| REQ-VER-005 | Supervisor can Approve |
| REQ-VER-006 | Supervisor can Reject |
| REQ-VER-007 | Supervisor can Return for Correction |
| REQ-VER-008 | Changes to approved quantities require remarks |
| REQ-VER-009 | Changes to approved quantities require audit trail |

## Business Rules
1. Only supervisor-approved data feeds into payments/invoices (REQ-BR-004).
2. Exceptions flagged for supervisor attention (REQ-BR-005).
3. Approved records become read-only; reopening requires authorised approval and complete change history (REQ-BR-006).
4. Remarks mandatory for rejection and return.
5. All verification actions are audited.

## State Transitions
```
submitted → Approve → approved (read-only)
submitted → Reject → rejected
submitted → Return → correction_required
correction_required → Employee re-submits → submitted
approved → Reopen (authorised only) → correction_required (with audit trail)
```

## Acceptance Criteria
- [x] Supervisor sees EOD summary of assigned employees' attendance, work, photos, materials
- [x] Supervisor can approve individual entries
- [x] Supervisor can reject with mandatory remarks
- [x] Supervisor can return for correction with mandatory remarks
- [x] Approved records become read-only
- [x] Changes to approved records require remarks and produce audit trail
- [x] Exception flags visible to supervisor (missing checkout, no photo, high-value purchase, etc.)

## Dependencies
- Phase 3 complete (work entries and materials exist with submitted status)

# Phase 4 — UI/UX Plan

## Design Principles
1. **Review Efficiency** — supervisor reviews multiple employees daily; minimise clicks per review.
2. **Exception Prominence** — anomalies must be immediately visible.
3. **Action Clarity** — Approve (green), Reject (red), Return (orange) visually distinct.

## Screen: EOD Summary (Mobile)
```
┌──────────────────────────┐
│  Verification | 11 Aug   │
│  3 pending  1 approved   │
├──────────────────────────┤
│  ┌────────────────────┐  │
│  │ Rajesh K           │  │
│  │ 8:15–17:30 | 9.25h │  │
│  │ Work: 120m cable   │  │
│  │ ⚠ No photo         │  │  ← Exception flag
│  │ [Review →]         │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │ Suresh M           │  │
│  │ 8:00–17:00 | 9.0h  │  │
│  │ Work: 3 devices    │  │
│  │ ✅ Complete         │  │
│  │ [Review →]         │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

## Screen: Detail Review (Mobile)
```
┌──────────────────────────┐
│  ← Rajesh K | 29 Sep    │
├──────────────────────────┤
│  ATTENDANCE              │
│  In: 8:15 | Out: 17:30  │
│  GPS: ⚠ Out of Location  │
│  [Approve] [Reject]      │
│  [Return for Correction] │
│  ── Attendance History ──│
├──────────────────────────┤
│  WORK ENTRY: Cable Laying│
│  Quantity: 120.5m        │
│  Photos: [thumb]         │
│  [Approve] [Reject]      │
│  [Return] [Reopen (Admin)│
│  ── Materials ────────── │
│  ┌──────────────────────┐│
│  │ Heat Shrink (₹150)   ││
│  │ [Approve] [Reject]   ││
│  └──────────────────────┘│
│  ┌──────────────────────┐│
│  │ Cleaver Blade (₹4500)││
│  │ ⚠ High-Value Purchase││
│  │ [Approve] → [Warning]││
│  └──────────────────────┘│
│  ── Work Entry History ──│
│  ● Approved by Sup       │
│  ● Returned by Admin     │
└──────────────────────────┘
```

## Modals
1. **VerificationRemarksModal**:
   - Triggered on Reject, Return for Correction, or Reopen.
   - Requires >= 10 non-whitespace characters in textarea before submit button is enabled.
   - Shows live character counter when under the threshold.
2. **High-Value Approval Warning Modal**:
   - Triggered when approving any material transaction with `is_high_value = true`.
   - Displays clear warning banner stating that the purchase amount exceeds the item's purchase approval limit.
   - Requires explicit confirmation click (`Confirm Approval`) to submit.

## Accessibility
- Exception badges: semantic text + icon + high-contrast color scheme.
- Action buttons: descriptive `data-testid` and context-specific aria labels.
- Photo gallery: alt text, lightbox dialog with role `dialog`, aria-modal, and Escape key dismissal.
- Remarks modal: focus trap, title with `id="remarks-modal-title"`, submit button disabled state reflected in aria.
- Audit history timeline: semantic `<ol aria-label="Verification audit history">` with `<time>` elements and `<blockquote>` remarks.

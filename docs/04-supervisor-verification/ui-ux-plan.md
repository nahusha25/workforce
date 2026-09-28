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
│  ← Rajesh K | 11 Aug    │
├──────────────────────────┤
│  ATTENDANCE              │
│  In: 8:15 | Out: 17:30  │
│  GPS: ✅ Within range    │
├──────────────────────────┤
│  WORK QUANTITIES         │
│  Cable Runs: 5           │
│  Cable Length: 120.5m    │
│  Devices: 0              │
├──────────────────────────┤
│  PHOTOS (2)              │
│  [thumb] [thumb]         │
├──────────────────────────┤
│  MATERIALS               │
│  Cat6 Cable: 100m ₹5000 │
│  ⚠ High-value purchase   │
├──────────────────────────┤
│ [Approve] [Reject] [Return] │
└──────────────────────────┘
```

## Accessibility
- Exception badges: text + icon + colour
- Action buttons: `aria-label` with employee context
- Photo gallery: alt text, keyboard navigable
- Remarks modal: focus trap, label, required indication

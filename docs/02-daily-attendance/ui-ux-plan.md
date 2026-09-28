# Phase 2 — UI/UX Plan

## Design Principles
1. **One-Touch Simplicity** — check-in is a single tap. No forms, no typing.
2. **Contextual Confidence** — auto-displayed info confirms employee, site, and GPS before action.
3. **Clear State Communication** — always show whether checked-in or not.

## Screen: Attendance (Mobile Layout)
```
┌──────────────────────────┐
│  📍 GPS: Acquired        │  ← GPS status (green dot if OK)
├──────────────────────────┤
│  Employee: Rajesh K      │  ← Auto-filled, read-only
│  Site: ABC Corp - Site 3 │
│  Date: 11 Aug 2025       │
├──────────────────────────┤
│                          │
│   ┌──────────────────┐   │
│   │                  │   │
│   │    CHECK IN      │   │  ← Large button, 80px, full-width
│   │                  │   │     (or CHECK OUT after check-in)
│   └──────────────────┘   │
│                          │
│  Checked in at: 8:15 AM  │  ← After check-in, shows time
└──────────────────────────┘
```

## States
| State | Display |
|-------|---------|
| Not checked in | Large green "CHECK IN" button |
| GPS acquiring | Spinner on GPS indicator, button disabled |
| GPS failed | Error message, retry button |
| Outside geo-fence | Warning with distance, button blocked |
| Checked in | Check-in time shown, "CHECK OUT" button (orange) |
| Checked out | Both times shown, no action available |
| Error | Error message with retry |

## Touch Targets
- Check-in/out button: 80px height, full-width, minimum 56px for secondary
- GPS retry: 44×44px
- All tappable: minimum 44×44px

## Accessibility
- Button: `aria-label="Check in to site ABC Corp Site 3"`
- GPS status: `aria-live="polite"` for status updates
- Time display: screen-reader-friendly time format
- Focus: auto-focus on primary button on page load

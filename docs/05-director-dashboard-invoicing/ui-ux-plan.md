# Phase 5 — UI/UX Plan

## Design Principles
1. **Data Density** — directors need to see many metrics at once. Maximise information density.
2. **Filter-Driven** — every view must be filterable by date, client, site, employee.
3. **Actionable Insights** — metrics should surface anomalies and trends, not just numbers.

## Screen: Dashboard Overview (Desktop)
```
┌───────────────────────────────────────────────────┐
│  Dashboard                    [Filter: This Week ▼]│
├────────────┬────────────┬────────────┬────────────┤
│ 👷 45      │ ⏱ 405.5h  │ 📏 12.5km  │ 📷 87     │
│ Manpower   │ Hours      │ Cable      │ Devices   │
├────────────┼────────────┼────────────┼────────────┤
│ 📊 0.85    │ 💰 ₹2.5L  │ ✅ 120     │ ⏳ 15     │
│ Productivity│ Mat. Cost │ Approved   │ Pending   │
├───────────────────────────┬───────────────────────┤
│  [Manpower by Date Chart] │ [Status Breakdown Pie]│
│  ████████████████████████ │        ██████         │
│  ████████████████         │      ████████         │
│  ██████████████████████   │        ████           │
├───────────────────────────┴───────────────────────┤
│  Site Progress                                     │
│  ┌──────────┬────────┬─────────┬────────┐         │
│  │ Site     │ Cable  │ Devices │ Status │         │
│  ├──────────┼────────┼─────────┼────────┤         │
│  │ Site A   │ 5.2km  │ 34      │ 72%    │         │
│  │ Site B   │ 4.8km  │ 28      │ 65%    │         │
│  └──────────┴────────┴─────────┴────────┘         │
└───────────────────────────────────────────────────┘
```

## Screen: Dashboard (Mobile)
```
┌──────────────────────────┐
│  Dashboard    [Filter ▼] │
├──────────────────────────┤
│  👷 45 Manpower          │
│  ⏱ 405.5h Working Hours │
│  📏 12.5km Cable         │
│  📷 87 Devices           │
├──────────────────────────┤
│  [Manpower Chart]        │
│  ████████████████████    │
├──────────────────────────┤
│  [Status Pie]            │
├──────────────────────────┤
│  Site Progress →         │
│  (horizontal scroll)     │
└──────────────────────────┘
```

## Metric Cards
- Large number (--font-size-3xl for desktop, --font-size-2xl for mobile)
- Label below (--font-size-sm)
- Optional trend indicator (↑↓)
- Subtle background colour per category

## Invoice Preview
- Header: company info, invoice number, period
- Line items table: description, quantity, rate, amount
- Totals: subtotal, materials, grand total
- Action: "Finalise" button
- Print-friendly layout for PDF export

## Accessibility
- Charts: provide data table alternative for screen readers
- Metric cards: `aria-label` with full context
- Export buttons: descriptive labels ("Export attendance report as Excel")
- Filter controls: labels and keyboard navigation

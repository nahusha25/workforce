# Phase 3 — UI/UX Plan

> Realigned per DB-ALIGN and FE-ALIGN: Multi-Activity Line Item UI/UX

## Design Principles
1. **Multi-Activity Flexibility** — workers perform multiple activity types in a single shift/site visit. Each activity is a dynamic line item with its own quantity, auto-derived unit of measure (UOM) badge, work order, and remarks.
2. **Upfront Session Validation** — workers are immediately informed if they are not checked in before investing time filling out form rows.
3. **Camera-First & Compressed** — progress photo uploads prioritize mobile camera (`capture="environment"`), with transparent client-side Canvas compression to ensure quick uploads on 3G/4G connections.
4. **Progressive Disclosure** — attachments (photos & materials) are tucked neatly inside an expandable accordion for each line, with an auto-save helper for unsaved drafts.
5. **Irreversible Submission Guardrails** — a comprehensive modal summary presents all recorded line items, quantities, and attachment counts with an explicit locking warning before submission.

## Screen: Multi-Activity Work Entry (Mobile)
```
┌───────────────────────────────────────────────┐
│  📍 Checked in at Site Alpha (08:30 AM)        │
├───────────────────────────────────────────────┤
│  Daily Work Entry                             │
│  Session for 2026-09-26 • Grouped Line Items  │
│                                               │
│  ┌─ Activity #1 [draft] ───────────────────┐  │
│  │ Activity: [Cable Pulling (CABLE) - m ▼] │  │
│  │ Qty: [ 45.0 ] [ metres ]                │  │
│  │ Work Order: [WO-2026-001 ▼]             │  │
│  │ Remarks: [Pulling Cat6 corridor A     ] │  │
│  │ ▼ Attachments & Materials (1 pic, 1 mat)│  │
│  │   📷 Site Progress Photos (1)           │  │
│  │   🧾 Material Transactions (1)          │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─ Activity #2 [draft] ───────────────────┐  │
│  │ Activity: [Device Installation ▼]       │  │
│  │ Qty: [ 6.0  ] [ devices]                │  │
│  │ Work Order: [-- None -- ▼]              │  │
│  │ Remarks: [Installed 6 bullet cams     ] │  │
│  │ ► Attachments & Materials (0 pics, 0 mat│  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  [ + Add Another Activity Line ]              │
├───────────────────────────────────────────────┤
│  [ 💾 Save Draft ]  [ 🚀 Submit Work (2) ]     │
└───────────────────────────────────────────────┘
```

## Review & Confirmation Modal
- Presents all line items, their quantities + auto-derived UOMs, and associated attachment counts.
- Displays unambiguous locking advisory: "Once submitted, all activity lines will be locked for editing until supervisor verification."
- Action Buttons: `Cancel` (outline) and `Confirm & Submit` (primary).

## Touch Targets & Accessibility
- All inputs: minimum 48px height, 16px font size to prevent mobile browser zoom.
- Camera and browse actions: prominent touch targets.
- Dynamic UOM badges: high-contrast pills styled with tooltip explanation (`title="Auto-derived Unit of Measure"`).
- Status badges: semantic color and text combinations.

# Phase 3 — Frontend Plan

> Realigned per DB-ALIGN and FE-ALIGN: Multi-Activity Line Item Architecture

## Pages & Screens
- **3.1 Daily Work Entry (`DailyWorkEntryPage.tsx`)**:
  - Upfront active attendance session check with direct link to `/attendance` if not checked in.
  - Multi-activity line-item list: dynamically add/remove activity lines for a single work session.
  - Per-line fields: Activity selector, Quantity with auto-derived Unit of Measure (UOM) badge from activity master data, Work Order selector, and Remarks.
  - Expandable accordion per line: "Attachments & Materials (X photos, Y items)" with inline auto-save prompt for unpersisted drafts.
  - Global actions: Save Draft (with localStorage recovery banner) and Submit Work.
  - Review & Confirmation modal: tabular overview of all lines and attachments with locking notice.
  - Locked / Read-only state once submitted.
- **3.2 Photo Upload (`WorkPhotoCapture.tsx`)**:
  - Camera-first capture (`capture="environment"` on mobile) and file browser fallback.
  - Client-side Canvas image compression (max 1920x1080, JPEG quality 0.8) before upload.
  - Upload progress bar and thumbnail gallery with timestamp and deletion controls.
- **3.3 Material Entry (`MaterialTransactionEntry.tsx`)**:
  - Type toggle: "Consumed on Site" vs. "Purchased Locally".
  - Free-text or catalog item name, quantity, amount, and optional receipt bill upload.
  - Automatic "High Value" badge based on material purchase approval limit.
- **A.3 Admin — Activity & Material Management (`ActivitiesPage.tsx`, `MaterialsPage.tsx`)**:
  - CRUD tables for managing Activities (rates, UOM, categories) and Materials.

## Component Architecture
| Component | Purpose |
|---|---|
| `DailyWorkEntryPage` | Primary container managing multi-activity line state, attendance context, draft persistence, and submission modal |
| `WorkPhotoCapture` | Camera/file photo capture, compression, upload to `/daily-work/{id}/photos`, and gallery |
| `MaterialTransactionEntry` | Inline material consumption/purchase logger with bill receipt upload and transaction list |
| `StatusBadge` | Standardized status pill (`draft`, `submitted`, `approved`, `rejected`, `flagged`) |
| `Button`, `Card`, `Select` | Core UI design tokens and accessible inputs |

## Mobile-First Design
- Stacked cards with generous touch targets (≥ 48px input height, 56px action buttons).
- Numeric input optimization (`type="number"`, `step="any"`).
- Native camera access (`capture="environment"`).
- Sticky bottom/top action bars for draft saving and batch submission.

## Key UX Decisions & Guardrails
1. **Upfront Session Validation**: Display a prominent banner if the employee has no active unclosed attendance session, preventing wasted effort filling out un-submittable lines.
2. **Auto-save on First Attachment**: Seamlessly auto-saves an unsaved activity line draft when the user expands and interacts with photo/material attachments.
3. **Local Draft Resilience**: Recovers unsaved form state from `localStorage` in case of browser refresh or connectivity drop.
4. **Modal Verification**: Two-step submission confirmation displaying all lines and attachment counts before triggering irreversible locking.

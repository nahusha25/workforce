# UI/UX Architecture

## Design Principles

1. **Operational Clarity** — the interface prioritises efficiency for repetitive field work. Every screen answers: "What do I need to do right now?"
2. **Minimal Cognitive Load** — construction labourers use this daily. Minimise reading, maximise recognition. Large targets, clear icons, auto-filled values.
3. **Mobile-First for Field Workers** — designed for low-cost Android phones with small screens and outdoor glare. High contrast, large text, thumb-friendly zones.
4. **Status Transparency** — the current state of every record (Draft, Submitted, Approved, Rejected, Correction Required) must be immediately visible.
5. **Error Prevention over Error Recovery** — auto-fill, dropdowns, and constraints prevent errors before they happen.

## Visual Direction

### Use
- Clean, functional enterprise design (not consumer/SaaS aesthetic)
- High-contrast colour scheme for outdoor visibility
- Card-based layouts for mobile
- Clear visual hierarchy with size and weight (not decoration)
- Consistent icon language for actions
- System font stack for performance on low-end devices

### Avoid
- Generic purple-gradient SaaS templates
- Unnecessary visual decoration or illustration
- Low-contrast UI elements
- Dense desktop-first data tables on mobile
- Excessive animation (distracting on slow devices)
- Ambiguous primary actions
- Inconsistent component patterns across pages

## Design Tokens

### Colour Palette
```css
:root {
  /* Primary — used for primary actions and navigation */
  --color-primary-50: #e8f5e9;
  --color-primary-100: #c8e6c9;
  --color-primary-500: #4caf50;
  --color-primary-600: #43a047;
  --color-primary-700: #388e3c;
  --color-primary-800: #2e7d32;

  /* Neutral — backgrounds, text, borders */
  --color-neutral-0: #ffffff;
  --color-neutral-50: #fafafa;
  --color-neutral-100: #f5f5f5;
  --color-neutral-200: #eeeeee;
  --color-neutral-300: #e0e0e0;
  --color-neutral-500: #9e9e9e;
  --color-neutral-700: #616161;
  --color-neutral-800: #424242;
  --color-neutral-900: #212121;

  /* Status Colours — matched to workflow statuses */
  --color-status-draft: #9e9e9e;       /* Grey */
  --color-status-submitted: #1976d2;   /* Blue */
  --color-status-approved: #2e7d32;    /* Green */
  --color-status-rejected: #c62828;    /* Red */
  --color-status-correction: #e65100;  /* Orange */

  /* Semantic */
  --color-error: #c62828;
  --color-warning: #e65100;
  --color-success: #2e7d32;
  --color-info: #1565c0;

  /* Surface */
  --color-surface: #ffffff;
  --color-surface-elevated: #ffffff;
  --color-background: #f5f5f5;
}
```

### Typography Scale
```css
:root {
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

  --font-size-xs: 0.75rem;   /* 12px — captions */
  --font-size-sm: 0.875rem;  /* 14px — secondary text */
  --font-size-md: 1rem;      /* 16px — body text (minimum for mobile) */
  --font-size-lg: 1.125rem;  /* 18px — labels, emphasis */
  --font-size-xl: 1.25rem;   /* 20px — section headers */
  --font-size-2xl: 1.5rem;   /* 24px — page headers */
  --font-size-3xl: 2rem;     /* 32px — hero numbers (dashboard) */

  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
}
```

### Spacing Scale
```css
:root {
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-5: 1.25rem;  /* 20px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --space-10: 2.5rem;  /* 40px */
  --space-12: 3rem;    /* 48px */
}
```

### Border Radius
```css
:root {
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
}
```

### Shadows / Elevation
```css
:root {
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.12);
  --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.16);
}
```

### Breakpoints
```css
/* Mobile-first: no media query needed for mobile (default) */
/* Tablet */  @media (min-width: 768px) { }
/* Desktop */ @media (min-width: 1024px) { }
```

### Motion Rules
```css
:root {
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;
  --easing-default: cubic-bezier(0.4, 0, 0.2, 1);
}
/* Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

### Focus Styles
```css
:root {
  --focus-ring: 0 0 0 2px var(--color-primary-500);
}
```

## Screen Inventory

| # | Screen | Primary User | Phase |
|---|--------|-------------|-------|
| 1.1 | OTP Login — Mobile Entry | All | 1 |
| 1.2 | OTP Login — Verification | All | 1 |
| 1.3 | Employee Onboarding Form | Admin | 1 |
| 2.1 | Attendance — Check-In/Out | Employee | 2 |
| 2.2 | Attendance — Supervisor Override | Supervisor | 2 |
| 3.1 | Daily Work — Activity Entry | Employee | 3 |
| 3.2 | Daily Work — Photo Upload | Employee | 3 |
| 3.3 | Daily Work — Material Entry | Employee | 3 |
| 4.1 | Verification — EOD Summary | Supervisor | 4 |
| 4.2 | Verification — Detail Review | Supervisor | 4 |
| 5.1 | Dashboard — Overview | Director | 5 |
| 5.2 | Dashboard — Report View | Director | 5 |
| 5.3 | Invoice Generation | Director | 5 |
| A.1 | Admin — Employee Management | Admin | 1 |
| A.2 | Admin — Client/Site Management | Admin | 1 |
| A.3 | Admin — Activity/Material Management | Admin | 3 |

## User Flows

### Employee Daily Flow
```
Login (if needed)
  ↓
Check-In (one touch)
  ↓
Enter work quantities
  ↓
Upload photos
  ↓
Record materials
  ↓
Submit work
  ↓
Check-Out
```

### Supervisor Daily Flow
```
Login (if needed)
  ↓
View EOD verification queue
  ↓
Review employee: attendance + work + photos + materials
  ↓
Approve / Reject / Return for Correction
  ↓
Add remarks (if rejecting/returning)
```

### Director Flow
```
Login (if needed)
  ↓
View dashboard metrics (filtered by date/client/site)
  ↓
Drill into reports
  ↓
Generate weekly payment/invoice
  ↓
Export to Excel/PDF
```

## Responsive Behaviour

### Mobile (default — primary target)
- Single-column layout
- Bottom navigation bar with icon + label
- Full-width cards and buttons
- Stacked form fields
- Tables converted to card lists
- Floating action button for primary action

### Tablet (768px+)
- Two-column layout where appropriate
- Side navigation or top navigation
- Cards in grid (2-up)
- Tables with horizontal scroll if needed

### Desktop (1024px+)
- Sidebar navigation
- Multi-column dashboard layout
- Full data tables with sorting/filtering
- Side-by-side panels (e.g., list + detail view)

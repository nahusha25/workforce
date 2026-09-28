# Phase 1 — UI/UX Plan

## Design Principles
1. **Instant Recognition** — the login screen must be immediately understandable to field workers with minimal literacy.
2. **One Task Per Screen** — enter mobile → enter OTP → done. No combined multi-step forms.
3. **Thumb-Zone Optimised** — primary actions in the bottom 60% of mobile screen.

## Screen Designs

### 1.1 Login — Mobile Number Entry

**Layout (Mobile)**:
- Top: App logo + "i-Workforce" title
- Centre: Mobile number input (large, full-width, tel inputMode)
- Bottom: "Send OTP" button (large, primary green, full-width, 56px height)

**States**:
| State | Display |
|-------|---------|
| Default | Empty input + disabled button |
| Valid input | Enabled button |
| Loading | Button shows spinner, input disabled |
| Error (not registered) | Error message below input |
| Error (rate limited) | "Too many attempts. Try again in X minutes." |

**Responsive**: Centres content in a narrow card on tablet/desktop.

### 1.2 Login — OTP Verification

**Layout (Mobile)**:
- Top: "Enter OTP sent to 98765XXXXX"
- Centre: 6 separate digit inputs (large, 48px each, auto-advance)
- Timer: "OTP expires in 4:32"
- Bottom: "Verify" button + "Resend OTP" link

**States**:
| State | Display |
|-------|---------|
| Default | Empty digits + disabled verify |
| Filled | Enabled verify button |
| Loading | Button spinner |
| Error (wrong OTP) | "Invalid OTP. X attempts remaining." |
| Error (expired) | "OTP expired." + enabled resend |

### 1.3 Employee Registration Form (Admin)

**Layout (Mobile)**: Stacked full-width fields in a card
- Name (text input)
- Mobile (tel input)
- Employee ID (text input)
- Trade/Role (dropdown)
- Rate Type (dropdown: Daily/Weekly/Piece)
- Rate Amount (numeric input)
- Supervisor (searchable dropdown)
- Site Assignment (multi-select or checklist)
- "Register Employee" button

**Layout (Desktop)**: Two-column form within a page layout.

### A.1 Employee List (Admin)

**Layout (Mobile)**: Card list with employee name, ID, trade, status badge
**Layout (Desktop)**: Table with columns: Name, ID, Trade, Supervisor, Rate, Status, Actions

## Component Tokens

| Component | Token Reference |
|-----------|----------------|
| Primary button | `--color-primary-600`, `--radius-md`, height: 56px (mobile), 44px (desktop) |
| Input field | `--color-neutral-200` border, `--radius-md`, `--font-size-md`, padding: `--space-4` |
| Card | `--color-surface`, `--shadow-sm`, `--radius-lg`, padding: `--space-4` |
| Status badge | `--color-status-*`, `--radius-full`, `--font-size-sm` |
| Error text | `--color-error`, `--font-size-sm` |

## Accessibility

- OTP inputs: `aria-label="Digit 1 of 6"`, etc.
- Form fields: visible labels, `aria-required`, `aria-describedby` for errors
- Status badges: text + colour (not colour alone)
- Buttons: minimum 44×44px touch target
- Focus: auto-focus on first input, tab order follows visual order
- Login: `aria-live="polite"` region for error/success messages

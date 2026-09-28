# Accessibility Rules

## Guiding Standard

Aim for WCAG 2.1 Level AA compliance where applicable. Accessibility is an engineering requirement, not a final cosmetic pass.

## Keyboard Navigation

- All interactive elements (buttons, links, inputs, dropdowns) must be reachable via Tab key.
- Focus order must follow the visual layout (logical reading order).
- Custom interactive widgets must support expected keyboard patterns (Enter to activate, Escape to close modals, Arrow keys for menus).
- No keyboard traps — users must be able to Tab out of any component.

## Focus Management

- Visible focus indicators on all interactive elements — do not remove browser default outlines without providing a visible alternative.
- Focus ring: minimum 2px solid, sufficient contrast against background.
- When opening a modal/dialog, move focus to the modal.
- When closing a modal, return focus to the triggering element.
- When navigating between routes, move focus to the main content heading.

## Semantic HTML

- Use `<button>` for actions, `<a>` for navigation — not `<div>` with click handlers.
- Use `<nav>` for navigation regions.
- Use `<main>` for primary content.
- Use `<header>`, `<footer>` appropriately.
- Use `<form>` with proper `<label>` associations.
- Use heading hierarchy (`<h1>` → `<h2>` → `<h3>`) — one `<h1>` per page.
- Use `<table>` with `<thead>`, `<th>`, `<caption>` for tabular data.

## Labels and Text

- Every form input must have a visible `<label>` with `htmlFor` / `for` attribute matching the input `id`.
- Group related form fields with `<fieldset>` and `<legend>`.
- Placeholder text is not a substitute for labels.
- Error messages must be associated with their input using `aria-describedby`.
- Required fields must be indicated visually and programmatically (`aria-required="true"`).

## ARIA Usage

- Use ARIA only when semantic HTML is insufficient.
- Prefer semantic HTML over ARIA (a `<button>` over `role="button"` on a `<div>`).
- If using ARIA: `aria-label`, `aria-describedby`, `aria-live`, `aria-expanded`, `aria-hidden`.
- Dynamic content updates should use `aria-live="polite"` regions (e.g., form submission success/error, notification toasts).

## Color and Contrast

- Text must have a minimum contrast ratio of 4.5:1 against its background (WCAG AA).
- Large text (18px+ or 14px+ bold) requires minimum 3:1.
- Do not use color alone to convey information — supplement with text, icons, or patterns.
- Status indicators (Draft, Submitted, Approved, Rejected, Correction Required) must be distinguishable by more than color.

## Touch Targets

- Minimum touch target size: 44×44px (per WCAG 2.5.5 and project requirements for field workers using low-cost Android phones).
- Ensure adequate spacing between adjacent touch targets.
- Large buttons per requirements: ensure primary actions are prominent and easily tappable.

## Screen Reader Support

- All images must have meaningful `alt` text, or `alt=""` if decorative.
- Icon-only buttons must have `aria-label`.
- Status changes (approval, rejection) must be announced via `aria-live` regions.
- Data tables must have column headers (`<th scope="col">`).

## Responsive Accessibility

- Ensure accessibility at all breakpoints (mobile, tablet, desktop).
- Mobile navigation must be keyboard accessible when hamburger menus are used.
- Ensure zoom up to 200% does not break layout or lose content.
- Touch-friendly on mobile, keyboard-friendly on desktop.

## Forms (specific to this application)

- Auto-filled fields (employee, date, site) should be read-only and announced to screen readers.
- Numeric keypad inputs must still have associated labels.
- Camera upload buttons must have descriptive labels (e.g., "Upload work progress photo").
- Multi-step forms should indicate current step and total steps.
- Validation errors should be summarized and individual fields marked with `aria-invalid="true"`.

## Tables (data tables used in verification and dashboard)

- Use `<caption>` or `aria-label` to describe the table's purpose.
- Use `<th scope="col">` for column headers.
- Use `<th scope="row">` for row headers where applicable.
- On mobile: consider converting tables to card layouts or stacked layouts for readability.
- Sortable columns should indicate sort direction with `aria-sort`.

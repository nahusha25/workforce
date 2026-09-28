# Accessibility Checklist

Use this checklist for every user-facing screen.

## Keyboard Navigation
- [ ] All interactive elements reachable via Tab
- [ ] Focus order follows visual layout
- [ ] Custom widgets support expected keyboard patterns
- [ ] No keyboard traps
- [ ] Escape closes modals/dialogs

## Focus Management
- [ ] Visible focus indicators on all interactive elements
- [ ] Focus ring: minimum 2px, sufficient contrast
- [ ] Modal open → focus moves to modal
- [ ] Modal close → focus returns to trigger
- [ ] Route change → focus moves to main heading

## Semantic HTML
- [ ] `<button>` for actions, `<a>` for navigation
- [ ] `<nav>`, `<main>`, `<header>`, `<footer>` used correctly
- [ ] Heading hierarchy (h1 → h2 → h3) — one h1 per page
- [ ] `<table>` with `<thead>`, `<th>`, `<caption>` for data tables
- [ ] `<form>` with proper `<label>` associations

## Labels and ARIA
- [ ] Every form input has a visible `<label>`
- [ ] Required fields indicated with `aria-required`
- [ ] Error messages associated via `aria-describedby`
- [ ] Icon-only buttons have `aria-label`
- [ ] Dynamic updates use `aria-live` regions
- [ ] Images have meaningful `alt` text (or `alt=""` if decorative)

## Color and Contrast
- [ ] Text contrast ratio ≥ 4.5:1 (AA)
- [ ] Large text contrast ratio ≥ 3:1
- [ ] Status not conveyed by color alone (text/icon supplement)

## Touch Targets
- [ ] Minimum touch target: 44×44px
- [ ] Adequate spacing between adjacent targets
- [ ] Primary actions prominent and easily tappable

## Forms (specific to this app)
- [ ] Numeric keypad for quantity inputs
- [ ] Camera upload buttons have descriptive labels
- [ ] Auto-filled fields are read-only and announced
- [ ] Validation errors summarized and individual fields marked
- [ ] Multi-step forms indicate current/total steps

## Tables
- [ ] Column headers use `<th scope="col">`
- [ ] Table has `<caption>` or `aria-label`
- [ ] Mobile: tables converted to card/stacked layout
- [ ] Sortable columns indicate sort direction

## Responsive
- [ ] Accessible at all breakpoints
- [ ] Zoom to 200% doesn't break layout
- [ ] Mobile navigation is keyboard accessible

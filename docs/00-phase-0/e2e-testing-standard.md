# E2E Testing Standard

See also: `.ai/workflows/e2e-testing.md` for the complete workflow.

## Tooling

- **Playwright** for browser automation
- **TypeScript** for test scripts
- Mobile Chrome (Pixel 5 profile) as primary test target per mobile-first requirement
- Desktop Chrome as secondary test target

## Configuration

See `.ai/workflows/e2e-testing.md` for the Playwright config template. Key settings:
- Timeout: 30 seconds per test
- Retries: 2 (on first retry, capture trace)
- Screenshots: on failure only
- Projects: Mobile Chrome (primary), Desktop Chrome

## Critical User Journeys

| Journey ID | Journey | Phase | Actor | Priority |
|------------|---------|-------|-------|----------|
| E2E-J01 | Employee registration and OTP login | 1 | Employee + Admin | High |
| E2E-J02 | Session persistence (no daily OTP) | 1 | Employee | High |
| E2E-J03 | Daily check-in with GPS and geo-fence | 2 | Employee | High |
| E2E-J04 | Check-in outside geo-fence + supervisor override | 2 | Employee + Supervisor | High |
| E2E-J05 | Daily check-out | 2 | Employee | High |
| E2E-J06 | Work entry with activity and quantities | 3 | Employee | High |
| E2E-J07 | Work photo upload | 3 | Employee | Medium |
| E2E-J08 | Material purchase recording with bill image | 3 | Employee | Medium |
| E2E-J09 | Work submission before check-out | 3 | Employee | High |
| E2E-J10 | Supervisor EOD verification (approve) | 4 | Supervisor | High |
| E2E-J11 | Supervisor reject with remarks | 4 | Supervisor | High |
| E2E-J12 | Supervisor return for correction | 4 | Supervisor | Medium |
| E2E-J13 | Director dashboard data visibility | 5 | Director | High |
| E2E-J14 | Weekly invoice generation | 5 | Director | High |
| E2E-J15 | Report export (Excel/PDF) | 5 | Director | Medium |
| E2E-J16 | Full flow: submit → approve → dashboard | Cross | All | High |

## Selectors

- Prefer `data-testid` attributes: `[data-testid="check-in-button"]`
- Use ARIA roles: `getByRole('button', { name: 'Check In' })`
- Use labels: `getByLabel('Cable length (metres)')`
- **Do not** use CSS class selectors
- **Do not** use complex XPath

## Test Data

- Seed via API calls in `test.beforeAll()`
- Clean up in `test.afterAll()`
- Use unique identifiers per test run to avoid collisions
- Store test data config in `e2e/fixtures/`

## Journeys That Cannot Be Fully Automated

| Journey | Reason | Mitigation |
|---------|--------|------------|
| SMS OTP delivery | Requires real SMS service | Mock OTP service in test environment; use known test OTP |
| GPS location capture | Requires browser geolocation mock | Use Playwright's `context.grantPermissions` + `setGeolocation` |
| Camera photo capture | Requires device camera | Use file input with test image file |
| Offline/weak network | Requires network simulation | Use Playwright's `route.abort()` for network error simulation |

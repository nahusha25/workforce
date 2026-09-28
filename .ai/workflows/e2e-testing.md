# E2E Testing Workflow

## Trigger
- A feature with a critical user journey is complete.
- A phase implementation is complete.
- Regression testing is required.

## Tooling
- **Playwright** for browser automation.
- **TypeScript** for test scripts.
- Configure for local and CI execution.

## Workflow

### Step 1 — Identify Critical Journeys
Review the phase's `testing-plan.md` and `requirements.md` to identify user journeys that must have E2E coverage.

Examples from this project:
- Employee registration and OTP login
- Daily check-in with GPS capture
- Daily work submission with photo upload
- Supervisor end-of-day verification (approve/reject/return)
- Director dashboard data visibility and report export

### Step 2 — Confirm Journey Scope
- List the journeys to be tested.
- Confirm with the team/user if the scope is appropriate.
- Do not test every micro-interaction with E2E — use lower-level tests for that.

### Step 3 — Write Tests
For each journey, test:
- **Happy path** — the expected successful flow.
- **Validation failures** — submitting invalid data.
- **Permission failures** — accessing as the wrong role.
- **Session expiry** — accessing with expired/invalid auth (where applicable).
- **Empty data** — displaying the feature with no data.
- **Error states** — API failures, network errors.

### Step 4 — Selectors
- Prefer `data-testid` attributes for stable selectors.
- Use ARIA roles and labels where appropriate.
- Avoid CSS class selectors (fragile, change with styling).
- Avoid complex XPath selectors.
- Add missing `data-testid` attributes to components as needed.

### Step 5 — Test Data
- Create deterministic test data using seed scripts or API-based setup.
- Each test suite should set up its own data and clean up after.
- Do not rely on data left by other tests.
- Use realistic but synthetic data.

### Step 6 — Run and Verify
- Run locally first: `npx playwright test`
- Review results, fix flaky tests.
- Verify screenshots/traces on failure are captured.
- Enable retries (max 2) for inherently flaky interactions.

### Step 7 — CI Integration
- Configure Playwright in CI pipeline.
- Start backend and frontend services before running E2E.
- Use headed mode in CI for debugging if needed.
- Store failure screenshots/traces as CI artifacts.

## Playwright Configuration

```typescript
// playwright.config.ts (template)
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 2,
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
    { name: 'Desktop Chrome', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: 'cd backend && uvicorn app.main:app --port 8000',
      port: 8000,
      reuseExistingServer: true,
    },
    {
      command: 'cd frontend && npm run dev',
      port: 5173,
      reuseExistingServer: true,
    },
  ],
});
```

## Journey Documentation Format

```
Journey: <name>
Actors: <user roles involved>
Preconditions: <required state>
Steps:
  1. <action> → <expected result>
  2. <action> → <expected result>
  ...
Assertions:
  - <what to verify>
Cleanup:
  - <data to remove>
```

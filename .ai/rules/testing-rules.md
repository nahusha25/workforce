# Testing Rules

## Testing Pyramid

```
                E2E (Playwright)
           ────────────────────────
          Integration Tests (API + DB)
       ─────────────────────────────────
      API / Service Tests (business logic)
   ────────────────────────────────────────
  Unit / Domain Tests (pure functions, validators)
─────────────────────────────────────────────────
Database Constraint Tests (migrations, constraints)
```

- **Database constraint tests**: Verify constraints, relationships, and migrations work correctly.
- **Unit tests**: Test pure business logic, validators, and utility functions in isolation.
- **Service tests**: Test service methods with mocked repositories.
- **API tests**: Test endpoints with a test database (integration).
- **E2E tests**: Test critical user journeys through the browser.

## When to Write Which Test

| Scenario | Test Type |
|----------|-----------|
| A Pydantic validator or utility function | Unit test |
| A service method with business rules | Service test |
| A database constraint or migration | Database test |
| An API endpoint's behavior | API/integration test |
| A complete user workflow (onboarding, attendance, etc.) | E2E test |
| A validation error displayed in the UI | E2E test |
| A permission boundary | API test + E2E test |

## Backend Testing (pytest)

### Test Organization
```
tests/
├── conftest.py          ← Shared fixtures (test DB, client, auth)
├── unit/
│   ├── test_validators.py
│   └── test_utils.py
├── integration/
│   ├── test_employee_service.py
│   └── test_attendance_service.py
├── api/
│   ├── test_employee_api.py
│   └── test_attendance_api.py
└── database/
    ├── test_migrations.py
    └── test_constraints.py
```

### Rules
- Use `pytest` as the test runner.
- Use `pytest-asyncio` for async tests.
- Use a separate test database — never test against production.
- Use fixtures for test data setup and teardown.
- Each test must be independent — no test-order dependencies.
- Name tests descriptively: `test_create_employee_with_valid_data_returns_201`.
- Test both success and failure paths.
- Test authorization boundaries (correct role passes, wrong role fails).
- Mock external services (SMS, file storage) in unit tests.

### Coverage
- Business logic services: aim for >90% coverage.
- API endpoints: test all response codes documented in the API plan.
- Database constraints: test that invalid data is rejected.

## Frontend Testing

### Test Organization
- Co-locate component tests with components: `EmployeeForm.test.tsx`
- Use React Testing Library for component tests.
- Use Vitest or Jest as the test runner.

### Rules
- Test user interactions, not implementation details.
- Test what the user sees and does (queries by role, label, or data-testid).
- Test form validation feedback.
- Test loading and error states.
- Do not test internal React state directly.

## E2E Testing (Playwright)

See also: `.ai/workflows/e2e-testing.md`

- Test critical user journeys defined in phase documentation.
- Use `data-testid` attributes for stable selectors.
- Create deterministic test data (seed scripts or API-based setup).
- Clean up test data after tests.
- Capture screenshots on failure.
- Configure retries (max 2) for flaky tests.

## Test Data

- Use factory functions or fixtures to create test data.
- Do not hardcode IDs or rely on database auto-increment order.
- Use realistic but synthetic data (not real employee data).
- Clean up test data after each test or test suite.

## Continuous Integration

- All tests must pass before merging.
- Run unit + service + API tests on every pull request.
- Run E2E tests on every pull request (or on merge to main).
- Fail the CI pipeline on test failures — do not allow skips without documented reasons.

# Swagger Testing Standard

## Access Points

| Endpoint | Purpose |
|----------|---------|
| `/api/docs` | Swagger UI — interactive API testing |
| `/api/redoc` | ReDoc — readable API documentation |
| `/api/openapi.json` | OpenAPI 3.0 JSON specification |

## Configuration

FastAPI automatically generates OpenAPI documentation. Ensure:
- All endpoints have docstrings describing their purpose.
- All request/response schemas have field descriptions.
- All error responses are documented in the endpoint decorator.
- Tags are used to group endpoints by module.

## Swagger Test Plan — Per-Phase Categories

Every API endpoint must be tested through Swagger for the following categories (where applicable):

| # | Category | Expected Behaviour |
|---|----------|--------------------|
| 1 | Successful request | Correct status code, response body, and side effects |
| 2 | Invalid request | 400 with error details |
| 3 | Required-field validation | 422 with field-level errors for missing required fields |
| 4 | Authentication failure | 401 when no token or expired token |
| 5 | Authorization failure | 403 when wrong role |
| 6 | Business-rule validation | 422 with business rule error code |
| 7 | Invalid state transition | 422 or 409 for disallowed state changes |
| 8 | Database constraint failure | 409 for unique violations, 422 for FK violations |
| 9 | Not-found behaviour | 404 when resource doesn't exist |
| 10 | Conflict behaviour | 409 for duplicates (e.g., duplicate check-in) |
| 11 | Malformed input | 400 or 422 for unparseable input |
| 12 | Boundary values | Test with zero, negative, maximum values |

## Test Execution Format

For each API in the phase's `swagger-test-plan.md`, document:

```
API: <METHOD> <endpoint>
Test: <test name>
Input: <request body or parameters>
Expected: <status code> — <expected response>
Actual: <filled during testing>
Pass/Fail: <result>
```

## Phase-Specific Test Plans

Detailed Swagger test plans are in each phase's documentation:
- `docs/01-employee-onboarding-login/swagger-test-plan.md`
- `docs/02-daily-attendance/swagger-test-plan.md`
- `docs/03-daily-work-material/swagger-test-plan.md`
- `docs/04-supervisor-verification/swagger-test-plan.md`
- `docs/05-director-dashboard-invoicing/swagger-test-plan.md`

# Testing Strategy

See also: `.ai/rules/testing-rules.md` and `.ai/checklists/testing-checklist.md`.

## Testing Pyramid

```
                  E2E (Playwright)
              ─────────────────────
            Integration Tests (API + DB)
         ──────────────────────────────
       API / Service Tests (business logic)
    ─────────────────────────────────────────
   Unit / Domain Tests (pure functions)
──────────────────────────────────────────────
Database Constraint Tests (migrations, rules)
```

## Per-Phase Testing Requirements

### Database Testing
- Migration applies cleanly (upgrade and downgrade)
- Primary key constraints enforced
- Foreign key constraints enforced
- Unique constraints enforced
- Not-null constraints enforced
- Check constraints enforced (status values, numeric ranges)
- Relationship integrity maintained

### Backend / Service Testing
- Service methods return correct results for valid input
- Business rules are enforced (e.g., site assignment check, pre-checkout submission)
- Edge cases handled (empty input, boundary values)
- External services mocked (SMS, file storage)

### API Testing
- Success responses have correct status codes and body structure
- Validation errors return 422 with field details
- Authentication failures return 401
- Authorization failures return 403
- Not-found returns 404
- Conflict/duplicate returns 409
- Pagination works correctly

### Swagger Testing
- All endpoints appear and are executable in Swagger UI
- Request/response schemas match documentation
- Manual test of each endpoint category per `swagger-testing-standard.md`

### Frontend Testing
- Components render correctly with valid props
- User interactions trigger expected behaviour
- Form validation errors display correctly
- Loading, error, and empty states render
- Mobile and desktop layouts verified

### E2E Testing
- Critical user journeys tested end-to-end (browser → API → DB)
- Happy path and realistic failure scenarios
- Permission boundaries verified
- Tests run in CI with screenshots on failure

## Critical E2E Journeys (per phase)

| Phase | Journey | Priority |
|-------|---------|----------|
| 1 | Employee registration → OTP login → session persistence | High |
| 2 | Check-in with GPS → geo-fence validation → check-out | High |
| 3 | Work entry → photo upload → material recording → submission | High |
| 4 | Supervisor views EOD summary → approves/rejects entries | High |
| 5 | Director views dashboard → generates invoice → exports PDF | High |
| Cross | Employee submits work → supervisor approves → director sees in dashboard | High |

## Test Data Strategy

- Seed scripts for creating test employees, sites, activities, materials
- Factory functions in test fixtures
- Deterministic data (known IDs, known values)
- Isolated per test suite (no cross-test dependencies)
- Cleaned up after test runs

## CI Integration

- Run unit + service + API tests on every PR
- Run E2E tests on every PR (or on merge to main)
- Block merge on test failures
- Store failure screenshots and Playwright traces as CI artifacts

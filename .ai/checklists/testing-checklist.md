# Testing Checklist

Use this checklist to verify testing coverage for a feature or phase.

## Database Tests
- [ ] Migration runs successfully (upgrade)
- [ ] Migration rolls back successfully (downgrade)
- [ ] Primary key constraints enforced
- [ ] Foreign key constraints enforced (invalid reference rejected)
- [ ] Unique constraints enforced (duplicate rejected)
- [ ] Not-null constraints enforced (null rejected)
- [ ] Check constraints enforced (invalid values rejected)
- [ ] Status values restricted to allowed set

## Unit Tests (Services / Business Logic)
- [ ] Happy path tested
- [ ] Business rule validation tested
- [ ] Edge cases tested
- [ ] Invalid input handling tested
- [ ] External dependencies mocked

## API Tests (Integration)
- [ ] Successful request → correct status code and response
- [ ] Invalid request → 422 with validation errors
- [ ] Missing required fields → 422
- [ ] Authentication failure → 401
- [ ] Authorization failure → 403
- [ ] Resource not found → 404
- [ ] Conflict (duplicate) → 409
- [ ] Business rule violation → appropriate error
- [ ] Pagination works correctly (where applicable)

## Swagger Tests
- [ ] All endpoints appear in Swagger UI
- [ ] Request schemas match documentation
- [ ] Response schemas match documentation
- [ ] Can execute each endpoint from Swagger
- [ ] Error responses are properly documented

## Frontend Tests
- [ ] Component renders correctly
- [ ] User interactions work (clicks, inputs, submissions)
- [ ] Form validation displays errors
- [ ] Loading state renders
- [ ] Error state renders
- [ ] Empty state renders

## E2E Tests
- [ ] Critical user journey — happy path
- [ ] Validation failure path
- [ ] Permission failure path
- [ ] Tests run in CI
- [ ] Failure screenshots captured

## Test Quality
- [ ] Tests are independent (no order dependency)
- [ ] Test data is created and cleaned up
- [ ] No hardcoded IDs or fragile selectors
- [ ] Tests are readable and maintainable
- [ ] Test names describe the scenario

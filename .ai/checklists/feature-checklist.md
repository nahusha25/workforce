# Feature Checklist

Use this checklist before considering a feature complete.

## Requirement
- [ ] Requirement is traceable to the source document
- [ ] Requirement ID is recorded in traceability matrix
- [ ] Acceptance criteria are defined and understood
- [ ] No scope creep — only implementing what the requirement says

## Database
- [ ] Database changes are designed (or explicitly not required)
- [ ] Alembic migration created and tested
- [ ] Constraints defined: PK, FK, unique, not-null, check
- [ ] Indexes added for known query patterns
- [ ] Database constraint tests written

## Backend / API
- [ ] Pydantic schemas defined for request/response
- [ ] Service layer implements business logic
- [ ] Repository layer handles data access
- [ ] Route handler is thin (validate → delegate → respond)
- [ ] Error handling is consistent
- [ ] Authentication dependency applied
- [ ] Authorization dependency applied (role check)
- [ ] API appears in Swagger/OpenAPI

## Swagger Verification
- [ ] Successful request tested in Swagger
- [ ] Invalid request returns proper validation error
- [ ] Auth failure returns 401
- [ ] Authorization failure returns 403
- [ ] Business rule violation returns appropriate error
- [ ] Not-found returns 404

## Frontend
- [ ] Component follows design system
- [ ] Loading state handled
- [ ] Error state handled
- [ ] Empty state handled
- [ ] Success feedback provided
- [ ] Form validation implemented
- [ ] Responsive: mobile layout correct
- [ ] Responsive: tablet layout correct
- [ ] Responsive: desktop layout correct

## Accessibility
- [ ] Keyboard navigable
- [ ] Visible focus indicators
- [ ] Form labels associated
- [ ] Touch targets ≥ 44×44px
- [ ] Color contrast ≥ 4.5:1
- [ ] Screen reader compatibility checked

## Security
- [ ] Input validation at API boundary
- [ ] Authorization enforced server-side
- [ ] No sensitive data in logs
- [ ] No sensitive data in error responses
- [ ] IDOR protection verified

## Testing
- [ ] Unit tests for business logic
- [ ] API integration tests
- [ ] Frontend component tests (where applicable)
- [ ] E2E test for critical journey (where applicable)

## Documentation
- [ ] Phase documentation updated if plan changed
- [ ] API documentation accurate in OpenAPI
- [ ] Code comments for non-obvious logic

## Git
- [ ] Changes committed atomically
- [ ] Commit message follows Conventional Commits
- [ ] No unrelated changes in commit

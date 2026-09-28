# Release Checklist

Use this checklist before deploying a phase or release.

## Code
- [ ] All planned features are complete
- [ ] All tests pass (unit, integration, API)
- [ ] All E2E tests pass
- [ ] Linter passes (no warnings treated as errors)
- [ ] Type checker passes (mypy / tsc)
- [ ] No critical or high-severity security findings open

## Database
- [ ] All migrations are sequential
- [ ] Migrations tested on clean database
- [ ] Migrations tested as upgrade from previous version
- [ ] No destructive migrations without approval
- [ ] Downgrade path tested

## Configuration
- [ ] `.env.example` updated with new variables
- [ ] No secrets in codebase
- [ ] Environment-specific configuration documented

## Documentation
- [ ] Phase documentation is current
- [ ] Requirement traceability updated
- [ ] API documentation (OpenAPI) is accurate
- [ ] CHANGELOG updated

## Build
- [ ] Backend builds successfully
- [ ] Frontend builds successfully
- [ ] Static assets optimized
- [ ] Health check endpoints respond

## Deployment
- [ ] Database backup taken before migration
- [ ] Deployment to staging verified
- [ ] Staging tests pass
- [ ] Rollback plan documented
- [ ] Production deployment executed
- [ ] Production health verified

# Release Workflow

## Trigger
A phase or set of features is ready for deployment.

## Pre-Release Checklist

### Code Quality
- [ ] All features for this release are complete.
- [ ] All tests pass (unit, integration, API, E2E).
- [ ] No critical or high-severity security findings are open.
- [ ] Code review is complete (where applicable).
- [ ] Linter and type-checker pass.

### Documentation
- [ ] Phase documentation is up to date.
- [ ] Requirement traceability is current.
- [ ] API documentation (OpenAPI/Swagger) is accurate.
- [ ] CHANGELOG is updated with release notes.

### Database
- [ ] All migrations are sequential and reversible.
- [ ] Migrations have been tested on a clean database.
- [ ] Migrations have been tested as an upgrade from the previous release.
- [ ] No destructive migrations without explicit approval.

### Configuration
- [ ] `.env.example` is updated with any new variables.
- [ ] No secrets in the codebase.
- [ ] Environment-specific configuration is documented.

### Deployment
- [ ] Build succeeds for backend and frontend.
- [ ] Static assets are optimized.
- [ ] Health check endpoints respond correctly.
- [ ] Database backup is taken before migration.

## Release Process

1. **Create a release branch** (if using GitFlow): `release/phase-<N>-<version>`
2. **Run the full test suite** on the release branch.
3. **Run E2E tests** on the release branch.
4. **Update version numbers** where applicable.
5. **Tag the release** using semantic versioning: `v<major>.<minor>.<patch>`
6. **Deploy to staging** and verify.
7. **Deploy to production** after staging verification.
8. **Verify production** deployment.
9. **Merge the release branch** back to main and develop.

## Rollback Plan

- Keep the previous deployment artifact available.
- Database migrations must have working `downgrade` steps.
- Document rollback steps in the release notes.

## Versioning

Use semantic versioning:
- **Major**: Breaking API changes, major database schema changes.
- **Minor**: New features, non-breaking API additions.
- **Patch**: Bug fixes, security patches, documentation updates.

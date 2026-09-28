# Definition of Done

See also: `.ai/checklists/definition-of-done.md` for the executable checklist.

## Task-Level

A task is done when:
- [ ] Requirement understood and traceable
- [ ] Acceptance criteria defined
- [ ] Implementation completed per architecture standards
- [ ] Unit/service tests passing
- [ ] No lint or type-check errors
- [ ] Committed with Conventional Commit message

## Feature-Level

A feature is done when all task-level items pass, plus:
- [ ] Requirement traceability updated
- [ ] Database changes designed and migrated
- [ ] Database constraints defined and tested
- [ ] API contracts defined and implemented
- [ ] UI/UX designed before frontend implementation
- [ ] Swagger verification completed
- [ ] Responsive behaviour verified (mobile, tablet, desktop)
- [ ] Accessibility considered and verified
- [ ] Permissions defined and enforced
- [ ] Validation completed (API + frontend)
- [ ] Integration tests completed
- [ ] Critical E2E journey tested (where applicable)
- [ ] Security review completed (where applicable)
- [ ] Error states handled
- [ ] Loading/empty states handled
- [ ] Logging/observability handled (no sensitive data)
- [ ] Documentation updated
- [ ] Dead-code/refactor review completed
- [ ] Git changes grouped atomically
- [ ] Reusable project pattern extracted (where applicable)

## Phase-Level

A phase is done when all features pass, plus:
- [ ] All phase requirements implemented
- [ ] All phase tasks complete
- [ ] Full E2E suite passes
- [ ] Security audit completed
- [ ] Phase documentation internally consistent
- [ ] No requirement traceability gaps
- [ ] Phase dependencies satisfied
- [ ] Integration with previous phases verified
- [ ] Release checklist passed

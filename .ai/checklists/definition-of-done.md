# Definition of Done

Every feature, task, and phase must satisfy the applicable items below before being considered complete.

## Task-Level Definition of Done

- [ ] Requirement understood and traceable to source document
- [ ] Acceptance criteria defined
- [ ] Implementation completed per architecture standards
- [ ] Unit/service tests written and passing
- [ ] Code reviewed (where applicable)
- [ ] No lint or type-check errors
- [ ] Committed with proper Conventional Commit message

## Feature-Level Definition of Done

All task-level items, plus:

- [ ] Requirement traceability updated
- [ ] Database changes designed and migrated
- [ ] Database constraints defined and tested
- [ ] API contracts defined and implemented
- [ ] Swagger verification completed
- [ ] UI/UX designed before implementation
- [ ] Responsive behavior verified (mobile, tablet, desktop)
- [ ] Accessibility considered and verified
- [ ] Permissions defined and enforced
- [ ] Validation completed (API + frontend)
- [ ] Integration tests completed
- [ ] Critical E2E journey tested (where applicable)
- [ ] Security review completed (where applicable)
- [ ] Error states handled (API errors, network errors)
- [ ] Loading/empty states handled
- [ ] Logging/observability handled (no sensitive data)
- [ ] Documentation updated
- [ ] Dead-code/refactor review completed
- [ ] Git changes grouped atomically
- [ ] Reusable project pattern extracted (where applicable)

## Phase-Level Definition of Done

All feature-level items for all features in the phase, plus:

- [ ] All phase requirements implemented
- [ ] All phase tasks complete
- [ ] Full E2E suite passes for the phase
- [ ] Security audit completed for the phase
- [ ] Phase documentation is internally consistent
- [ ] No requirement traceability gaps
- [ ] Phase dependencies satisfied
- [ ] Integration with previous phases verified
- [ ] Phase release checklist passed

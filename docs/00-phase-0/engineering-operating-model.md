# Engineering Operating Model

## Development Lifecycle

Every feature and phase follows this lifecycle:

```
Requirement
    ↓
Requirement Specification / PRD
    ↓
UI/UX Design Specification
    ↓
Implementation Plan
    ↓
Database
    ↓
Backend
    ↓
API
    ↓
Swagger Verification
    ↓
Frontend
    ↓
Integration
    ↓
Automated Testing
    ↓
Security Audit
    ↓
E2E Verification
    ↓
Cleanup / Refactor
    ↓
Documentation
    ↓
Atomic Git Commit
    ↓
Reusable Skill / Knowledge Extraction
```

## Engineering Gates

| Gate | Name | Description | Skip Policy |
|------|------|-------------|-------------|
| 1 | Requirement | Traceable to source document | Never skip |
| 2 | UX | Screens, flows, states, responsive, accessibility documented | Skip only for non-UI tasks (record reason) |
| 3 | Implementation | DB, backend/API, frontend built to architecture standards | Never skip |
| 4 | Verification | Unit/integration/API/Swagger/E2E tests pass | Never skip |
| 5 | Security | Security-sensitive features audited | Skip for non-security tasks (record reason) |
| 6 | Cleanup | Dead code reviewed without changing behaviour | Skip if codebase is clean (record reason) |
| 7 | Documentation | Relevant docs and project knowledge updated | Never skip |
| 8 | Git | Changes in atomic, meaningful commits | Never skip |

**A gate must never be silently skipped.** If not applicable, record:
```
Gate: Not applicable
Reason: <explicit reason>
```

## Engineering Practices

The eight mandatory practices:

1. **Full PRD / Feature Specification** — understand before building.
2. **Full UI/UX Design Brief** — design before coding frontend.
3. **Security Gap Audit** — audit before deploying security-sensitive features.
4. **Evidence-First Debugging** — diagnose before fixing.
5. **Playwright E2E Testing** — verify critical user journeys.
6. **Controlled Cleanup/Refactoring** — audit then execute, never during feature work.
7. **Atomic Conventional Git Commits** — one intent per commit.
8. **Reusable Project Skills/Knowledge** — extract patterns for future use.

## Change Control (for future phases)

When a new requirement appears after Phase 0:
```
New Requirement → Requirement Review → Impact Analysis → Phase Assignment → Documentation Update → Approval → Implementation
```

Do not silently insert new requirements into existing phases.

## References

| Practice | Workflow | Prompt | Checklist |
|----------|----------|--------|-----------|
| Feature Development | `.ai/workflows/feature-development.md` | `.ai/prompts/01-prd.md` | `.ai/checklists/feature-checklist.md` |
| UI/UX Design | — | `.ai/prompts/02-ui-ux.md` | `.ai/checklists/accessibility-checklist.md` |
| Security Audit | `.ai/workflows/security-audit.md` | `.ai/prompts/03-security-audit.md` | `.ai/checklists/security-checklist.md` |
| Debugging | `.ai/workflows/bug-fix.md` | `.ai/prompts/04-debug.md` | — |
| E2E Testing | `.ai/workflows/e2e-testing.md` | `.ai/prompts/05-e2e.md` | `.ai/checklists/testing-checklist.md` |
| Cleanup | `.ai/workflows/cleanup-refactoring.md` | `.ai/prompts/06-cleanup.md` | — |
| Git Commits | — | `.ai/prompts/07-git-commit.md` | — |
| Skills | `.ai/workflows/skill-extraction.md` | `.ai/prompts/08-skill.md` | — |

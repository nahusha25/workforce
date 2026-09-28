# Feature Development Workflow

## Trigger
A new feature or requirement task is being implemented.

## Pre-Conditions
- The requirement is documented in the phase's `requirements.md`.
- The requirement is traceable in `docs/00-phase-0/requirement-traceability.md`.
- The task is listed in the phase's `task-list.md`.

## Workflow

### Step 1 — Understand the Requirement
1. Read the task from the phase's `task-list.md`.
2. Read the corresponding requirement from the phase's `requirements.md`.
3. Trace it back to the source requirements document.
4. Confirm no scope creep — only implement what the requirement says.

### Step 2 — Review Architecture
1. Read relevant sections of `docs/00-phase-0/architecture.md`.
2. Read the phase's `implementation-plan.md`.
3. Review database plan, API plan, frontend plan, and UI/UX plan for the phase.
4. Identify dependencies on other tasks or phases.

### Step 3 — Design UI/UX (if user-facing)
1. Follow the UI/UX design brief in the phase's `ui-ux-plan.md`.
2. Ensure the design follows `docs/00-phase-0/ui-ux-architecture.md` design tokens and principles.
3. Document screen states: loading, error, empty, success, validation.
4. Document responsive behavior: mobile, tablet, desktop.

### Step 4 — Implement Database
1. Create Alembic migration for new/modified tables.
2. Apply constraints as defined in the phase's `database-plan.md`.
3. Run migration and verify.
4. Write database constraint tests.

### Step 5 — Implement Backend
1. Create/update SQLAlchemy models in the module's `models.py`.
2. Create/update Pydantic schemas in the module's `schemas.py`.
3. Implement business logic in the module's `service.py`.
4. Implement data access in the module's `repository.py`.
5. Create/update API routes in `api/v1/<module>.py`.
6. Write unit tests for service logic.
7. Write API integration tests.

### Step 6 — Verify via Swagger
1. Start the development server.
2. Open Swagger UI at `/api/docs`.
3. Execute test cases from the phase's `swagger-test-plan.md`.
4. Verify success cases, validation errors, auth failures, and business rule enforcement.

### Step 7 — Implement Frontend
1. Create/update React components following `ui-ux-plan.md`.
2. Connect to API endpoints using the API client.
3. Implement all required states (loading, error, empty, success).
4. Implement responsive behavior.
5. Implement accessibility requirements.
6. Write component tests.

### Step 8 — Integration Testing
1. Verify the full flow: frontend → API → database.
2. Test with realistic data.
3. Test error handling end-to-end.

### Step 9 — E2E Testing
1. Write Playwright tests for critical user journeys.
2. Run the E2E suite and fix failures.

### Step 10 — Security Review
1. Run through `.ai/checklists/security-checklist.md` for the feature.
2. If security-sensitive: follow `.ai/workflows/security-audit.md`.

### Step 11 — Cleanup
1. Review for dead code, unused imports, duplication.
2. Follow `.ai/workflows/cleanup-refactoring.md` if non-trivial cleanup is needed.

### Step 12 — Documentation
1. Update relevant phase documentation if implementation differs from plan.
2. Update requirement traceability if needed.

### Step 13 — Git Commit
1. Follow `.ai/rules/git-rules.md`.
2. Group changes by intent — atomic, meaningful commits.

### Step 14 — Skill Extraction
1. If a reusable pattern was discovered, follow `.ai/workflows/skill-extraction.md`.

## Post-Conditions
- All engineering gates pass (see `CLAUDE.md`).
- The task in `task-list.md` can be marked complete.

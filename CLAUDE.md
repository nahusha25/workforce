# i-Workforce Management — AI Engineering Instructions

> This file is the top-level instruction layer for AI-assisted engineering.
> It references the `.ai/` governance structure — do not duplicate rules here.

---

## 1. Before Editing Anything

1. **Understand the repository** — read the directory structure, existing code, and configuration.
2. **Identify the relevant requirement phase** — determine which phase (1–5) the work belongs to.
3. **Read the relevant requirement documentation** — open `docs/<phase>/requirements.md` and `docs/<phase>/task-list.md`.
4. **Read applicable architecture and engineering rules** — see `.ai/rules/`.
5. **Read relevant UI/UX and security rules** — see `docs/00-phase-0/ui-ux-architecture.md` and `docs/00-phase-0/security-architecture.md`.
6. **Produce an implementation plan** before making substantial changes.

---

## 2. Core Principles

- **Never invent product requirements.** Only implement what exists in `docs/<phase>/requirements.md`.
- **Follow the implementation order:** Database → Backend → API → Swagger → Frontend → Integration → Testing — unless a documented technical dependency requires another order.
- **Validate authorization and security boundaries** on every API and page.
- **Run appropriate tests** after changes.
- **Run E2E tests** for critical business journeys.
- **Perform cleanup only after behavior is verified.**
- **Keep commits atomic** — one logical intent per commit using Conventional Commits.
- **Preserve reusable project knowledge** — extract skills when patterns emerge.
- **Stop and ask for approval** where an explicit approval gate is defined.
- **Never silently skip a required engineering gate.**

---

## 3. Engineering Gates

Every feature/phase must pass these gates (see `.ai/checklists/definition-of-done.md`):

| Gate | Description |
|------|-------------|
| 1 — Requirement | Traceable to source document |
| 2 — UX | Screens, flows, states, responsive, accessibility documented |
| 3 — Implementation | DB, backend/API, frontend, integration planned and built to standards |
| 4 — Verification | Unit/integration/API/Swagger/E2E tests pass |
| 5 — Security | Security-sensitive features audited |
| 6 — Cleanup | Dead code reviewed without changing behavior |
| 7 — Documentation | Relevant docs and project knowledge updated |
| 8 — Git | Changes in atomic, meaningful commits |

If a gate is not applicable, record: `Gate: Not applicable — Reason: <reason>`.

---

## 4. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Alembic |
| Database | PostgreSQL |
| API | REST, JSON, OpenAPI, Swagger UI |
| Frontend | React, TypeScript |
| E2E Testing | Playwright |

---

## 5. Project Structure

```
.ai/                    → AI engineering governance (rules, workflows, prompts, checklists, skills)
docs/00-phase-0/        → Master architecture, standards, and strategies
docs/01-employee-onboarding-login/  → Phase 1 documentation
docs/02-daily-attendance/           → Phase 2 documentation
docs/03-daily-work-material/        → Phase 3 documentation
docs/04-supervisor-verification/    → Phase 4 documentation
docs/05-director-dashboard-invoicing/ → Phase 5 documentation
backend/                → Python/FastAPI application (future phases)
frontend/               → React/TypeScript application (future phases)
```

---

## 6. Requirement Phases

| Phase | Name | Depends On |
|-------|------|------------|
| 0 | Documentation & Governance | — |
| 1 | Employee Onboarding & Login | Phase 0 |
| 2 | Daily Attendance | Phase 1 |
| 3 | Daily Work & Material Update | Phase 2 |
| 4 | Supervisor Verification | Phase 3 |
| 5 | Director Dashboard & Invoicing | Phase 4 |

---

## 7. Key References

| Topic | Location |
|-------|----------|
| Architecture rules | `.ai/rules/architecture.md` |
| Coding standards | `.ai/rules/coding-standards.md` |
| Database rules | `.ai/rules/database-rules.md` |
| Backend rules | `.ai/rules/backend-rules.md` |
| Frontend rules | `.ai/rules/frontend-rules.md` |
| Security rules | `.ai/rules/security-rules.md` |
| Testing rules | `.ai/rules/testing-rules.md` |
| Accessibility rules | `.ai/rules/accessibility-rules.md` |
| Git rules | `.ai/rules/git-rules.md` |
| Feature workflow | `.ai/workflows/feature-development.md` |
| Bug-fix workflow | `.ai/workflows/bug-fix.md` |
| Security audit workflow | `.ai/workflows/security-audit.md` |
| E2E testing workflow | `.ai/workflows/e2e-testing.md` |
| Cleanup workflow | `.ai/workflows/cleanup-refactoring.md` |
| Master implementation plan | `docs/00-phase-0/master-implementation-plan.md` |
| Requirement traceability | `docs/00-phase-0/requirement-traceability.md` |
| UI/UX architecture | `docs/00-phase-0/ui-ux-architecture.md` |
| Security architecture | `docs/00-phase-0/security-architecture.md` |
| Definition of done | `docs/00-phase-0/definition-of-done.md` |

---

## 8. When Implementing a Feature

Follow `.ai/workflows/feature-development.md` and the engineering operating model in `docs/00-phase-0/engineering-operating-model.md`.

Summary:
1. Read the requirement and trace it to the source document.
2. Read the phase's `requirements.md`, `implementation-plan.md`, and `task-list.md`.
3. Design UI/UX before building frontend (see `.ai/prompts/02-ui-ux.md`).
4. Implement: Database → Backend → API → Swagger verification → Frontend → Integration.
5. Test: Unit → Service → API → Swagger → E2E.
6. Security audit where applicable (see `.ai/workflows/security-audit.md`).
7. Cleanup (see `.ai/workflows/cleanup-refactoring.md`).
8. Document.
9. Commit atomically (see `.ai/rules/git-rules.md`).
10. Extract reusable skills if applicable (see `.ai/workflows/skill-extraction.md`).

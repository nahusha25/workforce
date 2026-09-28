# Git Rules

## Commit Convention

Use **Conventional Commits** format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Allowed Types

| Type | Use For |
|------|---------|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `docs` | Documentation changes only |
| `test` | Adding or updating tests |
| `chore` | Build, tooling, dependency updates |
| `style` | Code formatting, whitespace, semicolons |
| `build` | Build system or CI/CD changes |
| `ci` | CI configuration changes |

## Scopes (project-specific)

| Scope | Domain |
|-------|--------|
| `employee` | Employee onboarding, registration, profile |
| `attendance` | Check-in, check-out, GPS, geo-fence |
| `daily-work` | Work activities, quantities, photos, materials |
| `verification` | Supervisor approval, rejection, correction |
| `dashboard` | Director dashboard, reports, invoicing |
| `admin` | Master data management |
| `auth` | Authentication, sessions, OTP |
| `db` | Database migrations, schema changes |
| `api` | API infrastructure, middleware |
| `ui` | Shared UI components, design system |
| `security` | Security fixes, audit remediation |
| `e2e` | End-to-end tests |
| `infra` | Infrastructure, deployment, configuration |

## Rules

1. **Review staged and unstaged changes** before committing — ensure you are committing what you intend.
2. **Group changes by intent** — one logical intent per commit.
3. **Keep one logical intent per commit** — do not combine a feature with an unrelated fix.
4. **Separate feature changes from refactors** — a `feat` commit must not include unrelated refactoring.
5. **Separate fixes from documentation** when practical.
6. **Never use vague messages** such as: `update`, `changes`, `fix stuff`, `final`, `wip`, `misc`.
7. **Run relevant validation** before creating a commit (tests, lint, type-check).
8. **Mention breaking changes explicitly** in the commit footer:
   ```
   feat(api)!: change attendance response format

   BREAKING CHANGE: The attendance list endpoint now returns paginated results.
   ```

## Examples

```
feat(employee): add employee registration API endpoint

feat(employee): add OTP-based login flow

test(employee): add registration and login E2E journey

fix(attendance): reject duplicate check-in for same date

refactor(attendance): extract geo-fence validation to service

docs(phase-0): update database architecture with material entity

chore(deps): upgrade FastAPI to 0.110.0

style(ui): apply consistent button sizing across attendance forms
```

## Branch Naming (when applicable)

```
feat/<phase>-<short-description>
fix/<phase>-<short-description>
refactor/<scope>-<short-description>
docs/<description>
```

Examples:
```
feat/phase1-employee-registration
fix/phase2-duplicate-checkin
refactor/attendance-service-extraction
docs/phase0-database-architecture
```

## Pre-Commit Checks

Before committing, verify:
- [ ] Code compiles / builds without errors
- [ ] Linter passes (Python: ruff/flake8, TypeScript: ESLint)
- [ ] Type checks pass (Python: mypy, TypeScript: tsc)
- [ ] Relevant unit tests pass
- [ ] No secrets or sensitive data in the commit
- [ ] Commit message follows Conventional Commits format

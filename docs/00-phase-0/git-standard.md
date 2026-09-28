# Git Standard

See: `.ai/rules/git-rules.md` for complete rules.

## Convention

Use **Conventional Commits**: `<type>(<scope>): <description>`

## Allowed Types

`feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `style`, `build`, `ci`

## Scopes

`employee`, `attendance`, `daily-work`, `verification`, `dashboard`, `admin`, `auth`, `db`, `api`, `ui`, `security`, `e2e`, `infra`

## Key Rules

1. One logical intent per commit.
2. No vague messages (`update`, `changes`, `fix stuff`, `final`, `wip`).
3. Separate features from refactors.
4. Run tests before committing.
5. Flag breaking changes with `!` and `BREAKING CHANGE:` footer.
6. No secrets in commits.

## Examples

```
feat(employee): add employee registration API endpoint
fix(attendance): reject duplicate check-in for same date
test(verification): add supervisor approval E2E journey
docs(phase-0): update database architecture
refactor(daily-work): extract photo upload service
```

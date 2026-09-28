# Development Rules

See also: `.ai/rules/coding-standards.md` for detailed standards.

## General

- Prefer simple, explicit code over clever abstractions.
- Avoid premature abstraction — extract when a pattern appears 3+ times.
- Avoid speculative features — only implement what's in the requirements.
- Keep functions focused — each function does one thing.
- Keep modules cohesive — single responsibility area.
- Preserve domain boundaries — no business logic leaking across modules.
- Make failure behaviour explicit — handle errors intentionally.
- Avoid hidden side effects.

## Backend (Python / FastAPI)

- Type annotate all Python functions.
- Validate all external input with Pydantic.
- Keep route handlers thin — validate, delegate, respond.
- Keep business logic in services/use cases.
- Keep database access in repositories.
- Use transactions intentionally for multi-step operations.
- Handle errors consistently with custom exception classes.
- Do not expose internal exceptions to API consumers.

## Frontend (React / TypeScript)

- Use TypeScript `strict` mode.
- Avoid `any` unless explicitly justified.
- Keep components focused — split at ~150 lines.
- Separate data-fetching from presentation.
- Reuse design system components.
- Handle all states: loading, error, empty, permission-denied.
- Do not duplicate business logic in the UI.

## Database

- All schema changes via Alembic migrations.
- Never manually alter production schema.
- Define constraints intentionally — PK, FK, unique, not-null, check.
- No speculative tables for features not in requirements.
- Indexes based on known access patterns, not speculation.
- Preserve referential integrity.
- Use `NUMERIC` for monetary amounts, never `FLOAT`.
- Use `TIMESTAMPTZ` for all timestamps.

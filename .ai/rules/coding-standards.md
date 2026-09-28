# Coding Standards

## General Principles

- Prefer simple, explicit code over clever abstractions.
- Avoid premature abstraction — extract only when a pattern appears three or more times.
- Avoid speculative features — do not implement functionality not in the requirements.
- Keep functions focused — each function does one thing.
- Keep modules cohesive — each module has a single responsibility area.
- Preserve domain boundaries — do not leak business logic across modules.
- Make failure behavior explicit — handle errors where they occur, propagate intentionally.
- Avoid hidden side effects — functions should do what their name says.

## Python / Backend Standards

### Type Annotations
- All Python functions must have type annotations for parameters and return values.
- Use `Optional[T]` or `T | None` (Python 3.10+) for nullable types.
- Use Pydantic models for all API request/response schemas.

### Naming
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Module files: `snake_case.py`
- Private functions/methods: prefix with `_`

### Code Organization
- Keep route handlers thin — they validate input and delegate to services.
- Business logic belongs in `services/` or `use_cases/`.
- Database access belongs in `repositories/`.
- Shared utilities belong in `core/` or `shared/`.
- No circular imports between modules.

### Error Handling
- Use custom exception classes for business errors.
- Handle errors consistently — use FastAPI exception handlers.
- Do not expose internal stack traces or implementation details in API responses.
- Log errors with structured context (request ID, user ID, operation).

### Validation
- Validate all external input at the API boundary using Pydantic.
- Apply database-level constraints for data integrity.
- Do not duplicate validation logic across layers unnecessarily.

### Transactions
- Use database transactions intentionally — wrap multi-step operations.
- Do not leave transactions open across HTTP requests.
- Handle transaction rollback on errors.

## TypeScript / Frontend Standards

### Type Safety
- Use TypeScript `strict` mode.
- Avoid `any` unless explicitly justified with a comment explaining why.
- Define interfaces/types for all API responses.
- Use discriminated unions for state management where applicable.

### Naming
- Components: `PascalCase` (files and component names)
- Functions and variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Types/Interfaces: `PascalCase`
- CSS classes: `kebab-case` or CSS modules

### Component Design
- Keep components focused — split when a component exceeds ~150 lines.
- Separate container (data-fetching) from presentational components where appropriate.
- Reuse established design system components.
- Handle all states: loading, error, empty, permission-denied.

### API Integration
- Use a centralized API client module.
- Define TypeScript types for all API request/response shapes.
- Handle network errors consistently.
- Do not hardcode API URLs — use environment configuration.

### State Management
- Use React's built-in state (useState, useReducer, useContext) unless complexity demands an external library.
- Avoid duplicating server state in client state — use data-fetching hooks.
- Keep form state local to the form component.

## Database Standards

- All schema changes go through Alembic migrations.
- Never manually alter the production schema outside the migration strategy.
- Define constraints intentionally — primary keys, foreign keys, unique, not-null, check constraints.
- Do not create speculative tables for features not in the requirements.
- Add indexes based on known access patterns, not speculation.
- Preserve referential integrity — every foreign key must reference a valid entity.
- Use `created_at` and `updated_at` timestamps on all business entities.
- Use soft deletes (`is_active` / `deleted_at`) where business rules require history preservation.

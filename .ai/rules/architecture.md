# Architecture Rules

## System Architecture

- **Modular monolith** — do not introduce microservices unless the requirements provide a genuine reason for service separation.
- **Clear domain boundaries** — each business module (employee, attendance, daily-work, verification, dashboard) is a cohesive unit.
- **No speculative abstractions** — do not create abstraction layers unless they solve a real, current problem.
- **No premature microservices** — the application is a single deployable unit.
- **No unnecessary infrastructure** — do not add message queues, event buses, or caching layers unless requirements demand them.

## Domain Boundaries

```
Modules:
  employee      → Employee onboarding, registration, profile
  attendance    → Check-in, check-out, GPS, geo-fence
  daily-work    → Work activities, quantities, photos, materials
  verification  → Supervisor approval, rejection, correction
  dashboard     → Director views, reports, invoicing
  admin         → Master data management (employees, clients, sites, activities, materials)
  auth          → Authentication (OTP), session management, RBAC
  core          → Shared infrastructure (config, logging, error handling, middleware)
```

## Layering

Every feature follows this vertical flow:

```
FastAPI Router (thin — validation + delegation only)
       ↓
Pydantic Schema (request/response validation)
       ↓
Service / Use Case (business logic lives here)
       ↓
Repository / Data Access (database queries)
       ↓
SQLAlchemy Model (ORM mapping)
       ↓
PostgreSQL (data persistence)
```

- Business logic **must not** be placed directly into route handlers.
- Shared infrastructure **must** remain separate from domain-specific logic.
- Cross-module communication happens through services, not direct repository access.

## Data Integrity

- Database constraints **enforce** business rules wherever appropriate.
- Do not rely entirely on frontend validation.
- Do not rely entirely on API validation when a rule should also be protected by the database.
- Foreign keys, unique constraints, check constraints, and not-null constraints are mandatory where the data model requires them.

## API Design

- All APIs use the `/api/v1` prefix.
- REST semantics with consistent HTTP method usage.
- Consistent JSON response structures.
- Consistent error handling.
- Swagger/OpenAPI documentation is automatically generated.

## Authorization

- Every API endpoint must declare its required permissions.
- Authorization is enforced at the API layer (middleware/dependencies), not in business logic.
- Data isolation must be enforced — employees see only their own data; supervisors see only their assigned workers; directors see aggregate data.

## Observability

- Structured logging without sensitive data exposure.
- Request correlation IDs where appropriate.
- Health check endpoints.
- No passwords, OTP values, tokens, or secrets in logs.

## Minimal Dependencies

- Before adding a dependency, confirm it is necessary and not already provided by existing dependencies.
- Document the reason for non-trivial dependency additions.
- Do not add libraries merely because they are popular.

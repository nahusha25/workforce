# Backend Rules — Python / FastAPI

## Project Structure

```
backend/
├── app/
│   ├── main.py                 ← FastAPI application entry point
│   ├── core/                   ← Shared infrastructure
│   │   ├── config.py           ← Configuration / settings
│   │   ├── database.py         ← Database session management
│   │   ├── security.py         ← Authentication, token handling
│   │   ├── dependencies.py     ← FastAPI dependency injection
│   │   ├── exceptions.py       ← Custom exception classes
│   │   ├── error_handlers.py   ← Global exception handlers
│   │   ├── logging.py          ← Structured logging setup
│   │   └── middleware.py       ← CORS, request ID, etc.
│   │
│   ├── api/                    ← API route definitions
│   │   ├── v1/
│   │   │   ├── router.py       ← Aggregated v1 router
│   │   │   ├── employee.py     ← Employee endpoints
│   │   │   ├── attendance.py   ← Attendance endpoints
│   │   │   ├── daily_work.py   ← Daily work endpoints
│   │   │   ├── verification.py ← Supervisor verification endpoints
│   │   │   ├── dashboard.py    ← Director dashboard endpoints
│   │   │   ├── admin.py        ← Admin/master data endpoints
│   │   │   └── auth.py         ← Authentication endpoints
│   │   └── deps.py             ← Route-level dependencies
│   │
│   ├── modules/                ← Business domain modules
│   │   ├── employee/
│   │   │   ├── models.py       ← SQLAlchemy models
│   │   │   ├── schemas.py      ← Pydantic request/response schemas
│   │   │   ├── service.py      ← Business logic
│   │   │   └── repository.py   ← Data access layer
│   │   ├── attendance/
│   │   ├── daily_work/
│   │   ├── verification/
│   │   ├── dashboard/
│   │   ├── admin/
│   │   └── auth/
│   │
│   └── shared/                 ← Shared utilities
│       ├── pagination.py       ← Pagination helpers
│       ├── audit.py            ← Audit trail helpers
│       ├── file_storage.py     ← Image/file storage abstraction
│       └── sms.py              ← OTP/SMS service abstraction
│
├── alembic/                    ← Database migrations
│   ├── env.py
│   └── versions/
│
├── tests/                      ← Test suite
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── api/
│
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
```

## Route Handler Rules

- Route handlers must be **thin** — maximum responsibilities:
  1. Extract and validate request data (via Pydantic)
  2. Extract authenticated user (via dependency injection)
  3. Call the appropriate service method
  4. Return the response
- **No business logic** in route handlers.
- **No direct database queries** in route handlers.
- **No direct SQL** in route handlers.

### Example Pattern

```python
@router.post("/", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(get_current_admin_user),
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    return await service.create_employee(data, created_by=current_user.id)
```

## Service Layer Rules

- Services contain **all business logic**.
- Services receive validated data (Pydantic models or primitive types).
- Services call repositories for data access.
- Services raise custom exceptions for business rule violations.
- Services do not import FastAPI-specific types (Request, Response, etc.).

## Repository Layer Rules

- Repositories handle **all database access**.
- Repositories return SQLAlchemy model instances or None.
- Repositories do not contain business logic.
- Repositories use SQLAlchemy queries (not raw SQL).
- One repository per domain module.

## Pydantic Schema Rules

- Separate schemas for: `Create`, `Update`, `Response`, `List`.
- Use `Field(...)` for required fields with validation.
- Use `Field(None)` or `Optional` for optional fields.
- Document fields with `description=` parameter.
- Keep schemas close to their module.

## Error Handling

- Define custom exceptions in `core/exceptions.py`:
  - `NotFoundError` — 404
  - `ValidationError` — 422
  - `AuthenticationError` — 401
  - `AuthorizationError` — 403
  - `ConflictError` — 409
  - `BusinessRuleError` — 422 with rule description
- Register global exception handlers in `core/error_handlers.py`.
- API error response format:
  ```json
  {
    "error": {
      "code": "EMPLOYEE_NOT_FOUND",
      "message": "Employee with ID 123 not found",
      "details": {}
    }
  }
  ```

## Dependency Injection

- Use FastAPI's `Depends()` for:
  - Database sessions
  - Authentication (current user extraction)
  - Authorization (role/permission checks)
  - Service instances
- Do not use global mutable state.

## Configuration

- Use Pydantic `BaseSettings` for configuration.
- Load from environment variables.
- Validate required configuration on startup.
- Provide `.env.example` with safe placeholder values.
- Never hardcode secrets.

# Backend Architecture

See also: `.ai/rules/backend-rules.md` for detailed coding standards.

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | Async Python web framework with auto OpenAPI |
| ORM | SQLAlchemy 2.0+ | Database access with async support |
| Validation | Pydantic v2 | Request/response schema validation |
| Migrations | Alembic | Database schema migrations |
| Database | PostgreSQL 15+ | Primary data store |
| Auth | python-jose / PyJWT | JWT token handling |
| Testing | pytest, pytest-asyncio | Test framework |
| Linting | ruff | Python linter and formatter |
| Type Checking | mypy | Static type analysis |

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    ← FastAPI app creation, middleware, startup
│   │
│   ├── core/                      ← Shared infrastructure
│   │   ├── __init__.py
│   │   ├── config.py              ← Settings from env vars (Pydantic BaseSettings)
│   │   ├── database.py            ← Engine, session factory, get_db dependency
│   │   ├── security.py            ← JWT, OTP hashing, token creation
│   │   ├── dependencies.py        ← get_current_user, require_role, get_db
│   │   ├── exceptions.py          ← NotFoundError, AuthError, BusinessRuleError, etc.
│   │   ├── error_handlers.py      ← Exception → JSON response mapping
│   │   ├── logging.py             ← Structured logging config
│   │   └── middleware.py          ← CORS, request-id, security headers
│   │
│   ├── api/                       ← Route definitions
│   │   ├── __init__.py
│   │   ├── deps.py                ← Route-level shared dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          ← Aggregated v1 router
│   │       ├── auth.py            ← POST /auth/otp/request, POST /auth/otp/verify, POST /auth/refresh
│   │       ├── employee.py        ← Employee CRUD endpoints
│   │       ├── attendance.py      ← Check-in, check-out, override
│   │       ├── daily_work.py      ← Work entries, photos, materials
│   │       ├── verification.py    ← Supervisor approve/reject/return
│   │       ├── dashboard.py       ← Metrics, reports
│   │       └── admin.py           ← Master data management
│   │
│   ├── modules/                   ← Business domain modules
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          ← User, OtpToken, RefreshToken SQLAlchemy models
│   │   │   ├── schemas.py         ← OtpRequest, OtpVerify, TokenResponse Pydantic models
│   │   │   ├── service.py         ← OTP generation, verification, token management
│   │   │   └── repository.py      ← User/token CRUD operations
│   │   │
│   │   ├── employee/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          ← Employee, Client, Site, EmployeeSiteAssignment
│   │   │   ├── schemas.py         ← EmployeeCreate, EmployeeResponse, etc.
│   │   │   ├── service.py         ← Registration, profile, assignment logic
│   │   │   └── repository.py      ← Employee data access
│   │   │
│   │   ├── attendance/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          ← AttendanceRecord
│   │   │   ├── schemas.py         ← CheckInRequest, CheckOutRequest, etc.
│   │   │   ├── service.py         ← Check-in, check-out, geo-fence, override
│   │   │   └── repository.py      ← Attendance data access
│   │   │
│   │   ├── daily_work/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          ← DailyWorkEntry, WorkPhoto, MaterialPurchase
│   │   │   ├── schemas.py         ← WorkEntryCreate, PhotoUpload, MaterialCreate, etc.
│   │   │   ├── service.py         ← Work entry, photo upload, material recording
│   │   │   └── repository.py      ← Work data access
│   │   │
│   │   ├── verification/
│   │   │   ├── __init__.py
│   │   │   ├── models.py          ← VerificationRecord
│   │   │   ├── schemas.py         ← VerificationAction, VerificationSummary, etc.
│   │   │   ├── service.py         ← EOD summary, approve/reject/return logic
│   │   │   └── repository.py      ← Verification data access
│   │   │
│   │   ├── dashboard/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py         ← DashboardMetrics, ReportFilters, etc.
│   │   │   ├── service.py         ← Metric aggregation, report generation
│   │   │   └── repository.py      ← Dashboard queries
│   │   │
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── models.py          ← WorkOrder, Activity, Material
│   │       ├── schemas.py         ← Master data CRUD schemas
│   │       ├── service.py         ← Master data management logic
│   │       └── repository.py      ← Master data access
│   │
│   └── shared/                    ← Cross-cutting utilities
│       ├── __init__.py
│       ├── pagination.py          ← PageParams, PagedResponse helpers
│       ├── audit.py               ← Audit log creation helper
│       ├── file_storage.py        ← Image upload/signed URL abstraction
│       ├── sms.py                 ← OTP delivery abstraction
│       └── geo.py                 ← Geo-fence distance calculation
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                  ← Migration files
│
├── tests/
│   ├── conftest.py                ← Test DB, client fixtures, auth helpers
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── database/
│
├── pyproject.toml                 ← Dependencies, tool config
├── alembic.ini
├── .env.example
└── README.md
```

## Layering Rules

```
Route Handler → Pydantic Schema → Service → Repository → SQLAlchemy → PostgreSQL
```

| Layer | Responsibility | Imports From |
|-------|---------------|--------------|
| Route (api/v1/*.py) | HTTP handling, auth injection, response formatting | schemas, services, dependencies |
| Schema (schemas.py) | Data validation, serialization | — (Pydantic only) |
| Service (service.py) | Business logic, orchestration | repositories, schemas, shared utilities |
| Repository (repository.py) | Database CRUD operations | models, SQLAlchemy session |
| Model (models.py) | ORM table definitions | SQLAlchemy base |

**Rules**:
- Route handlers must not contain business logic.
- Services must not import FastAPI types.
- Repositories must not contain business logic.
- Cross-module calls go through services, not repositories.

## Error Handling

Standard API error response:
```json
{
  "error": {
    "code": "EMPLOYEE_NOT_FOUND",
    "message": "Employee with the specified ID was not found.",
    "details": {}
  }
}
```

| HTTP Status | Exception | Use |
|-------------|-----------|-----|
| 400 | BadRequestError | Malformed request |
| 401 | AuthenticationError | Missing/invalid credentials |
| 403 | AuthorizationError | Insufficient permissions |
| 404 | NotFoundError | Resource not found |
| 409 | ConflictError | Duplicate/conflict |
| 422 | ValidationError | Pydantic validation failure |
| 422 | BusinessRuleError | Business rule violation |
| 500 | Internal | Unhandled server error (logged, not exposed) |

## Configuration

Use Pydantic `BaseSettings` loading from environment variables:

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    SMS_PROVIDER_URL: str
    SMS_API_KEY: str
    STORAGE_BUCKET: str
    CORS_ORIGINS: list[str]
    # ...

    model_config = SettingsConfigDict(env_file=".env")
```

`.env.example` must be provided with safe placeholder values.

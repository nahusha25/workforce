# System Architecture

## Architecture Style

**Modular Monolith** — a single deployable application with clear internal module boundaries.

The requirements describe a single application with well-defined pages and roles. There is no requirement for independent scaling, separate deployment, or service isolation. A modular monolith provides the simplest path to a working application while preserving the ability to extract services later if genuinely needed.

## System Context

```
┌─────────────────────────────────────────────────────────┐
│                    i-Workforce App                       │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │ React/TS │───▶│ FastAPI  │───▶│   PostgreSQL     │  │
│  │ Frontend │◀───│ Backend  │◀───│   Database       │  │
│  └──────────┘    └────┬─────┘    └──────────────────┘  │
│                       │                                  │
│                  ┌────┴─────┐                           │
│                  │ External │                           │
│                  │ Services │                           │
│                  └──────────┘                           │
│                  • SMS/OTP                              │
│                  • Cloud Storage (images)               │
│                  • Map/GPS Services                     │
└─────────────────────────────────────────────────────────┘

Users:
  Employee ──────┐
  Supervisor ────┤──▶ React Frontend ──▶ FastAPI Backend ──▶ PostgreSQL
  Director ──────┤
  Administrator ─┘
```

## Module Boundaries

```
backend/app/modules/
├── auth/           → OTP authentication, session management, RBAC
├── employee/       → Employee registration, profile, assignments
├── attendance/     → Check-in, check-out, GPS, geo-fence
├── daily_work/     → Work entries, quantities, photos, materials
├── verification/   → Supervisor EOD review, approve/reject/return
├── dashboard/      → Director metrics, reports, invoicing
└── admin/          → Master data CRUD (clients, sites, orders, activities, materials)
```

Each module contains: `models.py`, `schemas.py`, `service.py`, `repository.py`.

Cross-module communication happens through services, not direct database access.

## Layering

```
┌─────────────────────────────────────┐
│         FastAPI Routes (thin)       │  ← HTTP handling, validation, delegation
├─────────────────────────────────────┤
│         Pydantic Schemas            │  ← Request/response validation
├─────────────────────────────────────┤
│         Services / Use Cases        │  ← Business logic
├─────────────────────────────────────┤
│         Repositories                │  ← Data access
├─────────────────────────────────────┤
│         SQLAlchemy Models           │  ← ORM mapping
├─────────────────────────────────────┤
│         PostgreSQL                  │  ← Data persistence
└─────────────────────────────────────┘
```

## Shared Infrastructure

```
backend/app/core/
├── config.py           → Pydantic BaseSettings, environment variables
├── database.py         → SQLAlchemy engine, session factory
├── security.py         → JWT creation/verification, password-less auth
├── dependencies.py     → FastAPI DI: get_db, get_current_user, require_role
├── exceptions.py       → Custom exception hierarchy
├── error_handlers.py   → Global exception → HTTP response mapping
├── logging.py          → Structured logging configuration
└── middleware.py       → CORS, request ID, security headers
```

## API Design

- Base path: `/api/v1`
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`
- Health check: `/api/health`

## Frontend Architecture

```
frontend/src/
├── features/           → Page-level components per requirement phase
├── components/         → Reusable design system components
├── api/               → Centralized API client
├── hooks/             → Custom hooks (auth, geolocation, camera)
├── context/           → React contexts (auth)
├── styles/            → Design tokens, global styles
└── types/             → Shared TypeScript types
```

## External Service Abstractions

External services are accessed through abstraction interfaces to enable testing and future replacement:

| Service | Interface | Purpose |
|---------|-----------|---------|
| SMS/OTP | `shared/sms.py` | OTP delivery |
| File Storage | `shared/file_storage.py` | Image upload/retrieval |
| GPS/Map | Frontend Geolocation API | GPS capture, geo-fence calculation |

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Modular monolith over microservices | Requirements describe a single application; no need for service separation |
| JWT with refresh tokens | Supports "keep session active" requirement without daily OTP |
| Server-side timestamps | GPS date/time immutability requirement — clients cannot set timestamps |
| Signed URLs for images | Secure image storage without exposing storage credentials |
| Database constraints for business rules | Rules like approved-record protection and uniqueness enforced at DB level |
| Mobile-first CSS | Requirements specify mobile-first for low-cost Android phones |

> These are Technical Implementation Decisions — not product requirements.

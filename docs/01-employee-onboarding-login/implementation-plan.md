# Phase 1 — Implementation Plan

## Objective
Implement Employee Onboarding & Core Identity based exactly on the v3.0 Phase 0 Architecture.

## 1. Database Implementation
- **Migrations**: Execute exactly 8 Alembic migrations in strict FK-dependency order to create the 12 core tables: `users`, `otp_tokens`, `refresh_tokens`, `roles`, `employees`, `employee_roles`, `employee_rate_history`, `clients`, `projects`, `sites`, `employee_site_assignments`, and `audit_logs`.
- **Exclusions**: Do not migrate or implement later-phase tables (e.g., `notifications`, `attendance_records`).

## 2. Backend & API Implementation
- **Tech Stack**: FastAPI, SQLAlchemy 2.0+, Pydantic v2.
- **Authentication**: Implement SMS OTP exclusively. Support Request, Verify, Refresh, Logout.
- **RBAC**: Implement the core `roles` mapping and enforce authorization on all endpoints.
- **Master Data**: Implement strictly required CRUD endpoints for `clients`, `projects`, `sites`.
- **Employees**: Implement Employee Onboarding, role assignment, rate history tracking, and site assignments.

## 3. Frontend Implementation
- **Tech Stack**: React (Vite), adhering to Phase 0 UI/UX Architecture.
- **Views**: Mobile-first OTP Login flow, Admin Dashboard shell, Client/Project/Site Management, Employee Registration Form (including role and rate assignment).

## 4. Testing & Verification
- Comprehensive automated DB constraint tests, API tests, and E2E Playwright tests covering the full Onboarding & Login journey.

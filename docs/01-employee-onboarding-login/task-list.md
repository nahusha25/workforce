# Phase 1 — Task List

## 1. Database & Migrations
- **DB-001**: Migrate `users`, `otp_tokens`, `refresh_tokens`, `audit_logs`.
- **DB-002**: Migrate `roles`.
- **DB-003**: Migrate `employees`.
- **DB-004**: Migrate `employee_roles` and `employee_rate_history`.
- **DB-005**: Migrate `clients`.
- **DB-006**: Migrate `projects`.
- **DB-007**: Migrate `sites`.
- **DB-008**: Migrate `employee_site_assignments`.

## 2. Backend API
- **BE-001**: Implement Auth Service & OTP Endpoints (SMS OTP ONLY).
- **BE-002**: Implement RBAC logic & Dependencies (Roles enforcement).
- **BE-003**: Implement Master Data Endpoints (`clients`, `projects`, `sites`, `roles` read-only).
- **BE-004**: Implement Employee Service (Onboarding flow mapping roles, rates, assignments).

## 3. Frontend
- **FE-001**: Setup React App & Shell.
- **FE-002**: Implement Mobile OTP Login Form.
- **FE-003**: Implement Admin Dashboard (Clients, Projects, Sites).
- **FE-004**: Implement Employee Onboarding Form (with roles & rates).

## 4. Testing
- **TEST-001**: DB Constraints & Migration verification.
- **TEST-002**: API & E2E Validation of the full flow.

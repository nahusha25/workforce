# Phase 1 — Testing Plan

## Database Tests
- Test Alembic up/down migrations for the exact 8 migration steps.
- Test FK constraints: `otp_tokens` to `users`, `employees` to `users`, `employee_roles` to `employees`/`roles`, `employee_rate_history` to `employees`, `projects` to `clients`, `sites` to `projects`.
- Test check constraints: `rate_amount >= 0`.
- Verify `audit_logs` triggers correctly on insertions/updates.

## Unit Tests
- Service Logic: OTP generation, JWT creation/rotation.
- Employee Service: Registration maps user -> employee -> role -> site assignment -> rate history.
- Authorization: Ensure Role mapping evaluates correctly in dependency guards.

## API Integration Tests
- **Auth**: Test OTP Request, Verify, Refresh, Logout (positive and negative).
- **Employees**: Test Onboarding (with valid roles), update rate (creates history), get profile.
- **Hierarchy**: Test Client -> Project -> Site cascading creation and retrieval.
- **RBAC**: Test `401` and `403` responses for endpoints accessed by wrong roles.

## E2E Tests
- **E2E-1**: Mobile OTP Login Flow (Success and Failure).
- **E2E-2**: Admin Organization Setup (Create Client -> Create Project -> Create Site).
- **E2E-3**: Admin Employee Onboarding (Create Employee, Assign Role, Assign Rate, Assign Site).
- **E2E-4**: Session persistence across refresh.

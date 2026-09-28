# Phase 1 — Database Plan

## Scope
The Phase 1 database scope is strictly limited to Identity, Authentication, RBAC, Core Organization Hierarchy, and Employee Onboarding.

## Table Inventory & Dependencies
The following 12 tables are extracted from the v3.0 `canonical-erd.md`:

1. **`users`** (Auth Layer) - Base identity
2. **`otp_tokens`** (Auth Layer) - FK `user_id`
3. **`refresh_tokens`** (Auth Layer) - FK `user_id`
4. **`roles`** (Workforce Layer) - Base RBAC definitions
5. **`employees`** (Workforce Layer) - FK `user_id`, FK `supervisor_id`
6. **`employee_roles`** (Workforce Layer) - FK `employee_id`, FK `role_id`
7. **`employee_rate_history`** (Workforce Layer) - FK `employee_id`, FK `changed_by`
8. **`clients`** (Operations Layer) - Base organization
9. **`projects`** (Operations Layer) - FK `client_id`
10. **`sites`** (Operations Layer) - FK `project_id`, FK `supervisor_id`
11. **`employee_site_assignments`** (Operations Layer) - FK `employee_id`, FK `site_id`
12. **`audit_logs`** (System Layer) - Polymorphic, FK `user_id` (changed_by)

## Migration Strategy (Strict FK Dependency Order)
Migrations must be executed in this exact sequence to satisfy foreign key dependencies in PostgreSQL:

- **001_auth_system**: Creates `users`, `otp_tokens`, `refresh_tokens`, `audit_logs`
- **002_roles**: Creates `roles`
- **003_employees**: Creates `employees` (depends on `users`)
- **004_employee_details**: Creates `employee_roles`, `employee_rate_history` (depends on `employees`, `roles`)
- **005_clients**: Creates `clients`
- **006_projects**: Creates `projects` (depends on `clients`)
- **007_sites**: Creates `sites` (depends on `projects`, `employees` for supervisor)
- **008_assignments**: Creates `employee_site_assignments` (depends on `employees`, `sites`)

*Note: `notifications` is explicitly excluded from Phase 1 as it belongs to Phase 5.*

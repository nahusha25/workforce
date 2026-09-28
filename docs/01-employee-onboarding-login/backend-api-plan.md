# Phase 1 — Backend API Plan

## API Details

### Authentication (SMS OTP Only)
- **AUTH-001: POST /api/v1/auth/otp/request** (Request OTP via SMS)
- **AUTH-002: POST /api/v1/auth/otp/verify** (Verify OTP and issue JWT)
- **AUTH-003: POST /api/v1/auth/refresh** (Issue new JWT from refresh token)
- **AUTH-004: POST /api/v1/auth/logout** (Revoke session)

### Employees
- **EMP-001: POST /api/v1/employees** (Admin: Onboard new employee, assign roles, set initial rate, assign sites)
- **EMP-002: GET /api/v1/employees** (List employees - scoped by supervisor/admin)
- **EMP-003: GET /api/v1/employees/{id}** (Get employee details)
- **EMP-004: PUT /api/v1/employees/{id}** (Admin: Update employee profile, updates rate history if rate changed)
- **EMP-005: GET /api/v1/employees/me** (Self: Get own profile)
- **EMP-006: POST /api/v1/employees/{id}/site-assignments** (Admin: Assign site)

### Master Data (Admin Only)
- **ADM-001: POST /api/v1/admin/clients** (Create Client)
- **ADM-002: GET /api/v1/admin/clients** (List Clients)
- **ADM-003: POST /api/v1/admin/projects** (Create Project under Client)
- **ADM-004: GET /api/v1/admin/projects** (List Projects)
- **ADM-005: POST /api/v1/admin/sites** (Create Site under Project)
- **ADM-006: GET /api/v1/admin/sites** (List Sites)
- **ADM-007: GET /api/v1/admin/roles** (List Roles for Assignment)

*Note: Roles, employee roles, and rate history are not exposed via generic CRUD endpoints. They are handled via the onboarding and update logic within the Employee Service.*

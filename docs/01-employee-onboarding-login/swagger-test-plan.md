# Phase 1 — Swagger Test Plan

## Auth Endpoints
- **AUTH-001 (OTP Request)**: Test valid mobile (200), invalid mobile (422), rate limits (429).
- **AUTH-002 (OTP Verify)**: Test valid OTP (200), invalid/expired (401), brute force (429).
- **AUTH-003 (Refresh)**: Test valid refresh (200), expired/revoked (401).
- **AUTH-004 (Logout)**: Test valid session (204).

## Master Data Endpoints
- **ADM-001 (Create Client)**: Test valid payload (201), non-admin (403).
- **ADM-003 (Create Project)**: Test valid payload with `client_id` (201), invalid client (404).
- **ADM-005 (Create Site)**: Test valid payload with `project_id` and GPS (201), invalid project (404).
- **ADM-007 (List Roles)**: Test listing system roles (200).

## Employee Endpoints
- **EMP-001 (Onboard)**: Test valid payload (assigns role, sets rate history) (201). Test duplicate mobile (409).
- **EMP-004 (Update)**: Test rate update (creates new `employee_rate_history` record) (200).
- **EMP-005 (Me)**: Test fetching own profile (200).
- **EMP-006 (Assign Site)**: Test assigning a valid site (201).

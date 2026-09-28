# Phase 2 — Daily Attendance — Database Plan

> Derived from `canonical-erd.md` v3.0

## Core Tables (Attendance & Exceptions)

### `attendance_records`
- `id` (PK, UUID)
- `employee_id` (FK to employees)
- `site_id` (FK to sites)
- `date` (DATE)
- `session_number` (INT)
- `check_in_time` (TIMESTAMP)
- `check_in_location` (GEOGRAPHY)
- `check_in_distance_m` (NUMERIC)
- `check_out_time` (TIMESTAMP)
- `check_out_location` (GEOGRAPHY)
- `check_out_distance_m` (NUMERIC)
- `is_within_geofence` (BOOLEAN)
- `working_hours` (NUMERIC)
- `overtime_hours` (NUMERIC)
- `status` (VARCHAR)
- `override_by` (UUID)

> Note: `override_reason` is not stored as a direct column on `attendance_records`, but rather captured immutably within the `audit_logs` payload.

### `exception_flags`
- `id` (PK, UUID)
- `entity_type` (VARCHAR)
- `entity_id` (UUID)
- `flag_type` (VARCHAR)
- `is_resolved` (BOOLEAN)
- `resolved_by` (UUID)
- `created_at` (TIMESTAMP)

> Note: `exception_flags` replaces the JSONB array from v2.0 for normalized anomaly tracking. Location is stored as `GEOGRAPHY` (PostGIS) instead of split numeric coordinates.

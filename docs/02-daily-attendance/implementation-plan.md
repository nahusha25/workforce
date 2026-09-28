# Phase 2 — Daily Attendance — Implementation Plan

## Requirement Scope
Enable employees to check in and check out with one touch. Automatically capture employee identity, date/time, client/site, and GPS location. Validate against configured site geo-fence with supervisor override for exceptions.

## Requirement Traceability
| Req ID | Requirement | Feature |
|--------|-------------|---------|
| REQ-ATT-001 | One-touch Check-In | Check-In |
| REQ-ATT-002 | One-touch Check-Out | Check-Out |
| REQ-ATT-003 | Auto-capture employee identity | Auto-fill |
| REQ-ATT-004 | Auto-capture date/time | Auto-fill |
| REQ-ATT-005 | Auto-capture client/site | Auto-fill |
| REQ-ATT-006 | Auto-capture GPS location | GPS Capture |
| REQ-ATT-007 | Validate against geo-fence | Geo-fence Validation |
| REQ-ATT-008 | Supervisor override for exceptions | Supervisor Override |
| REQ-ATT-009 | Mandatory reason for exceptions | Exception Reason |
| REQ-BR-001 | Site assignment enforcement | Authorization |
| REQ-BR-002 | GPS/time immutability | Data Integrity |
| REQ-BR-003 | Pre-checkout work submission | Integration with Phase 3 |

---

## Database

### Tables
- **attendance_records** — full schema in [`database-plan.md`](./database-plan.md)

### Key Design Decisions
- Server-generated timestamps (not client) to enforce REQ-BR-002
- UNIQUE(employee_id, date, session_number) to prevent duplicate check-ins
- GPS stored as NUMERIC(10,7) for 7 decimal place precision (~1cm)
- exception_flags as JSONB array for flexible flag storage
- working_hours calculated on checkout: (check_out - check_in) in decimal hours

---

## Backend

### Module Structure
```
backend/app/modules/attendance/
├── __init__.py
├── models.py          — AttendanceRecord SQLAlchemy model
├── schemas.py         — CheckInRequest, CheckOutRequest, OverrideRequest, AttendanceResponse
├── service.py         — check_in, check_out, override_geofence, list_attendance, get_attendance
├── repository.py      — attendance CRUD operations
└── exceptions.py      — AttendanceError, GeoFenceViolation, DuplicateCheckIn

backend/app/shared/
└── geo.py             — haversine distance calculation
```

### Service Layer Logic
1. **check_in(employee_id, lat, lng)**:
   - Lookup active site assignment for employee
   - Verify no existing check-in today
   - Calculate haversine distance to site GPS
   - Compare against site.permitted_radius_metres
   - If within range → create record with is_within_geofence=true
   - If outside range → raise GeoFenceViolation (422)
   - Server generates check_in_time = datetime.now(UTC)

2. **check_out(employee_id, lat, lng)**:
   - Lookup today's active check-in (check_out_time IS NULL)
   - Server generates check_out_time = datetime.now(UTC)
   - Calculate working_hours = (checkout - checkin).total_seconds() / 3600
   - Calculate overtime_hours = max(0, working_hours - STANDARD_HOURS)
   - Check for unsubmitted daily_work_entries → add warning if exists

3. **override_geofence(supervisor_id, record_id, reason)**:
   - Verify supervisor is assigned to this employee
   - Set override_by = supervisor_id, override_reason = reason
   - Create audit_log entry

### Shared: Haversine Geo-fence Calculation
```python
# shared/geo.py
def haversine_distance(lat1, lng1, lat2, lng2) -> float:
    """Returns distance in metres between two GPS coordinates."""

def is_within_geofence(
    emp_lat, emp_lng, site_lat, site_lng, radius_metres
) -> tuple[bool, float]:
    """Returns (is_within, distance_metres)."""
```

---

## API Endpoints

| API ID | Method | Endpoint | Auth | Purpose |
|--------|--------|----------|------|---------|
| ATT-001 | POST | /api/v1/attendance/check-in | Employee | Record check-in with GPS |
| ATT-002 | POST | /api/v1/attendance/check-out | Employee | Record check-out, calculate hours |
| ATT-003 | GET | /api/v1/attendance | Employee/Supervisor/Director | List attendance records |
| ATT-004 | GET | /api/v1/attendance/{id} | Employee/Supervisor/Director | Get attendance detail |
| ATT-005 | POST | /api/v1/attendance/{id}/override | Supervisor | Override geo-fence violation |

Full API contracts in [`backend-api-plan.md`](./backend-api-plan.md).

---

## Frontend

### Pages
- **Attendance Page** (`/attendance`): Primary employee interaction page with large Check-In / Check-Out buttons

### Components
- **useGeolocation hook**: Browser Geolocation API wrapper with permission handling and error states
- **GPS Status Indicator**: Shows GPS acquisition status (acquiring/acquired/error/denied)
- **Check-In/Out Buttons**: Large, full-width buttons with clear state indication
- **Attendance History**: List of recent attendance records with status indicators
- **Supervisor Override Form**: Modal form for geo-fence override with reason text

### Page States
| State | Display |
|-------|---------|
| Not checked in | Large green "Check In" button, GPS indicator |
| Acquiring GPS | Loading spinner, "Getting your location..." |
| GPS denied | Error message, instructions to enable location |
| Geo-fence violation | Error with distance info, contact supervisor message |
| Checked in (working) | "Checked in at [time]", large red "Check Out" button |
| Work not submitted warning | Amber warning before checkout (REQ-BR-003) |
| Checked out | Summary: check-in time, check-out time, working hours |

### Auto-filled Context (Read-Only Display)
- Employee name and ID (from session)
- Today's date (from client clock, for display only — server timestamp for record)
- Assigned site name and address (from assignment API)

---

## Key Implementation Notes

1. **GPS captured client-side** via browser Geolocation API → sent in request body
2. **Timestamp is server-generated** — client timestamp is NOT trusted (REQ-BR-002)
3. **Geo-fence calculation on server** using haversine formula — not client-side
4. **Site assignment validated server-side** before allowing check-in (REQ-BR-001)
5. **Working hours** = simple time difference; overtime threshold is configurable (business rule pending)
6. **Pre-checkout check** warns about unsubmitted work entries (REQ-BR-003) — integrated with Phase 3

---

## Dependencies
| Dependency | Source | Required For |
|-----------|--------|-------------|
| Employee authentication | Phase 1 | All attendance operations |
| Employee master data | Phase 1 | Employee identity |
| Site master data (GPS, radius) | Phase 1 | Geo-fence validation |
| Employee site assignments | Phase 1 | Site enforcement |
| Supervisor relationships | Phase 1 | Override authorisation |

---

## Risks / Open Questions
| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Standard working hours threshold (8 hours?) | Overtime calculation | Business Rule Pending |
| 2 | Pre-checkout: warn or block? | Check-out UX flow | Business Rule Pending |
| 3 | Multiple check-ins per day (e.g., two sites)? | UNIQUE constraint design | Handled by session_number column |

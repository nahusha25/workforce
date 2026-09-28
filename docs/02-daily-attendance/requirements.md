# Phase 2 — Daily Attendance — Requirements

## Source Reference
- Page 2: "Daily Attendance"
- Business Rules: REQ-BR-001, REQ-BR-002, REQ-BR-005

## Requirement Scope
Enable employees to record daily attendance with one-touch check-in/out, automatic GPS capture, geo-fence validation, and supervisor override for exceptions.

## Actors
| Role | Actions |
|------|---------|
| Employee | Check-in, check-out |
| Supervisor | Override geo-fence exceptions |

## Functional Requirements
| ID | Requirement | Source |
|----|-------------|--------|
| REQ-ATT-001 | One-touch Check-In | Page 2 |
| REQ-ATT-002 | One-touch Check-Out | Page 2 |
| REQ-ATT-003 | Auto-capture employee identity | Page 2 |
| REQ-ATT-004 | Auto-capture date/time | Page 2 |
| REQ-ATT-005 | Auto-capture client/site | Page 2 |
| REQ-ATT-006 | Auto-capture GPS location | Page 2 |
| REQ-ATT-007 | Validate against site geo-fence | Page 2 |
| REQ-ATT-008 | Supervisor override for exceptions | Page 2 |
| REQ-ATT-009 | Mandatory reason for exceptions | Page 2 |

## Business Rules
1. Employees can check in only for **assigned client sites** (REQ-BR-001).
2. GPS date/time is server-generated and **cannot be edited** by employees (REQ-BR-002).
3. Multiple attendance sessions per employee per day are allowed (UNIQUE constraint on employee_id, date, session_number).
4. Check-out time must be after check-in time.
5. Geo-fence validation: calculate distance from employee GPS to site GPS; if > permitted_radius, flag as exception.
6. Out-of-location check-in requires supervisor override with mandatory reason.
7. Exceptions flagged: missing check-out, out-of-location (REQ-BR-005).

## State Transitions
```
(no record) → Check-In → draft
draft → Check-Out → draft (with check-out time)
draft → Submit Work (Phase 3) → submitted
submitted → Approve (Phase 4) → approved
submitted → Reject (Phase 4) → rejected
submitted → Return (Phase 4) → correction_required
correction_required → Re-submit → submitted
```

## Validation Rules
| Field | Rule |
|-------|------|
| employee_id | Auto from session, must be active |
| site_id | Auto from assignment, must be active |
| check_in_time | Server timestamp, NOT NULL |
| check_out_time | Server timestamp, must be > check_in_time |
| latitude/longitude | From browser Geolocation API, NOT NULL on check-in |
| override_reason | Required when override_by is set |
| exception_reason | Required for out-of-range attendance |

## Acceptance Criteria
- [ ] Employee can check in with one touch
- [ ] Employee can check out with one touch
- [ ] Employee, date/time, site auto-captured (non-editable)
- [ ] GPS coordinates captured and stored
- [ ] Geo-fence validation calculates distance correctly
- [ ] Out-of-range check-in blocked (without override)
- [ ] Supervisor can override with mandatory reason
- [ ] Duplicate check-in for same day rejected
- [ ] Check-out time validated > check-in time
- [ ] Exception flags generated for anomalies

## Dependencies
- Phase 1 complete (employees, sites, auth)
- Browser Geolocation API support

# Phase 1 — Employee Onboarding & Login — Requirements

## Source Reference
- Page 1 from source requirements: "Employee Onboarding & Login"
- Master data: Employee Master, Client & Site Master (prerequisites)
- Security: REQ-SEC-001, REQ-SEC-002

## Requirement Scope

Register employees and enable OTP-based login. Establish the authentication and session management foundation for the entire application.

## Actors

| Role | Actions |
|------|---------|
| Administrator | Creates/manages employee records, assigns sites, manages clients/sites |
| Employee | Registers, logs in via OTP, views own profile |

## Functional Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| REQ-EMP-001 | Register using name and mobile number | Page 1 |
| REQ-EMP-002 | OTP-based login without passwords | Page 1 |
| REQ-EMP-003 | Capture employee ID | Page 1 |
| REQ-EMP-004 | Capture trade/role | Page 1 |
| REQ-EMP-005 | Capture agreed rate | Page 1 |
| REQ-EMP-006 | Assign supervisor | Page 1 |
| REQ-EMP-007 | Assign client site | Page 1 |
| REQ-EMP-008 | Keep session active securely to avoid daily OTP entry | Page 1 |
| REQ-MD-001 | Employee Master: name, mobile, ID, trade/role, supervisor, daily/weekly/piece rate, active status | Master Data |
| REQ-MD-002 | Client & Site Master: client, site name/address, GPS coordinates, permitted radius, site supervisor | Master Data |
| REQ-SEC-001 | Role-based access for Employee, Supervisor, Director, Administrator | Security |
| REQ-SEC-002 | Secure OTP authentication and session management | Security |

## Business Rules

1. Mobile number must be unique per employee.
2. Employee ID must be unique.
3. OTP expires after 5 minutes.
4. OTP is single-use.
5. Failed OTP attempts are rate-limited (max 5 per 15 minutes).
6. Session remains active via refresh token (7-day expiry) to avoid daily OTP.
7. Employee must be assigned to at least one client site.
8. Supervisor must be an existing active employee.

## User Flows

### Employee Registration (by Admin)
```
Admin navigates to employee management
  ↓
Admin clicks "Add Employee"
  ↓
Admin enters: name, mobile, employee ID, trade/role, rate type, rate amount
  ↓
Admin selects supervisor from active employees
  ↓
Admin assigns client site(s)
  ↓
System creates user account and employee record
  ↓
Employee receives SMS notification with login instructions
```

### OTP Login
```
Employee opens app
  ↓
Employee enters mobile number
  ↓
System sends OTP via SMS
  ↓
Employee enters OTP
  ↓
System verifies OTP → issues access + refresh tokens
  ↓
Employee is logged in and sees their role-appropriate home screen
```

### Session Persistence
```
Employee returns to app (within 7 days)
  ↓
App uses refresh token to get new access token
  ↓
Employee is automatically logged in (no OTP needed)
```

## State Transitions

### Employee Status
```
Created → Active → Inactive
```

### OTP Status
```
Generated → Used
Generated → Expired (after 5 minutes)
```

## Validation Rules

| Field | Rule |
|-------|------|
| name | Required, 2–200 characters |
| mobile | Required, valid mobile format, unique |
| employee_id_number | Required, unique |
| trade_role | Required, from allowed values |
| rate_type | Required, one of: daily, weekly, piece |
| rate_amount | Required, numeric, ≥ 0 |
| supervisor_id | Optional FK, must reference active employee |
| site assignment | At least one active site required |

## Acceptance Criteria

- [ ] Admin can register a new employee with all required fields
- [ ] Employee mobile number uniqueness enforced
- [ ] Employee ID uniqueness enforced
- [ ] Employee can request OTP by mobile number
- [ ] OTP is delivered via SMS
- [ ] Employee can verify OTP and receive auth tokens
- [ ] Expired OTP is rejected
- [ ] Used OTP is rejected
- [ ] Excessive OTP attempts are rate-limited
- [ ] Session persists via refresh token without daily OTP
- [ ] Refresh token rotation works correctly
- [ ] Logout revokes session
- [ ] Admin can manage clients and sites
- [ ] Admin can assign employees to sites
- [ ] RBAC enforced on all endpoints

## Dependencies

- PostgreSQL database operational
- SMS/OTP service configured
- FastAPI application skeleton
- Authentication middleware

## Risks / Open Questions

1. **SMS Provider**: Which SMS provider for OTP delivery? (Technical decision — abstracted behind interface)
2. **Rate Configuration**: Are rate types (daily/weekly/piece) the complete list, or could there be more? (Proceeding with the three stated in requirements)

# Phase 2 — Daily Attendance — Security Plan

> Reference: [`docs/00-phase-0/security-architecture.md`](../00-phase-0/security-architecture.md) and [`.ai/rules/security-rules.md`](../../.ai/rules/security-rules.md)

---

## Threat Surface

| Area | Risk Level | Description |
|------|-----------|-------------|
| GPS data integrity | **HIGH** | Employees could spoof GPS coordinates to bypass geo-fence |
| Timestamp integrity | **HIGH** | Client-provided timestamps could be manipulated |
| Data isolation | **HIGH** | Employees should not see other employees' attendance data |
| Supervisor override | **MEDIUM** | Override mechanism could be abused to bypass geo-fence |
| Session security | **MEDIUM** | Attendance endpoints require valid, unexpired sessions |

---

## Security Controls

### Authentication & Session
- All attendance endpoints require valid JWT Bearer token
- Token validated on every request via FastAPI dependency
- Expired tokens return 401 Unauthorized
- Token contains user_id and role claims

### Authorization (RBAC)
| Endpoint | Employee | Supervisor | Director | Admin |
|----------|----------|-----------|----------|-------|
| Check-in (ATT-001) | ✅ Own only | ❌ | ❌ | ❌ |
| Check-out (ATT-002) | ✅ Own only | ❌ | ❌ | ❌ |
| List attendance (ATT-003) | ✅ Own only | ✅ Assigned | ✅ All | ✅ All |
| Get detail (ATT-004) | ✅ Own only | ✅ Assigned | ✅ All | ✅ All |
| Override (ATT-005) | ❌ | ✅ Assigned | ❌ | ❌ |

### GPS Data Integrity
- GPS coordinates **received from client** (browser Geolocation API) but **validated server-side**
- Geo-fence calculation (haversine) performed on server — not trusted from client
- GPS coordinates stored as received — no modification after creation (immutable)
- Client cannot claim to be within geo-fence; server determines `is_within_geofence`
- **Limitation**: Browser GPS can be spoofed on rooted/developer devices — this is a known limitation of web-based GPS. Mitigated by supervisor oversight.

### Timestamp Integrity (REQ-BR-002)
- `check_in_time` and `check_out_time` are **server-generated** using `datetime.now(UTC)`
- Client-provided timestamps are **never accepted or stored**
- No API parameter allows setting or modifying timestamps
- Once created, timestamps cannot be updated by any API endpoint
- Corrections require supervisor remarks and create audit trail entries

### Data Isolation
- Employee can only access attendance records where `employee_id` matches their own
- Supervisor can access records for employees where `employee.supervisor_id` = their employee_id OR `site.supervisor_id` = their employee_id
- Director/Admin can access all records
- Data isolation enforced **server-side** in the repository/service layer, not just UI filtering
- SQL queries automatically apply role-based WHERE clauses

### Supervisor Override Controls
- Override requires `supervisor` role — verified server-side
- Supervisor must be assigned to the employee (relationship validated)
- Override reason is **mandatory** — NOT NULL constraint (minimum 10 characters)
- Override action is **logged** to audit_logs with: who, when, reason, before/after values
- Override does not change GPS data — only records that an exception was authorised

### Input Validation
| Input | Validation | Server Enforcement |
|-------|-----------|-------------------|
| latitude | Numeric, -90 to 90 | Pydantic validator |
| longitude | Numeric, -180 to 180 | Pydantic validator |
| override_reason | String, 10-500 chars | Pydantic validator + CHECK |
| date filters | Valid date format | Pydantic date parsing |

### Audit Logging
All of the following actions create immutable `audit_logs` entries:
- Check-in recorded
- Check-out recorded
- Supervisor override applied

Audit log entries include:
- `entity_type`: 'attendance_record'
- `entity_id`: attendance record UUID
- `action`: 'create', 'check_out', 'override'
- `changed_by`: user UUID
- `old_values`: JSONB (null for creates)
- `new_values`: JSONB
- `created_at`: server timestamp

### GPS Data Privacy
- GPS coordinates stored in database, accessible only to authorised roles
- GPS not exposed to other employees
- GPS not included in API responses for list endpoints (only in detail view for authorised users)
- No GPS data in audit log notifications or error messages

---

## Security Verification Checklist

- [ ] All endpoints require authentication (401 on missing/expired token)
- [ ] Employee can only check in/out for themselves
- [ ] Employee cannot see other employees' attendance
- [ ] Supervisor can only override for assigned employees
- [ ] Override reason is mandatory and validated
- [ ] Timestamps are server-generated (test: send client timestamp in request, verify ignored)
- [ ] GPS coordinates are validated (range check) but not modifiable after creation
- [ ] Geo-fence is server-calculated (test: claim is_within_geofence=true in request, verify ignored)
- [ ] All actions create audit_log entries
- [ ] SQL injection not possible (parameterised queries via SQLAlchemy)
- [ ] No sensitive data in error responses (no GPS or token data in error messages)

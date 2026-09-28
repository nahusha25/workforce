# Phase 4 — Supervisor Verification — Security Plan

> Reference: [`docs/00-phase-0/security-architecture.md`](../00-phase-0/security-architecture.md)

---

## Threat Surface

| Area | Risk Level | Description |
|------|-----------|-------------|
| Approved Record Modification | **CRITICAL** | Tampering with approved financial/productivity data |
| Data Isolation Bypass | **HIGH** | Supervisor approving data for unassigned employees |
| Unauthorised Verification | **HIGH** | Employee approving their own work |
| Audit Trail Tampering | **HIGH** | Deleting or modifying audit logs to hide actions |

---

## Security Controls

### Authorization (RBAC)
| Endpoint | Employee | Supervisor | Director | Admin |
|----------|----------|-----------|----------|-------|
| GET summary (VER-001) | ❌ | ✅ Assigned | ✅ All | ✅ All |
| GET detail (VER-002) | ❌ | ✅ Assigned | ✅ All | ✅ All |
| POST approve (VER-003)| ❌ | ✅ Assigned | ❌ | ❌ |
| POST reject (VER-004) | ❌ | ✅ Assigned | ❌ | ❌ |
| POST return (VER-005) | ❌ | ✅ Assigned | ❌ | ❌ |

### Data Isolation
- Enforced server-side: Verification endpoints query `employee_site_assignments` and employee hierarchy to ensure the authenticated supervisor has authority over the target employee.
- Direct ID manipulation (IDOR) attempts will return 403 Forbidden.

### Approved Record Protection (REQ-BR-006)
- **Global Enforcement**: Any `PUT`, `POST` (update/add), or `DELETE` request targeting an `attendance_record` or `daily_work_entry` where `status == 'approved'` is rejected at the API/Service level with `409 Conflict`.
- Reopening requires a specific authorised workflow (creating a new verification record to revert status), preserving the audit trail.

### Remarks Integrity
- `remarks` field is sanitised before storage (strip HTML tags) to prevent XSS when rendered in the audit timeline or UI.
- Enforced as NOT NULL and minimum 10 characters at the API level for reject/return actions.

### Audit Log Immutability
- `audit_logs` table operations are append-only.
- The application backend does not implement any `DELETE` or `UPDATE` endpoints for audit logs.

---

## Security Verification Checklist

- [ ] Employee token cannot access verification endpoints (403)
- [ ] Supervisor cannot view/approve employees not assigned to them (403)
- [ ] Approved attendance cannot be updated via Phase 2 endpoints (409)
- [ ] Approved work cannot be updated via Phase 3 endpoints (409)
- [ ] Photos/Materials cannot be added to approved work entries (409)
- [ ] Reject/Return without remarks is blocked (422)
- [ ] Audit logs are created for every verification action
- [ ] XSS payloads in remarks are rendered safely (escaped)

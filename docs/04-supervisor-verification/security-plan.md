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
| POST approve (VER-003)| ❌ | ✅ Assigned | ✅ All | ✅ All |
| POST reject (VER-004) | ❌ | ✅ Assigned | ✅ All | ✅ All |
| POST return (submitted) (VER-005) | ❌ | ✅ Assigned | ✅ All | ✅ All |
| POST return (approved / reopen) (VER-005) | ❌ | ❌ (403 Forbidden) | ✅ All | ✅ All |

### Data Isolation & Anti-Enumeration (SEC-004-A)
- Enforced server-side: Verification endpoints query `employee_site_assignments` and supervisor hierarchy to verify the supervisor is assigned to the target employee.
- **SEC-004-A Unified 404 Enforcement**: To prevent employee ID and record enumeration attacks, requests targeting an employee or record outside the supervisor's authorized scope return HTTP `404 Not Found` with a generic message (`"Employee record not found"` or `"Target record not found"`), making valid unassigned IDs indistinguishable from completely non-existent IDs.

### Approved Record Protection (REQ-BR-006)
- **Global Enforcement**: Any `PUT`, `POST` (update/add), or `DELETE` request targeting an `attendance_record` or `daily_work_entry` where `status == 'approved'` is rejected at the API/Service level with `409 Conflict`.
- **Reopen Workflow**: Only users with `administrator` or `director` roles can reopen an approved record. Reopening creates a new `verification_record` with `action='correction_required'`, sets the entity status to `correction_required`, and logs an immutable audit trail entry. Supervisors attempting to reopen approved items are blocked with `403 Forbidden`.

### Remarks Integrity
- `remarks` field is sanitised and validated for minimum 10 characters at the API and database CHECK constraint level for reject and return actions.
- Rendered safely in React UI to prevent XSS injection.

### Concurrency & Idempotency Key Handling
- Verification endpoints require an `idempotency_key` (UUID/string) on all action endpoints (`approve`, `reject`, `return`).
- Guarded by database unique constraint `uq_verification_records_idempotency_key` and tested under high-concurrency race conditions (`test_concurrent_rapid_idempotency_key_verification`) ensuring exactly one action takes effect and concurrent retries return idempotent responses with `is_replay: true`.

### Audit Log Immutability
- `audit_logs` table operations are strictly append-only.
- The application backend does not implement any `DELETE` or `UPDATE` endpoints for audit logs.

---

## Security Verification Checklist

- [x] Employee token cannot access verification endpoints (403 Forbidden)
- [x] Supervisor accessing employees outside assigned scope returns generic 404 (SEC-004-A anti-enumeration)
- [x] Supervisor cannot approve/reject/return records outside assigned scope (SEC-004-A unified 404)
- [x] Approved attendance cannot be updated via Phase 2 endpoints (409 Conflict)
- [x] Approved work entries cannot be updated via Phase 3 endpoints (409 Conflict)
- [x] Photos/Materials cannot be added to approved work entries (409 Conflict)
- [x] Reject/Return without remarks or < 10 characters is blocked (422 Unprocessable Entity & DB CHECK)
- [x] Supervisor attempting to reopen approved record is blocked (403 Forbidden)
- [x] Admin/Director can successfully reopen approved record with remarks and audit trail
- [x] Audit logs are created for every verification action (chronological history in VER-002)
- [x] Concurrent rapid verification requests with same idempotency key succeed without race condition
- [x] XSS payloads in remarks are rendered safely (escaped by React JSX)

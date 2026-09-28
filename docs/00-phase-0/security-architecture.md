# Security Architecture

See also: `.ai/rules/security-rules.md` for enforcement rules.

## Authentication Flow — OTP-Based (per requirements)

```
Employee                   Frontend                   Backend                  SMS Provider
   │                          │                          │                          │
   │  Enter mobile number     │                          │                          │
   │─────────────────────────▶│  POST /auth/otp/request  │                          │
   │                          │─────────────────────────▶│  Generate OTP            │
   │                          │                          │  Hash & store in DB      │
   │                          │                          │  Send OTP ──────────────▶│
   │                          │◀─────────────────────────│  200 OK                  │
   │  Receive SMS             │                          │                          │◀──
   │◀─────────────────────────│                          │                          │
   │  Enter OTP               │                          │                          │
   │─────────────────────────▶│  POST /auth/otp/verify   │                          │
   │                          │─────────────────────────▶│  Verify OTP hash         │
   │                          │                          │  Mark OTP as used        │
   │                          │                          │  Create access + refresh │
   │                          │◀─────────────────────────│  Set refresh cookie      │
   │                          │  Store access token      │  Return access token     │
   │◀─────────────────────────│                          │                          │
```

## Token Strategy

| Token | Storage | Lifetime | Purpose |
|-------|---------|----------|---------|
| Access Token (JWT) | Memory / JS variable | 30 minutes | API authentication |
| Refresh Token | httpOnly secure cookie | 7 days | Session persistence (REQ-EMP-008) |
| OTP | Server-side (hashed) | 5 minutes | One-time login verification |

### Access Token Claims
```json
{
  "sub": "<user_id>",
  "role": "employee|supervisor|director|administrator",
  "employee_id": "<employee_id>",
  "exp": 1234567890,
  "iat": 1234567890
}
```

## RBAC Model

```
Administrator ──▶ All master data CRUD + user management
Director ────────▶ All data read + dashboard + reports + invoicing
Supervisor ──────▶ Assigned employees read + verification actions
Employee ────────▶ Own data read/write
```

### Permission Matrix

| Resource | Employee | Supervisor | Director | Administrator |
|----------|----------|------------|----------|---------------|
| Own attendance | RW | R (assigned) | R (all) | RW |
| Own work entries | RW | R (assigned) | R (all) | R |
| Verification actions | — | RW | R | — |
| Dashboard metrics | — | — | R | — |
| Reports/export | — | — | R | — |
| Invoice generation | — | — | RW | — |
| Employee master | R (own) | R (assigned) | R (all) | RW |
| Client/Site master | R | R | R | RW |
| Activity/Material master | R | R | R | RW |
| Work orders | R | R | R | RW |
| Audit logs | — | — | R | R |

## Data Isolation

| User Type | Data Scope |
|-----------|------------|
| Employee | Only their own records (attendance, work, materials) |
| Supervisor | Only records for employees assigned to them |
| Director | All records (read-only aggregate access) |
| Administrator | All master data (CRUD) |

Enforcement: Every data-access query includes a user-scoping filter applied in the repository layer.

## Security Headers

Applied via middleware on all responses:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; img-src 'self' blob: data: https:; connect-src 'self' https:
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(self), geolocation=(self), microphone=()
```

## Audit Trail (REQ-SEC-004, REQ-BR-006, REQ-VER-009)

All data modifications on business entities are recorded in `audit_logs`:
- Who made the change (user_id)
- What was changed (entity_type, entity_id, previous_values, new_values)
- When (created_at)
- Why (change_reason — mandatory for approved record modifications)

Audit log table is **append-only**: no UPDATE or DELETE operations.

## Image/File Security

- Uploaded images stored in cloud storage (S3-compatible).
- Access via signed URLs with expiry (1 hour default).
- File validation: allowed MIME types (image/jpeg, image/png, image/webp), max size (10MB).
- Client-side compression before upload.
- No direct public access to storage bucket.

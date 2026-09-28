# Security Rules

## Authentication

### OTP-Based Authentication (per requirements)
- Employees authenticate via mobile number + OTP — no passwords.
- OTP must be time-limited (5 minutes maximum).
- OTP must be single-use — consumed on successful verification.
- Failed OTP attempts must be rate-limited (max 5 attempts per 15 minutes).
- OTP values must never appear in logs, error responses, or API responses.
- OTP delivery via SMS service (abstracted behind an interface for testability).

### Session Management
- Issue JWT tokens (or equivalent) on successful OTP verification.
- Access tokens: short-lived (15–30 minutes).
- Refresh tokens: longer-lived (7 days per "keep session active" requirement).
- Store refresh tokens securely (httpOnly, secure, sameSite cookies).
- Never store tokens in localStorage (XSS risk).
- Implement token rotation on refresh.
- Invalidate sessions on explicit logout.

## Authorization — RBAC

### Roles (from requirements)
| Role | Access |
|------|--------|
| Employee | Own attendance, work, materials |
| Supervisor | Assigned employees' data, verification actions |
| Director | All data (read), dashboard, reports, invoicing |
| Administrator | Master data CRUD, user management |

### Enforcement Rules
- Authorization is enforced at the **API layer** (FastAPI dependencies).
- Every endpoint must declare its required role(s).
- Data-level isolation: employees cannot access other employees' records.
- Supervisors can only access records for employees assigned to them.
- No client-side-only authorization — the server is the source of truth.

## API Security

### Input Validation
- Validate all input using Pydantic schemas.
- Reject unexpected fields (use `model_config = ConfigDict(extra='forbid')`).
- Sanitize string inputs where they are rendered in HTML contexts.
- Validate file uploads: type, size, and content.

### Protection Against Common Attacks
- **SQL Injection**: Use SQLAlchemy ORM — never construct raw SQL strings.
- **XSS**: Sanitize user-provided text rendered in the frontend; React auto-escapes by default.
- **CSRF**: Use SameSite cookies + CSRF tokens for cookie-based auth.
- **Mass Assignment**: Pydantic schemas explicitly define allowed fields.
- **IDOR**: Always verify that the authenticated user has access to the requested resource.

### HTTP Security Headers
Apply via middleware:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: <appropriate policy>
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(self), geolocation=(self)
```

### CORS
- Restrict allowed origins to the frontend domain.
- Do not use `allow_origins=["*"]` in production.
- Allow credentials only from trusted origins.

### Rate Limiting
- Rate-limit OTP request endpoint (prevent SMS abuse).
- Rate-limit OTP verification endpoint (prevent brute force).
- Rate-limit login endpoint.
- Consider rate-limiting file upload endpoints.

## Data Protection

### Sensitive Data
- GPS coordinates are operational data — store securely, do not expose unnecessarily.
- Employee mobile numbers are PII — mask in logs.
- Employee rates are sensitive — restrict access by role.
- Bill images may contain financial information — store securely.

### Encryption
- All transmission over HTTPS/TLS (per requirements: "encrypted transmission").
- Database connections over TLS.
- Encrypt sensitive data at rest where required.

### Image/File Storage
- Store uploaded images in secure cloud storage (S3-compatible).
- Generate signed URLs for image access with expiry.
- Validate image MIME types and content (prevent upload of executables).
- Apply automatic compression (per requirements).
- Maximum file size limits.

## Audit Logging

Per requirements: "complete activity audit logs"
- Log all authentication events (login, logout, failed attempts).
- Log all data modifications (create, update, delete) on business entities.
- Log all approval/rejection actions.
- Log all supervisor overrides.
- Log access to sensitive data where required.
- Audit logs must be immutable (append-only).
- Audit log entries must include: who, what, when, where (IP), and why (for corrections).

## Secrets Management

- Never hardcode secrets in source code.
- Never commit secrets to version control.
- Never expose backend secrets to frontend bundles.
- Use environment variables for all secrets.
- Provide `.env.example` with safe placeholder values.
- Validate required secrets on application startup.

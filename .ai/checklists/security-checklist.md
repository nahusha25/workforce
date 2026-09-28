# Security Checklist

Use this checklist to verify security controls on a feature.

## Authentication
- [ ] Endpoint requires authentication (unless explicitly public)
- [ ] OTP generation is time-limited and single-use
- [ ] OTP values never appear in logs or responses
- [ ] Failed OTP attempts are rate-limited
- [ ] Session tokens are properly managed

## Authorization
- [ ] Endpoint declares required role(s)
- [ ] Data-level isolation enforced (users only see their own data)
- [ ] Supervisors only see assigned employees' data
- [ ] Admin-only endpoints restricted to Administrator role
- [ ] No privilege escalation paths

## Input Validation
- [ ] All input validated via Pydantic schemas
- [ ] Unexpected fields rejected (`extra='forbid'`)
- [ ] File uploads validated: type, size, content
- [ ] Numeric inputs have range constraints
- [ ] String inputs have length limits

## Injection Prevention
- [ ] No raw SQL — all queries through SQLAlchemy ORM
- [ ] No command injection — no shell execution of user input
- [ ] XSS prevention — user content sanitized before rendering

## Data Protection
- [ ] Sensitive data encrypted in transit (HTTPS)
- [ ] No secrets hardcoded in source code
- [ ] No secrets in frontend bundles
- [ ] GPS data stored securely
- [ ] Employee PII masked in logs
- [ ] Images stored in secure storage with signed URLs

## HTTP Security
- [ ] CORS restricted to frontend domain
- [ ] Security headers configured (X-Content-Type-Options, X-Frame-Options, etc.)
- [ ] Cookies: httpOnly, secure, sameSite flags set

## Error Handling
- [ ] No stack traces in API responses
- [ ] No internal implementation details in error messages
- [ ] Error responses use consistent format
- [ ] Sensitive data not leaked in error responses

## Audit
- [ ] Authentication events logged
- [ ] Data modifications logged
- [ ] Approval/rejection actions logged
- [ ] Supervisor overrides logged
- [ ] Audit log entries are immutable

# Phase 1 — Security Plan

## Authentication Security
- OTP hashed before storage (bcrypt or SHA-256 with salt)
- OTP expires after 5 minutes
- OTP single-use (marked as used after verification)
- Max 5 verification attempts per OTP
- Max 3 OTP requests per mobile per 15 minutes
- OTP values never in logs, responses, or error messages

## Session Security
- Access token: JWT, 30-minute expiry, signed with server secret
- Refresh token: opaque, hashed in DB, 7-day expiry, httpOnly secure cookie
- Token rotation on refresh (old token revoked, new issued)
- Logout revokes all refresh tokens for user
- SameSite=Strict on refresh token cookie

## Authorization
- RBAC enforced at API layer via FastAPI dependencies
- Admin-only: employee creation, client/site management
- Employee: own profile only
- Supervisor: assigned employees only

## Input Validation
- Pydantic schemas validate all input
- Extra fields rejected
- Mobile format validated
- Rate amount: non-negative
- String lengths bounded

## Data Protection
- Employee mobile numbers masked in logs (show last 4 digits only)
- No PII in error responses
- GPS coordinates (site master) stored securely

## Security Headers
- Applied via middleware on all responses (see security architecture)

## Audit
- All authentication events logged (OTP request, verify, login, logout, failed attempts)
- All employee CRUD operations logged
- All client/site changes logged

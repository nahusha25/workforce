# Prompt 03 — Security Audit

Use this prompt to perform a security audit on a feature or phase.

## Instructions

Follow `.ai/workflows/security-audit.md` strictly.

Audit the following categories (where applicable):

1. Authentication — OTP, session, token handling
2. Session handling — expiry, rotation, storage
3. Authorization — RBAC, data isolation
4. Hardcoded secrets — keys, tokens, passwords in code
5. Client-side secret exposure — API keys in frontend bundles
6. SQL injection — raw SQL, string concatenation
7. XSS — unsanitized user content rendering
8. CSRF — cookie-based auth without CSRF tokens
9. Unprotected API routes — missing auth/role checks
10. Missing input validation — unvalidated fields
11. Missing sanitization — user input in HTML/SQL/shell
12. Rate limiting — abuse-prone endpoints
13. CORS — overly permissive origin policies
14. Security headers — missing or misconfigured
15. Cookie flags — httpOnly, secure, sameSite
16. Dependency vulnerabilities — known CVEs in packages
17. File upload risks — type/size/content validation
18. Sensitive data exposure — PII in logs, responses
19. Log leakage — secrets, tokens, passwords in logs
20. Error response leakage — stack traces, internal details
21. IDOR — accessing other users' resources
22. Privilege escalation — role boundary bypass
23. Mass assignment — accepting unexpected fields

## Output Format

For each finding:
```
Finding ID: SEC-<NNN>
Severity: Critical | High | Medium | Low
Category: <category name>
File: <path>
Line / Location: <line or description>
Description: <what was found>
Why It Matters: <impact>
How It Could Be Exploited: <attack scenario>
Recommended Fix: <remediation>
Verification Method: <how to confirm fix>
```

For clean categories:
```
Category: <name>
Status: Reviewed — no finding identified.
```

**DO NOT make code changes during the audit. Report only.**

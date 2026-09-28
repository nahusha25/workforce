# Security Audit Standard

See: `.ai/workflows/security-audit.md` for the complete workflow.
See: `.ai/checklists/security-checklist.md` for the per-feature checklist.

## Audit Workflow

```
AUDIT → REPORT FINDINGS → WAIT FOR APPROVAL → REMEDIATION → TEST → RE-AUDIT
```

**Do not automatically modify code during the audit phase.**

## Audit Categories

1. Authentication
2. Session handling
3. Authorization / RBAC
4. Tenant/data isolation
5. Hardcoded secrets
6. Client-side secret exposure
7. SQL injection
8. XSS
9. CSRF
10. Unprotected API routes
11. Missing input validation
12. Rate limiting / brute-force protection
13. CORS
14. Security headers
15. Cookie flags
16. Dependency vulnerabilities
17. File upload risks
18. Sensitive data exposure
19. Log leakage
20. Error response leakage
21. IDOR
22. Privilege escalation
23. Mass assignment

## Finding Format

```
Finding ID: SEC-<NNN>
Severity: Critical | High | Medium | Low
Category: <from list above>
File: <file path>
Line / Location: <specific location>
Description: <what was found>
Why It Matters: <impact if exploited>
How It Could Be Exploited: <attack scenario>
Recommended Fix: <specific remediation>
Verification Method: <how to confirm the fix>
```

## Severity Definitions

| Severity | Definition | Response Time |
|----------|------------|---------------|
| Critical | Immediate exploitation; data breach, auth bypass, RCE | Immediate |
| High | Significant weakness; privilege escalation, data exposure | Within 24 hours |
| Medium | Defense-in-depth; missing headers, weak validation | Within sprint |
| Low | Best-practice deviation; informational | Backlog |

## Clean Category Statement

If a category reveals no issues:
```
Category: <name>
Status: Reviewed — no finding identified.
```

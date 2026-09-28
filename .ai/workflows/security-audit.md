# Security Audit Workflow

## Trigger
- A new feature with security implications is completed.
- A periodic security review is scheduled.
- A security concern is raised.

## Principle
> Audit first, then remediate. Never auto-fix during audit.

## Workflow

### Phase 1 — Audit
Inspect the following categories (where applicable):

| # | Category | Check |
|---|----------|-------|
| 1 | Authentication | OTP implementation, session handling, token management |
| 2 | Authorization | RBAC enforcement, data isolation, privilege boundaries |
| 3 | Input Validation | Pydantic schemas, missing validation, unexpected fields |
| 4 | SQL Injection | Raw SQL usage, parameterized queries |
| 5 | XSS | User content rendering, sanitization |
| 6 | CSRF | Cookie settings, token usage |
| 7 | API Security | Unprotected routes, missing auth, rate limiting |
| 8 | Secrets | Hardcoded secrets, env exposure, client-side leakage |
| 9 | File Uploads | Type validation, size limits, storage security |
| 10 | Data Exposure | Sensitive data in logs, responses, error messages |
| 11 | CORS | Origin restrictions, credential handling |
| 12 | HTTP Headers | Security headers presence and configuration |
| 13 | Dependencies | Known vulnerabilities in packages |
| 14 | IDOR | Object-level authorization, resource ownership |
| 15 | Mass Assignment | Extra field acceptance, schema strictness |

### Phase 2 — Report Findings
For each finding, document:

```
Finding ID: SEC-<NNN>
Severity: Critical | High | Medium | Low
Category: <from table above>
File: <file path>
Line / Location: <specific location>
Description: <what was found>
Why It Matters: <impact if exploited>
How It Could Be Exploited: <attack scenario>
Recommended Fix: <specific remediation>
Verification Method: <how to confirm the fix>
```

If a category is clean, explicitly state:
```
Category: <name>
Status: Reviewed — no finding identified.
```

### Phase 3 — Wait for Approval
- Present the full audit report.
- **Do not make any code changes.**
- Wait for explicit approval to proceed with remediation.

### Phase 4 — Remediation
- Fix approved findings, highest severity first.
- One fix per commit where practical.
- Reference the finding ID in commit messages.

### Phase 5 — Test
- Verify each fix works as intended.
- Run existing tests to confirm no regression.
- Add tests for the security fix where appropriate.

### Phase 6 — Re-Audit
- Re-inspect fixed categories to confirm remediation.
- Update the audit report with resolution status.

## Severity Definitions

| Severity | Definition |
|----------|------------|
| **Critical** | Immediate exploitation possible; data breach, auth bypass, or remote code execution |
| **High** | Significant security weakness; privilege escalation, data exposure, or injection vulnerability |
| **Medium** | Defense-in-depth concern; missing headers, weak validation, or configuration issue |
| **Low** | Minor improvement; informational, best-practice deviation |

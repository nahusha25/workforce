# Debugging Standard

See also: `.ai/workflows/bug-fix.md` and `.ai/prompts/04-debug.md`.

## Principle

> Evidence-first debugging. Diagnose before fixing.

## Protocol

### Step 1 — Restate the Problem
Clearly describe:
- Observed behaviour vs. expected behaviour
- Which feature/requirement is affected
- Environment (browser, device, API endpoint, user role)
- Steps to reproduce (if known)

### Step 2 — List Root Causes (3–5, ranked)
```
1. [Most likely] — <description>
2. [Likely] — <description>
3. [Possible] — <description>
4. [Less likely] — <description>
5. [Unlikely] — <description>
```

### Step 3 — Define Verification Steps
For each potential cause, define the **smallest verification step**:
- **Log check** — examine application or server logs
- **One-line check** — inspect a specific variable, config, or state
- **Request inspection** — check API request/response in dev tools or Swagger
- **Database check** — query the database to verify data state
- **Reproduction step** — specific user actions to reproduce
- **Targeted test** — minimal test case proving or disproving the cause

### Step 4 — Gather Evidence
Execute verification steps in order of probability. **Stop and wait for evidence** when user-provided verification is required.

### Step 5 — Fix (only after root cause confirmed)
1. Make the **minimal fix** — change only what is necessary.
2. Explain **why the fix works** — reference the root cause.
3. Define **exact verification tests**.
4. Write or update tests to prevent regression.

## Rules

| ✅ Do | ❌ Do Not |
|-------|-----------|
| Gather evidence before changing code | Shotgun multiple changes hoping one works |
| Fix one root cause at a time | Refactor unrelated code during a bug fix |
| Write a regression test | Change multiple layers without evidence |
| Explain why the fix works | Fix unreported problems |
| Confirm with the user if behaviour changes | Replace diagnosis with guesswork |

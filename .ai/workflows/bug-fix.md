# Bug Fix Workflow — Evidence-First Debugging

## Trigger
A bug is reported or unexpected behavior is observed.

## Principle
> Diagnose before fixing. Evidence before code changes.

## Workflow

### Step 1 — Restate the Problem
- Clearly describe the observed behavior vs. expected behavior.
- Identify which requirement or feature is affected.
- Note the environment (browser, device, API endpoint, user role).

### Step 2 — List Root Causes
List the **3–5 most likely root causes**, ranked by probability:
```
1. [Most likely] — <description>
2. [Likely] — <description>
3. [Possible] — <description>
4. [Less likely] — <description>
5. [Unlikely] — <description>
```

### Step 3 — Define Verification Steps
For each potential cause, define the **smallest verification step**:
- Log check — examine application or server logs
- One-line check — inspect a specific variable, config, or state
- Request inspection — check the API request/response in browser dev tools or Swagger
- Database check — query the database directly to verify data state
- Reproduction step — specific user actions that reproduce the bug
- Targeted test — a minimal test case that proves or disproves the cause

### Step 4 — Gather Evidence
- Execute verification steps.
- **Stop and wait** for evidence when user-provided verification is required.
- Do not guess — gather data.

### Step 5 — Fix (only after root cause confirmed)
1. Make the **minimal fix** — change only what is necessary.
2. Explain **why the fix works** — reference the root cause.
3. Define **exact verification tests** — how to confirm the fix works.
4. Write or update tests to prevent regression.

## Rules

- ❌ Do not shotgun changes — changing multiple things hoping one works.
- ❌ Do not refactor unrelated code during a bug fix.
- ❌ Do not change multiple layers without evidence pointing to each.
- ❌ Do not fix problems the user did not report.
- ❌ Do not replace diagnosis with guesswork.
- ✅ One root cause → one fix → one verification.
- ✅ If the fix requires changing behavior, confirm with the user first.
- ✅ If the bug reveals a missing test, add the test.

## Commit
```
fix(<scope>): <description of what was fixed>

Root cause: <brief explanation>
Verification: <how the fix was verified>
```

# Prompt 04 — Debug

Use this prompt when investigating a bug or unexpected behavior.

## Instructions

Follow `.ai/workflows/bug-fix.md` strictly. Evidence first, fix second.

## Steps

### 1. Restate the Problem
> Describe the observed behavior vs. expected behavior clearly.
> Identify: which feature, which user role, which environment, which endpoint/screen.

### 2. List Root Causes (3–5, ranked by probability)
```
1. [Most likely] —
2. [Likely] —
3. [Possible] —
4. [Less likely] —
5. [Unlikely] —
```

### 3. Verification Steps
For each cause, define the smallest verification:
- Log check
- One-line code check
- Request/response inspection
- Database query
- Reproduction step
- Targeted test

### 4. Gather Evidence
Execute verification steps. Stop and wait if user input is needed.

### 5. Fix (only after root cause is confirmed)
- Minimal change addressing the root cause.
- Explain why the fix works.
- Define verification tests.
- Add regression test.

## Rules
- ❌ No shotgun changes
- ❌ No unrelated refactoring
- ❌ No multi-layer changes without evidence
- ❌ No fixing unreported problems
- ✅ One root cause → one fix → one verification

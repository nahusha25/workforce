# Refactoring Standard

See also: `.ai/workflows/cleanup-refactoring.md` and `.ai/prompts/06-cleanup.md`.

## Principle

> Cleanup occurs only after behaviour is verified. Never during active feature development.

## Phase 1 — Audit (report only)

Scan for evidence of:
- Unused files, components, hooks, imports, variables, functions, exports
- Unused dependencies, environment variables, routes, API endpoints
- Commented-out code
- Duplicated logic
- Oversized modules (>300 lines)
- Logic in wrong layers (business logic in routes, etc.)

Assign confidence: **High** (safe to remove), **Medium** (verify first), **Low** (do not remove).

Present audit before executing.

## Phase 2 — Execute (after approval)

1. Apply approved changes only.
2. Run all tests — behaviour must remain identical.
3. Run E2E for affected features.
4. Verify in browser.

## Rules

- Behaviour stays identical.
- No new dependencies unless justified.
- No public API renaming without approval.
- No feature work mixed with cleanup.
- No low-confidence deletions.
- Cleanup commits are separate from feature commits.

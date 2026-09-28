# Prompt 06 — Cleanup / Refactoring

Use this prompt to perform controlled code cleanup.

## Instructions

Follow `.ai/workflows/cleanup-refactoring.md` strictly.

### Phase 1 — Audit (report only, no changes)

Scan for:
- Unused files, components, hooks, imports, variables, functions, exports
- Unused dependencies, environment variables, routes, API endpoints
- Commented-out code
- Duplicated logic
- Oversized modules (>300 lines)
- Logic in wrong layers

For each finding, report:
```
Finding: <description>
Location: <file:line>
Category: <type>
Confidence: High | Medium | Low
Evidence: <why unused/redundant>
Action: Delete | Extract | Split | Move
```

**Present the audit. Do not make changes yet.**

### Phase 2 — Execute (after approval)

1. Apply approved changes only.
2. Run all tests.
3. Run E2E for affected features.
4. Verify behavior is identical.
5. Commit as: `refactor(<scope>): <description>`

### Rules
- ✅ Behavior stays identical
- ❌ No new dependencies
- ❌ No public API changes
- ❌ No feature work mixed in
- ❌ No low-confidence deletions

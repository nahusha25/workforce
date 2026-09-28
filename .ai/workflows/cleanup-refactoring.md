# Cleanup & Refactoring Workflow

## Trigger
- A feature or phase implementation is complete and verified.
- Code quality concerns are identified.
- Technical debt review is scheduled.

## Principle
> Cleanup occurs only after behavior is verified. Never during active feature development.

## Phase 1 — Audit

Find with evidence (not speculation):

| Category | Look For |
|----------|----------|
| Unused files | Files not imported or referenced anywhere |
| Unused components | React components not rendered anywhere |
| Unused hooks | Custom hooks not called anywhere |
| Unused imports | Import statements for unused modules |
| Unused variables | Declared but never read |
| Unused functions | Defined but never called |
| Unused exports | Exported but never imported elsewhere |
| Unused dependencies | Packages in package.json/pyproject.toml not imported |
| Unused environment variables | Defined in .env but never read |
| Unused routes | API routes or frontend routes not reachable |
| Unused API endpoints | Backend endpoints not called by frontend or tests |
| Commented-out code | Code blocks disabled with comments |
| Duplicated logic | Same logic implemented in multiple places |
| Oversized modules | Files exceeding ~300 lines that could be split |
| Unclear boundaries | Logic in the wrong layer (business logic in routes, etc.) |

### Confidence Levels

For each finding, assign:
| Confidence | Meaning | Action |
|------------|---------|--------|
| **High** | Strong evidence of non-use; safe to remove | Remove |
| **Medium** | Likely unused but verify with team | Remove after confirmation |
| **Low** | Uncertain; may be used in untested paths | Do not remove |

### Audit Report Format
```
Finding: <description>
Location: <file:line>
Category: <from table above>
Confidence: High | Medium | Low
Evidence: <why this is believed unused/redundant>
Recommended Action: <delete / extract / split / move>
```

**Present the audit report before making any changes.**

## Phase 2 — Execute (only after approval)

1. Delete confirmed dead code.
2. Extract genuinely duplicated logic into shared utilities.
3. Split oversized modules where justified.
4. Improve responsibility boundaries (move logic to correct layers).
5. Run all tests — behavior must remain identical.
6. Run E2E tests for affected features.
7. Review behavior in the browser.

## Rules

- ✅ Behavior must remain identical after cleanup.
- ✅ Provide a change summary.
- ❌ No new dependencies unless justified.
- ❌ No public API renaming unless explicitly approved.
- ❌ No unrelated feature changes during cleanup.
- ❌ Do not delete low-confidence items.
- ❌ Do not combine cleanup commits with feature commits.

## Commit
```
refactor(<scope>): <description of cleanup>
```

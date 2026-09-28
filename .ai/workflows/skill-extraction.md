# Skill Extraction Workflow

## Trigger
A non-trivial task has been completed and a reusable project pattern was discovered.

## Principle
> Skills are promoted from real project experience, not created speculatively.

## When to Extract a Skill

Extract a skill when:
- You implemented a pattern that will clearly recur in future phases.
- The pattern involves multiple layers (DB + Backend + Frontend + Testing).
- The pattern is not obvious and required decisions that should be preserved.

Do NOT extract a skill when:
- The pattern is trivial (e.g., "how to create a Python file").
- The pattern is one-off and unlikely to recur.
- The pattern is standard framework usage covered by official documentation.

## Skill Format

Save skills to `.ai/skills/<skill-name>/SKILL.md`:

```markdown
---
name: <skill-name>
description: <one-line description>
---

# <Skill Name>

## Purpose
<What this pattern solves>

## When to Use
<Situations where this pattern applies>

## When NOT to Use
<Situations where this pattern is inappropriate>

## Prerequisites
<What must exist before applying this pattern>

## Inputs
<What information is needed>

## Step-by-Step Instructions

### Database Pattern
<Schema, migrations, constraints>

### Backend Pattern
<Models, schemas, services, repositories, routes>

### Frontend Pattern
<Components, hooks, API calls, states>

### Testing Pattern
<Unit tests, API tests, E2E tests>

### Security Considerations
<Auth, authorization, validation>

## Expected Output
<What the result looks like when complete>

## Common Failure Modes
<What can go wrong and how to avoid it>

## Verification Checklist
- [ ] <Check 1>
- [ ] <Check 2>
- [ ] <Check 3>
```

## Possible Future Skills (do not create until implemented)

- `employee-crud` — Full CRUD for a master data entity
- `role-permission` — Adding a new role/permission boundary
- `audit-log` — Adding audit trail to an entity
- `approval-workflow` — Submit → Approve/Reject/Return pattern
- `paginated-table` — Backend pagination + frontend table
- `file-upload` — Image/document upload with storage
- `notification` — User notification pattern
- `report-export` — Data aggregation + Excel/PDF export

## Commit
```
docs(skills): add <skill-name> skill from <phase/feature>
```

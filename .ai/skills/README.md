# Skills System

This directory contains reusable project patterns (skills) extracted from real implementation experience.

## Purpose

Skills capture project-specific patterns that span multiple layers (database, backend, frontend, testing) and would otherwise require re-discovery when implementing similar features.

## When to Create a Skill

Create a skill when:
- You implemented a multi-layer pattern that will clearly recur.
- The pattern required non-obvious decisions that should be preserved.
- Future developers (human or AI) would benefit from the documented approach.

Do NOT create a skill when:
- The pattern is trivial or obvious.
- The pattern is a one-off unlikely to recur.
- The pattern is standard framework usage documented elsewhere.

## Skill Structure

```
.ai/skills/<skill-name>/
└── SKILL.md
```

Each `SKILL.md` follows the template in `.ai/prompts/08-skill.md`.

## Current Skills

_No skills have been extracted yet. Skills are promoted from real project experience during implementation phases._

## Possible Future Skills

These are anticipated patterns based on the requirements. They will only be created when the pattern is actually implemented and validated:

- `employee-crud` — Full CRUD for a master data entity
- `role-permission` — Adding a new role/permission boundary
- `audit-log` — Adding audit trail to an entity
- `approval-workflow` — Submit → Approve/Reject/Return pattern
- `paginated-table` — Backend pagination + frontend data table
- `file-upload` — Image/document upload with secure storage
- `notification` — User notification pattern
- `report-export` — Data aggregation + Excel/PDF export

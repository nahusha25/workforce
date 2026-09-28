# Prompt 08 — Skill Extraction

Use this prompt after completing a non-trivial task to extract reusable project knowledge.

## Instructions

Follow `.ai/workflows/skill-extraction.md`.

### 1. Evaluate
Ask: "Did I discover a pattern that will recur in future phases?"

If YES → proceed. If NO → skip.

### 2. Define the Skill
```markdown
---
name: <skill-name>
description: <one-line description>
---

# <Skill Name>

## Purpose
<What problem this pattern solves>

## When to Use
<Specific situations where this applies>

## When NOT to Use
<Situations where this is inappropriate>

## Prerequisites
<What must exist before using this pattern>

## Inputs
<What information is needed>

## Step-by-Step Instructions

### Database Pattern
<Migrations, models, constraints>

### Backend Pattern
<Services, repositories, routes, schemas>

### Frontend Pattern
<Components, hooks, API integration>

### Testing Pattern
<Unit, API, E2E tests>

### Security Considerations
<Auth, authorization, validation>

## Expected Output
<What success looks like>

## Common Failure Modes
<What can go wrong>

## Verification Checklist
- [ ] <item>
```

### 3. Save
Save to `.ai/skills/<skill-name>/SKILL.md`.

### 4. Commit
```
docs(skills): add <skill-name> skill from <feature>
```

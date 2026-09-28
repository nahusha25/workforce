# `.ai/` — AI Engineering Governance System

This directory contains the repository-level AI engineering operating system for the **i-Workforce Management Web Application**.

## Purpose

Establish consistent engineering practices for AI-assisted development across all phases of the project. Every AI agent (Claude, Antigravity, or equivalent) working in this repository must follow the rules, workflows, and standards defined here.

## Structure

```
.ai/
├── README.md               ← This file
│
├── rules/                  ← Engineering rules and standards
│   ├── architecture.md     ← System architecture principles
│   ├── coding-standards.md ← General coding standards (Python, TypeScript)
│   ├── database-rules.md   ← Database design and migration rules
│   ├── backend-rules.md    ← Python/FastAPI backend rules
│   ├── frontend-rules.md   ← React/TypeScript frontend rules
│   ├── security-rules.md   ← Security engineering rules
│   ├── testing-rules.md    ← Testing strategy and rules
│   ├── accessibility-rules.md ← Accessibility requirements
│   └── git-rules.md        ← Git workflow and commit rules
│
├── workflows/              ← Step-by-step engineering workflows
│   ├── feature-development.md  ← How to implement a new feature
│   ├── bug-fix.md              ← Evidence-first debugging protocol
│   ├── security-audit.md       ← Security audit → remediation workflow
│   ├── e2e-testing.md          ← End-to-end testing workflow
│   ├── cleanup-refactoring.md  ← Controlled cleanup/refactoring
│   ├── release.md              ← Release preparation workflow
│   └── skill-extraction.md     ← Reusable knowledge extraction
│
├── prompts/                ← Structured prompts for AI-assisted tasks
│   ├── 01-prd.md           ← Product requirement / feature specification
│   ├── 02-ui-ux.md         ← UI/UX design brief
│   ├── 03-security-audit.md ← Security audit prompt
│   ├── 04-debug.md         ← Debugging prompt
│   ├── 05-e2e.md           ← E2E test creation prompt
│   ├── 06-cleanup.md       ← Cleanup/refactoring prompt
│   ├── 07-git-commit.md    ← Git commit prompt
│   └── 08-skill.md         ← Skill extraction prompt
│
├── checklists/             ← Verification checklists
│   ├── feature-checklist.md     ← Feature completion checklist
│   ├── security-checklist.md    ← Security review checklist
│   ├── accessibility-checklist.md ← Accessibility checklist
│   ├── testing-checklist.md     ← Testing completion checklist
│   ├── release-checklist.md     ← Release readiness checklist
│   └── definition-of-done.md   ← Universal definition of done
│
└── skills/                 ← Reusable project patterns (populated during implementation)
    └── README.md           ← Skill system documentation and template
```

## How to Use

1. **Before any work**: Read `CLAUDE.md` at the repository root.
2. **Before a feature**: Follow `workflows/feature-development.md`.
3. **Before debugging**: Follow `workflows/bug-fix.md`.
4. **Before security work**: Follow `workflows/security-audit.md`.
5. **Before cleanup**: Follow `workflows/cleanup-refactoring.md`.
6. **Before committing**: Follow `rules/git-rules.md`.
7. **After completing a feature**: Run through `checklists/definition-of-done.md`.

## Source of Truth Hierarchy

1. **Approved Requirements Document** — business/product functionality
2. **Phase 0 Master Documentation** (`docs/00-phase-0/`) — engineering standards
3. **This `.ai/` governance system** — operational rules and workflows
4. **Repository-specific technical facts** — existing code and configuration
5. **General engineering best practices** — only where not covered above

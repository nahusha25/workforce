# MASTER PROMPT --- PHASE 0

## Workforce Management Web Application --- Master Product, Engineering & AI Implementation Documentation

You are the lead product architect, database architect, Python/FastAPI
backend architect, frontend architect, QA architect, application
security engineer, DevOps-aware engineer, UI/UX systems architect, and
technical project planner for this project.

You are operating inside an existing repository.

You have been provided with the approved **Workforce Management Web
Application Requirements Document** and this master Phase 0 prompt.

Your task is to implement **PHASE 0 ONLY**.

The output of Phase 0 is not the business application. The output is the
complete, developer-ready product, architecture, engineering, UX,
security, testing, and phase-by-phase implementation documentation
required to build the application safely and consistently.

------------------------------------------------------------------------

# 0. SOURCE-OF-TRUTH HIERARCHY

Use the following hierarchy throughout this project:

1.  **Approved Workforce Management Requirements Document**
    -   Primary source of truth for explicitly requested business/product
        functionality.
1B. **Supplied Reference Photos / Handwritten Notes**
    -   Secondary requirement source containing business discussions,
        workflows, calculations, UI concepts, and requirements captured
        by the project team.
    -   Must be analyzed and compared against other sources.
    -   Not automatically confirmed scope; requires triangulation (see
        Requirement Triangulation Framework below).
1C. **Onsite Teams Reference Application** (https://onsiteteams.com/)
    -   Real-world construction/workforce management validation reference.
    -   Used to validate and discover requirements that are independently
        supported by the supplied reference photos.
    -   NOT a source to blindly clone. A capability observed in Onsite is
        relevant ONLY when independently supported by evidence from the
        supplied reference photos.
2.  **This Master Phase 0 Prompt**
    -   Defines how the requirements must be converted into engineering
        documentation and how the project must be engineered.
3.  **Repository-specific technical facts**
    -   Existing code, configuration, dependencies, conventions, and
        architecture discovered during repository inspection.
4.  **Explicit technical implementation decisions**
    -   Allowed only when necessary to implement the requirements and
        must be clearly labeled as technical decisions.
5.  **General engineering best practices**
    -   May be used for implementation quality, security, testing,
        accessibility, maintainability, and reliability, but must never
        become an invented product requirement.

If sources conflict:

-   Do not silently choose one.
-   Record the conflict.
-   Identify each source's interpretation.
-   Determine whether the difference is a scope difference, terminology
    difference, business-rule difference, or implementation difference.
-   Preserve the original evidence from each source.
-   Identify the business decision required.
-   Mark the requirement as unresolved until appropriately resolved.
-   Never invent a business rule merely to make the implementation plan
    complete.
-   Do not invent missing business behavior.

------------------------------------------------------------------------

# 1. CRITICAL PRODUCT SCOPE RULE

The supplied requirements document is the **primary baseline** for
product functionality.

However, the formal document MUST NOT be assumed to contain every
requirement. Phase 0 must perform **Requirement Triangulation** (see
Section 10) by analyzing the supplied reference photos/handwritten notes
and comparing them against the Onsite Teams reference application.

If the SAME or substantially equivalent business capability is supported
by BOTH:

A.  the supplied reference photos / handwritten requirement notes

AND

B.  the Onsite Teams reference application

then the capability must be treated as a **HIGH-CONFIDENCE
MISSING-REQUIREMENT CANDIDATE**, even if it is absent or insufficiently
specified in the original formal requirements document.

Such requirements MUST be incorporated into the Phase-0 master
requirement baseline after evidence-based analysis.

Do not ignore these requirements simply because they were omitted from
the original requirements document.

## DO NOT

-   Invent additional business features.
-   Add generic ERP modules.
-   Add payroll systems beyond what the document explicitly requires.
-   Add CRM.
-   Add inventory management beyond specified material requirements.
-   Add unnecessary integrations.
-   Add mobile applications.
-   Add unnecessary microservices.
-   Add features because they are common in enterprise software.
-   Expand the product beyond supplied requirements.
-   Change terminology used by the requirements document.
-   Assume unstated business rules.
-   Implement future business phases during Phase 0.
-   **Blindly copy every feature observed in Onsite Teams.**
-   **Automatically promote a capability into project scope without
    evidence from both reference photos AND Onsite.**
-   **Silently choose one source when sources conflict.**

If something is not supported by the requirements document, do not add
it as a product feature.

If a technical decision is necessary, label it:

> Technical Implementation Decision --- not a product requirement.

------------------------------------------------------------------------

# 2. WHAT PHASE 0 ACTUALLY IS

Phase 0 is the:

> **Master Product + Architecture + Engineering Governance + UI/UX +
> Security + Testing + Phase Implementation Documentation Phase**

Phase 0 is NOT the implementation of all business features.

The primary output is a complete developer-ready documentation package
that tells the engineering team exactly:

-   What needs to be built.
-   Why it needs to be built.
-   Which requirement it satisfies.
-   In which phase it belongs.
-   What database work is required.
-   What Python/FastAPI backend work is required.
-   What APIs are required.
-   How Swagger must be tested.
-   What frontend work is required.
-   What UI/UX behavior is required.
-   What accessibility and responsive behavior is required.
-   What security controls are required.
-   What tests are required.
-   What dependencies exist.
-   What the definition of done is.
-   What engineering gates must pass before a phase is complete.
-   What reusable project knowledge should be preserved.

------------------------------------------------------------------------

# 3. REQUIRED REQUIREMENT PHASES

The source requirements identify the following functional sequence:

1.  Employee Onboarding & Login
2.  Daily Attendance
3.  Daily Work & Material Update
4.  Supervisor Verification
5.  Director Dashboard & Invoicing

These phases must remain faithful to the source document.

Do not rename or expand them unnecessarily.

Phase 0 must establish their dependencies and implementation order.

------------------------------------------------------------------------

# 4. PHASE 0 OUTPUT --- DOCUMENTATION STRUCTURE

Create and maintain:

``` text
docs/
│
├── 00-phase-0/
│   ├── master-implementation-plan.md
│   ├── requirement-traceability.md
│   ├── requirement-discovery-matrix.md
│   ├── architecture.md
│   ├── database-architecture.md
│   ├── backend-architecture.md
│   ├── frontend-architecture.md
│   ├── ui-ux-architecture.md
│   ├── api-development-standard.md
│   ├── swagger-testing-standard.md
│   ├── security-architecture.md
│   ├── security-audit-standard.md
│   ├── testing-strategy.md
│   ├── e2e-testing-standard.md
│   ├── debugging-standard.md
│   ├── refactoring-standard.md
│   ├── git-standard.md
│   ├── engineering-operating-model.md
│   ├── phase-dependencies.md
│   ├── development-rules.md
│   └── definition-of-done.md
│
├── 01-employee-onboarding-login/
│   ├── requirements.md
│   ├── implementation-plan.md
│   ├── database-plan.md
│   ├── backend-api-plan.md
│   ├── swagger-test-plan.md
│   ├── frontend-plan.md
│   ├── ui-ux-plan.md
│   ├── security-plan.md
│   ├── testing-plan.md
│   └── task-list.md
│
├── 02-daily-attendance/
│   ├── requirements.md
│   ├── implementation-plan.md
│   ├── database-plan.md
│   ├── backend-api-plan.md
│   ├── swagger-test-plan.md
│   ├── frontend-plan.md
│   ├── ui-ux-plan.md
│   ├── security-plan.md
│   ├── testing-plan.md
│   └── task-list.md
│
├── 03-daily-work-material/
│   ├── requirements.md
│   ├── implementation-plan.md
│   ├── database-plan.md
│   ├── backend-api-plan.md
│   ├── swagger-test-plan.md
│   ├── frontend-plan.md
│   ├── ui-ux-plan.md
│   ├── security-plan.md
│   ├── testing-plan.md
│   └── task-list.md
│
├── 04-supervisor-verification/
│   ├── requirements.md
│   ├── implementation-plan.md
│   ├── database-plan.md
│   ├── backend-api-plan.md
│   ├── swagger-test-plan.md
│   ├── frontend-plan.md
│   ├── ui-ux-plan.md
│   ├── security-plan.md
│   ├── testing-plan.md
│   └── task-list.md
│
└── 05-director-dashboard-invoicing/
    ├── requirements.md
    ├── implementation-plan.md
    ├── database-plan.md
    ├── backend-api-plan.md
    ├── swagger-test-plan.md
    ├── frontend-plan.md
    ├── ui-ux-plan.md
    ├── security-plan.md
    ├── testing-plan.md
    └── task-list.md
```

You may adjust filenames slightly if technically necessary, but preserve
the separation of concerns.

------------------------------------------------------------------------

# 5. REPOSITORY ENGINEERING GOVERNANCE

The project must establish a repository-level AI engineering operating
system.

Create:

``` text
.ai/
├── README.md
│
├── rules/
│   ├── architecture.md
│   ├── coding-standards.md
│   ├── database-rules.md
│   ├── backend-rules.md
│   ├── frontend-rules.md
│   ├── security-rules.md
│   ├── testing-rules.md
│   ├── accessibility-rules.md
│   └── git-rules.md
│
├── workflows/
│   ├── feature-development.md
│   ├── bug-fix.md
│   ├── security-audit.md
│   ├── e2e-testing.md
│   ├── cleanup-refactoring.md
│   ├── release.md
│   └── skill-extraction.md
│
├── prompts/
│   ├── 01-prd.md
│   ├── 02-ui-ux.md
│   ├── 03-security-audit.md
│   ├── 04-debug.md
│   ├── 05-e2e.md
│   ├── 06-cleanup.md
│   ├── 07-git-commit.md
│   └── 08-skill.md
│
├── checklists/
│   ├── feature-checklist.md
│   ├── security-checklist.md
│   ├── accessibility-checklist.md
│   ├── testing-checklist.md
│   ├── release-checklist.md
│   └── definition-of-done.md
│
└── skills/
    └── README.md
```

Also create/update the repository root:

``` text
CLAUDE.md
```

The exact contents must be repository-specific after inspection, but it
must establish the rules in this prompt.

------------------------------------------------------------------------

# 6. CLAUDE.MD ROLE

`CLAUDE.md` is the top-level instruction layer for future AI-assisted
engineering.

It must instruct Claude/Antigravity to:

1.  Understand the repository before editing.
2.  Identify the relevant requirement phase.
3.  Read the relevant requirement documentation.
4.  Read applicable architecture and engineering rules.
5.  Read relevant UI/UX and security rules.
6.  Produce an implementation plan before substantial changes.
7.  Never invent product requirements.
8.  Follow database → backend → API → Swagger → frontend → integration →
    testing order unless a documented technical dependency requires
    another order.
9.  Validate authorization and security boundaries.
10. Run appropriate tests.
11. Run E2E tests for critical business journeys.
12. Perform cleanup only after behavior is verified.
13. Keep commits atomic.
14. Preserve reusable project knowledge.
15. Stop and ask for approval where an explicit approval gate is
    defined.
16. Never silently skip a required engineering gate.

`CLAUDE.md` must reference `.ai/` instead of duplicating every rule.

------------------------------------------------------------------------

# 7. ENGINEERING OPERATING MODEL

Create:

``` text
docs/00-phase-0/engineering-operating-model.md
```

The project must follow this lifecycle:

``` text
Requirement
    ↓
Requirement Specification / PRD
    ↓
UI/UX Design Specification
    ↓
Implementation Plan
    ↓
Database
    ↓
Backend
    ↓
API
    ↓
Swagger Verification
    ↓
Frontend
    ↓
Integration
    ↓
Automated Testing
    ↓
Security Audit
    ↓
E2E Verification
    ↓
Cleanup / Refactor
    ↓
Documentation
    ↓
Atomic Git Commit
    ↓
Reusable Skill / Knowledge Extraction
```

This lifecycle applies to future implementation phases.

Phase 0 establishes the system; it does not implement the business
features.

------------------------------------------------------------------------

# 8. ENGINEERING GATES

Every future feature/phase must pass explicit gates.

## Gate 1 --- Requirement

The requirement is traceable to the source document.

## Gate 2 --- UX

All relevant screens, flows, states, responsive behavior, and
accessibility requirements are documented.

## Gate 3 --- Implementation

DB, backend/API, frontend, and integration work are planned and
implemented according to architecture standards.

## Gate 4 --- Verification

Unit/integration/API/Swagger/E2E testing appropriate to the feature
passes.

## Gate 5 --- Security

Security-sensitive functionality is audited.

## Gate 6 --- Cleanup

Dead code and unnecessary duplication are reviewed without changing
behavior.

## Gate 7 --- Documentation

Relevant documentation and project knowledge are updated.

## Gate 8 --- Git

Changes are grouped into atomic, meaningful commits.

A gate must never be silently skipped.

If a gate is not applicable, record:

``` text
Gate: Not applicable
Reason: <explicit reason>
```

------------------------------------------------------------------------

# 9. FIRST TASK --- STUDY THE REQUIREMENTS

Before creating any implementation plan:

1.  Read the complete requirements document.
2.  Extract every functional requirement.
3.  Extract every business rule.
4.  Extract every user role.
5.  Extract every application page.
6.  Extract every master-data requirement.
7.  Extract every usability requirement.
8.  Extract every security requirement.
9.  Extract every reporting requirement.
10. Extract every stated implementation priority.
11. Extract all explicit workflow/state transitions.
12. Extract all validation rules.
13. Extract all approval/rejection behavior.
14. Extract all stated data relationships.
15. Extract all stated outputs/reports.

Do not begin implementation planning until this extraction is complete.

------------------------------------------------------------------------

# 10. REQUIREMENT TRIANGULATION FRAMEWORK

Phase 0 must perform **Requirement Triangulation** using three sources:

``` text
FORMAL REQUIREMENTS DOCUMENT
        +
SUPPLIED REFERENCE PHOTOS / HANDWRITTEN NOTES
        +
ONSITE TEAMS REFERENCE APPLICATION
        ↓
REQUIREMENT DISCOVERY & VALIDATION
        ↓
PHOTO + ONSITE AGREEMENT
        ↓
HIGH-CONFIDENCE MISSING REQUIREMENT
        ↓
ADD TO MASTER REQUIREMENT BASELINE
        ↓
PHASE-WISE DB + BACKEND + FRONTEND IMPLEMENTATION PLAN
```

## Triangulation Principle

The formal requirements document remains the primary baseline. However,
it MUST NOT be assumed to contain every requirement.

Phase 0 must:

1.  Analyze all supplied reference photos/handwritten notes.
2.  Analyze the Onsite Teams reference application.
3.  Compare photo findings against Onsite capabilities.
4.  Only promote a capability into the project requirement baseline
    when evidence supports it from BOTH sources.

The purpose is NOT: "Build everything Onsite has."

The purpose IS: "Use Onsite as a real-world reference to validate and
discover requirements that are independently supported by the supplied
project references."

## Evidence Classification System

Every discovered requirement must be classified into one of these levels:

### LEVEL 1 --- EXPLICIT REQUIREMENT

Requirement appears in the formal approved requirements/documentation.

**Action:**

-   Treat as project scope.
-   Analyze it fully.
-   Assign a requirement ID.
-   Map it to an implementation phase.

### LEVEL 2 --- TRIANGULATED REQUIREMENT

Requirement appears in BOTH:

-   supplied reference photos/handwritten notes

AND

-   Onsite Teams reference application

even when it is absent or incomplete in the formal requirements.

**Action:**

-   Treat as a **HIGH-CONFIDENCE** requirement candidate.
-   Add it to the Phase-0 master requirement baseline.
-   Assign a unique requirement ID.
-   Record evidence from both sources.
-   Define functional behavior.
-   Define business rules.
-   Define edge cases.
-   Define DB implications.
-   Define backend/API implications.
-   Define frontend/UI implications.
-   Define permissions/roles.
-   Define reporting implications where applicable.
-   Assign it to an implementation phase.
-   Add acceptance criteria.
-   Add traceability.
-   Identify unresolved business decisions rather than inventing them.

This category is CRITICAL and must not be missed.

### LEVEL 3A --- PHOTO-ONLY REQUIREMENT

Requirement appears in the supplied reference photos/handwritten notes
but is not verified in Onsite.

**Action:**

-   Do NOT silently promote it to confirmed scope.
-   Record it as a **BUSINESS REQUIREMENT --- PENDING VALIDATION**.
-   Preserve the requirement and its context.
-   Identify what must be validated before implementation.
-   Do not delete it.

### LEVEL 3B --- ONSITE-ONLY CAPABILITY

Capability is observed in Onsite but is not supported by either the
formal requirements or the supplied reference photos.

**Action:**

-   Do NOT automatically add it to project scope.
-   Record it as a **REFERENCE CAPABILITY / POTENTIAL FUTURE ENHANCEMENT**
    when relevant.
-   Explain why it was not promoted into the current scope.

### LEVEL 4 --- UNSUPPORTED / INVENTED REQUIREMENT

Requirement is not supported by the formal requirements, supplied
reference material, or justified evidence.

**Action:**

-   Do NOT invent it.
-   Do NOT add it to scope.
-   If useful, record it as an open product decision only when there is
    a legitimate reason to clarify it.

## Conflict Resolution

If formal requirements, handwritten/reference photos, and Onsite
reference disagree with each other:

DO NOT silently choose one.

Phase 0 must:

1.  Record the conflict.
2.  Identify each source's interpretation.
3.  Determine whether the difference is a scope difference, terminology
    difference, business-rule difference, or implementation difference.
4.  Preserve the original evidence.
5.  Identify the business decision required.
6.  Mark the requirement as unresolved until appropriately resolved.
7.  Never invent a business rule merely to make the implementation plan
    complete.

## Safety Rule

Do not allow future implementation agents to say:

> "The requirement was not present in the original requirements document,
> so it is out of scope."

That statement is **INVALID** when the capability has been confirmed
through Reference Photos + Onsite Reference triangulation.

The correct behavior is: **"Check the Phase-0 triangulation matrix."**

------------------------------------------------------------------------

# 11. REQUIREMENT DISCOVERY AREAS

During Phase 0, explicitly inspect the supplied handwritten/reference
photos for business capabilities including, but not limited to:

-   employee attendance (punch in, punch out, multiple entries per day)
-   employee location / GPS tracking
-   work entry and updates
-   working hours calculation
-   daily working hours
-   overtime and overtime calculation
-   daily earnings
-   employee payment (daily, weekly, monthly)
-   salary registration
-   automatic salary/payment calculation
-   employee/team relationships
-   multiple work activities per day
-   daily reporting, weekly reporting, monthly reporting
-   material management (purchase, receipt, usage, consumption, remaining)
-   material inventory / quantity tracking
-   workforce productivity
-   task/work assignment
-   project/site/location relationships
-   cable laying quantities and types
-   any other clearly represented workflow or calculation

**IMPORTANT:** These are NOT automatically confirmed requirements merely
because they are listed here. The Phase-0 agent must inspect the actual
reference photos and verify whether each capability is actually
represented. Then compare those findings with the Onsite reference. Only
capabilities supported by both sources should be promoted under the
LEVEL 2 --- TRIANGULATED REQUIREMENT rule.

## Business Calculation Discovery

The handwritten photos contain examples of business calculations and
flows. Phase 0 must explicitly inspect for calculations such as:

-   working-hour calculations
-   overtime calculations
-   daily earnings
-   salary/payment calculations
-   monthly payment calculations
-   attendance-based calculations
-   material quantity calculations
-   productivity calculations
-   other formulas represented in the source material

If a calculation is visible in the photos and corresponding
functionality exists in Onsite, treat it as a triangulated requirement.

However: DO NOT invent the exact formula if the source does not define
it clearly. Instead document:

-   observed calculation concept
-   source evidence
-   confirmed behavior
-   unknown formula/rule
-   business decision required

## Material Management Lifecycle Discovery

Phase 0 must specifically investigate the material lifecycle
represented in the photos. For example, the reference material may
represent a lifecycle such as:

``` text
Material Requirement
    ↓
Purchase
    ↓
Receipt
    ↓
Available Material
    ↓
Material Usage
    ↓
Remaining Quantity
```

Compare this workflow against the corresponding Onsite capability. If
both sources support the workflow, promote the corresponding material
lifecycle capability into the project requirements. Do not reduce this
to simply "material purchase." Capture the complete lifecycle supported
by evidence.

## Employee Payment / Salary Discovery

Phase 0 must specifically investigate employee payment/salary
capabilities represented in the photos. Potential concepts include:

-   employee salary registration
-   salary type (daily, weekly, monthly)
-   attendance-based payment
-   working-hour-based payment
-   overtime payment
-   salary calculation
-   automatic payment calculation
-   payment records and reporting
-   PPF / deduction management

Compare these against the Onsite reference. If the capability exists
in BOTH the photos and Onsite, promote it to the triangulated
requirement baseline. If the exact calculation formula is not defined,
do not invent it. Document the missing business rule as an explicit
open decision.

## Overtime Discovery

Phase 0 must specifically investigate overtime. The supplied reference
photos represent the concept of:

``` text
Standard Working Hours
        +
Additional Hours
        ↓
Overtime
```

Compare this with the corresponding Onsite workforce/payment behavior.
If both sources support overtime, overtime MUST be added to the project
requirement baseline.

Phase 0 must define/document, where supported:

-   standard working hours
-   additional hours
-   overtime eligibility
-   overtime calculation concept
-   overtime payment relationship
-   attendance relationship
-   salary/payment relationship
-   approval requirements if supported
-   reporting requirements if supported

If the exact overtime threshold or rate is not specified: DO NOT invent
the rate. Record: **"Business Rule Pending Confirmation"**

------------------------------------------------------------------------

# 12. REQUIREMENT DISCOVERY TABLE

Phase 0 must maintain a requirement discovery/triangulation matrix in:

``` text
docs/00-phase-0/requirement-discovery-matrix.md
```

The matrix must contain at minimum:

  -----------------------------------------------------------------------
  Column                      Description
  --------------------------- -------------------------------------------
  Requirement ID              Unique identifier

  Capability                  Business capability name

  Formal Requirements         YES / NO / PARTIAL / UNKNOWN

  Reference Photos            YES / NO / PARTIAL / UNKNOWN

  Onsite Reference            YES / NO / PARTIAL / UNKNOWN

  Evidence Classification     LEVEL 1 / LEVEL 2 / LEVEL 3A / LEVEL 3B /
                              LEVEL 4

  Requirement Status          CONFIRMED / PENDING VALIDATION / REFERENCE
                              ONLY / NOT IN SCOPE

  Business Description        Description of the capability

  Business Rules              Known business rules

  Dependencies                Requirements this depends on

  DB Impact                   Database changes required

  Backend/API Impact          Backend/API changes required

  Frontend Impact             Frontend/UI changes required

  Roles/Permissions           Which roles can access

  Reporting Impact            Reporting implications

  Implementation Phase        Which phase this belongs to

  Acceptance Criteria         How to verify completion

  Open Questions              Unresolved business decisions

  Source/Evidence Notes        References to specific photos, Onsite
                              pages, or formal document sections
  -----------------------------------------------------------------------

Use clear indicators: **YES**, **NO**, **PARTIAL**, **UNKNOWN**.

Do not use unsupported assumptions to fill evidence fields.

## Phase Assignment for Triangulated Requirements

Triangulated requirements must not remain only as analysis notes.

After discovery, Phase 0 must assign each confirmed/approved
triangulated requirement to the appropriate implementation phase.

The phase plan must contain:

-   requirement ID
-   feature/module
-   dependencies
-   DB tasks
-   backend tasks
-   API tasks
-   frontend tasks
-   permissions
-   validation
-   testing
-   acceptance criteria

The implementation phases must reflect both:

A.  original formal requirements

AND

B.  validated high-confidence requirements discovered through
    triangulation.

------------------------------------------------------------------------

# 13. REQUIREMENT TRACEABILITY

Create:

``` text
docs/00-phase-0/requirement-traceability.md
```

Create a complete mapping:

``` text
Source Evidence (Formal / Photo / Onsite)
    ↓
Evidence Classification (Level 1 / 2 / 3A / 3B)
    ↓
Requirement
    ↓
Phase
    ↓
Feature
    ↓
Database
    ↓
Backend/API
    ↓
Swagger
    ↓
Frontend/UI
    ↓
Security
    ↓
Testing
    ↓
Acceptance Criteria
```

Use:

  ---------------------------------------------------------------------------------------------------------------------------------
  Requirement   Source      Evidence     Requirement   Phase   Feature   DB    Backend   API   Swagger   Frontend   Security   Test
  ID            Evidence   Level                                                                                             
  ------------- ---------- ------------ ------------- ------- --------- ----- --------- ----- --------- ---------- ---------- ------

  ---------------------------------------------------------------------------------------------------------------------------------

Create IDs if the source document does not provide them.

Do not lose any requirement.

Do not create requirements that do not exist in any confirmed source.

The Phase-0 documentation must make it possible to determine:

> "Why does this requirement exist?"

and

> "Where did this requirement come from?"

------------------------------------------------------------------------

# 14. MASTER IMPLEMENTATION PLAN

Create:

``` text
docs/00-phase-0/master-implementation-plan.md
```

It must contain:

## 11.1 Product scope

Strictly summarize the supplied requirements.

## 11.2 Users

Only roles defined in the requirements.

## 11.3 Application pages

Only pages supported by the requirements.

## 11.4 Functional requirements

All requirements.

## 11.5 Business rules

All explicit rules.

## 11.6 Technical architecture

The architecture needed to implement the requirements.

## 11.7 Phase sequence

Complete implementation order.

## 11.8 Dependencies

Phase and feature dependencies.

## 11.9 Engineering gates

Required gates for every phase.

## 11.10 Definition of done

How each task, feature, and phase becomes complete.

------------------------------------------------------------------------

# 15. TECHNOLOGY DECISIONS

The project must use:

## Backend

``` text
Python
FastAPI
SQLAlchemy
Pydantic
Alembic
PostgreSQL
```

## API

``` text
REST
JSON
OpenAPI
Swagger UI
```

Swagger UI is the primary manual API testing interface.

## Frontend

``` text
React
TypeScript
```

The requirements specify a responsive/mobile-first web application
approach.

Do not introduce another frontend framework unless technically necessary
and explicitly documented.

------------------------------------------------------------------------

# 16. ARCHITECTURE PRINCIPLES

The project must prioritize:

1.  **Modular monolith architecture** unless the requirements provide a
    genuine reason for service separation.
2.  **Clear domain boundaries.**
3.  **Database integrity.**
4.  **Explicit authorization.**
5.  **Thin API route handlers.**
6.  **Business logic in services/use cases.**
7.  **Data access through repositories or an equivalent documented
    boundary.**
8.  **Strong validation at API and database boundaries.**
9.  **Testability.**
10. **Observability without leaking sensitive data.**
11. **Minimal dependencies.**
12. **No speculative abstractions.**
13. **No premature microservices.**
14. **No unnecessary infrastructure.**

------------------------------------------------------------------------

# 17. DATABASE-FIRST ARCHITECTURE

Create:

``` text
docs/00-phase-0/database-architecture.md
```

Identify only entities required by the requirements.

For every entity specify:

``` text
Entity
Purpose
Fields
Relationships
Constraints
Indexes where required
Status values where required
Audit requirements where required
Phase introduced
```

The database plan must distinguish:

### Phase 0 technical foundation

from:

### Future phase business tables

Do not implement future business tables during Phase 0 unless required
for the technical foundation.

------------------------------------------------------------------------

# 18. DATABASE CONSTRAINT PLANNING

For every requirement phase explicitly identify:

``` text
Primary keys
Foreign keys
Unique constraints
Not-null constraints
Check constraints
Relationship constraints
Allowed status values
Date constraints
Quantity constraints
Amount constraints
Reference integrity
```

Database constraints should enforce rules wherever appropriate.

Do not rely entirely on frontend validation.

Do not rely entirely on API validation when a rule should also be
protected by the database.

------------------------------------------------------------------------

# 19. BACKEND ARCHITECTURE

Create:

``` text
docs/00-phase-0/backend-architecture.md
```

Recommended structure:

``` text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   ├── api/
│   ├── modules/
│   └── shared/
│
├── alembic/
├── tests/
├── pyproject.toml
└── README.md
```

Each business requirement phase should have an appropriate module.

Do not create modules for functionality not in the requirements.

------------------------------------------------------------------------

# 20. BACKEND LAYERING

Every feature should follow:

``` text
FastAPI Router
      ↓
Pydantic Schema
      ↓
Service / Use Case
      ↓
Repository / Data Access
      ↓
SQLAlchemy
      ↓
PostgreSQL
```

Business logic must not be placed directly into route handlers.

Shared infrastructure must remain separate from domain-specific logic.

------------------------------------------------------------------------

# 21. API DESIGN STANDARD

All APIs must use:

``` text
/api/v1
```

For every API planned, document:

``` text
API ID
Endpoint
HTTP Method
Purpose
Requirement Reference
Request
Response
Validation
Business Rules
Authentication
Authorization
Database Interaction
Error Cases
Swagger Test Cases
```

Do not invent unrelated APIs.

Use consistent:

-   HTTP semantics
-   response structures
-   validation errors
-   pagination conventions where needed
-   error handling
-   authentication behavior
-   authorization behavior
-   API versioning

Document these conventions centrally.

------------------------------------------------------------------------

# 22. SWAGGER STANDARD

Swagger UI must be available through FastAPI.

Expected development endpoints:

``` text
/api/docs
/api/redoc
/openapi.json
```

Every future API must automatically appear in OpenAPI/Swagger.

Every API phase must have a Swagger test plan covering, where
applicable:

``` text
Successful request
Invalid request
Required-field validation
Authentication failure
Authorization failure
Business-rule validation
Invalid state transition
Database constraint failure
Not-found behavior
Conflict behavior
Malformed input
Boundary values
```

------------------------------------------------------------------------

# 23. FRONTEND ARCHITECTURE

Create:

``` text
docs/00-phase-0/frontend-architecture.md
```

Use:

``` text
React
TypeScript
```

Define:

``` text
Application shell
Routing
Feature structure
API client
Reusable components
Forms
Tables
Loading states
Error states
Empty states
Permission states
Notifications
Responsive/mobile-first behavior
Accessibility
```

Do not design screens not supported by requirements.

------------------------------------------------------------------------

# 24. UI/UX DESIGN SYSTEM --- MANDATORY FOR FUTURE PHASES

Create:

``` text
docs/00-phase-0/ui-ux-architecture.md
```

The UI/UX workflow must follow the principle:

> **Design before code.**

For every user-facing requirement, create a design brief before
implementation.

The design brief must contain:

1.  Design principles --- 3 or more concrete principles.
2.  Visual direction --- references, patterns to use, and patterns to
    avoid.
3.  Design tokens.
4.  Screen inventory.
5.  User flows.
6.  Per-screen layout.
7.  Component library usage.
8.  Screen states.
9.  Responsive behavior.
10. Accessibility.

------------------------------------------------------------------------

# 25. UI DESIGN PRINCIPLES

Do not use generic templates or arbitrary design defaults.

The design must be appropriate for a serious enterprise workforce
application.

The design documentation must explicitly justify:

``` text
Typography
Color
Spacing
Information density
Navigation
Hierarchy
Status communication
Action placement
Forms
Tables
Filters
Dialogs
Notifications
```

Avoid:

-   generic purple-gradient SaaS templates
-   unnecessary visual decoration
-   inconsistent component patterns
-   excessive animation
-   ambiguous primary actions
-   inaccessible low-contrast UI
-   desktop-only layouts

The design should optimize for operational clarity and efficient
repetitive workflows.

------------------------------------------------------------------------

# 26. DESIGN TOKENS

Define centrally:

``` text
Color palette
Typography scale
Spacing scale
Border radius
Shadows/elevation
Breakpoints
Motion rules
Focus styles
Status colors
Semantic colors
```

Do not hardcode arbitrary design values repeatedly across features.

Feature screens must consume the established design system.

------------------------------------------------------------------------

# 27. SCREEN INVENTORY

For each phase, identify every required screen and its purpose.

For each screen document:

``` text
Screen
Purpose
Primary user
Entry points
Primary action
Secondary actions
Information hierarchy
Components
Data requirements
Permission requirements
Loading state
Empty state
Error state
Success state
Validation state
Responsive behavior
Accessibility behavior
```

------------------------------------------------------------------------

# 28. ACCESSIBILITY STANDARD

Accessibility is part of the engineering standard.

Every relevant screen must document:

``` text
Keyboard navigation
Focus order
Visible focus
Semantic HTML
Labels
Form error association
ARIA only where necessary
Color contrast
Touch target considerations
Screen-reader behavior
Modal focus management
Table accessibility
```

Do not treat accessibility as a final cosmetic pass.

------------------------------------------------------------------------

# 29. RESPONSIVE/MOBILE-FIRST STANDARD

The requirements specify a responsive/mobile-first web application.

Each screen must document behavior for:

``` text
Mobile
Tablet
Desktop
```

Do not merely shrink the desktop layout.

Define:

-   navigation transformation
-   table behavior
-   form layout
-   action placement
-   fixed/sticky controls where needed
-   touch targets
-   information prioritization
-   overflow behavior

------------------------------------------------------------------------

# 30. SECURITY ENGINEERING SYSTEM

Create:

``` text
docs/00-phase-0/security-architecture.md
docs/00-phase-0/security-audit-standard.md
.ai/rules/security-rules.md
.ai/workflows/security-audit.md
.ai/prompts/03-security-audit.md
```

Security is a mandatory engineering gate.

The security audit must inspect, as applicable:

``` text
Authentication
Session handling
Authorization
RBAC
Tenant/data isolation if applicable
Hardcoded secrets
Keys/tokens
Client-side secret exposure
SQL injection
NoSQL injection where applicable
Command injection
XSS
CSRF
Unprotected API routes
Missing input validation
Missing sanitization
Rate limiting
Brute-force protection
CORS
Security headers
Cookie flags
Dependency vulnerabilities
File upload risks
Sensitive data exposure
Log leakage
Error-response leakage
Insecure direct object references
Privilege escalation
Mass assignment
```

------------------------------------------------------------------------

# 31. SECURITY AUDIT --- ANALYSIS FIRST

The security workflow must be:

``` text
AUDIT
 ↓
REPORT FINDINGS
 ↓
WAIT FOR APPROVAL
 ↓
REMEDIATION
 ↓
TEST
 ↓
RE-AUDIT
```

Do not automatically modify application code while performing the
initial audit.

Every finding must include:

``` text
Finding ID
Severity
Category
File
Line / location
Description
Why it matters
How it could be exploited
Recommended fix
Verification method
```

Severity:

``` text
Critical
High
Medium
Low
```

If a category is clean, explicitly state that it was reviewed and no
finding was identified.

------------------------------------------------------------------------

# 32. DEBUGGING STANDARD

Create:

``` text
docs/00-phase-0/debugging-standard.md
.ai/workflows/bug-fix.md
.ai/prompts/04-debug.md
```

The debugging protocol is evidence-first.

When a bug is reported:

### Step 1

Restate the problem.

### Step 2

List the 3--5 most likely root causes, ranked by probability.

### Step 3

For each cause, give the smallest verification step: - log check -
one-line check - request inspection - database check - reproduction
step - targeted test

### Step 4

Stop and wait for evidence where user-provided verification is required.

### Step 5

Only after the root cause is confirmed: - make the minimal fix - explain
why it works - define exact verification tests

Rules:

-   Do not shotgun changes.
-   Do not refactor unrelated code.
-   Do not change multiple layers without evidence.
-   Do not fix problems the user did not report.
-   Do not replace diagnosis with guesswork.

------------------------------------------------------------------------

# 33. END-TO-END TESTING STANDARD

Create:

``` text
docs/00-phase-0/e2e-testing-standard.md
.ai/workflows/e2e-testing.md
.ai/prompts/05-e2e.md
```

Use Playwright for end-to-end browser testing.

The E2E strategy must:

1.  Configure Playwright for local and CI execution.
2.  Enable retries where appropriate.
3.  Capture screenshots/traces on failure.
4.  Identify critical user journeys from the requirements.
5.  Obtain approval/confirmation of journey scope when needed.
6.  Test happy paths.
7.  Test realistic failure states.
8.  Test validation failures.
9.  Test permission failures.
10. Test expired/invalid sessions where applicable.
11. Test empty data states where applicable.
12. Prefer role-based or data-testid selectors.
13. Add missing `data-testid` attributes where stable selectors are
    necessary.
14. Create deterministic test data.
15. Isolate test data and clean it up.
16. Provide scripts for local and CI execution.
17. Ensure the suite can run reliably on every pull request.

Explain any requirement journey that cannot be reliably automated and
why.

------------------------------------------------------------------------

# 34. TESTING PYRAMID

Future implementation phases should use an appropriate test pyramid:

``` text
             E2E
          Integration
       API / Service Tests
     Unit / Domain Tests
 Database constraint tests
```

Do not use E2E tests for every small validation.

Do not rely only on unit tests for end-to-end business workflows.

Critical business journeys must have E2E coverage.

------------------------------------------------------------------------

# 35. CLEANUP & REFACTORING STANDARD

Create:

``` text
docs/00-phase-0/refactoring-standard.md
.ai/workflows/cleanup-refactoring.md
.ai/prompts/06-cleanup.md
```

Cleanup occurs only after behavior is verified.

Use two phases.

## Phase 1 --- Audit

Find with evidence:

``` text
Unused files
Unused components
Unused hooks
Unused imports
Unused variables
Unused functions
Unused exports
Unused dependencies
Unused environment variables
Unused routes
Unused API endpoints
Commented-out code
Duplicated logic
Oversized modules
Unclear responsibility boundaries
```

Assign confidence:

``` text
High
Medium
Low
```

Do not delete low-confidence items.

Present the audit before execution.

## Phase 2 --- Execute

Only after approval:

``` text
Delete confirmed dead code
Extract genuinely duplicated logic
Split oversized modules where justified
Improve responsibility boundaries
Run tests
Run E2E
Review behavior
```

Rules:

-   behavior must remain identical
-   no new dependency unless justified
-   no public API renaming unless explicitly approved
-   no unrelated feature changes
-   provide a change summary

------------------------------------------------------------------------

# 36. GIT COMMIT STANDARD

Create:

``` text
docs/00-phase-0/git-standard.md
.ai/rules/git-rules.md
.ai/prompts/07-git-commit.md
```

Use Conventional Commits.

Allowed types include:

``` text
feat
fix
refactor
perf
docs
test
chore
style
build
ci
```

Rules:

1.  Review staged and unstaged changes.
2.  Group changes by intent.
3.  Keep one logical intent per commit.
4.  Separate feature changes from refactors.
5.  Separate fixes from documentation when practical.
6.  Never use vague messages such as:
    -   update
    -   changes
    -   fix stuff
    -   final
    -   wip
7.  Run the relevant validation before creating a commit.
8.  Mention breaking changes explicitly.

Examples:

``` text
feat(employee): add employee onboarding API

feat(employee): add onboarding form

test(employee): add onboarding e2e journey

fix(attendance): reject duplicate check-in

refactor(attendance): extract attendance validation service
```

------------------------------------------------------------------------

# 37. PROJECT SKILL / KNOWLEDGE SYSTEM

Create:

``` text
.ai/prompts/08-skill.md
.ai/workflows/skill-extraction.md
.ai/skills/README.md
```

After completing a non-trivial task, determine whether a reusable
project pattern was discovered.

A skill should be created only when the pattern is reusable.

Each skill must contain:

``` text
Name
Purpose
When to use
When not to use
Prerequisites
Inputs
Step-by-step instructions
Database pattern
Backend pattern
Frontend pattern
Testing pattern
Security considerations
Expected output
Common failure modes
Verification checklist
```

Examples of possible future project skills:

``` text
employee-crud
role-permission
audit-log
approval-workflow
paginated-table
file-upload
notification
report-export
```

Do not create speculative skills during Phase 0. Create the skill system
and template; skills are promoted from real project experience during
future implementation.

------------------------------------------------------------------------

# 38. DEVELOPMENT RULES

Create:

``` text
docs/00-phase-0/development-rules.md
.ai/rules/coding-standards.md
```

The engineering standards must include:

## General

-   Prefer simple, explicit code.
-   Avoid premature abstraction.
-   Avoid speculative features.
-   Keep functions focused.
-   Keep modules cohesive.
-   Preserve domain boundaries.
-   Make failure behavior explicit.
-   Avoid hidden side effects.

## Backend

-   Type annotate Python.
-   Validate external input.
-   Keep route handlers thin.
-   Keep business logic in services/use cases.
-   Keep database access controlled.
-   Use transactions intentionally.
-   Handle errors consistently.
-   Do not expose internal exceptions.

## Frontend

-   Use TypeScript strictly.
-   Avoid `any` unless explicitly justified.
-   Keep components focused.
-   Separate server/API concerns from presentation where appropriate.
-   Reuse established components.
-   Handle loading/error/empty/permission states.
-   Avoid duplicated business logic in UI.

## Database

-   Use migrations.
-   Never manually alter production schema outside migration strategy.
-   Define constraints intentionally.
-   Avoid speculative tables.
-   Use indexes based on access patterns.
-   Preserve referential integrity.

------------------------------------------------------------------------

# 39. OBSERVABILITY & ERROR HANDLING

Define project standards for:

``` text
Structured application logging
Request correlation where appropriate
Error categorization
Safe error responses
Audit logging where requirements require history/accountability
Monitoring hooks
Health checks
```

Do not log:

``` text
Passwords
OTP values
Authentication tokens
Secrets
Sensitive personal data unless explicitly required and protected
```

Observability is technical infrastructure, not a product feature, unless
the requirements explicitly expose it to users.

------------------------------------------------------------------------

# 40. ENVIRONMENT & SECRETS STANDARD

Define:

``` text
Environment variables
Local configuration
Test configuration
Production configuration
Secret management
Configuration validation
```

Rules:

-   Never hardcode secrets.
-   Never commit secrets.
-   Never expose backend secrets to frontend bundles.
-   Provide safe `.env.example` values.
-   Validate required configuration during application startup where
    appropriate.

------------------------------------------------------------------------

# 41. DEPENDENCY STANDARD

Before adding a dependency:

1.  Confirm it is necessary.
2.  Confirm it solves a real requirement or engineering problem.
3.  Check whether existing dependencies already provide the capability.
4.  Consider maintenance/security implications.
5.  Document the reason when non-trivial.

Do not add libraries merely because they are popular.

------------------------------------------------------------------------

# 42. PHASE IMPLEMENTATION ORDER

The implementation planning must follow:

``` text
Requirement
    ↓
Database
    ↓
Backend
    ↓
API
    ↓
Swagger Testing
    ↓
Frontend
    ↓
Integration
    ↓
Automated Testing
    ↓
Security Verification
    ↓
E2E Verification
    ↓
Cleanup
    ↓
Documentation
```

If a different order is technically required for a specific task,
document the reason.

------------------------------------------------------------------------

# 43. REQUIREMENT PHASE DOCUMENT STANDARD

Every phase must contain:

``` text
1. Requirement Scope
2. Requirement Traceability
3. Actors
4. User Flows
5. Business Rules
6. State Transitions
7. Database Plan
8. Backend Plan
9. API Plan
10. Swagger Plan
11. Frontend Plan
12. UI/UX Plan
13. Accessibility Plan
14. Security Plan
15. Integration Plan
16. Testing Plan
17. E2E Plan
18. Task Breakdown
19. Dependencies
20. Acceptance Criteria
21. Definition of Done
22. Risks / Open Questions
```

------------------------------------------------------------------------

# 44. TASK-WISE IMPLEMENTATION

This is mandatory.

Do not write:

> Implement attendance backend.

Break work into actual tasks.

Use IDs:

``` text
DB-001
DB-002

BE-001
BE-002

API-001
API-002

SWG-001
SWG-002

FE-001
FE-002

UX-001
UX-002

SEC-001
SEC-002

TEST-001
TEST-002

E2E-001
E2E-002

DOC-001
```

------------------------------------------------------------------------

# 45. TASK FORMAT

Every task must contain:

``` text
Task ID:
Task:
Layer:
Requirement Reference:
Purpose:
Description:
Dependencies:
Implementation Details:
Expected Output:
Validation:
Acceptance Criteria:
Definition of Done:
```

Example:

``` text
Task ID:
DB-001

Task:
Create attendance record structure

Layer:
Database

Requirement Reference:
Daily Attendance

Purpose:
Persist the attendance information explicitly required by the requirements.

Description:
Define the required attendance structure and relationships.

Dependencies:
Database foundation.

Implementation Details:
Define the required employee/site/time/GPS relationships and constraints
supported by the source requirement.

Expected Output:
Migration and database structure.

Validation:
Required constraints are enforced.

Acceptance Criteria:
A valid attendance record can be persisted and invalid required
relationships are rejected.

Definition of Done:
Migration exists, constraints are verified, tests pass, and documentation
is updated.
```

------------------------------------------------------------------------

# 46. PHASE 1 --- EMPLOYEE ONBOARDING & LOGIN

Create the complete phase documentation strictly from the requirements.

Cover only documented requirements around:

-   Employee registration
-   Name
-   Mobile
-   OTP login
-   Employee ID
-   Trade/role
-   Agreed rate
-   Supervisor
-   Assigned client site
-   Secure active session

Break implementation into:

-   Database
-   Backend
-   API
-   Swagger
-   Frontend
-   UI/UX
-   Security
-   Testing
-   E2E
-   Documentation

Do not add unrelated employee-management functionality.

------------------------------------------------------------------------

# 47. PHASE 2 --- DAILY ATTENDANCE

Use only the attendance requirements from the source document.

Plan tasks for:

### Database

-   Attendance structure
-   Employee relationship
-   Client/site relationship
-   Date/time
-   GPS
-   Geo-fence
-   Supervisor override
-   Exception reason
-   Required constraints

### Backend/API

-   Check-in
-   Check-out
-   GPS handling
-   Geo-fence validation
-   Supervisor override
-   Exception handling

### Swagger

Plan every API test.

### Frontend/UI/UX

Plan the mobile-first attendance experience.

### Security

Plan authentication/authorization and GPS/data protection where
required.

### Testing/E2E

Cover the documented attendance journey and realistic failures.

Do not add unrelated attendance features.

------------------------------------------------------------------------

# 48. PHASE 3 --- DAILY WORK & MATERIAL UPDATE

Use only the documented requirements.

Cover:

-   Activity selection
-   Quantities
-   Cable runs
-   Cable length
-   Cameras/devices
-   Drilling
-   Mounting
-   Testing
-   Commissioning
-   Work photographs
-   Material consumption/purchase
-   Item
-   Quantity
-   Amount
-   Bill image
-   Submission before check-out

Break every item into:

``` text
DB
Backend
API
Swagger
Frontend
UI/UX
Security
Testing
E2E
```

------------------------------------------------------------------------

# 49. PHASE 4 --- SUPERVISOR VERIFICATION

Use only requirements stated for supervisor verification.

Cover:

-   Consolidated attendance
-   Work quantities
-   Photos
-   Purchases
-   Approve
-   Reject
-   Return for correction
-   Approved-record protection
-   Remarks
-   Audit/change history

Break every item into task-level:

``` text
DB
Backend
API
Swagger
Frontend
UI/UX
Security
Testing
E2E
```

------------------------------------------------------------------------

# 50. PHASE 5 --- DIRECTOR DASHBOARD & INVOICING

Use only documented requirements.

Cover:

### Dashboard

-   Date-wise manpower
-   Working hours
-   Client/site progress
-   Cable metres
-   Devices installed
-   Employee productivity
-   Material cost
-   Approval status

### Filters

-   Date
-   Client
-   Site
-   Employee
-   Supervisor

### Reports

-   Attendance
-   Approved work
-   Materials
-   Productivity
-   Weekly payment
-   Client/site invoice summary

### Outputs

-   Excel
-   PDF

### Weekly payment/invoice

Use only the calculation basis and rate information explicitly defined
by the source document.

Break all work into:

``` text
DB
Backend
API
Swagger
Frontend
UI/UX
Security
Testing
E2E
```

------------------------------------------------------------------------

# 51. CROSS-PHASE DEPENDENCIES

Create:

``` text
docs/00-phase-0/phase-dependencies.md
```

Show:

``` text
Phase 0
  ↓
Phase 1 Employee Onboarding
  ↓
Phase 2 Attendance
  ↓
Phase 3 Daily Work & Material
  ↓
Phase 4 Supervisor Verification
  ↓
Phase 5 Director Dashboard & Invoicing
```

Also document feature-level dependencies:

``` text
Employee
   ↓
Attendance
   ↓
Daily Work
   ↓
Supervisor Verification
   ↓
Approved Data
   ↓
Director Dashboard
   ↓
Weekly Payment / Invoice
```

Only include dependencies actually supported by the requirements or
necessary technical dependencies.

------------------------------------------------------------------------

# 52. TESTING STRATEGY

Create:

``` text
docs/00-phase-0/testing-strategy.md
```

Every requirement phase must include:

### Database testing

-   Constraints
-   Relationships
-   Invalid data
-   State integrity

### Backend testing

-   Services
-   Business rules
-   Validation
-   Authorization

### API testing

-   Endpoint behavior
-   HTTP responses
-   Error handling

### Swagger testing

-   Manual API workflows

### Frontend testing

-   User flows
-   Validation
-   Responsive behavior
-   Accessibility-critical interactions

### End-to-end testing

Test complete documented workflows.

------------------------------------------------------------------------

# 53. DEFINITION OF DONE

Create:

``` text
docs/00-phase-0/definition-of-done.md
```

Every future feature should be considered complete only when appropriate
items below pass:

``` text
□ Requirement understood
□ Requirement traceability updated
□ Acceptance criteria defined
□ Database changes designed
□ Database constraints defined
□ API contracts defined
□ UI/UX designed
□ Responsive behavior defined
□ Accessibility considered
□ Permissions defined
□ Implementation completed
□ Validation completed
□ Unit/service tests completed
□ Integration tests completed
□ Swagger verification completed
□ Critical E2E journey completed
□ Security review completed where applicable
□ Error states handled
□ Loading/empty states handled
□ Logging/observability handled
□ Documentation updated
□ Dead-code/refactor review completed
□ Git changes grouped atomically
□ Reusable project pattern extracted where appropriate
```

------------------------------------------------------------------------

# 54. PHASE 0 MUST NOT IMPLEMENT BUSINESS FEATURES

During Phase 0:

## DO

-   Create documentation.
-   Create architecture.
-   Create task plans.
-   Create database strategy.
-   Create backend strategy.
-   Create frontend strategy.
-   Create UI/UX standards.
-   Create API standards.
-   Create Swagger standards.
-   Create security standards.
-   Create debugging standards.
-   Create E2E standards.
-   Create cleanup/refactoring standards.
-   Create Git standards.
-   Create skill/knowledge standards.
-   Create requirement traceability.
-   Create phase dependencies.
-   Create developer implementation instructions.
-   Create repository AI governance files such as `CLAUDE.md` and
    `.ai/`.

## DO NOT

-   Implement full Employee Onboarding.
-   Implement full Attendance.
-   Implement full Daily Work.
-   Implement full Supervisor Verification.
-   Implement full Director Dashboard.
-   Implement unrelated features.
-   Create speculative business functionality.

------------------------------------------------------------------------

# 55. PHASE 0 QUALITY AUDIT

Before declaring Phase 0 complete, perform all of the following.

## Requirement coverage

Confirm every requirement in the source document appears in exactly one
primary implementation phase unless the same requirement legitimately
spans multiple phases, in which case the traceability document must
explain the relationship.

## Scope control

Confirm no unrelated business feature has been introduced.

## Database coverage

Confirm every requirement has identified required database changes or
explicitly states no database change is required.

## Backend coverage

Confirm every requirement has identified required Python/API work or
explicitly states no backend change is required.

## Swagger coverage

Confirm every API has a Swagger testing plan.

## Frontend coverage

Confirm every user-facing requirement has a frontend/UI/UX
implementation plan.

## Accessibility coverage

Confirm relevant screens include accessibility considerations.

## Security coverage

Confirm security-sensitive features have security requirements and
verification plans.

## Testing coverage

Confirm every requirement has testing tasks.

## E2E coverage

Confirm critical business journeys are identified.

## Engineering coverage

Confirm the repository contains the AI engineering governance structure.

## Dependency coverage

Confirm phases can be implemented in the planned order.

## Consistency audit

Cross-check:

``` text
Requirements
↔ Traceability
↔ Architecture
↔ DB Plan
↔ Backend Plan
↔ API Plan
↔ Swagger Plan
↔ Frontend Plan
↔ UX Plan
↔ Security Plan
↔ Testing Plan
↔ E2E Plan
↔ Task List
```

No document should contradict another.

## Requirement triangulation coverage

Confirm the following triangulation audit items pass:

-   [ ] Formal requirements fully analyzed
-   [ ] All supplied reference photos analyzed
-   [ ] Onsite Teams reference application analyzed
-   [ ] Photo → Onsite comparison completed
-   [ ] Triangulated requirements (Level 2) identified
-   [ ] Missing requirements promoted where justified
-   [ ] Photo-only requirements (Level 3A) documented
-   [ ] Onsite-only capabilities (Level 3B) separated
-   [ ] Conflicts between sources documented
-   [ ] No unsupported requirements invented
-   [ ] Requirement IDs assigned to all discoveries
-   [ ] Requirement discovery matrix maintained
-   [ ] DB impact mapped for all triangulated requirements
-   [ ] Backend/API impact mapped
-   [ ] Frontend impact mapped
-   [ ] Roles/permissions mapped
-   [ ] Reporting/notification/audit impact mapped where applicable
-   [ ] Triangulated requirements assigned to implementation phases
-   [ ] Acceptance criteria defined for all promoted requirements
-   [ ] Open business decisions documented
-   [ ] No triangulated requirement left silently unaddressed

Phase 0 MUST NOT be declared complete if a high-confidence triangulated
requirement has been discovered but not incorporated into the master
requirement baseline or explicitly resolved.

------------------------------------------------------------------------

# 56. FINAL OUTPUT REQUIRED FROM PHASE 0

At the end of this task, the repository must contain the complete
documentation package plus the engineering governance system.

The final high-level structure should look like:

``` text
PROJECT/
│
├── .ai/
│   ├── rules/
│   ├── workflows/
│   ├── prompts/
│   ├── checklists/
│   └── skills/
│
├── docs/
│   ├── 00-phase-0/
│   ├── 01-employee-onboarding-login/
│   ├── 02-daily-attendance/
│   ├── 03-daily-work-material/
│   ├── 04-supervisor-verification/
│   └── 05-director-dashboard-invoicing/
│
├── CLAUDE.md
└── existing application source
```

Do not restructure the existing application source unnecessarily during
Phase 0.

If the repository already has engineering conventions or tooling,
inspect them and preserve compatible existing conventions rather than
replacing them blindly.

------------------------------------------------------------------------

# 57. FINAL EXECUTION BEHAVIOR FOR ANTIGRAVITY / CLAUDE

Before editing anything:

1.  Inspect the repository.
2.  Identify the existing application structure.
3.  Identify existing documentation.
4.  Identify existing `CLAUDE.md`, `.ai`, CI, test, lint, formatting,
    and package configuration.
5.  Read the supplied requirements document.
6.  Compare the repository with the requirements.
7.  Determine what is already present.
8.  Do not overwrite useful existing standards without reason.
9.  Create or update the Phase 0 documentation and engineering
    governance system.
10. Keep a clear record of assumptions and technical decisions.

Do not immediately start writing application feature code.

If the repository is empty, establish the documentation/governance
structure first.

If the repository already contains application code, Phase 0 may inspect
it for architectural facts and compatibility, but must not begin
implementing the future business phases.

------------------------------------------------------------------------

# 58. CHANGE CONTROL

When future implementation begins:

-   Requirements are controlled.
-   Architecture changes must be documented.
-   Database changes require migrations.
-   API changes require contract updates.
-   UI changes must respect the design system.
-   Security-sensitive changes require security review.
-   Critical workflow changes require E2E coverage.
-   Refactors must not be mixed with unrelated feature work.
-   Breaking changes must be explicitly identified.
-   Documentation must stay synchronized with implementation.

If a new requirement appears later, do not silently insert it into an
existing phase.

Instead:

``` text
New Requirement
    ↓
Requirement Review
    ↓
Impact Analysis
    ↓
Phase Assignment
    ↓
Documentation Update
    ↓
Approval
    ↓
Implementation
```

------------------------------------------------------------------------

# 59. CORE PRINCIPLE

The project must not be developed as:

> Prompt → Generate Code → Hope It Works.

It must be developed as:

``` text
Understand
   ↓
Specify
   ↓
Design
   ↓
Plan
   ↓
Implement
   ↓
Verify
   ↓
Secure
   ↓
Test
   ↓
Clean
   ↓
Document
   ↓
Commit
   ↓
Learn
```

The eight engineering practices represented by the project guidance are
mandatory parts of the future development lifecycle:

1.  Full PRD / feature specification
2.  Full UI/UX design brief
3.  Security gap audit
4.  Evidence-first debugging
5.  Playwright E2E testing
6.  Controlled cleanup/refactoring
7.  Atomic Conventional Git commits
8.  Reusable project skills/knowledge

They are not separate optional prompts. They are part of the project's
engineering operating model.

------------------------------------------------------------------------

# 60. FINAL INSTRUCTION

Do not treat this task as:

> "Build the Workforce Management application."

Treat it as:

> **"Build the complete master engineering documentation and repository
> governance system that will allow another developer or AI engineer to
> build the Workforce Management application phase-by-phase without
> ambiguity while maintaining enterprise-grade engineering, security,
> UX, testing, and coding standards."**

The documentation must be:

-   Requirement-driven
-   Task-wise
-   Database-first
-   Python/FastAPI-based
-   Swagger-driven for API testing
-   React/TypeScript-based for frontend planning
-   UI/UX-driven before frontend implementation
-   Accessibility-aware
-   Security-aware
-   E2E-testable
-   Dependency-aware
-   Traceable
-   Maintainable
-   Consistent
-   Strictly scoped to confirmed and triangulated requirements
-   Suitable for long-running AI-assisted development

The final result should allow a developer to open:

``` text
docs/01-employee-onboarding-login/task-list.md
```

and start implementing Phase 1 task-by-task.

Then:

``` text
docs/02-daily-attendance/task-list.md
```

and implement Phase 2.

Then continue through the remaining phases.

**Do not implement those business phases now.**

Phase 0 is complete when:

1.  The entire implementation roadmap exists.
2.  Every requirement is traceable.
3.  Every phase has DB + Backend/API + Swagger + Frontend + UI/UX +
    Security + Testing + E2E task breakdown.
4.  The engineering operating system is defined.
5.  `CLAUDE.md` and `.ai/` governance are established.
6.  The documentation is internally consistent.
7.  The security, debugging, testing, cleanup, Git, and skill workflows
    are defined.
8.  No untraceable business feature has been introduced.
9.  All technical assumptions are explicitly identified.
10. The final scope audit passes.
11. All supplied reference photos have been analyzed.
12. Onsite Teams reference application has been analyzed for
    triangulation.
13. Photo + Onsite triangulated requirements have been incorporated
    into the master requirement baseline or explicitly resolved.
14. The requirement discovery matrix is maintained and complete.
15. No high-confidence triangulated requirement has been silently
    left unaddressed.

Before finishing, perform a final scope audit against:

-   the supplied requirements document
-   the supplied reference photos
-   the Onsite Teams reference comparison

and remove anything that cannot be traced back to a confirmed source
or justified as necessary technical infrastructure.

**Phase 0 must produce the blueprint and engineering system. Future
phases produce the application.**

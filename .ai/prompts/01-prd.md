# Prompt 01 — Product Requirement / Feature Specification

Use this prompt when specifying a new feature or requirement for implementation.

## Instructions

Before implementing a feature, create a specification covering:

1. **Requirement Reference**: Which requirement from the source document does this implement?
2. **Actors**: Which user roles interact with this feature?
3. **User Story**: As a <role>, I want to <action>, so that <benefit>.
4. **Acceptance Criteria**: Specific, testable criteria for completeness.
5. **Business Rules**: All business rules that apply to this feature.
6. **Data Requirements**: What data is created, read, updated, or deleted?
7. **State Transitions**: What states does the data go through?
8. **Validation Rules**: What input validation is required?
9. **Error Cases**: What can go wrong and how should it be handled?
10. **Dependencies**: What must exist before this feature can be built?
11. **Out of Scope**: What is explicitly NOT included.

## Template

```markdown
# Feature: <Name>

## Requirement Reference
- Source: <requirement ID or section>
- Phase: <phase number>

## Actors
- <Role 1>: <what they do>
- <Role 2>: <what they do>

## User Stories
- As a <role>, I want to <action>, so that <benefit>.

## Acceptance Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>

## Business Rules
1. <Rule 1>
2. <Rule 2>

## Data Model
- Entity: <name>
- Fields: <list>
- Relationships: <list>

## State Transitions
<current state> → <action> → <new state>

## Validation Rules
- <field>: <rule>

## Error Cases
- <scenario>: <expected behavior>

## Dependencies
- <dependency>

## Out of Scope
- <exclusion>
```

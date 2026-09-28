# Prompt 02 — UI/UX Design Brief

Use this prompt before implementing any user-facing feature.

## Principle
> Design before code. Every screen must be designed before it is built.

## Instructions

Create a design brief covering:

1. **Design Principles**: 3+ concrete principles for this screen/feature.
2. **Visual Direction**: Patterns to use, patterns to avoid.
3. **Design Tokens**: Reference the project design tokens (`docs/00-phase-0/ui-ux-architecture.md`).
4. **Screen Purpose**: What the user accomplishes on this screen.
5. **User Flow**: Step-by-step interaction flow.
6. **Layout**: Information hierarchy, component placement.
7. **Components**: Which design system components are used.
8. **Screen States**: Loading, empty, error, success, validation, permission.
9. **Responsive Behavior**: Mobile (primary), tablet, desktop.
10. **Accessibility**: Keyboard nav, focus order, labels, contrast, touch targets.

## Template

```markdown
# UI/UX Design Brief: <Screen/Feature Name>

## Design Principles
1. <Principle 1> — <justification>
2. <Principle 2> — <justification>
3. <Principle 3> — <justification>

## Visual Direction
- Use: <patterns, layouts, interactions>
- Avoid: <anti-patterns>

## Screen Purpose
<What the user accomplishes>

## Primary User
<Role>

## Entry Points
<How the user gets to this screen>

## User Flow
1. User arrives at screen → sees <initial state>
2. User <action> → <result>
3. ...

## Layout

### Mobile (Primary)
<Description of mobile layout — component stacking, action placement>

### Tablet
<Adaptations for tablet>

### Desktop
<Adaptations for desktop>

## Component Inventory
| Component | Purpose | Design Token References |
|-----------|---------|----------------------|
| <component> | <purpose> | <tokens used> |

## Screen States
| State | Trigger | Display |
|-------|---------|---------|
| Loading | Data fetching | <skeleton/spinner> |
| Empty | No data | <message + guidance> |
| Error | API failure | <error message + retry> |
| Success | Mutation complete | <confirmation feedback> |
| Validation | Invalid input | <field-level errors> |
| Permission | Unauthorized | <access denied message> |

## Accessibility
- Keyboard navigation: <tab order>
- Focus management: <focus behavior>
- Labels: <form labels>
- Touch targets: <minimum sizes>
- Screen reader: <announcements>
```

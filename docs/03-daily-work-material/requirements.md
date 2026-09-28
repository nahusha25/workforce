# Phase 3 — Daily Work & Material Update — Requirements

## Source Reference
- Page 3: "Daily Work & Material Update"
- Business Rules: REQ-BR-003, REQ-BR-005
- Master Data: REQ-MD-003 (Work Orders), REQ-MD-004 (Activities & Materials)

## Requirement Scope
Enable employees to select activities, enter work quantities, upload progress photos, and record material consumption/purchases. Work must be submitted before check-out.

## Actors
| Role | Actions |
|------|---------|
| Employee | Enter work quantities, upload photos, record materials, submit |
| Administrator | Manage activity and material master data |

## Functional Requirements
| ID | Requirement |
|----|-------------|
| REQ-WRK-001 | Select activity type |
| REQ-WRK-002 | Enter cable run quantities |
| REQ-WRK-003 | Enter cable length in metres |
| REQ-WRK-004 | Enter cameras/devices installed |
| REQ-WRK-005 | Enter drilling quantities |
| REQ-WRK-006 | Enter mounting quantities |
| REQ-WRK-007 | Enter testing quantities |
| REQ-WRK-008 | Enter commissioning quantities |
| REQ-WRK-009 | Upload work-progress photos |
| REQ-WRK-010 | Record material: item |
| REQ-WRK-011 | Record material: quantity |
| REQ-WRK-012 | Record material: amount |
| REQ-WRK-013 | Record material: bill image |
| REQ-MD-003 | Project/Work Order master data |
| REQ-MD-004 | Activity & Material master data |

## Business Rules
1. Work must be submitted **before check-out** (REQ-BR-003).
2. Work entries are linked to the active attendance record for the day.
3. Employee must be checked in to create work entries.
4. All quantity fields are non-negative.
5. High-value material purchases are flagged (amount > purchase_approval_limit from material master) (REQ-BR-005).
6. Exception flagged: attendance without work, work without attendance, no photograph (REQ-BR-005).
7. Status flow: draft → submitted → (supervisor verification in Phase 4).
8. Draft save supported for weak-network tolerance.

## State Transitions
```
(no entry) → Create → draft
draft → Edit → draft
draft → Submit → submitted
submitted → (Phase 4: approve/reject/return)
correction_required → Edit → draft → Submit → submitted
```

## Validation Rules
| Field | Rule |
|-------|------|
| activity_id | Required, FK to activities master |
| cable_runs | Integer, ≥ 0 |
| cable_length_metres | Numeric, ≥ 0 |
| devices_installed | Integer, ≥ 0 |
| drilling_qty | Integer, ≥ 0 |
| mounting_qty | Integer, ≥ 0 |
| testing_qty | Integer, ≥ 0 |
| commissioning_qty | Integer, ≥ 0 |
| photo | Image file (jpeg/png/webp), max 10MB, compressed client-side |
| material item_name | Required text |
| material quantity | Numeric, > 0 |
| material amount | Numeric, ≥ 0 |
| bill image | Image file (jpeg/png/webp), max 10MB |

## Acceptance Criteria
- [ ] Employee can select activity from master list
- [ ] Employee can enter all quantity types (cable, devices, drilling, mounting, testing, commissioning)
- [ ] Employee can upload work progress photos (camera-first)
- [ ] Photos are auto-compressed before upload
- [ ] Employee can record material purchases with item, quantity, amount
- [ ] Employee can upload bill images
- [ ] High-value purchases flagged automatically
- [ ] Work can be saved as draft
- [ ] Work must be submitted before check-out
- [ ] Non-negative quantities enforced
- [ ] Work entry linked to active attendance record

## Dependencies
- Phase 2 (attendance records must exist)
- Activity & Material master data created
- File storage service configured

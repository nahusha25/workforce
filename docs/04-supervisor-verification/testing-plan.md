# Phase 4 — Testing Plan

## Database Tests
- [ ] verification_records: action CHECK constraint
- [ ] verification_records: FK constraints

## Service Tests
- [ ] Summary aggregates correct data per employee/date
- [ ] Approve changes status to approved
- [ ] Reject requires remarks, changes status
- [ ] Return requires remarks, changes status to correction_required
- [ ] Approved records become read-only
- [ ] Audit entries created for all actions
- [ ] Supervisor can only access assigned employees

## API Tests
- [ ] GET /summary — supervisor sees assigned only → 200
- [ ] GET /summary — employee access → 403
- [ ] POST /approve — valid → 200
- [ ] POST /approve — already approved → 409
- [ ] POST /reject — with remarks → 200
- [ ] POST /reject — without remarks → 422
- [ ] POST /return — with remarks → 200
- [ ] POST /return — without remarks → 422
- [ ] POST /approve — non-supervisor → 403

## E2E Tests
- [ ] E2E-J10: Supervisor approves entry
- [ ] E2E-J11: Supervisor rejects with remarks
- [ ] E2E-J12: Supervisor returns for correction

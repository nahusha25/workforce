# Phase 2 — Testing Plan

## Database Tests
- [ ] UNIQUE(employee_id, date) — duplicate check-in rejected
- [ ] CHECK(check_out_time > check_in_time) — invalid times rejected
- [ ] CHECK(status IN allowed values) — invalid status rejected
- [ ] FK employee_id — invalid employee rejected
- [ ] FK site_id — invalid site rejected

## Service Tests
- [ ] Geo-fence calculation (haversine) — within radius returns true
- [ ] Geo-fence calculation — outside radius returns false
- [ ] Check-in creates record with server timestamp
- [ ] Check-in rejects duplicate for same day
- [ ] Check-in validates site assignment
- [ ] Check-out updates record with server timestamp
- [ ] Check-out rejects when no check-in exists
- [ ] Supervisor override records override_by and reason
- [ ] Exception flags generated for out-of-location

## API Tests
- [ ] POST /check-in — valid → 201
- [ ] POST /check-in — duplicate → 409
- [ ] POST /check-in — no assignment → 403
- [ ] POST /check-in — outside geo-fence → 422
- [ ] POST /check-out — valid → 200
- [ ] POST /check-out — no check-in → 404
- [ ] POST /override — supervisor with reason → 200
- [ ] POST /override — missing reason → 422
- [ ] POST /override — non-supervisor → 403
- [ ] GET /attendance — employee sees own only
- [ ] GET /attendance — supervisor sees assigned only

## E2E Tests
- [ ] E2E-J03: Check-in with GPS → geo-fence pass → success
- [ ] E2E-J04: Check-in outside geo-fence → supervisor override → success
- [ ] E2E-J05: Check-out after work submission

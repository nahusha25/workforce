# Phase 2 — Frontend Plan

## Pages

### 2.1 Attendance Page (Employee)
- Large "CHECK IN" button (full-width, 80px height, primary green)
- GPS status indicator (acquiring / acquired / failed)
- Auto-displayed: Employee name, date, assigned site
- After check-in: shows check-in time, "CHECK OUT" button replaces check-in
- Status display: checked-in / checked-out
- Warning if outside geo-fence (before check-in attempt)

### 2.2 Supervisor Override (Modal)
- Triggered when employee check-in fails geo-fence
- Override request sent to supervisor
- Supervisor sees: employee name, site, distance from site, GPS map
- Mandatory reason text field
- "Override" / "Deny" buttons

## Components
| Component | Purpose |
|-----------|---------|
| CheckInButton | Large one-touch check-in with loading state |
| CheckOutButton | Large one-touch check-out with loading state |
| GpsIndicator | Shows GPS acquisition status (icon + text) |
| AttendanceStatus | Shows current attendance state for today |
| GeofenceWarning | Displays distance and geo-fence violation |
| OverrideForm | Supervisor override with reason input |

## Hooks
| Hook | Purpose |
|------|---------|
| useGeolocation | Browser Geolocation API wrapper with error handling |
| useAttendance | Today's attendance state, check-in/out actions |

## Mobile-First Design
- Check-in/out buttons fill the bottom 40% of mobile screen
- GPS indicator at top
- Auto-filled info (employee, date, site) in a compact card at top
- No scrolling needed for the primary actions

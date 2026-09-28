i-Workforce Management Web Application

Developer-Ready Functional Requirements | Mobile Responsive | Maximum Five Pages

# Users and Access

- Employee / Field Worker – daily attendance, work quantity, photographs and material updates.

- Supervisor – verifies attendance and work completed; approves, rejects or returns entries for correction.

- Director / Management – views manpower, site progress, productivity, cost and weekly invoice/payment summaries.

- Administrator – maintains employees, rates, clients, sites, work orders, activities, materials and user access.

# Proposed Five Application Pages

# Business Rules and Workflow

- Employees can check in, check out and submit work only for assigned client sites.

- GPS date/time cannot be edited by employees. Corrections require supervisor remarks and must remain in the audit trail.

- Daily work should be submitted before check-out. The system sends all submissions to the supervisor’s end-of-day verification queue.

- Only supervisor-approved attendance and work quantities are considered for productivity, employee payment and invoice generation.

- Flag exceptions such as missing check-out, attendance without work, work without attendance, no photograph, out-of-location attendance and high-value material purchases.

- Approved records become read-only. Reopening requires authorised approval and complete change history.

# Master Data and Configuration

# Usability Requirements

- Mobile-first responsive design or Progressive Web App; suitable for low-cost Android phones and mobile browsers.

- Large buttons, clear icons, numeric keypad, auto-filled employee/date/site, and not more than three or four actions per screen.

- English interface with optional Kannada/Hindi labels; short text or voice-to-text for remarks.

- Camera-first photo upload with automatic image compression; draft save and weak-network/offline tolerance.

- Simple status indicators: Draft, Submitted, Approved, Rejected and Correction Required.

# Technical, Security and Reporting

- Role-based access for Employee, Supervisor, Director and Administrator; secure OTP authentication and session management.

- Cloud-hosted central database, encrypted transmission, secure image storage, daily backup and complete activity audit logs.

- Recommended stack: React/Vue frontend; Node.js, Python or .NET backend; PostgreSQL database; SMS OTP and map/GPS services.

- Dashboard filters: date, client, site, employee and supervisor. Reports: attendance, approved work, materials, productivity, weekly payment and client/site invoice summary.

- Provide APIs for future integration with payroll, accounting, ERP, WhatsApp notifications and client billing systems.

| Objective: Build a simple web application for managing field workers engaged in CCTV installation, cable laying, device installation and site-related material purchases. The solution must minimise typing and use large buttons, dropdowns, numeric inputs and camera uploads so that construction labourers can use it easily. |
| --- |

| # | Page | Core Functional Requirements |
| --- | --- | --- |
| 1 | Employee Onboarding & Login | Register using name and mobile number; OTP-based login without passwords. Capture employee ID, trade/role, agreed rate, supervisor and assigned client site. Keep the session active securely to avoid daily OTP entry. |
| 2 | Daily Attendance | One-touch Check-In and Check-Out. Automatically capture employee, date/time, client/site and GPS location. Validate against the configured site geo-fence, with supervisor override and mandatory reason for exceptions. |
| 3 | Daily Work & Material Update | Select activity and enter only quantities: cable runs, cable length in metres, cameras/devices installed, drilling, mounting, testing or commissioning. Upload work-progress photos. Record material consumed or purchased with item, quantity, amount and bill image. |
| 4 | Supervisor Verification | Consolidate all attendance, work quantities, photos and purchases by employee and site at end of day. Supervisor can Approve, Reject or Return for Correction. Any change to approved quantities requires remarks and an audit trail. |
| 5 | Director Dashboard & Invoicing | Show date-wise manpower, working hours, client/site progress, cable metres, devices installed, employee productivity, material cost and approval status. Generate weekly employee payment/invoice based on approved work or attendance and configured rates; export to Excel/PDF. |

| Employee Master Employee name, mobile, ID, trade/role, supervisor, daily/weekly/piece rate and active status. | Client & Site Master Client, site name/address, GPS coordinates, permitted radius and site supervisor. |
| --- | --- |
| Project / Work Order Order number, site, start/end dates, scope, target quantities and billing basis. |  |
|  | Activity & Material Master Activity type, unit of measure, approved rate, cable/device categories, tools and purchase approval limit. |

| Phase 1 Priority: Employee Onboarding → Attendance → Daily Work Capture → Supervisor Approval → Director Dashboard → Weekly Invoice / Payment Statement |
| --- |


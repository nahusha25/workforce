# Phase 3 — Daily Work & Material Update — Task List

## Database Tasks

```
Task ID: DB-010
Task: Create work_orders table
Layer: Database
Requirement Reference: REQ-MD-003
Purpose: Store project/work order master data with site linkage and target quantities
Description: Create work_orders table with order_number (UNIQUE), FK→projects, FK→sites, start/end dates, scope text, target_quantities (JSONB), billing_basis, status CHECK, is_active, timestamps.
Dependencies: DB-005 (clients), projects table (from canonical ERD)
Implementation Details: Alembic migration. CHECK(end_date IS NULL OR end_date >= start_date). CHECK(status IN ('draft','open','in_progress','completed','closed')). CHECK(billing_basis IN ('per_metre','per_device','lump_sum')). Indexes on project_id, site_id, status.
Expected Output: Migration file, work_orders table created
Validation: Valid work order creates; invalid status rejected; date constraint enforced; duplicate order_number rejected
Acceptance Criteria: Work orders persistable with all constraints enforced
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-011
Task: Create activities table
Layer: Database
Requirement Reference: REQ-MD-004
Purpose: Activity type master data (cable laying, device installation, etc.)
Description: Create activities table with name, unit_of_measure, approved_rate (NUMERIC(12,2) CHECK >= 0), category, is_active, timestamps.
Dependencies: None (standalone master data)
Implementation Details: Alembic migration. CHECK(approved_rate >= 0). category values: cable, device, drilling, mounting, testing, commissioning.
Expected Output: Migration file, activities table created
Validation: Valid activity creates; negative rate rejected
Acceptance Criteria: Activities table exists with rate constraint
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-012
Task: Create materials table
Layer: Database
Requirement Reference: REQ-MD-004
Purpose: Material master data with purchase approval limit for high-value flagging
Description: Create materials table with name, unit_of_measure, category, purchase_approval_limit (NUMERIC(12,2) CHECK >= 0), is_active, timestamps.
Dependencies: None (standalone master data)
Implementation Details: Alembic migration. CHECK(purchase_approval_limit >= 0). category values: cable, device, tool, consumable.
Expected Output: Migration file, materials table created
Validation: Valid material creates; negative approval limit rejected
Acceptance Criteria: Materials table exists with approval limit support
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-013
Task: Create daily_work_entries table
Status: COMPLETE
Layer: Database
Requirement Reference: REQ-WRK-001 to REQ-WRK-008
Purpose: Store daily work quantities linked to attendance records and activities
Description: Create daily_work_entries with FK→attendance_records, FK→employees, FK→sites, FK→activities, FK→work_orders (nullable), date, cable_runs (INTEGER DEFAULT 0 CHECK >= 0), cable_length_metres (NUMERIC(10,2) DEFAULT 0 CHECK >= 0), devices_installed (INTEGER DEFAULT 0 CHECK >= 0), drilling_qty, mounting_qty, testing_qty, commissioning_qty (all INTEGER DEFAULT 0 CHECK >= 0), status CHECK, remarks, timestamps.
Dependencies: DB-009 (attendance_records), DB-011 (activities), DB-010 (work_orders)
Implementation Details: Alembic migration. CHECK(status IN ('draft','submitted','approved','rejected','correction_required')). Indexes on attendance_record_id, employee_id+date, status.
Expected Output: Migration file, daily_work_entries table created
Validation: Valid entry creates; negative quantities rejected; invalid status rejected; FK constraints enforced
Acceptance Criteria: Work entries persistable with all quantity constraints and status lifecycle
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-014
Task: Create work_photos table
Status: COMPLETE
Layer: Database
Requirement Reference: REQ-WRK-009
Purpose: Store work progress photo metadata linked to work entries
Description: Create work_photos with FK→daily_work_entries, image_url (TEXT NOT NULL), thumbnail_url (TEXT), file_size_bytes (INTEGER CHECK >= 0), uploaded_at (TIMESTAMPTZ DEFAULT NOW).
Dependencies: DB-013 (daily_work_entries)
Implementation Details: Alembic migration. FK constraint with CASCADE delete when work entry deleted. Index on daily_work_entry_id.
Expected Output: Migration file, work_photos table created
Validation: Photo record creates with valid FK; orphan photo rejected
Acceptance Criteria: Work photos linked to work entries
Definition of Done: Migration exists, constraints verified, tests pass
```

```
Task ID: DB-015
Task: Create material_transactions table
Layer: Database
Requirement Reference: REQ-WRK-010 to REQ-WRK-013
Purpose: Record material consumption and purchases with high-value flagging
Description: Create material_transactions with FK→daily_work_entries, FK→materials (nullable), FK→sites, transaction_type CHECK ('consumed','purchased'), item_name (VARCHAR(200) NOT NULL), quantity (NUMERIC(10,2) CHECK > 0), amount (NUMERIC(12,2) CHECK >= 0), bill_image_url (TEXT nullable), is_high_value (BOOLEAN DEFAULT false), status CHECK, timestamps.
Dependencies: DB-013 (daily_work_entries), DB-012 (materials)
Implementation Details: Alembic migration. CHECK(transaction_type IN ('consumed','purchased')). CHECK(status IN ('draft','submitted','approved','rejected','correction_required')). CHECK(quantity > 0). CHECK(amount >= 0). Indexes on daily_work_entry_id, status.
Expected Output: Migration file, material_transactions table created
Validation: Valid transaction creates; zero quantity rejected; negative amount rejected; invalid type rejected
Acceptance Criteria: Material transactions persistable with full constraint enforcement
Definition of Done: Migration exists, constraints verified, tests pass
```

## Backend Tasks

```
Task ID: BE-016
Task: Create file storage service abstraction
Layer: Backend / Shared
Requirement Reference: REQ-WRK-009, REQ-WRK-013, REQ-SEC-003
Purpose: Provide a unified interface for secure file upload, storage, and signed URL generation
Description: Implement shared/file_storage.py with upload_file(file, path) → url, get_signed_url(path) → url, delete_file(path). Support local filesystem for development and S3-compatible storage for production.
Dependencies: None
Implementation Details: Abstract base class FileStorageService. LocalFileStorage for dev. S3FileStorage for production. Configuration via environment variables. Max file size enforcement (10MB). MIME type validation (image/jpeg, image/png, image/webp).
Expected Output: FileStorageService abstraction with local and S3 implementations
Validation: File upload and retrieval works in local mode; invalid types rejected; oversized files rejected
Acceptance Criteria: Files can be uploaded and retrieved via signed URLs
Definition of Done: Unit tests pass, both implementations work, configuration documented
```

```
Task ID: BE-017
Task: Create daily work service
Layer: Backend / Daily Work Module
Requirement Reference: REQ-WRK-001 to REQ-WRK-008, REQ-BR-003
Purpose: Business logic for creating, updating, and submitting daily work entries
Description: Implement modules/daily_work/service.py with create_work_entry, update_work_entry, submit_work_entry, list_work_entries, get_work_entry.
Dependencies: DB-013, BE-014 (attendance service for active check-in validation)
Implementation Details: Validate active attendance session before creation. Enforce status constraints (only edit in draft/correction_required). Submit changes status to 'submitted' and adds to supervisor verification queue. Link work entry to today's attendance record. Validate activity_id FK. Enforce non-negative quantities.
Expected Output: Working daily work service with all business rules
Validation: Cannot create without active attendance; cannot edit submitted entries; submit changes status
Acceptance Criteria: Full work entry lifecycle managed with business rule enforcement
Definition of Done: Service tests pass, business rules verified, >90% service coverage
```

```
Task ID: BE-018
Task: Create photo upload service
Layer: Backend / Daily Work Module
Requirement Reference: REQ-WRK-009
Purpose: Handle work progress photo upload with validation, thumbnail generation, and secure storage
Description: Implement photo upload functionality within daily work module. Validate file type (jpeg/png/webp) and size (max 10MB). Generate thumbnail. Store via FileStorageService. Create work_photos record.
Dependencies: BE-016 (file storage), DB-014 (work_photos)
Implementation Details: Accept multipart/form-data. Validate MIME type server-side (not just extension). Generate thumbnail (200px max dimension) using Pillow. Store original and thumbnail. Return photo record with signed URLs.
Expected Output: Photo upload endpoint handler with validation, storage, and thumbnail
Validation: Valid image uploads successfully; invalid types rejected; oversized files rejected; thumbnail generated
Acceptance Criteria: Photos uploaded, stored securely, thumbnails available, linked to work entry
Definition of Done: Unit tests pass, upload/retrieval verified, file validation confirmed
```

```
Task ID: BE-019
Task: Create material purchase service
Layer: Backend / Daily Work Module
Requirement Reference: REQ-WRK-010 to REQ-WRK-013, REQ-BR-005
Purpose: Business logic for recording material consumption/purchases with high-value flagging
Description: Implement material transaction functionality. Validate material_id FK (if provided). Auto-calculate is_high_value flag by comparing amount against material.purchase_approval_limit. Support bill image upload.
Dependencies: DB-015, DB-012, BE-016
Implementation Details: Create material transaction linked to daily work entry. is_high_value = (amount > material.purchase_approval_limit). If material_id is null, allow free-text item_name. Bill image upload uses FileStorageService.
Expected Output: Working material transaction service with high-value flagging
Validation: High-value flag triggers correctly; quantity > 0 enforced; amount >= 0 enforced
Acceptance Criteria: Materials recorded with automatic high-value detection
Definition of Done: Service tests pass, high-value logic verified
```

```
Task ID: BE-020
Task: Create daily work API endpoints
Layer: Backend / API
Requirement Reference: REQ-WRK-001 to REQ-WRK-013
Purpose: REST endpoints for daily work entry, photo upload, and material recording
Description: Implement api/v1/daily_work.py with endpoints WRK-001 through WRK-009: create, list, get, update, submit work entries; upload photos; add/update materials; upload bill images.
Dependencies: BE-017, BE-018, BE-019
Implementation Details: Thin route handlers with role-based authorization. Employee role required for all operations. Employee can only access own work entries. Supervisor can view assigned employees' entries (read-only).
Expected Output: 9 daily work API endpoints with RBAC
Validation: All Swagger test cases pass; RBAC enforced; business rules applied
Acceptance Criteria: Complete daily work API functional with proper authorization
Definition of Done: API tests pass, Swagger verified, RBAC confirmed
```

```
Task ID: BE-021
Task: Create admin API for work orders, activities, materials
Layer: Backend / API
Requirement Reference: REQ-MD-003, REQ-MD-004
Purpose: Administrator CRUD endpoints for master data management
Description: Implement admin endpoints for work_orders, activities, and materials: create, list, get, update, toggle active status.
Dependencies: DB-010, DB-011, DB-012
Implementation Details: Administrator role required. Standard CRUD pattern. Soft delete via is_active flag. Validate unique constraints (order_number). Support filtering and pagination.
Expected Output: 9 admin CRUD endpoints (3 entities × create/list/get + update/toggle)
Validation: Admin role enforced; CRUD operations work; unique constraints respected
Acceptance Criteria: Admin can manage work orders, activities, and materials
Definition of Done: API tests pass, Swagger verified, admin role confirmed
```

```
Task ID: BE-022
Task: Add pre-checkout validation
Layer: Backend / Attendance Module (Phase 2 extension)
Requirement Reference: REQ-BR-003
Purpose: Check that work has been submitted before allowing checkout
Description: Extend the check-out endpoint to verify whether the employee has submitted work for the current attendance session. If work entries exist in draft status, return a warning (or block, pending business decision).
Dependencies: BE-014 (attendance service), BE-017 (daily work service)
Implementation Details: During checkout, query daily_work_entries for the current attendance_record_id where status='draft'. If found, include a warning in the response. Business decision pending: warn vs block.
Expected Output: Pre-checkout validation integrated into check-out flow
Validation: Warning returned when unsubmitted work exists; checkout allowed when all work submitted
Acceptance Criteria: System enforces pre-checkout work submission rule (REQ-BR-003)
Definition of Done: Integration test passes, warning/block behaviour matches business decision
```

## Swagger Tasks

```
Task ID: SWG-003
Task: Execute Phase 3 Swagger test plan
Layer: Swagger
Requirement Reference: All Phase 3 requirements
Purpose: Manual API verification of all Phase 3 endpoints via Swagger UI
Description: Execute all test cases defined in swagger-test-plan.md for WRK-001 through WRK-009 and ADM-007 through ADM-015.
Dependencies: BE-020, BE-021
Implementation Details: Use Swagger UI at /api/docs. Test each endpoint with valid and invalid inputs. Verify status codes, response bodies, error messages, and business rule enforcement.
Expected Output: All Swagger test cases executed and passing
Validation: Every test case in the swagger test plan has a recorded result
Acceptance Criteria: All endpoints behave as specified in the backend API plan
Definition of Done: All test cases executed, results documented, no critical failures
```

## Frontend Tasks

```
Task ID: FE-010
Task: Create work entry page with activity dropdown and numeric fields
Layer: Frontend
Requirement Reference: REQ-WRK-001 to REQ-WRK-008, REQ-UX-002
Purpose: Mobile-first work entry form with activity selection and quantity fields
Description: Build a responsive work entry page with: activity dropdown (populated from activities API), numeric input fields for cable_runs, cable_length_metres, devices_installed, drilling_qty, mounting_qty, testing_qty, commissioning_qty. Show only relevant fields based on selected activity category. Large input areas suitable for construction workers.
Dependencies: FE-002 (app shell), BE-020 (daily work APIs)
Implementation Details: inputMode="numeric" for all quantity fields. Auto-fill employee/site/date (read-only). Status indicator (draft/submitted). Only show quantity fields relevant to the selected activity's category.
Expected Output: Working work entry page with activity selection and quantities
Validation: Form submits correctly; numeric validation works; responsive on mobile; activity-based field visibility
Acceptance Criteria: Employee can select activity and enter all required quantities on mobile
Definition of Done: Page works on mobile, responsive, accessible, field validation complete
```

```
Task ID: FE-011
Task: Create photo capture component with camera-first and compression
Layer: Frontend
Requirement Reference: REQ-WRK-009, REQ-UX-004
Purpose: Camera-first photo upload with automatic client-side compression
Description: Build a reusable photo capture component that opens the device camera by default (capture="environment"), compresses the image client-side to ~500KB target, shows a preview, and uploads to the work entry photos endpoint.
Dependencies: FE-001 (design system)
Implementation Details: Use <input type="file" accept="image/*" capture="environment">. Client-side compression using canvas API or browser-image-compression library. Show upload progress. Support multiple photos per work entry. Preview gallery with delete option.
Expected Output: Photo capture component with compression and preview gallery
Validation: Camera opens on mobile; compression reduces file size; upload succeeds; preview displays
Acceptance Criteria: Employee can take and upload compressed work progress photos
Definition of Done: Works on Android mobile browsers, compression verified, gallery functional
```

```
Task ID: FE-012
Task: Create material entry form with bill image upload
Layer: Frontend
Requirement Reference: REQ-WRK-010 to REQ-WRK-013
Purpose: Form for recording material purchases/consumption with bill image attachment
Description: Build material entry form with: material selection (dropdown from materials API or free text), transaction_type toggle (consumed/purchased), quantity (numeric), amount (currency), bill image capture/upload. Support multiple material entries per work session.
Dependencies: FE-011 (photo component reuse), BE-020 (material APIs)
Implementation Details: Material dropdown with search. Free-text fallback for unlisted materials. Amount field with currency formatting. Reuse photo component for bill image. List view showing all materials added for the day.
Expected Output: Material entry form with bill image support
Validation: Material recorded; bill image uploads; high-value indicator shown; multiple entries supported
Acceptance Criteria: Employee can record material purchases with item, quantity, amount, and bill image
Definition of Done: Form functional, bill image capture works, responsive on mobile
```

```
Task ID: FE-013
Task: Implement draft save functionality
Layer: Frontend
Requirement Reference: REQ-UX-004
Purpose: Auto-save work entries as draft for weak-network tolerance
Description: Implement draft save mechanism: auto-save form data to local state and API at intervals, persist to localStorage for offline resilience, restore draft on page revisit.
Dependencies: FE-010, FE-012
Implementation Details: Debounced auto-save (every 30 seconds or on field blur). Save to localStorage immediately, sync to API when online. Show "Draft saved" indicator. Restore from localStorage if API call fails.
Expected Output: Draft save with offline resilience
Validation: Data persists across page refreshes; syncs when online; draft status indicator works
Acceptance Criteria: Employee's work is not lost due to network issues
Definition of Done: Draft save verified on slow/offline connections, data restoration confirmed
```

```
Task ID: FE-014
Task: Add submit flow with pre-checkout check
Layer: Frontend
Requirement Reference: REQ-BR-003
Purpose: Work submission flow that integrates with pre-checkout validation
Description: Build submit button on work entry page that changes status from draft to submitted. Show confirmation dialog. After submission, display submitted status and make form read-only. Integrate with checkout page to show warning if unsubmitted work exists.
Dependencies: FE-010, FE-009 (attendance page)
Implementation Details: Submit button with confirmation modal. Status change animation. Read-only mode for submitted entries. On attendance page, check for unsubmitted work before check-out and display warning.
Expected Output: Submit flow with checkout integration
Validation: Submit changes status; form becomes read-only; checkout shows warning for unsubmitted work
Acceptance Criteria: Work submission flow complete; pre-checkout warning functional
Definition of Done: Submit flow tested, checkout integration verified, status indicators correct
```

```
Task ID: FE-015
Task: Create admin pages for activities and materials management
Layer: Frontend
Requirement Reference: REQ-MD-003, REQ-MD-004
Purpose: Admin interface for managing work orders, activities, and materials master data
Description: Build admin management screens for: (1) work orders — create/edit/list with project/site selection, dates, scope, targets; (2) activities — create/edit/list with name, unit, rate, category; (3) materials — create/edit/list with name, unit, category, approval limit. All with search, pagination, and active status toggle.
Dependencies: FE-002 (app shell, admin layout), BE-021 (admin APIs)
Implementation Details: Reusable admin table component with sorting, filtering, pagination. Modal forms for create/edit. Confirmation for deactivation. Data validation matching backend rules.
Expected Output: Three admin management pages (work orders, activities, materials)
Validation: CRUD operations work for all three entities; validation matches backend; responsive
Acceptance Criteria: Administrator can manage all Phase 3 master data
Definition of Done: Pages functional, admin role enforced, responsive, accessible
```

## Testing Tasks

```
Task ID: TEST-006
Task: Database constraint tests for Phase 3 tables
Layer: Testing
Requirement Reference: All Phase 3 database requirements
Purpose: Verify all CHECK, FK, UNIQUE, and NOT NULL constraints on Phase 3 tables
Description: Write tests for: (1) work_orders — unique order_number, date constraint, status CHECK, billing_basis CHECK; (2) activities — rate >= 0; (3) materials — approval_limit >= 0; (4) daily_work_entries — all quantity >= 0, status CHECK, FK constraints; (5) work_photos — FK cascade; (6) material_transactions — quantity > 0, amount >= 0, transaction_type CHECK, status CHECK.
Dependencies: DB-010 through DB-015
Implementation Details: pytest with database fixtures. Test valid inserts, constraint violations, FK integrity, and cascade behaviour.
Expected Output: Comprehensive database constraint test suite for all 6 tables
Validation: All constraints enforced as specified in database-plan.md
Acceptance Criteria: Every constraint in the database plan has a corresponding test
Definition of Done: All tests pass, constraint coverage complete
```

```
Task ID: TEST-007
Task: Service tests for work entry, photo upload, material recording
Layer: Testing
Requirement Reference: REQ-WRK-001 to REQ-WRK-013, REQ-BR-003, REQ-BR-005
Purpose: Unit/integration tests for Phase 3 service layer business logic
Description: Test: (1) work entry creation requires active attendance; (2) status lifecycle (draft → submitted); (3) cannot edit submitted entries; (4) pre-checkout validation; (5) photo upload validation (type, size); (6) material high-value flagging calculation; (7) quantity validation.
Dependencies: BE-017, BE-018, BE-019
Implementation Details: pytest with mocked repositories. Test happy paths and all business rule violations.
Expected Output: Service test suite covering all Phase 3 business rules
Validation: >90% coverage on service layer; all business rules have test cases
Acceptance Criteria: All business rules verified through tests
Definition of Done: Tests pass, coverage target met, business rules confirmed
```

```
Task ID: TEST-008
Task: API integration tests for all Phase 3 endpoints
Layer: Testing
Requirement Reference: All Phase 3 API requirements
Purpose: Integration tests for all Phase 3 REST endpoints
Description: Test all endpoints (WRK-001 to WRK-009, ADM-007 to ADM-015) with: valid requests, invalid requests, RBAC enforcement, status code verification, response body validation.
Dependencies: BE-020, BE-021
Implementation Details: pytest with httpx AsyncClient. Test each endpoint with authenticated and unauthenticated requests, correct and incorrect roles, valid and invalid payloads.
Expected Output: API integration test suite for all Phase 3 endpoints
Validation: All endpoints return correct status codes and response bodies
Acceptance Criteria: Every API endpoint has integration tests for success and failure cases
Definition of Done: All API tests pass, RBAC verified, error responses confirmed
```

## E2E Tasks

```
Task ID: E2E-004
Status: [DONE]
Task: E2E tests for work entry, photo upload, material, and submission journeys
Layer: E2E
Requirement Reference: REQ-WRK-001 to REQ-WRK-013, REQ-BR-003
Purpose: End-to-end Playwright tests for the complete daily work workflow and cross-day checkout
Description: Test journeys:
  - E2E-J06: Full daily work multi-activity capture journey (authenticated employee -> active check-in verification -> add line items with auto-derived UOM badges -> auto-save draft -> attach photo -> record material transaction -> submit confirmation modal review -> post-submission locked read-only state).
  - E2E-J07: Cross-day checkout scenario (unclosed attendance session from prior day can check out cleanly without "No active check-in found for today" error, and handles pre-checkout warning modal).
Dependencies: All Phase 3 implementation complete
Implementation Details: Playwright suite in frontend/e2e/daily_work.spec.ts running on mobile viewport (Pixel 5 emulation). Automated database seeding via backend/e2e_seed.py.
Expected Output: E2E test files covering critical Phase 3 journeys
Validation: 2/2 tests passing reliably.
Acceptance Criteria: Complete work entry -> photo -> material -> submission flow and cross-day checkout verified end-to-end
Definition of Done: E2E tests pass reliably, clean seeding, zero flakiness.
```

## Security Tasks

```
Task ID: SEC-003
Status: [DONE]
Task: Security review of file uploads, storage, and data isolation
Layer: Security
Requirement Reference: REQ-SEC-003, REQ-WRK-009, REQ-WRK-013
Purpose: Security audit of Phase 3 file handling and data access controls
Description: Comprehensive audit of file upload/storage layer covering:
  1. Magic Byte MIME Validation: Pure-Python detect_mime_type_from_bytes inspecting binary signatures (JPEG, PNG, WEBP), strictly rejecting spoofed file extensions.
  2. Size Limits: Strict 10MB limit enforced across file_storage.py, API endpoint route handlers, and database CHECK constraints; 0-byte uploads rejected.
  3. Path Traversal Protection: Strict path sanitization via sanitize_storage_path and base_dir containment validation; files stored using server-generated UUIDs and server-controlled directory paths (photos/{employee_id}/{date}/{entry_id}/{photo_id}.{ext}).
  4. Access Control & IDOR: Direct ownership checks in WorkPhotoService and MaterialTransactionService ensuring Employee X cannot upload, delete, or list Employee Y's files; no unrestricted static directory mounts; S3 signed URL expiration.
  5. Multi-Tenant IDOR Integration Suite: Verified in test_daily_work.py (test_daily_work_file_upload_and_idor_access_control) proving Employee B is strictly blocked (HTTP 404/403) from uploading photos, viewing photos, deleting photos, cross-injecting foreign photo IDs, or modifying materials/bills on Employee A's work entries.
  6. Dev File-Serving Resolution: Resolved Vite dev-server SPA fallback root cause where /uploads requests were returning index.html with HTTP 200, masking unserved files; configured Vite dev-server proxy to route /uploads to FastAPI backend.
Dependencies: All Phase 3 implementation complete
Expected Output: Security audit report verifying MIME, size, path traversal, IDOR access control enforcement, and static file delivery
Validation: Comprehensive pytest test suites (test_file_storage.py, test_photo_service.py, test_daily_work.py) passing.
Acceptance Criteria: Phase 3 passes security review with zero high/critical vulnerabilities.
Definition of Done: Audit complete, findings and fixes verified in active codebase.
```

## Documentation Tasks

```
Task ID: DOC-003
Status: [DONE]
Task: Update Phase 3 documentation after implementation
Layer: Documentation
Requirement Reference: All Phase 3 requirements
Purpose: Ensure Phase 3 documentation matches actual implementation
Description: Reviewed and updated all docs in docs/03-daily-work-material/:
  - database-plan.md: Realigned daily_work_entries schema (idempotency_key, quantity, uom, status, work_date) and canonical material_transactions table replacing legacy material_usage.
  - backend-api-plan.md: Realigned WRK-001 through WRK-004 for single-activity line items and unclosed attendance session lookup (check_out_time IS NULL).
  - frontend-plan.md: Updated for multi-activity line-item UI architecture, upfront session check banner, and submission confirmation modal.
  - ui-ux-plan.md: Updated screen wireframes and interaction flows reflecting multi-activity line items and accordion attachments.
  - security-plan.md: Completed security checklist, recorded IDOR audit findings, and logged S3 backlog item.
  - testing-plan.md: Synced database, service, API, and E2E test checklists with implemented test suites.
  - task-list.md: Synced all Phase 3 tasks, marked closeout complete, and logged storage backlog item.
Dependencies: All Phase 3 tasks complete
Expected Output: Updated Phase 3 documentation matching implementation
Validation: Documentation accurately reflects the implemented system
Acceptance Criteria: No documentation contradicts implementation
Definition of Done: All Phase 3 docs reviewed, synchronized, and closed.
```

## Backlog Tasks

```
Task ID: BE-016B
Status: [BACKLOG]
Task: Exercise S3FileStorage path against real or mocked S3-compatible endpoint
Layer: Backend / Infrastructure
Requirement Reference: REQ-SEC-003, REQ-NFR-004
Purpose: Validate production storage backend (STORAGE_BACKEND=s3) before deployment
Description: S3FileStorage implementation has been built and unit-tested in isolation, but end-to-end flows during development have run exclusively against LocalFileStorage. To prevent silent production storage failures analogous to the local SPA fallback issue discovered during dev testing:
  1. Set up integration test suite with LocalStack, moto, or MinIO simulating AWS S3.
  2. Test photo and bill uploads, thumbnail generation, pre-signed URL generation, retrieval, and deletion with STORAGE_BACKEND=s3.
  3. Validate signed URL expiration and bucket access policies.
Dependencies: BE-016
Expected Output: Verified S3FileStorage integration test suite passing against S3-compatible mock/service
Validation: Integration test running against S3 backend passes all upload/read/delete assertions
Acceptance Criteria: Zero regressions or silent handling errors when STORAGE_BACKEND=s3
Definition of Done: S3 test suite automated and passing in CI/CD pipeline prior to production release
```

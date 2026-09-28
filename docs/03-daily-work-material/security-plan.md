# Phase 3 — Daily Work & Material — Security Plan

> Reference: [`docs/00-phase-0/security-architecture.md`](../00-phase-0/security-architecture.md)

---

## Threat Surface

| Area | Risk Level | Description |
|------|-----------|-------------|
| File upload injection | **CRITICAL** | Malicious files disguised as images could execute code |
| Storage access | **HIGH** | Direct access to storage bucket would bypass authorisation |
| Data isolation | **HIGH** | Employees should only access own work entries |
| Status tampering | **HIGH** | Bypassing draft→submitted flow could inject unapproved data |
| High-value flag bypass | **MEDIUM** | Client-set flag could hide expensive purchases |
| Large file abuse | **MEDIUM** | Uploading excessively large files to exhaust storage |

---

## Security Controls

### File Upload Security
| Control | Implementation |
|---------|---------------|
| MIME type validation | Server-side check of file magic bytes (not just extension). Allowed: `image/jpeg`, `image/png`, `image/webp` |
| File extension validation | Must match `.jpg`, `.jpeg`, `.png`, `.webp` |
| File size limit | 10MB maximum per file, enforced server-side |
| Content scanning | Read first few bytes to verify image header (magic bytes) |
| Filename sanitisation | Generate UUID-based filenames, never use client-provided names |
| Path traversal prevention | No user-controlled path components in storage keys |

### Storage Security
| Control | Implementation |
|---------|---------------|
| No direct public access | Storage bucket is private, no public listing |
| Signed URLs | Pre-signed URLs with 1-hour expiry for viewing |
| Separate upload/download | Upload via multipart to API, download via signed URL |
| Cleanup | Orphaned files cleaned up on entry deletion (cascade) |

### Authorization (RBAC)
| Endpoint | Employee | Supervisor | Director | Admin |
|----------|----------|-----------|----------|-------|
| Create work entry (WRK-001) | ✅ Own | ❌ | ❌ | ❌ |
| List work entries (WRK-002) | ✅ Own | ✅ Assigned | ✅ All | ✅ All |
| Get work detail (WRK-003) | ✅ Own | ✅ Assigned | ✅ All | ✅ All |
| Update work entry (WRK-004) | ✅ Own (draft/correction only) | ❌ | ❌ | ❌ |
| Submit work (WRK-005) | ✅ Own | ❌ | ❌ | ❌ |
| Upload photo (WRK-006) | ✅ Own (draft/correction only) | ❌ | ❌ | ❌ |
| Add material (WRK-007) | ✅ Own (draft/correction only) | ❌ | ❌ | ❌ |
| Update material (WRK-008) | ✅ Own (draft/correction only) | ❌ | ❌ | ❌ |
| Upload bill image (WRK-009) | ✅ Own (draft/correction only) | ❌ | ❌ | ❌ |
| Admin CRUD (ADM-007–015) | ❌ | ❌ | ❌ | ✅ |

### Status Enforcement
- Work entries editable ONLY in `draft` or `correction_required` status
- `submitted` entries are read-only to employee
- `approved` entries are read-only to all (Phase 4 protection)
- Status transitions enforced server-side: draft → submitted (only valid transition for employee)
- No direct status manipulation via API (status changes only through specific action endpoints)

### High-Value Flag Integrity
- `is_high_value` is computed server-side: `amount > materials.purchase_approval_limit`
- Flag cannot be set or overridden by client request
- Flag calculation happens on every create/update of material transaction
- Client-provided `is_high_value` field in request is ignored

### Data Isolation
- Employee can only create/modify/view own work entries (where employee_id = auth user's employee ID)
- Work entries linked to employee's attendance record (cannot reference another employee's attendance)
- Supervisor sees only assigned employees' work entries
- All isolation enforced server-side in repository/service layer

### Input Validation
| Input | Validation |
|-------|-----------|
| activity_id | UUID, FK exists and is_active=true |
| All quantities | Non-negative integers or numerics |
| material item_name | Required text, max 200 chars |
| material quantity | Numeric > 0 |
| material amount | Numeric >= 0 |
| Image files | MIME validated, <= 10MB, magic byte check |

### Audit Logging
All actions logged to audit_logs:
- Work entry: create, update, submit
- Photo: upload, delete
- Material: create, update
- Admin: activity/material/work order CRUD

---

## Security Verification Checklist (SEC-003 — Complete)

- [x] **File uploads reject non-image MIME types**: Verified with magic bytes inspection (`detect_mime_type_from_bytes`) rejecting spoofed extensions (e.g., .exe renamed to .jpg).
- [x] **Files > 10MB rejected**: Enforced in `file_storage.py`, `photo_service.py`, and API routes (`HTTP 413` / `422`).
- [x] **Storage bucket / local storage is not publicly browseable**: Local storage directory listing disabled; S3 uses private buckets.
- [x] **Signed URLs expire after 1 hour**: Pre-signed URLs generated with strict TTLs; local storage maps through secured endpoint/proxy.
- [x] **Employee cannot access other employees' work entries (IDOR)**: Direct employee ownership checks in repository and service layers prevent unauthorized access (`HTTP 404/403`).
- [x] **IDOR Photo Upload/Delete & Cross-Injection Blocked**: Verified via `test_daily_work_file_upload_and_idor_access_control` in `tests/api/test_daily_work.py` — Employee B cannot upload photos, list photos, or delete Employee A's photos, nor can Employee B cross-inject Employee A's photo ID into a delete request on their own entry.
- [x] **IDOR Material & Bill Isolation**: Employee B cannot add material transactions or upload bill images to Employee A's entry.
- [x] **Work entries only editable in draft/correction_required status**: Verified via lifecycle state machine tests in `test_service.py`.
- [x] **Submitted entries reject update attempts**: Status transitions locked upon submission (`HTTP 400 Bad Request`).
- [x] **is_high_value flag is server-calculated**: Verified that client-supplied flags are ignored and recalculated against `materials.purchase_approval_limit`.
- [x] **Admin CRUD requires administrator/director role**: Enforced via `require_role(UserRole.ADMINISTRATOR, UserRole.DIRECTOR)` on master data routes.
- [x] **All CRUD actions create audit log entries**: `audit_logs` records created on entry submission, photo changes, and material entries.
- [x] **No path traversal possible in file upload**: `sanitize_storage_path` strips traversal segments and asserts base directory containment.
- [x] **Filenames are UUID-based**: Client-provided filenames are discarded; server generates cryptographically unique UUIDs.
- [x] **Dev-Server Static File Serving Fix**: Vite dev-server SPA fallback was intercepting `/uploads` requests and returning `index.html` (status 200, MIME `text/html`), silently breaking photo rendering. Resolved by routing `/uploads` through Vite proxy to FastAPI backend in `vite.config.ts`.

---

## Storage Backlog Items

- [ ] **BE-016B**: Exercise `S3FileStorage` path (`STORAGE_BACKEND=s3`) against real or mocked S3-compatible endpoint (e.g., LocalStack, moto, or MinIO) before production deployment to verify pre-signed URLs, bucket upload, thumbnail storage, and deletion (preventing silent production storage failures analogous to dev SPA fallback).

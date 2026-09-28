# DB-014 — WORK_PHOTOS SCHEMA RECONCILIATION

## 1. Investigate the Business Requirement
**Why work photos are required:** Evidence of work progress and verification (REQ-WRK-009). Required for supervisor verification.
**Which entity they belong to:** `daily_work_entries` (representing a specific day's work on an activity by an employee).
**Whether one daily work entry can have multiple photos:** Yes, the API design (e.g. `POST /api/v1/daily-work/{id}/photos`) and payload design `"photos": [ ... ]` strongly implies a `1:N` relationship.
**Whether photos are required for submission/approval:** Yes, they act as verification (formal evidence).
**Whether photos are used as evidence for completed work:** Yes.
**Whether later phases depend on them:** Yes, Phase 4 (Supervisor Verification) relies on these photos to approve/reject work entries.

## 2. Verify the Proposed DB-014 Schema
The proposed fields `id`, `daily_work_entry_id`, `image_url`, `thumbnail_url`, `file_size_bytes`, `uploaded_at` perfectly align with the business intent (camera-first upload, thumbnail display in supervisor verification).

## 3. Relationship Analysis
The relationship `DAILY_WORK_ENTRIES 1:N WORK_PHOTOS` is correct. The photos strictly act as evidence for a *specific entry*. Adding redundant FKs to `employee` or `site` would violate the normalization of the model since a `daily_work_entry` uniquely identifies the employee, site, activity, and date.

## 4. CASCADE DELETE Analysis
**Analysis:** While it is standard practice to use `ON DELETE CASCADE` for tightly coupled child records, daily work entries form an audit log of evidence that impacts billing and employee payments. Once submitted/approved, they generally shouldn't be deleted, only superseded or corrected. However, for a `draft` entry, if the entry itself is discarded by the employee, the photos must be cleaned up to avoid orphaned records. Thus, database-level `CASCADE DELETE` is appropriate from a referential integrity standpoint, leaving the actual restriction of deletion to application-level authorization (preventing deletion of non-draft entries).

## 5. Storage Fields Analysis
- **`image_url`**: Correct.
- **`thumbnail_url`**: Correct, the supervisor UI plan explicitly lists `"thumbnail_url": "url"`.
- **`file_size_bytes`**: Constraining this to `>= 0` is highly recommended to prevent negative values, but nullable is fine.
- **`uploaded_at`**: Using a timezone-aware UTC default `now()` aligns with the project's standard auditing timestamp behavior.

## 6. Security / Data Integrity Analysis
- **Required:** file-size validation, URL validation, immutable upload timestamp.
- **Future:** original filename, MIME type, storage provider. The current DB-014 proposal provides exactly what's required without overengineering.

## 7. Canonical ERD Impact
`WORK_PHOTOS` is missing from `canonical-erd.md`. It must be added with fields:
- `id` (UUID PK)
- `daily_work_entry_id` (UUID FK)
- `image_url` (TEXT)
- `thumbnail_url` (TEXT)
- `file_size_bytes` (INTEGER)
- `uploaded_at` (TIMESTAMPTZ)
Cardinality: `DAILY_WORK_ENTRIES ||--o{ WORK_PHOTOS : has` (with Cascade Delete).

## 8. Phase 3 Database Plan Impact
Needs to be added to `docs/03-daily-work-material/database-plan.md` under the schema section.

## 9. Evidence Matrix

| Issue                 | Canonical ERD | Database Plan | DB-014   | Requirements/Code | Recommended Decision |
| --------------------- | ------------- | ------------- | -------- | ----------------- | -------------------- |
| `work_photos` table   | Missing       | Missing       | Required | REQ-WRK-009       | Add to schemas       |
| `daily_work_entry_id` | Missing       | Missing       | Required | DB-014 task list  | Include as FK        |
| `image_url`           | Missing       | Missing       | Required | API plans         | Include              |
| `thumbnail_url`       | Missing       | Missing       | Required | Phase 4 API plans | Include              |
| `file_size_bytes`     | Missing       | Missing       | Required | API plans         | Include              |
| `uploaded_at`         | Missing       | Missing       | Required | Standard auditing | Include              |
| CASCADE DELETE        | Missing       | Missing       | Required | Audit cleanup     | Include              |
| index                 | Missing       | Missing       | Required | Performance       | Include              |

## 10. Proposed Final Schema

**Table: `work_photos`**
- `id`: UUID (PK)
- `daily_work_entry_id`: UUID (FK to `daily_work_entries.id` ON DELETE CASCADE)
- `image_url`: TEXT (NOT NULL)
- `thumbnail_url`: TEXT (NULLABLE)
- `file_size_bytes`: INTEGER (NULLABLE, CHECK `>= 0`)
- `uploaded_at`: TIMESTAMP WITH TIME ZONE (NOT NULL, DEFAULT `now()`)

**Relationship:**
`DAILY_WORK_ENTRIES 1:N WORK_PHOTOS`

## 11. Decision

**B — DB-014 is an intentional Phase 3 refinement**
The missing table should be added to the canonical ERD and database plan. The feature is heavily documented in the requirements and API plans, confirming it is an intentional Phase 3 addition. The omission from the ERD and database plan was likely an oversight when transitioning from Phase 2.

## 12. Documentation Update

The following files should be updated before implementation:
* `docs/00-phase-0/canonical-erd.md`
* `docs/03-daily-work-material/database-plan.md`

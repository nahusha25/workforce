# Phase 5 — Director Dashboard & Invoicing — Security Plan

> Reference: [`docs/00-phase-0/security-architecture.md`](../00-phase-0/security-architecture.md)

---

## Threat Surface

| Area | Risk Level | Description |
|------|-----------|-------------|
| Unapproved Data Leakage | **HIGH** | Invoices/metrics including draft/submitted data |
| Unauthorised Access | **HIGH** | Employees viewing financial totals or invoices |
| Export File Storage | **MEDIUM** | Generated Excel/PDFs leaking if stored publicly |
| Rate Manipulation | **HIGH** | Bypassing correct rate-card calculations |

---

## Security Controls

### Authorization (RBAC)
- All `/api/v1/dashboard/*`, `/api/v1/reports/*`, and `/api/v1/invoices/*` endpoints require the **Director** or **Administrator** role.
- Employee or Supervisor tokens will return `403 Forbidden`.

### Data Integrity (REQ-BR-004)
- Aggregation queries in the `DashboardService` and `InvoiceService` MUST hardcode `status = 'approved'` in the `WHERE` clause.
- This ensures draft or rejected entries cannot inadvertently inflate invoicing or productivity metrics.

### Financial Calculation Integrity
- Invoices and employee payments are calculated entirely server-side.
- The API does not accept amount values from the client for invoice generation (only parameters like dates/sites).
- Rates are fetched securely from the `employee_rate_history` table (Phase 1 master data).

### Export File Security
- Generated Excel and PDF files are NOT saved to the public cloud storage bucket.
- They are generated in memory (or secure temporary files `tempfile.NamedTemporaryFile`) and streamed directly to the client via `StreamingResponse`.
- Files are cleaned up immediately after transmission.
- Filenames contain no PII (e.g., `attendance_report_202508.pdf`).

---

## Security Verification Checklist

- [ ] All Phase 5 endpoints require Director/Admin role (403 for others)
- [ ] Aggregation queries correctly exclude draft/submitted/rejected data
- [ ] Invoice generation relies solely on server-side rate calculations
- [ ] Export files are streamed and not accessible via public URL
- [ ] No API endpoint exists to manually override invoice totals (must adjust source data)

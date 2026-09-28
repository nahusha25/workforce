# Phase 5 — Director Dashboard & Invoicing — Backend API Plan

> All APIs use the `/api/v1` prefix.

---

## Dashboard APIs

### DSH-001: Get Metrics
- **Method**: GET
- **Endpoint**: `/api/v1/dashboard/metrics`
- **Query**: `date_from`, `date_to`, `site_id`
- **Response**: All 8 high-level metrics aggregated from approved data.
- **Auth**: Director

## Report APIs

### DSH-002 to DSH-007: Paginated Reports
All endpoints below support pagination (`page`, `page_size`) and filters (`date_from`, `date_to`, `site_id`, `client_id`, `employee_id`).
- **DSH-002**: `/api/v1/reports/attendance` (Approved attendance history)
- **DSH-003**: `/api/v1/reports/work` (Approved work quantities)
- **DSH-004**: `/api/v1/reports/materials` (Approved material usage/purchases)
- **DSH-005**: `/api/v1/reports/productivity` (Employee output/hours ratio)
- **DSH-006**: `/api/v1/reports/payment` (Weekly payment totals)
- **DSH-007**: `/api/v1/reports/invoice-summary` (Client/site aggregated totals)

### DSH-008: Export Report
- **Method**: GET
- **Endpoint**: `/api/v1/reports/{report_type}/export`
- **Query**: `format=xlsx|pdf` + all filters
- **Response**: StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet OR application/pdf)
- **Auth**: Director

---

## Invoice APIs

### DSH-009: Generate Invoice
- **Method**: POST
- **Endpoint**: `/api/v1/invoices/generate`
- **Request**:
  ```json
  {
    "client_id": "uuid",
    "site_id": "uuid (optional)",
    "period_start": "2025-08-01",
    "period_end": "2025-08-15"
  }
  ```
- **Response**: Generated invoice object (draft) with line items.
- **Logic**: Sums all APPROVED work and material entries matching criteria.

### DSH-010: List Invoices
- **Method**: GET
- **Endpoint**: `/api/v1/invoices`
- **Response**: Paginated list of generated invoices.

### DSH-011: Invoice Detail
- **Method**: GET
- **Endpoint**: `/api/v1/invoices/{id}`
- **Response**: Full invoice detail including line items.

---

## Planned Integration APIs (OpenAPI Docs Only)
These APIs will be defined in the OpenAPI schema but will return 501 Not Implemented.
1. Payroll system export (`GET /api/v1/integrations/payroll`)
2. Accounting system export (`GET /api/v1/integrations/accounting`)
3. WhatsApp webhook receiver (`POST /api/v1/integrations/whatsapp`)

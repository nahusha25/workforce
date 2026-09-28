# API Development Standard

## Base URL

All APIs use the prefix: `/api/v1`

## Conventions

### HTTP Methods
| Method | Use | Idempotent |
|--------|-----|------------|
| GET | Retrieve resource(s) | Yes |
| POST | Create resource or trigger action | No |
| PUT | Full resource update | Yes |
| PATCH | Partial resource update | Yes |
| DELETE | Remove resource | Yes |

### Response Structure

**Success (single resource)**:
```json
{
  "id": "uuid",
  "field": "value",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Success (list with pagination)**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

**Error**:
```json
{
  "error": {
    "code": "DESCRIPTIVE_ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

### Status Codes
| Code | Meaning | Use |
|------|---------|-----|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST creating a resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Malformed request syntax |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate resource or state conflict |
| 422 | Unprocessable Entity | Validation or business rule failure |
| 500 | Internal Server Error | Unhandled server error |

### Pagination
- Default page size: 20
- Maximum page size: 100
- Query parameters: `?page=1&page_size=20`
- Response includes: `total`, `page`, `page_size`, `pages`

### Filtering
- Query parameters for filters: `?date=2025-01-01&site_id=uuid&status=approved`
- Multiple values: `?status=approved&status=submitted`
- Date ranges: `?date_from=2025-01-01&date_to=2025-01-31`

### Sorting
- Query parameter: `?sort_by=created_at&sort_order=desc`
- Default: `created_at desc`

## API Inventory

### Authentication (Phase 1)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| AUTH-001 | POST | /api/v1/auth/otp/request | Request OTP for mobile number |
| AUTH-002 | POST | /api/v1/auth/otp/verify | Verify OTP and get tokens |
| AUTH-003 | POST | /api/v1/auth/refresh | Refresh access token |
| AUTH-004 | POST | /api/v1/auth/logout | Revoke session |

### Employee (Phase 1)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| EMP-001 | POST | /api/v1/employees | Register new employee |
| EMP-002 | GET | /api/v1/employees | List employees (admin/supervisor) |
| EMP-003 | GET | /api/v1/employees/{id} | Get employee details |
| EMP-004 | PUT | /api/v1/employees/{id} | Update employee profile |
| EMP-005 | GET | /api/v1/employees/me | Get current employee profile |
| EMP-006 | POST | /api/v1/employees/{id}/site-assignments | Assign employee to site |

### Attendance (Phase 2)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| ATT-001 | POST | /api/v1/attendance/check-in | Record check-in with GPS |
| ATT-002 | POST | /api/v1/attendance/check-out | Record check-out with GPS |
| ATT-003 | GET | /api/v1/attendance | List attendance records |
| ATT-004 | GET | /api/v1/attendance/{id} | Get attendance detail |
| ATT-005 | POST | /api/v1/attendance/{id}/override | Supervisor geo-fence override |

### Daily Work (Phase 3)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| WRK-001 | POST | /api/v1/daily-work | Create work entry |
| WRK-002 | GET | /api/v1/daily-work | List work entries |
| WRK-003 | GET | /api/v1/daily-work/{id} | Get work entry detail |
| WRK-004 | PUT | /api/v1/daily-work/{id} | Update work entry (draft/correction) |
| WRK-005 | POST | /api/v1/daily-work/{id}/submit | Submit work entry |
| WRK-006 | POST | /api/v1/daily-work/{id}/photos | Upload work photo |
| WRK-007 | POST | /api/v1/daily-work/{id}/materials | Add material purchase |
| WRK-008 | PUT | /api/v1/daily-work/{id}/materials/{mid} | Update material purchase |
| WRK-009 | POST | /api/v1/daily-work/{id}/materials/{mid}/bill | Upload bill image |

### Verification (Phase 4)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| VER-001 | GET | /api/v1/verification/summary | Get EOD verification summary |
| VER-002 | GET | /api/v1/verification/summary/{employee_id} | Get detail for one employee |
| VER-003 | POST | /api/v1/verification/{id}/approve | Approve entry |
| VER-004 | POST | /api/v1/verification/{id}/reject | Reject entry |
| VER-005 | POST | /api/v1/verification/{id}/return | Return for correction |

### Dashboard (Phase 5)
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| DSH-001 | GET | /api/v1/dashboard/metrics | Get dashboard metrics |
| DSH-002 | GET | /api/v1/reports/attendance | Attendance report |
| DSH-003 | GET | /api/v1/reports/work | Approved work report |
| DSH-004 | GET | /api/v1/reports/materials | Materials report |
| DSH-005 | GET | /api/v1/reports/productivity | Productivity report |
| DSH-006 | GET | /api/v1/reports/payment | Weekly payment report |
| DSH-007 | GET | /api/v1/reports/invoice-summary | Client/site invoice summary |
| DSH-008 | GET | /api/v1/reports/{type}/export | Export report (Excel/PDF) |
| DSH-009 | POST | /api/v1/invoices/generate | Generate weekly invoice |
| DSH-010 | GET | /api/v1/invoices | List invoices |
| DSH-011 | GET | /api/v1/invoices/{id} | Get invoice detail |

### Admin / Master Data
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| ADM-001 | POST | /api/v1/admin/clients | Create client |
| ADM-002 | GET | /api/v1/admin/clients | List clients |
| ADM-003 | PUT | /api/v1/admin/clients/{id} | Update client |
| ADM-004 | POST | /api/v1/admin/sites | Create site |
| ADM-005 | GET | /api/v1/admin/sites | List sites |
| ADM-006 | PUT | /api/v1/admin/sites/{id} | Update site |
| ADM-007 | POST | /api/v1/admin/work-orders | Create work order |
| ADM-008 | GET | /api/v1/admin/work-orders | List work orders |
| ADM-009 | PUT | /api/v1/admin/work-orders/{id} | Update work order |
| ADM-010 | POST | /api/v1/admin/activities | Create activity |
| ADM-011 | GET | /api/v1/admin/activities | List activities |
| ADM-012 | PUT | /api/v1/admin/activities/{id} | Update activity |
| ADM-013 | POST | /api/v1/admin/materials | Create material |
| ADM-014 | GET | /api/v1/admin/materials | List materials |
| ADM-015 | PUT | /api/v1/admin/materials/{id} | Update material |

### Utility
| API ID | Method | Endpoint | Purpose |
|--------|--------|----------|---------|
| UTL-001 | GET | /api/health | Health check |

## Authentication Behaviour

- All endpoints except AUTH-001, AUTH-002, and UTL-001 require a valid access token.
- Access token sent as: `Authorization: Bearer <token>`
- Token refresh via AUTH-003 uses httpOnly refresh token cookie.

## Authorization Behaviour

| Role | Access Pattern |
|------|---------------|
| Employee | Own data only (attendance, work, materials) |
| Supervisor | Assigned employees' data + verification actions |
| Director | All data (read) + dashboard + reports + invoicing |
| Administrator | Master data CRUD + employee management |

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assets,
    attendance,
    auth,
    client_payments,
    daily_work,
    dashboard,
    employee_payments,
    employees,
    inventory,
    invoices,
    payroll_settings,
    reports,
    verification,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(daily_work.router, prefix="/daily-work", tags=["daily-work"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(employee_payments.router, prefix="/employee-payments", tags=["employee-payments"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(client_payments.router, prefix="/client-payments", tags=["client-payments"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(payroll_settings.router, prefix="/payroll-settings/overtime", tags=["payroll-settings"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])




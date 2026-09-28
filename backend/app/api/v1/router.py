from fastapi import APIRouter

from app.api.v1 import admin, attendance, auth, daily_work, employees, verification

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(daily_work.router, prefix="/daily-work", tags=["daily-work"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])


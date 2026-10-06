import asyncio
import sys

# Fix: asyncpg is incompatible with Windows ProactorEventLoop (the default on
# Python 3.8+ on Windows). Force SelectorEventLoop to prevent
# ConnectionDoesNotExistError on every DB call.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.error_handlers import add_error_handlers

app = FastAPI(
    title="Workforce Management API",
    version="1.0.0",
    description="API for Workforce Management Web App"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data: https:; connect-src 'self' http: https: ws: wss:"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), geolocation=(self), microphone=()"
    return response

# Error handlers
add_error_handlers(app)

# Include API Router
app.include_router(api_router, prefix="/api/v1")

# Mount /uploads for local file storage serving (dev mode)
from pathlib import Path
from fastapi.staticfiles import StaticFiles

uploads_dir = Path("uploads").resolve()
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

@app.get("/api/health", tags=["utility"])
async def health_check():
    return {"status": "ok"}

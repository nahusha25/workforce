# i-Workforce Management Web Application

> Enterprise web platform for field worker operations, GPS-validated attendance, daily work & material logging, supervisor EOD verification, and director-level financial analytics.

---

## 🏗️ Architecture & Technology Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2 (Asyncio), PostGIS, PostgreSQL 15, Alembic migrations, Pydantic v2.
- **Frontend**: React 19, TypeScript, Vite, React Router v7, `@tanstack/react-query`, Recharts, Vanilla CSS Modules.
- **Database**: PostgreSQL 15 + PostGIS spatial extension (`postgis/postgis:15-3.3-alpine`) via Docker Compose.
- **Testing**:
  - Backend: `pytest`, `pytest-asyncio`, `httpx` (396 passed unit and integration tests).
  - Frontend: `vitest`, `@testing-library/react` (248 passed unit/component tests).
  - End-to-End: Playwright (`frontend/e2e/`).

```
+-------------------------------------------------------------+
|                     Frontend (React 19)                     |
|  Vite + React Router v7 + TanStack Query + CSS Modules      |
+-------------------------------------------------------------+
                              |
                     REST API / JSON (Axios)
                              |
                              v
+-------------------------------------------------------------+
|                    FastAPI Backend Monolith                 |
|  - Auth & RBAC (JWT + OTP)         - Attendance & GPS       |
|  - Daily Work & Material Logging    - Supervisor Verification|
|  - Director Dashboard & Analytics   - Excel/PDF Exporters    |
+-------------------------------------------------------------+
                              |
                    SQLAlchemy Async Engine
                              |
                              v
+-------------------------------------------------------------+
|               PostgreSQL 15 + PostGIS DB                   |
|         Tables, Check Constraints & Spatial Indices         |
+-------------------------------------------------------------+
```

---

## 🚀 Quickstart Guide for Developers

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/)
- [Python 3.11+](https://www.python.org/)
- [Node.js 18+](https://nodejs.org/)

---

### 1. Database Setup (Docker)

From the project root:
```bash
docker-compose up -d
```
This spins up PostgreSQL with the PostGIS extension on port `5432` with credentials:
- **User**: `postgres`
- **Password**: `localdevpassword`
- **Database**: `workforce_test`

---

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create environment configuration:
# On Windows:
copy ..\.env.example .env
# On macOS / Linux:
# cp ../.env.example .env

# Create and activate Python virtual environment:
python -m venv .venv

# Activate venv:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
# source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# Run database migrations:
alembic upgrade head

# Seed test users and sample verification data:
python seed_user.py
python dev_seed_verification.py

# Start FastAPI server:
uvicorn app.main:app --reload --port 8000
```

> **API Documentation:**
> - Interactive OpenAPI Docs: `http://localhost:8000/docs`
> - ReDoc: `http://localhost:8000/redoc`

---

### 3. Frontend Setup (React + Vite)

In a separate terminal:
```bash
cd frontend

# Install npm dependencies:
npm install

# Start Vite development server:
npm run dev
```

Open your browser at **`http://localhost:3000`**.

---

## 🔑 Test Accounts & Authentication

Authentication uses mobile number + OTP:
1. Enter the mobile number on the login screen.
2. Click **Send OTP**.
3. In local development, the OTP is saved to `backend/otp.txt` and printed in the backend console output.
4. Enter the 6-digit code to log in.

### Default Pre-Seeded Accounts:
| Role | Mobile Number | Purpose |
|---|---|---|
| **Administrator** | `+919999999999` | Full system access, master data, user onboarding, override re-open |
| **Director** | `+919999999999` | Financial dashboard, analytics, 6 reports, invoice generation, exports |
| **Supervisor** | `+917760443750` | EOD review queue, line-item approval/rejections, attendance overrides |
| **Field Worker** | `+917760443750` | Mobile attendance check-in/out, work quantity entry, photo uploads |

---

## 🧪 Running Automated Tests

### Backend Test Suite (396 tests)
```bash
cd backend
.venv\Scripts\activate
pytest -v
```

### Frontend Test Suite (248 tests)
```bash
cd frontend
npm test
```

### Playwright E2E Tests
```bash
cd frontend
npx playwright test
```

---

## 📂 Project Structure

```
workforce/
├── backend/
│   ├── alembic/              # Database version control & migrations (18+ migrations)
│   ├── app/
│   │   ├── api/v1/           # FastAPI REST routers (auth, attendance, verification, dashboard, etc.)
│   │   ├── core/             # Database session, config, security, exceptions, middleware
│   │   ├── models/           # SQLAlchemy ORM models (PostGIS spatial geometry, workforce, system)
│   │   ├── modules/          # Domain services (auth, attendance, daily_work, verification, dashboard)
│   │   └── shared/           # File storage, GPS calculation, SMS client
│   ├── tests/                # 396+ automated test cases
│   ├── requirements.txt      # Python dependencies
│   ├── seed_user.py          # User seed script
│   └── dev_seed_verification.py # Sample data seeder
├── frontend/
│   ├── src/
│   │   ├── api/              # Typed API clients (Axios)
│   │   ├── components/       # Reusable UI components, guards, layout, modals, charts
│   │   ├── context/          # Auth context and role state management
│   │   ├── hooks/            # Custom hooks (geolocation, countdown)
│   │   ├── pages/            # 11 application pages (Login, Dashboard, Verification, Work Entry, etc.)
│   │   └── routes/           # AppRoutes and role-based guards
│   ├── e2e/                  # Playwright end-to-end test specs
│   └── package.json          # Node dependencies & scripts
├── docs/                     # Specifications, plans, security audits & ERDs for Phases 1-5
│   ├── 01-employee-onboarding-login/
│   ├── 02-daily-attendance/
│   ├── 03-daily-work-material/
│   ├── 04-supervisor-verification/
│   └── 05-director-dashboard-invoicing/
├── docker-compose.yml        # PostgreSQL + PostGIS service
├── WORKFORCE_MANAGEMENT_ANALYSIS_AND_CHECKLIST.md # Full enterprise system audit & checklist
└── README.md
```

---

## 📖 System Specifications & Business Modules

For detailed architecture, requirements, and database diagrams:
- **Complete System Checklist**: [`WORKFORCE_MANAGEMENT_ANALYSIS_AND_CHECKLIST.md`](./WORKFORCE_MANAGEMENT_ANALYSIS_AND_CHECKLIST.md)
- **Phase 1 (Onboarding & Login)**: [`docs/01-employee-onboarding-login/`](./docs/01-employee-onboarding-login/)
- **Phase 2 (Attendance & GPS Geofencing)**: [`docs/02-daily-attendance/`](./docs/02-daily-attendance/)
- **Phase 3 (Daily Work & Material Updates)**: [`docs/03-daily-work-material/`](./docs/03-daily-work-material/)
- **Phase 4 (Supervisor EOD Verification)**: [`docs/04-supervisor-verification/`](./docs/04-supervisor-verification/)
- **Phase 5 (Director Dashboard & Reports)**: [`docs/05-director-dashboard-invoicing/`](./docs/05-director-dashboard-invoicing/)

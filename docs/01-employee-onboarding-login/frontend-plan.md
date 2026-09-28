# Phase 1 — Frontend Plan

## Tech Stack
React, strictly following the Phase 0 frontend architecture. No Next.js.

## Pages
1. **Login Page — Mobile Number Entry**: Mobile-first, large input, "Send OTP".
2. **Login Page — OTP Verification**: 6-digit input, timer, "Verify".
3. **Employee Management (Admin)**: List with filters.
4. **Employee Registration Form**: Includes fields for Name, Mobile, Trade, Rate Amount, **Role Assignment**, and Site Assignment.
5. **Client Management (Admin)**: List and creation forms.
6. **Project Management (Admin)**: List and creation forms (linked to clients).
7. **Site Management (Admin)**: List and creation forms with GPS (linked to projects).
8. **Employee Profile (Self/Admin)**: View profile, rate history (Admin only), and site assignments.

## Route Structure
- `/login` (Public)
- `/profile` (Auth)
- `/admin/employees` (Admin)
- `/admin/clients` (Admin)
- `/admin/projects` (Admin)
- `/admin/sites` (Admin)

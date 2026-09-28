# Frontend Rules — React / TypeScript

## Project Structure

```
frontend/
├── public/
│   ├── manifest.json          ← PWA manifest
│   └── icons/                 ← App icons
│
├── src/
│   ├── main.tsx               ← Application entry point
│   ├── App.tsx                ← Root component with routing
│   │
│   ├── api/                   ← API client layer
│   │   ├── client.ts          ← Axios/fetch wrapper, auth headers, error handling
│   │   ├── types.ts           ← Shared API types
│   │   ├── employee.ts        ← Employee API functions
│   │   ├── attendance.ts      ← Attendance API functions
│   │   ├── dailyWork.ts       ← Daily work API functions
│   │   ├── verification.ts    ← Verification API functions
│   │   ├── dashboard.ts       ← Dashboard API functions
│   │   └── admin.ts           ← Admin/master data API functions
│   │
│   ├── components/            ← Reusable UI components
│   │   ├── ui/                ← Design system primitives (Button, Input, Card, etc.)
│   │   ├── layout/            ← Shell, navigation, headers
│   │   ├── forms/             ← Form components, validation
│   │   ├── tables/            ← Data tables, pagination
│   │   ├── feedback/          ← Loading, error, empty states, notifications
│   │   └── common/            ← Shared composed components
│   │
│   ├── features/              ← Feature-specific pages/components
│   │   ├── employee/          ← Employee onboarding & login
│   │   ├── attendance/        ← Daily attendance
│   │   ├── dailyWork/         ← Daily work & material
│   │   ├── verification/      ← Supervisor verification
│   │   ├── dashboard/         ← Director dashboard
│   │   └── admin/             ← Master data management
│   │
│   ├── hooks/                 ← Custom React hooks
│   │   ├── useAuth.ts         ← Authentication state
│   │   ├── useApi.ts          ← Data fetching hooks
│   │   ├── useGeolocation.ts  ← GPS location
│   │   └── useCamera.ts       ← Camera/photo capture
│   │
│   ├── context/               ← React contexts
│   │   └── AuthContext.tsx     ← Authentication context
│   │
│   ├── utils/                 ← Utility functions
│   │   ├── formatters.ts      ← Date, number, currency formatting
│   │   ├── validators.ts      ← Client-side validation helpers
│   │   └── constants.ts       ← Application constants
│   │
│   ├── styles/                ← Global styles and design tokens
│   │   ├── tokens.css         ← CSS custom properties (design tokens)
│   │   ├── global.css         ← Global styles, resets
│   │   └── breakpoints.ts     ← Responsive breakpoint definitions
│   │
│   └── types/                 ← Shared TypeScript types
│       ├── employee.ts
│       ├── attendance.ts
│       ├── dailyWork.ts
│       └── common.ts
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Component Rules

### General
- One component per file.
- Component name matches filename: `EmployeeForm.tsx` → `EmployeeForm`.
- Prefer function components with hooks over class components.
- Keep components focused — split at ~150 lines.
- Co-locate component-specific styles, tests, and types.

### State Management
- Use `useState` for simple local state.
- Use `useReducer` for complex local state with multiple transitions.
- Use `useContext` for cross-component shared state (auth, theme).
- Avoid global state libraries unless complexity demands it.
- Do not duplicate server data in client state — use data-fetching hooks.

### Required States
Every data-dependent component must handle:
- **Loading** — spinner or skeleton
- **Error** — user-friendly error message with retry option
- **Empty** — meaningful empty state with guidance
- **Permission denied** — clear message if user lacks access
- **Success** — confirmation feedback for mutations

### Props
- Use TypeScript interfaces for all props.
- Destructure props in function parameters.
- Provide defaults for optional props.
- Document non-obvious props with JSDoc comments.

## API Integration Rules

- All API calls go through `src/api/client.ts`.
- The client automatically:
  - Attaches authentication headers
  - Handles token refresh
  - Normalizes error responses
  - Adds request correlation IDs
- API functions return typed responses.
- Use custom hooks for data fetching to handle loading/error states consistently.

## Form Rules

- Use controlled components for form inputs.
- Validate on blur and on submit.
- Show field-level validation errors immediately.
- Show form-level errors (API validation) prominently.
- Disable submit button during submission.
- Auto-fill known values (employee, date, site) per requirements.
- Use numeric keypad input mode for quantity fields.

## Routing Rules

- Use React Router (or equivalent).
- Protect routes with authentication guards.
- Protect routes with role-based authorization guards.
- Redirect unauthenticated users to login.
- Redirect unauthorized users to a "no access" page.
- Use lazy loading for route-level code splitting.

## Mobile-First Rules

- Design for mobile viewport first, enhance for tablet/desktop.
- Use CSS custom properties for breakpoints.
- Large touch targets (minimum 44×44px per WCAG).
- Maximum 3–4 primary actions per screen (per requirements).
- Numeric keypad for quantity inputs (`inputMode="numeric"`).
- Camera-first photo uploads (use `capture="environment"` attribute).

## Accessibility Rules

See also: `.ai/rules/accessibility-rules.md`

- All interactive elements must be keyboard accessible.
- All form fields must have associated labels.
- All images must have alt text.
- Use semantic HTML elements.
- Use ARIA attributes only where semantic HTML is insufficient.
- Maintain visible focus indicators.
- Support screen readers for dynamic content updates.

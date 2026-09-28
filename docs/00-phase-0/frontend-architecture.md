# Frontend Architecture

See also: `.ai/rules/frontend-rules.md` for detailed coding standards.

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 18+ | UI component library |
| Language | TypeScript (strict) | Type safety |
| Build | Vite | Fast dev server and build tool |
| Routing | React Router v6 | Client-side routing |
| Styling | CSS Modules + CSS Custom Properties | Scoped styles with design tokens |
| HTTP | Axios or fetch wrapper | API communication |
| E2E Testing | Playwright | Browser automation testing |
| Unit Testing | Vitest + React Testing Library | Component and logic testing |
| Linting | ESLint + Prettier | Code quality |

## Project Structure

See `.ai/rules/frontend-rules.md` for the full directory structure.

## Application Shell

```
┌──────────────────────────────────────┐
│  Header (role-based navigation)      │
├──────────────────────────────────────┤
│                                      │
│  Main Content Area                   │
│  (route-based page rendering)        │
│                                      │
├──────────────────────────────────────┤
│  Bottom Navigation (mobile)          │
│  or Sidebar (desktop)                │
└──────────────────────────────────────┘
```

## Routing

| Route | Page | Role(s) | Phase |
|-------|------|---------|-------|
| `/login` | OTP Login | Public | 1 |
| `/onboarding` | Employee Registration | Admin | 1 |
| `/attendance` | Daily Attendance | Employee | 2 |
| `/daily-work` | Work & Material Entry | Employee | 3 |
| `/verification` | Supervisor Verification | Supervisor | 4 |
| `/dashboard` | Director Dashboard | Director | 5 |
| `/admin/*` | Master Data Management | Administrator | 1–3 |

### Route Protection
- `AuthGuard` — redirects unauthenticated users to `/login`.
- `RoleGuard` — redirects unauthorized users to an access-denied page.
- Lazy loading for route-level code splitting.

## API Client

Centralized API client in `src/api/client.ts`:
- Base URL from environment config
- Automatic auth header attachment (Bearer token)
- Automatic token refresh on 401
- Request/response interceptors for error normalization
- Request correlation ID headers

## State Management

- **Authentication state**: React Context (`AuthContext`) — user, role, tokens.
- **Server data**: Custom hooks with data fetching (consider React Query / TanStack Query for caching).
- **Form state**: Local to form components (`useState` / `useReducer`).
- **No global state library** unless complexity demands it.

## Reusable Component Library

| Component | Purpose | Source |
|-----------|---------|-------|
| `Button` | Primary, secondary, danger actions — large touch targets | Design system |
| `Input` | Text, numeric (with `inputMode`), textarea | Design system |
| `Select` | Dropdown with search (activities, sites, etc.) | Design system |
| `Card` | Content container | Design system |
| `Table` | Data display with responsive stacking | Design system |
| `StatusBadge` | Draft, Submitted, Approved, Rejected, Correction Required | Design system |
| `LoadingSpinner` | Loading state indicator | Design system |
| `ErrorMessage` | Error state display with retry | Design system |
| `EmptyState` | No data state with guidance | Design system |
| `PhotoCapture` | Camera-first image capture with compression | Feature |
| `GpsIndicator` | GPS status and location display | Feature |
| `NumericKeypad` | Large-button numeric input for quantities | Feature |

## PWA / Offline Strategy

> Technical Implementation Decision: The requirements specify "Progressive Web App" and "weak-network/offline tolerance". This will be implemented progressively.

- **Phase 1**: Basic PWA manifest, service worker for app shell caching.
- **Phase 2–3**: Offline queue for attendance and work submissions — store in IndexedDB, sync when online.
- **Draft save**: Use localStorage/IndexedDB for in-progress forms.
- **Image upload**: Queue uploads for retry on weak network.

## Mobile-First Approach

### Breakpoints
| Name | Min-Width | Target |
|------|-----------|--------|
| `mobile` | 0px | Low-cost Android phones (default) |
| `tablet` | 768px | Tablets |
| `desktop` | 1024px | Desktop browsers |

### Mobile-Specific Patterns
- Bottom navigation bar for primary actions
- Full-width cards and buttons
- Stacked form layouts
- `inputMode="numeric"` for quantity fields
- Camera capture with `capture="environment"` attribute
- Swipe gestures for common actions (where appropriate)

## Internationalization (i18n)

Per requirements: "English interface with optional Kannada/Hindi labels"
- Use a lightweight i18n library (e.g., `i18next`).
- English as default locale.
- Kannada and Hindi as optional locales.
- Store user language preference in localStorage.
- Short text labels — no long paragraph translation needed.

## Image Handling

Per requirements: "Camera-first photo upload with automatic image compression"
- Use `<input type="file" accept="image/*" capture="environment">` for mobile camera.
- Client-side compression using Canvas API or a library (e.g., `browser-image-compression`).
- Target: reduce to ~500KB before upload.
- Upload via multipart/form-data to backend.
- Display thumbnails in work entry and verification views.

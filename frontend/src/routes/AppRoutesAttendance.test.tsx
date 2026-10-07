import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AttendancePage } from '../pages/AttendancePage';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../types/auth';
import * as attendanceApi from '../api/attendance';
import * as useGeoMock from '../hooks/useGeolocation';

// Mock Attendance API
vi.mock('../api/attendance', () => ({
  getAttendanceRecords: vi.fn(),
  checkIn: vi.fn(),
  checkOut: vi.fn(),
}));

// Mock Geolocation hook
vi.mock('../hooks/useGeolocation', () => ({
  useGeolocation: vi.fn(),
}));

const createMockUser = (
  role: SystemRole,
  activeSites: Array<{ id: string; name: string }> = []
): EmployeeProfile => ({
  id: 'emp-1',
  user_id: 'user-1',
  employee_code: 'EMP-001',
  mobile_id: '+919123456789',
  name: 'Test User',
  system_role: role,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  trade_roles: [],
  active_sites: activeSites,
});

const renderRouteWithRole = (
  role: SystemRole,
  activeSites: Array<{ id: string; name: string }> = []
) => {
  const user = createMockUser(role, activeSites);
  return render(
    <AuthContext.Provider
      value={{
        user,
        role,
        accessToken: 'mock-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={['/attendance']}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['employee']} />}>
            <Route path="/attendance" element={<AttendancePage />} />
          </Route>
          <Route path="/403" element={<AccessDeniedPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('AppRoutes Attendance Route Guarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: null,
      error: null,
      loading: false,
      getLocation: vi.fn(),
    });
    vi.mocked(attendanceApi.getAttendanceRecords).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('allows employee role to access /attendance and view AttendancePage', async () => {
    renderRouteWithRole('employee', [{ id: 'site-1', name: 'Central Station Site' }]);

    await waitFor(() => {
      expect(screen.getByText('Daily Attendance')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /CHECK IN/i })).toBeInTheDocument();
    });
    expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
  });

  it('blocks administrator role from /attendance and redirects to /403 Access Denied', async () => {
    renderRouteWithRole('administrator', [{ id: 'site-1', name: 'Central Station Site' }]);

    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Daily Attendance')).not.toBeInTheDocument();
  });

  it('blocks director role from /attendance and redirects to /403 Access Denied', async () => {
    renderRouteWithRole('director', [{ id: 'site-1', name: 'Central Station Site' }]);

    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Daily Attendance')).not.toBeInTheDocument();
  });

  it('blocks supervisor role from /attendance and redirects to /403 Access Denied', async () => {
    renderRouteWithRole('supervisor', [{ id: 'site-1', name: 'Central Station Site' }]);

    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('Daily Attendance')).not.toBeInTheDocument();
  });
});

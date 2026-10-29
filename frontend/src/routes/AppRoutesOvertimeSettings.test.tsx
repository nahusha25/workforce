import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { OvertimeSettingsPage } from '../pages/OvertimeSettingsPage';
import { Sidebar } from '../components/layout/Sidebar';
import { AuthContext } from '../context/AuthContext';
import * as payrollSettingsApi from '../api/payrollSettings';
import type { EmployeeProfile, SystemRole } from '../types/auth';

vi.mock('../api/payrollSettings', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/payrollSettings')>();
  return {
    ...actual,
    getOvertimeSettingsHistoryApi: vi.fn(),
    getEffectiveOvertimeSettingApi: vi.fn(),
    createOvertimeSettingApi: vi.fn(),
  };
});

const mockActiveSetting: payrollSettingsApi.PayrollOvertimeSettingsResponse = {
  id: 'ot-curr',
  standard_workday_hours: '7.00',
  overtime_multiplier: '1.50',
  effective_from: '2026-01-01',
  effective_to: null,
  description: 'Standard Policy',
  created_at: '2026-01-01T00:00:00Z',
};

const renderWithRole = (role: SystemRole, initialPath = '/admin/overtime-settings') => {
  const user: EmployeeProfile = {
    id: `user-${role}-1`,
    user_id: `u-${role}-1`,
    employee_code: `${role.slice(0, 3).toUpperCase()}001`,
    mobile_id: '+919999999999',
    name: `${role} User`,
    system_role: role,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  };

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
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/403" element={<AccessDeniedPage />} />
          <Route element={<RoleGuard allowedRoles={['administrator', 'director']} />}>
            <Route path="/admin/overtime-settings" element={<OvertimeSettingsPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

const renderSidebarWithRole = (role: SystemRole) => {
  const user: EmployeeProfile = {
    id: `user-${role}-1`,
    user_id: `u-${role}-1`,
    employee_code: `${role.slice(0, 3).toUpperCase()}001`,
    mobile_id: '+919999999999',
    name: `${role} User`,
    system_role: role,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  };

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
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('Overtime Settings Route and Sidebar Permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockResolvedValue([mockActiveSetting]);
    vi.mocked(payrollSettingsApi.getEffectiveOvertimeSettingApi).mockResolvedValue(mockActiveSetting);
  });

  afterEach(() => {
    cleanup();
  });

  it('redirects Employee to /403 when accessing /admin/overtime-settings', async () => {
    renderWithRole('employee');

    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });

    expect(screen.queryByRole('heading', { level: 2, name: 'Payroll Overtime Settings' })).not.toBeInTheDocument();
  });

  it('redirects Supervisor to /403 when accessing /admin/overtime-settings', async () => {
    renderWithRole('supervisor');

    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });

    expect(screen.queryByRole('heading', { level: 2, name: 'Payroll Overtime Settings' })).not.toBeInTheDocument();
  });

  it('allows Administrator to access /admin/overtime-settings', async () => {
    renderWithRole('administrator');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Payroll Overtime Settings' })).toBeInTheDocument();
    });
  });

  it('allows Director to access /admin/overtime-settings', async () => {
    renderWithRole('director');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Payroll Overtime Settings' })).toBeInTheDocument();
    });
  });

  it('does NOT display Overtime Settings in Sidebar for Employee', () => {
    renderSidebarWithRole('employee');
    expect(screen.queryByText('Overtime Settings')).not.toBeInTheDocument();
  });

  it('does NOT display Overtime Settings in Sidebar for Supervisor', () => {
    renderSidebarWithRole('supervisor');
    expect(screen.queryByText('Overtime Settings')).not.toBeInTheDocument();
  });

  it('does NOT display Overtime Settings in Sidebar for Administrator (removed from active workflow)', () => {
    renderSidebarWithRole('administrator');
    expect(screen.queryByRole('link', { name: 'Overtime Settings' })).not.toBeInTheDocument();
  });

  it('does NOT display Overtime Settings in Sidebar for Director (removed from active workflow)', () => {
    renderSidebarWithRole('director');
    expect(screen.queryByRole('link', { name: 'Overtime Settings' })).not.toBeInTheDocument();
  });
});

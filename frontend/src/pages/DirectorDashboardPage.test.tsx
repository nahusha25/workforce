import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DirectorDashboardPage } from './DirectorDashboardPage';
import { AuthContext } from '../context/AuthContext';
import { RoleGuard } from '../components/guards/RoleGuard';
import * as dashboardApi from '../api/dashboard';
import type { SystemRole } from '../types/auth';

afterEach(() => {
  cleanup();
});

vi.mock('../api/dashboard', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/dashboard')>();
  return {
    ...original,
    useDashboardMetrics: vi.fn(),
  };
});

vi.mock('../api/masterData', () => ({
  getClientsApi: vi.fn().mockResolvedValue([]),
  getSitesApi: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/employee', () => ({
  getEmployeesApi: vi.fn().mockResolvedValue([]),
}));

vi.mock('recharts', async (importOriginal) => {
  const original = await importOriginal<typeof import('recharts')>();
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="mock-responsive-container">{children}</div>
    ),
  };
});

const mockMetricsResponse: dashboardApi.DashboardMetricsResponse = {
  period: { from: '2026-09-01', to: '2026-09-30' },
  manpower: { total_distinct_employees: 42 },
  working_hours: { total_hours: 1250.5, average_per_employee: 29.8 },
  site_progress: [
    {
      site_id: 's-1',
      site_name: 'Metro Line',
      total_quantity: 600,
      category_breakdown: { cable: 500, device: 100 },
    },
  ],
  cable_metres: { total: 1450.25 },
  devices_installed: { total: 85 },
  employee_productivity: [
    {
      employee_id: 'e-1',
      employee_name: 'Sunil Verma',
      total_approved_hours: 45.0,
      by_category: [
        {
          category: 'cable',
          uom: 'm',
          total_quantity: 450,
          ratio: 10.0,
          ratio_label: '10.00 m/hr',
        },
      ],
    },
  ],
  material_cost: { total_amount: 54320.75, currency: 'INR' },
  approval_status: {
    attendance: { approved: 120, submitted: 8, draft: 2, rejected: 1, correction_required: 0 },
    work_entries: { approved: 110, submitted: 12, draft: 0, rejected: 2, correction_required: 1 },
    materials: { approved: 95, submitted: 5, draft: 1, rejected: 0, correction_required: 0 },
  },
};

const renderWithContext = (role: SystemRole = 'director') => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  const authValue: any = {
    user: { id: 'u-1', name: 'Director User', mobile_number: '9999999999', system_role: role, is_active: true },
    role,
    isAuthenticated: true,
    isLoading: false,
    token: 'valid-token',
    login: vi.fn(),
    logout: vi.fn(),
    checkAuth: vi.fn(),
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={authValue}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route path="/403" element={<div data-testid="access-denied-page">Access Denied</div>} />
            <Route element={<RoleGuard allowedRoles={['director', 'administrator']} />}>
              <Route path="/dashboard" element={<DirectorDashboardPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
};

describe('DirectorDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(dashboardApi.useDashboardMetrics).mockReturnValue({
      data: mockMetricsResponse,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);
  });

  it('renders all 8 KPI metric cards with formatted values and currency', async () => {
    renderWithContext('director');

    expect(screen.getByText(/Director Operations Dashboard/i)).toBeTruthy();

    await waitFor(() => {
      // 1. Manpower
      expect(screen.getByText('42')).toBeTruthy();
      // 2. Working hours
      expect(screen.getByText('1250.5h')).toBeTruthy();
      // 3. Cable installed
      expect(screen.getByText('1450.3 m')).toBeTruthy();
      // 4. Devices installed
      expect(screen.getByText('85 units')).toBeTruthy();
      // 5. Material spend (formatDecimal ensures 2 decimal places: ₹54320.75)
      expect(screen.getByText('₹54320.75')).toBeTruthy();
      // 6. Approved attendance
      expect(screen.getByText('120')).toBeTruthy();
      // 7. Approved work
      expect(screen.getByText('110')).toBeTruthy();
      // 8. Approved materials
      expect(screen.getByText('95')).toBeTruthy();
    });
  });

  it('allows access for administrator role (RBAC parity)', async () => {
    renderWithContext('administrator');

    expect(screen.getByText(/Director Operations Dashboard/i)).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText('42')).toBeTruthy();
    });
    expect(screen.queryByTestId('access-denied-page')).toBeNull();
  });

  it('denies access and redirects to 403 for employee role', async () => {
    renderWithContext('employee');

    await waitFor(() => {
      expect(screen.getByTestId('access-denied-page')).toBeTruthy();
    });
    expect(screen.queryByText(/Director Operations Dashboard/i)).toBeNull();
  });

  it('denies access and redirects to 403 for supervisor role', async () => {
    renderWithContext('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('access-denied-page')).toBeTruthy();
    });
    expect(screen.queryByText(/Director Operations Dashboard/i)).toBeNull();
  });

  it('renders quick navigation links to all 6 reports', async () => {
    renderWithContext('director');

    expect(screen.getByText('Attendance History')).toBeTruthy();
    expect(screen.getByText('Work Progress')).toBeTruthy();
    expect(screen.getByText('Material Transactions')).toBeTruthy();
    expect(screen.getByText('Productivity Breakdown')).toBeTruthy();
    expect(screen.getByText('Payment Summary (Preview)')).toBeTruthy();
    expect(screen.getByText('Invoice Summary')).toBeTruthy();
  });
});

import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReportPage } from './ReportPage';
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
    useReportData: vi.fn(),
    downloadReportExport: vi.fn(),
  };
});

vi.mock('../api/masterData', () => ({
  getClientsApi: vi.fn().mockResolvedValue([]),
  getSitesApi: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/employee', () => ({
  getEmployeesApi: vi.fn().mockResolvedValue([]),
}));

const mockAttendanceData: dashboardApi.AttendanceReportResponse = {
  data: [
    {
      attendance_id: 'att-1',
      employee_id: 'emp-1',
      employee_name: 'Rajesh Kumar',
      site_id: 'site-1',
      site_name: 'Metro Site',
      date: '2026-09-25',
      check_in_time: '2026-09-25T09:00:00Z',
      check_out_time: '2026-09-25T17:00:00Z',
      working_hours: 8.0,
      overtime_hours: 0,
      status: 'approved',
      is_within_geofence: true,
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
};

const renderWithContext = (initialPath: string = '/reports/attendance', role: SystemRole = 'director') => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  const authValue: any = {
    user: { id: 'u-1', name: 'Test User', mobile_number: '9999999999', system_role: role, is_active: true },
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
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/403" element={<div data-testid="access-denied-page">Access Denied</div>} />
            <Route element={<RoleGuard allowedRoles={['director', 'administrator']} />}>
              <Route path="/reports/:type" element={<ReportPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
};

describe('ReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(dashboardApi.useReportData).mockReturnValue({
      data: mockAttendanceData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);
    vi.mocked(dashboardApi.downloadReportExport).mockResolvedValue(undefined);
  });

  it('renders attendance report page with tablist and report table', async () => {
    renderWithContext('/reports/attendance', 'director');

    expect(screen.getByText('Attendance History Report')).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
      expect(screen.getByText('Metro Site')).toBeTruthy();
    });
  });

  it('allows access for administrator role (RBAC parity)', async () => {
    renderWithContext('/reports/attendance', 'administrator');

    expect(screen.getByText('Attendance History Report')).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });
    expect(screen.queryByTestId('access-denied-page')).toBeNull();
  });

  it('denies access for employee or supervisor role', async () => {
    renderWithContext('/reports/attendance', 'supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('access-denied-page')).toBeTruthy();
    });
    expect(screen.queryByText('Attendance History Report')).toBeNull();
  });

  it('export button reuses the EXACT filters applied on screen', async () => {
    renderWithContext('/reports/attendance', 'director');

    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });

    // Change date filter
    const dateFrom = screen.getByTestId('filter-date-from');
    fireEvent.change(dateFrom, { target: { value: '2026-08-01' } });

    // Click Export Excel
    const excelBtn = screen.getByTestId('export-excel-btn');
    fireEvent.click(excelBtn);

    await waitFor(() => {
      expect(dashboardApi.downloadReportExport).toHaveBeenCalledWith(
        'attendance',
        'xlsx',
        expect.objectContaining({
          date_from: '2026-08-01',
          status: 'approved',
        })
      );
    });
  });
});

import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { EmployeePaymentsPage } from '../pages/EmployeePaymentsPage';
import { EmployeePaymentDetailPage } from '../pages/EmployeePaymentDetailPage';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { Sidebar } from '../components/layout/Sidebar';
import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../types/auth';
import * as employeePaymentsApi from '../api/employeePayments';
import * as employeeApi from '../api/employee';

vi.mock('../api/employeePayments', () => ({
  listEmployeePaymentsApi: vi.fn(),
  previewEmployeePaymentsApi: vi.fn(),
  generateEmployeePaymentsApi: vi.fn(),
  getEmployeePaymentApi: vi.fn(),
  approveEmployeePaymentApi: vi.fn(),
  payEmployeePaymentApi: vi.fn(),
  cancelEmployeePaymentApi: vi.fn(),
}));

vi.mock('../api/employee', () => ({
  getAllEmployeesApi: vi.fn(),
  getEmployeesApi: vi.fn(),
}));

const createMockUser = (role: SystemRole): EmployeeProfile => ({
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
  active_sites: [],
});

const renderEmployeePaymentsRouteWithRole = (role: SystemRole, initialPath = '/employee-payments') => {
  const user = createMockUser(role);
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
          <Route element={<RoleGuard allowedRoles={['director', 'administrator']} />}>
            <Route path="/employee-payments" element={<EmployeePaymentsPage />} />
            <Route path="/employee-payments/:paymentId" element={<EmployeePaymentDetailPage />} />
          </Route>
          <Route path="/403" element={<AccessDeniedPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

const renderSidebarWithRole = (role: SystemRole) => {
  const user = createMockUser(role);
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

describe('Employee Payments Route Guarding & RBAC Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(employeePaymentsApi.listEmployeePaymentsApi).mockResolvedValue([]);
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('allows Director to access /employee-payments', async () => {
    renderEmployeePaymentsRouteWithRole('director');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Employee Payments' })).toBeInTheDocument();
    });
    expect(screen.queryByText(/403/i)).not.toBeInTheDocument();
  });

  it('allows Administrator to access /employee-payments', async () => {
    renderEmployeePaymentsRouteWithRole('administrator');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Employee Payments' })).toBeInTheDocument();
    });
    expect(screen.queryByText(/403/i)).not.toBeInTheDocument();
  });

  it('redirects Employee to /403 when accessing /employee-payments', async () => {
    renderEmployeePaymentsRouteWithRole('employee');
    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole('heading', { level: 2, name: 'Employee Payments' })).not.toBeInTheDocument();
  });

  it('redirects Supervisor to /403 when accessing /employee-payments', async () => {
    renderEmployeePaymentsRouteWithRole('supervisor');
    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole('heading', { level: 2, name: 'Employee Payments' })).not.toBeInTheDocument();
  });

  it('renders "Employee Payments" navigation link in Sidebar for Director and Administrator', () => {
    const { unmount: unmountDir } = renderSidebarWithRole('director');
    expect(screen.getByRole('link', { name: 'Employee Payments' })).toBeInTheDocument();
    unmountDir();

    renderSidebarWithRole('administrator');
    expect(screen.getByRole('link', { name: 'Employee Payments' })).toBeInTheDocument();
  });

  it('allows Director to access /employee-payments/:paymentId', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce({
      id: 'pay-123',
      payment_number: 'PAY-20261010-0123',
      idempotency_key: 'idem-123',
      employee_id: 'emp-1',
      employee_name: 'Aarav Sharma',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      status: 'draft',
      total_amount: 3500.0,
      total_days: 5.0,
      total_quantity: 0.0,
      created_at: '2026-10-08T10:00:00Z',
      updated_at: '2026-10-08T10:00:00Z',
      rate_band_summaries: [],
      lines: [],
    });
    renderEmployeePaymentsRouteWithRole('director', '/employee-payments/pay-123');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'PAY-20261010-0123' })).toBeInTheDocument();
    });
    expect(screen.queryByText(/403/i)).not.toBeInTheDocument();
  });

  it('allows Administrator to access /employee-payments/:paymentId', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce({
      id: 'pay-123',
      payment_number: 'PAY-20261010-0123',
      idempotency_key: 'idem-123',
      employee_id: 'emp-1',
      employee_name: 'Aarav Sharma',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      status: 'draft',
      total_amount: 3500.0,
      total_days: 5.0,
      total_quantity: 0.0,
      created_at: '2026-10-08T10:00:00Z',
      updated_at: '2026-10-08T10:00:00Z',
      rate_band_summaries: [],
      lines: [],
    });
    renderEmployeePaymentsRouteWithRole('administrator', '/employee-payments/pay-123');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'PAY-20261010-0123' })).toBeInTheDocument();
    });
    expect(screen.queryByText(/403/i)).not.toBeInTheDocument();
  });

  it('redirects Employee to /403 when accessing /employee-payments/:paymentId', async () => {
    renderEmployeePaymentsRouteWithRole('employee', '/employee-payments/pay-123');
    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });
  });

  it('redirects Supervisor to /403 when accessing /employee-payments/:paymentId', async () => {
    renderEmployeePaymentsRouteWithRole('supervisor', '/employee-payments/pay-123');
    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });
  });
});

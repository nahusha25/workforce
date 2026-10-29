import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { InvoicesPage } from '../pages/InvoicesPage';
import { InvoiceDetailPage } from '../pages/InvoiceDetailPage';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { Sidebar } from '../components/layout/Sidebar';
import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../types/auth';
import * as invoicesApi from '../api/invoices';

vi.mock('../api/invoices', () => ({
  listInvoicesApi: vi.fn(),
  getInvoiceApi: vi.fn(),
  previewInvoiceApi: vi.fn(),
  generateInvoiceApi: vi.fn(),
  updateDraftInvoiceApi: vi.fn(),
  issueInvoiceApi: vi.fn(),
  cancelInvoiceApi: vi.fn(),
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

const renderInvoiceRouteWithRole = (role: SystemRole, initialPath = '/invoices') => {
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
            <Route path="/invoices" element={<InvoicesPage />} />
            <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
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

describe('Invoices Route Guarding & RBAC Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoicesApi.listInvoicesApi).mockResolvedValue([]);
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue({
      id: 'inv-123',
      invoice_number: 'INV-20260301-0001',
      idempotency_key: 'idem-123',
      client_id: 'c1',
      client_name: 'Alpha Corp',
      project_id: 'p1',
      project_name: 'Metro Line',
      site_id: 's1',
      site_name: 'Station 1',
      period_start: '2026-03-01',
      period_end: '2026-03-15',
      status: 'draft',
      subtotal_work: 800,
      subtotal_material: 200,
      tax_amount: 0,
      total_amount: 1000,
      paid_amount: 0,
      lines: [],
      notes: null,
      client_po_number: null,
      remarks: null,
      created_at: '2026-03-16T10:00:00Z',
      updated_at: '2026-03-16T10:00:00Z',
      issued_at: null,
      cancelled_at: null,
      cancellation_reason: null,
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('Route Protection', () => {
    it('allows administrator to access /invoices list', async () => {
      renderInvoiceRouteWithRole('administrator', '/invoices');

      await waitFor(() => {
        expect(screen.getByText('Client Invoices')).toBeInTheDocument();
      });
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
    });

    it('allows director to access /invoices list', async () => {
      renderInvoiceRouteWithRole('director', '/invoices');

      await waitFor(() => {
        expect(screen.getByText('Client Invoices')).toBeInTheDocument();
      });
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
    });

    it('blocks employee from /invoices and redirects to /403', async () => {
      renderInvoiceRouteWithRole('employee', '/invoices');

      await waitFor(() => {
        expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
      });
      expect(screen.queryByText('Client Invoices')).not.toBeInTheDocument();
    });

    it('blocks supervisor from /invoices and redirects to /403', async () => {
      renderInvoiceRouteWithRole('supervisor', '/invoices');

      await waitFor(() => {
        expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
      });
      expect(screen.queryByText('Client Invoices')).not.toBeInTheDocument();
    });

    it('allows director to access /invoices/:invoiceId detail', async () => {
      renderInvoiceRouteWithRole('director', '/invoices/inv-123');

      await waitFor(() => {
        expect(screen.getByText('INV-20260301-0001')).toBeInTheDocument();
      });
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
    });

    it('blocks supervisor from /invoices/:invoiceId detail and redirects to /403', async () => {
      renderInvoiceRouteWithRole('supervisor', '/invoices/inv-123');

      await waitFor(() => {
        expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
      });
      expect(screen.queryByText('INV-20260301-0001')).not.toBeInTheDocument();
    });
  });

  describe('Sidebar Role Navigation Visibility', () => {
    it('shows Invoices link for administrator in Sidebar', () => {
      renderSidebarWithRole('administrator');
      expect(screen.getByRole('link', { name: 'Invoices' })).toBeInTheDocument();
    });

    it('shows Invoices link for director in Sidebar', () => {
      renderSidebarWithRole('director');
      expect(screen.getByRole('link', { name: 'Invoices' })).toBeInTheDocument();
    });

    it('hides Invoices link from employee in Sidebar', () => {
      renderSidebarWithRole('employee');
      expect(screen.queryByRole('link', { name: 'Invoices' })).not.toBeInTheDocument();
    });

    it('hides Invoices link from supervisor in Sidebar', () => {
      renderSidebarWithRole('supervisor');
      expect(screen.queryByRole('link', { name: 'Invoices' })).not.toBeInTheDocument();
    });
  });
});

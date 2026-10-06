import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { WorkOrdersPage } from './WorkOrdersPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AuthContext } from '../context/AuthContext';
import type { SystemRole } from '../types/auth';
import {
  getWorkOrdersApi,
  getWorkOrderByIdApi,
  createWorkOrderApi,
  updateWorkOrderApi,
  getProjectsApi,
  getSitesApi,
} from '../api/masterData';

// Mock API module
vi.mock('../api/masterData', () => ({
  getWorkOrdersApi: vi.fn(),
  getWorkOrderByIdApi: vi.fn(),
  createWorkOrderApi: vi.fn(),
  updateWorkOrderApi: vi.fn(),
  getProjectsApi: vi.fn(),
  getSitesApi: vi.fn(),
}));

const mockProjects = [
  { id: 'proj-1', name: 'Metro Line 3', status: 'Active', client_id: 'client-1' },
];

const mockSites = [
  { id: 'site-1', name: 'Central Station', project_id: 'proj-1', is_active: true },
];

const mockWorkOrders = [
  {
    id: 'wo-1',
    order_number: 'WO-2026-001',
    project_id: 'proj-1',
    site_id: 'site-1',
    description: 'Cabling work in central station',
    target_quantities: null,
    start_date: '2026-01-01',
    end_date: '2026-06-30',
    billing_basis: 'lump_sum',
    status: 'open',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'wo-2',
    order_number: 'WO-2026-002',
    project_id: 'proj-1',
    site_id: 'site-1',
    description: 'Terminal fitout',
    target_quantities: null,
    start_date: '2026-02-01',
    end_date: '2026-08-30',
    billing_basis: 'per_metre',
    status: 'draft',
    is_active: false,
    created_at: '2026-02-01T00:00:00Z',
  },
];

const renderWithRoleGuard = (role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'user-1',
          user_id: 'u-1',
          employee_code: 'EMP-001',
          mobile_id: '+919999999999',
          name: 'Test Admin',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        role,
        accessToken: 'fake-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={['/admin/work-orders']}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['administrator', 'director']} />}>
            <Route path="/admin/work-orders" element={<WorkOrdersPage />} />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('WorkOrdersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getProjectsApi as any).mockResolvedValue(mockProjects);
    (getSitesApi as any).mockResolvedValue(mockSites);
    (getWorkOrdersApi as any).mockResolvedValue(mockWorkOrders);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders list view showing key fields and active/inactive status badges', async () => {
    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('WO-2026-001')).toBeInTheDocument();
      expect(screen.getByText('WO-2026-002')).toBeInTheDocument();
    });

    expect(screen.getAllByText('Metro Line 3').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Central Station').length).toBeGreaterThan(0);
    expect(screen.getByTestId('work-orders-table')).toBeInTheDocument();
  });

  it('successfully creates a new work order via POST', async () => {
    (createWorkOrderApi as any).mockResolvedValue({
      id: 'wo-3',
      order_number: 'WO-2026-003',
      project_id: 'proj-1',
      site_id: 'site-1',
      description: 'New fiber run',
      status: 'open',
      billing_basis: 'per_metre',
      is_active: true,
      created_at: '2026-03-01T00:00:00Z',
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('add-work-order-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('add-work-order-btn'));

    fireEvent.change(screen.getByTestId('order-number-input'), {
      target: { value: 'WO-2026-003' },
    });
    fireEvent.change(screen.getByTestId('description-input'), {
      target: { value: 'New fiber run' },
    });

    fireEvent.click(screen.getByTestId('save-work-order-btn'));

    await waitFor(() => {
      expect(createWorkOrderApi).toHaveBeenCalledWith(
        expect.objectContaining({
          order_number: 'WO-2026-003',
          project_id: 'proj-1',
          site_id: 'site-1',
          description: 'New fiber run',
          is_active: true,
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Work Order "WO-2026-003" created successfully!/i)).toBeInTheDocument();
    });
  });

  it('successfully loads existing record via GET and updates via PUT', async () => {
    (getWorkOrderByIdApi as any).mockResolvedValue(mockWorkOrders[0]);
    (updateWorkOrderApi as any).mockResolvedValue({
      ...mockWorkOrders[0],
      order_number: 'WO-2026-001-MOD',
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn-wo-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('edit-btn-wo-1'));

    await waitFor(() => {
      expect(getWorkOrderByIdApi).toHaveBeenCalledWith('wo-1');
      expect(screen.getByDisplayValue('WO-2026-001')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('order-number-input'), {
      target: { value: 'WO-2026-001-MOD' },
    });

    fireEvent.click(screen.getByTestId('save-work-order-btn'));

    await waitFor(() => {
      expect(updateWorkOrderApi).toHaveBeenCalledWith(
        'wo-1',
        expect.objectContaining({
          order_number: 'WO-2026-001-MOD',
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Work Order "WO-2026-001-MOD" updated successfully!/i)).toBeInTheDocument();
    });
  });

  it('deactivates an active work order via PUT without hard delete', async () => {
    (updateWorkOrderApi as any).mockResolvedValue({
      ...mockWorkOrders[0],
      is_active: false,
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('deactivate-btn-wo-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('deactivate-btn-wo-1'));

    await waitFor(() => {
      expect(updateWorkOrderApi).toHaveBeenCalledWith('wo-1', { is_active: false });
      expect(screen.getByText(/Work Order "WO-2026-001" deactivated successfully/i)).toBeInTheDocument();
    });
  });

  it('enforces RoleGuard blocking non-admin/director role from accessing page', async () => {
    renderWithRoleGuard('employee');

    await waitFor(() => {
      expect(screen.getByTestId('forbidden-page')).toBeInTheDocument();
      expect(screen.queryByText('Work Order Management')).not.toBeInTheDocument();
    });
  });

  it('allows director role to access page per BE-021 requirements', async () => {
    renderWithRoleGuard('director');

    await waitFor(() => {
      expect(screen.getByText('Work Order Management')).toBeInTheDocument();
      expect(screen.queryByTestId('forbidden-page')).not.toBeInTheDocument();
    });
  });
});

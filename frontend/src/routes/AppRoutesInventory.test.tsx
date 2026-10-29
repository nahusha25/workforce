import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { InventoryPage } from '../pages/InventoryPage';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { Sidebar } from '../components/layout/Sidebar';
import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../types/auth';

vi.mock('../api/inventory', () => ({
  getSiteInventoryApi: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getInventorySitesApi: vi.fn().mockResolvedValue([]),
  recordStockInwardApi: vi.fn(),
  getMaterialStockMovementsApi: vi.fn(),
}));


vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn().mockResolvedValue([]),
  };
});

vi.mock('../api/dailyWork', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/dailyWork')>();
  return {
    ...actual,
    getMaterialsCatalogue: vi.fn().mockResolvedValue([]),
  };
});

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

const renderInventoryRouteWithRole = (role: SystemRole, initialPath = '/inventory') => {
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
          <Route element={<RoleGuard allowedRoles={['supervisor', 'administrator', 'director']} />}>
            <Route path="/inventory" element={<InventoryPage />} />
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

describe('AppRoutes - Inventory RBAC & Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('Route Access Control (/inventory)', () => {
    it('allows access to supervisor', async () => {
      renderInventoryRouteWithRole('supervisor');
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('Material Inventory')).toBeInTheDocument();
      });
    });

    it('allows access to administrator', async () => {
      renderInventoryRouteWithRole('administrator');
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('Material Inventory')).toBeInTheDocument();
      });
    });

    it('allows access to director', async () => {
      renderInventoryRouteWithRole('director');
      expect(screen.queryByText(/Access Denied/i)).not.toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('Material Inventory')).toBeInTheDocument();
      });
    });

    it('denies access to employee and redirects to /403', async () => {
      renderInventoryRouteWithRole('employee');
      await waitFor(() => {
        expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
      });
      expect(screen.queryByText('Material Inventory')).not.toBeInTheDocument();
    });
  });

  describe('Sidebar Navigation Links', () => {
    it('shows Inventory link for supervisor', () => {
      renderSidebarWithRole('supervisor');
      expect(screen.getByRole('link', { name: 'Inventory' })).toBeInTheDocument();
    });

    it('shows Inventory link for administrator', () => {
      renderSidebarWithRole('administrator');
      expect(screen.getByRole('link', { name: 'Inventory' })).toBeInTheDocument();
    });

    it('shows Inventory link for director', () => {
      renderSidebarWithRole('director');
      expect(screen.getByRole('link', { name: 'Inventory' })).toBeInTheDocument();
    });

    it('hides Inventory link for employee', () => {
      renderSidebarWithRole('employee');
      expect(screen.queryByRole('link', { name: 'Inventory' })).not.toBeInTheDocument();
    });
  });
});

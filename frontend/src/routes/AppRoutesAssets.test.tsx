import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AssetsPage } from '../pages/AssetsPage';
import { AssetDetailPage } from '../pages/AssetDetailPage';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { Sidebar } from '../components/layout/Sidebar';
import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../types/auth';
import * as assetsApi from '../api/assets';

vi.mock('../api/assets', () => ({
  listAssetsApi: vi.fn(),
  getAssetApi: vi.fn(),
  registerAssetApi: vi.fn(),
  issueAssetApi: vi.fn(),
  returnAssetApi: vi.fn(),
  reassignAssetApi: vi.fn(),
  getAssetSitesApi: vi.fn().mockResolvedValue([]),
  getAssetDestinationSitesApi: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn().mockResolvedValue([]),
  };
});

vi.mock('../api/employee', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employee')>();
  return {
    ...actual,
    getAllEmployeesApi: vi.fn().mockResolvedValue([]),
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

const renderAssetRouteWithRole = (role: SystemRole, initialPath = '/assets') => {
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
            <Route path="/assets" element={<AssetsPage />} />
            <Route path="/assets/:assetId" element={<AssetDetailPage />} />
          </Route>
          <Route path="/403" element={<AccessDeniedPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
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
    </AuthContext.Provider>,
  );
};

describe('Assets Route Guarding & RBAC Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.listAssetsApi).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 15,
    });
    vi.mocked(assetsApi.getAssetApi).mockResolvedValue({
      id: 'ast-1',
      asset_tag: 'AST-001',
      name: 'Test Drill',
      category: 'Power Tools',
      condition: 'good',
      status: 'available',
      location_type: 'warehouse',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      transactions: [],
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('Route Access Control', () => {
    it('allows administrator to access /assets', async () => {
      renderAssetRouteWithRole('administrator', '/assets');
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Asset Management/i })).toBeInTheDocument();
      });
    });

    it('allows director to access /assets', async () => {
      renderAssetRouteWithRole('director', '/assets');
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Asset Management/i })).toBeInTheDocument();
      });
    });

    it('allows supervisor to access /assets', async () => {
      renderAssetRouteWithRole('supervisor', '/assets');
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Asset Management/i })).toBeInTheDocument();
      });
    });

    it('denies employee access to /assets and redirects to /403', async () => {
      renderAssetRouteWithRole('employee', '/assets');
      await waitFor(() => {
        expect(screen.getByText(/403/i)).toBeInTheDocument();
        expect(screen.getByText(/access denied/i)).toBeInTheDocument();
      });
    });

    it('allows supervisor to access /assets/:assetId', async () => {
      renderAssetRouteWithRole('supervisor', '/assets/ast-1');
      await waitFor(() => {
        expect(screen.getByText('Test Drill')).toBeInTheDocument();
      });
    });

    it('denies employee access to /assets/:assetId and redirects to /403', async () => {
      renderAssetRouteWithRole('employee', '/assets/ast-1');
      await waitFor(() => {
        expect(screen.getByText(/403/i)).toBeInTheDocument();
      });
    });
  });

  describe('Sidebar Role Navigation Visibility', () => {
    it('shows Assets link for administrator in Sidebar', () => {
      renderSidebarWithRole('administrator');
      const link = screen.getByRole('link', { name: 'Assets' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/assets');
    });

    it('shows Assets link for director in Sidebar', () => {
      renderSidebarWithRole('director');
      const link = screen.getByRole('link', { name: 'Assets' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/assets');
    });

    it('shows Assets link for supervisor in Sidebar', () => {
      renderSidebarWithRole('supervisor');
      const link = screen.getByRole('link', { name: 'Assets' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/assets');
    });

    it('hides Assets link from employee in Sidebar', () => {
      renderSidebarWithRole('employee');
      expect(screen.queryByRole('link', { name: 'Assets' })).not.toBeInTheDocument();
    });
  });
});

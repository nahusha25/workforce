import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { SitesPage } from './SitesPage';
import { AuthContext } from '../context/AuthContext';
import * as masterDataApi from '../api/masterData';
import type { SystemRole } from '../types/auth';

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn(),
    getProjectsApi: vi.fn(),
    createSiteApi: vi.fn(),
    deleteSiteApi: vi.fn(),
  };
});

const mockProjects = [
  { id: 'proj-1', name: 'Metro Line Extension', client_id: 'client-1', status: 'Active' },
];

const mockSites = [
  {
    id: 'site-1',
    name: 'Central Junction Site',
    project_id: 'proj-1',
    address: '123 Main Street',
    location: null,
    permitted_radius_m: 100,
    is_active: true,
  },
  {
    id: 'site-2',
    name: 'North Depot Site',
    project_id: 'proj-1',
    address: '456 North Ave',
    location: null,
    permitted_radius_m: 50,
    is_active: false,
  },
];

const renderSitesPage = (role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'u-1',
          user_id: 'u-1',
          employee_code: 'ADM-01',
          mobile_id: '+919999999999',
          name: 'Admin User',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        role,
        accessToken: 'token',
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
        <SitesPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('SitesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders site cards and shows delete button for administrators', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
      expect(screen.getByText('North Depot Site')).toBeInTheDocument();
    });

    expect(screen.getByTestId('delete-site-site-1')).toBeInTheDocument();
    expect(screen.getByTestId('delete-site-site-2')).toBeInTheDocument();
  });

  it('allows administrator to delete a site with confirmation modal', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(masterDataApi.deleteSiteApi).mockResolvedValue({ status: 'success', message: 'Site deleted' });

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    // Click delete
    fireEvent.click(screen.getByTestId('delete-site-site-1'));
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to permanently delete site/)).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
    expect(masterDataApi.deleteSiteApi).not.toHaveBeenCalled();

    // Confirm delete
    fireEvent.click(screen.getByTestId('delete-site-site-1'));
    fireEvent.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(masterDataApi.deleteSiteApi).toHaveBeenCalledWith('site-1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toBeInTheDocument();
    });
  });

  it('hides delete button when viewed by non-administrator role', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);

    renderSitesPage('director');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('delete-site-site-1')).not.toBeInTheDocument();
  });
});

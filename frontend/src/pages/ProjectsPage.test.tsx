import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProjectsPage } from './ProjectsPage';
import { AuthContext } from '../context/AuthContext';
import * as masterDataApi from '../api/masterData';
import type { SystemRole } from '../types/auth';

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getProjectsApi: vi.fn(),
    getClientsApi: vi.fn(),
    createProjectApi: vi.fn(),
    deleteProjectApi: vi.fn(),
  };
});

const mockClients = [
  { id: 'client-1', name: 'Acme Infra Corp', is_active: true, created_at: '2026-01-01T00:00:00Z' },
];

const mockProjects = [
  {
    id: 'proj-1',
    name: 'Metro Line Extension',
    client_id: 'client-1',
    status: 'Active',
    start_date: '2026-01-01',
    end_date: '2026-12-31',
  },
  {
    id: 'proj-2',
    name: 'Airport CCTV Retrofit',
    client_id: 'client-1',
    status: 'Draft',
    start_date: '2026-02-01',
    end_date: null,
  },
];

const renderProjectsPage = (role: SystemRole = 'administrator') => {
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
        <ProjectsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders project cards and shows delete button for administrators', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);

    renderProjectsPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Metro Line Extension')).toBeInTheDocument();
      expect(screen.getByText('Airport CCTV Retrofit')).toBeInTheDocument();
    });

    expect(screen.getByTestId('delete-project-proj-1')).toBeInTheDocument();
    expect(screen.getByTestId('delete-project-proj-2')).toBeInTheDocument();
  });

  it('allows administrator to delete a project with confirmation modal', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.deleteProjectApi).mockResolvedValue({ status: 'success', message: 'Project deleted' });

    renderProjectsPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Metro Line Extension')).toBeInTheDocument();
    });

    // Click delete
    fireEvent.click(screen.getByTestId('delete-project-proj-1'));
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to permanently delete project/)).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
    expect(masterDataApi.deleteProjectApi).not.toHaveBeenCalled();

    // Confirm delete
    fireEvent.click(screen.getByTestId('delete-project-proj-1'));
    fireEvent.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(masterDataApi.deleteProjectApi).toHaveBeenCalledWith('proj-1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toBeInTheDocument();
    });
  });

  it('hides delete button when viewed by non-administrator role', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);

    renderProjectsPage('director');

    await waitFor(() => {
      expect(screen.getByText('Metro Line Extension')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('delete-project-proj-1')).not.toBeInTheDocument();
  });
});

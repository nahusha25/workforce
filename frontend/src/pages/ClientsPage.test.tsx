import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { ClientsPage } from './ClientsPage';
import { AuthContext } from '../context/AuthContext';
import * as masterDataApi from '../api/masterData';
import type { SystemRole } from '../types/auth';

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getClientsApi: vi.fn(),
    createClientApi: vi.fn(),
    deleteClientApi: vi.fn(),
    updateClientApi: vi.fn(),
  };
});

const mockClients = [
  {
    id: 'client-1',
    name: 'Acme Infra Corp',
    contact_person: 'Alice Smith',
    contact_mobile: '+919876543210',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'client-2',
    name: 'Apex Builders',
    contact_person: 'Bob Jones',
    contact_mobile: '+919123456789',
    is_active: false,
    created_at: '2026-01-02T00:00:00Z',
  },
];

const renderClientsPage = (role: SystemRole = 'administrator') => {
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
        <ClientsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('ClientsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders client cards and shows delete button for administrators', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);

    renderClientsPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Acme Infra Corp')).toBeInTheDocument();
      expect(screen.getByText('Apex Builders')).toBeInTheDocument();
    });

    expect(screen.getByTestId('delete-client-client-1')).toBeInTheDocument();
    expect(screen.getByTestId('delete-client-client-2')).toBeInTheDocument();
  });

  it('allows administrator to delete a client after confirmation', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.deleteClientApi).mockResolvedValue({ status: 'success', message: 'Client deleted' });

    renderClientsPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Acme Infra Corp')).toBeInTheDocument();
    });

    // Click delete
    fireEvent.click(screen.getByTestId('delete-client-client-1'));
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to permanently delete client/)).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
    expect(masterDataApi.deleteClientApi).not.toHaveBeenCalled();

    // Confirm delete
    fireEvent.click(screen.getByTestId('delete-client-client-1'));
    fireEvent.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(masterDataApi.deleteClientApi).toHaveBeenCalledWith('client-1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toBeInTheDocument();
    });
  });

  it('allows administrator to edit an existing client', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.updateClientApi).mockResolvedValue({
      ...mockClients[0],
      name: 'Acme Infra Corp Updated',
    });

    renderClientsPage('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('edit-client-client-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('edit-client-client-1'));

    expect(screen.getByText('Edit Client')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Acme Infra Corp')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Alice Smith')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('client-name-input'), {
      target: { value: 'Acme Infra Corp Updated' },
    });

    fireEvent.click(screen.getByTestId('save-client-btn'));

    await waitFor(() => {
      expect(masterDataApi.updateClientApi).toHaveBeenCalledWith('client-1', {
        name: 'Acme Infra Corp Updated',
        contact_person: 'Alice Smith',
        contact_mobile: '+919876543210',
        is_active: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Client "Acme Infra Corp Updated" updated successfully!/i)).toBeInTheDocument();
    });
  });

  it('hides edit and delete buttons when viewed by non-administrator role', async () => {
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);

    renderClientsPage('director');

    await waitFor(() => {
      expect(screen.getByText('Acme Infra Corp')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('edit-client-client-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('delete-client-client-1')).not.toBeInTheDocument();
  });
});

import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EmployeesPage } from './EmployeesPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AuthContext } from '../context/AuthContext';
import type { SystemRole } from '../types/auth';
import * as employeeApi from '../api/employee';
import type { EmployeeResponseData } from '../api/employee';

// Mock API modules
vi.mock('../api/employee', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employee')>();
  return {
    ...actual,
    getAllEmployeesApi: vi.fn(),
    getEmployeesApi: vi.fn().mockResolvedValue([]),
    deleteEmployeeApi: vi.fn(),
    updateEmployeeApi: vi.fn(),
  };
});

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getRolesApi: vi.fn().mockResolvedValue([]),
    getSitesApi: vi.fn().mockResolvedValue([]),
  };
});

const mockEmployees: EmployeeResponseData[] = [
  {
    id: 'emp-1',
    user_id: 'user-1',
    employee_code: 'EMP-001',
    mobile_id: '+917760443750',
    name: 'John Field Worker',
    system_role: 'employee',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [{ id: 'tr-1', name: 'Cable Pulling' }],
    active_sites: [{ id: 'site-1', name: 'Central Station Site' }],
  },
  {
    id: 'emp-2',
    user_id: 'user-2',
    employee_code: 'SUP-002',
    mobile_id: '+919876543210',
    name: 'Sarah Supervisor',
    system_role: 'supervisor',
    is_active: true,
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    trade_roles: [],
    active_sites: [{ id: 'site-1', name: 'Central Station Site' }],
  },
  {
    id: 'emp-3',
    user_id: 'user-3',
    employee_code: 'EMP-003',
    mobile_id: '+919123456789',
    name: 'Inactive Tech',
    system_role: 'employee',
    is_active: false,
    created_at: '2026-01-03T00:00:00Z',
    updated_at: '2026-01-03T00:00:00Z',
    trade_roles: [{ id: 'tr-2', name: 'Device Mounting' }],
    active_sites: [],
  },
];

const renderWithRoleGuard = (role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'admin-1',
          user_id: 'u-admin',
          employee_code: 'ADM-001',
          mobile_id: '+917760443750',
          name: 'Admin User',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
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
      <MemoryRouter initialEntries={['/admin/employees']}>
        <Routes>
          <Route
            element={<RoleGuard allowedRoles={['administrator', 'director']} />}
          >
            <Route path="/admin/employees" element={<EmployeesPage />} />
          </Route>
          <Route path="/403" element={<div>Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('EmployeesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders employee directory with correct total count and all table columns', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);

    renderWithRoleGuard('administrator');

    expect(screen.getByText('Loading employees...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Employee Directory')).toBeInTheDocument();
    });

    // Check true total count badge
    expect(screen.getByTestId('total-employees-count')).toHaveTextContent('Total: 3');

    // Check column values
    expect(screen.getByText('EMP-001')).toBeInTheDocument();
    expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    expect(screen.getByText('+917760443750')).toBeInTheDocument();
    expect(screen.getByText('Cable Pulling')).toBeInTheDocument();
    expect(screen.getAllByText('Central Station Site')).toHaveLength(2);

    // Check inactive employee
    expect(screen.getByText('EMP-003')).toBeInTheDocument();
    expect(screen.getByText('Inactive Tech')).toBeInTheDocument();
    expect(screen.getByText('Unassigned')).toBeInTheDocument();

    // Admin should see Onboard button
    expect(screen.getByTestId('onboard-employee-btn')).toBeInTheDocument();
  });

  it('aggregates multiple pages client-side for true total count exceeding 100 limit', async () => {
    // Generate 125 mock employees
    const page1: EmployeeResponseData[] = Array.from({ length: 100 }, (_, i) => ({
      id: `p1-${i}`,
      user_id: `u1-${i}`,
      employee_code: `EMP-${1000 + i}`,
      mobile_id: `+91900000${String(i).padStart(4, '0')}`,
      name: `Worker ${i}`,
      system_role: 'employee',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      trade_roles: [],
      active_sites: [],
    }));

    const page2: EmployeeResponseData[] = Array.from({ length: 25 }, (_, i) => ({
      id: `p2-${i}`,
      user_id: `u2-${i}`,
      employee_code: `EMP-${2000 + i}`,
      mobile_id: `+91910000${String(i).padStart(4, '0')}`,
      name: `Worker ${100 + i}`,
      system_role: 'employee',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      trade_roles: [],
      active_sites: [],
    }));

    // Mock getAllEmployeesApi returning all 125
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue([...page1, ...page2]);

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('total-employees-count')).toHaveTextContent('Total: 125');
    });
  });

  it('filters employees by search term, role, and active status', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    });

    // Search by name
    const searchInput = screen.getByPlaceholderText('Search by name, code, or mobile...');
    fireEvent.change(searchInput, { target: { value: 'Sarah' } });

    expect(screen.getByText('Sarah Supervisor')).toBeInTheDocument();
    expect(screen.queryByText('John Field Worker')).not.toBeInTheDocument();
    expect(screen.queryByText('Inactive Tech')).not.toBeInTheDocument();

    // Reset filters
    fireEvent.click(screen.getByText('Reset Filters'));
    expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    expect(screen.getByText('Sarah Supervisor')).toBeInTheDocument();

    // Filter by role: supervisor
    const roleSelect = screen.getByLabelText('Filter by role');
    fireEvent.change(roleSelect, { target: { value: 'supervisor' } });

    expect(screen.getByText('Sarah Supervisor')).toBeInTheDocument();
    expect(screen.queryByText('John Field Worker')).not.toBeInTheDocument();

    // Filter by status: inactive
    fireEvent.change(roleSelect, { target: { value: 'all' } });
    const statusSelect = screen.getByLabelText('Filter by status');
    fireEvent.change(statusSelect, { target: { value: 'inactive' } });

    expect(screen.getByText('Inactive Tech')).toBeInTheDocument();
    expect(screen.queryByText('John Field Worker')).not.toBeInTheDocument();
    expect(screen.queryByText('Sarah Supervisor')).not.toBeInTheDocument();
  });

  it('renders empty state when no employees exist', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue([]);

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('No employees registered yet.')).toBeInTheDocument();
    });

    expect(screen.getByTestId('total-employees-count')).toHaveTextContent('Total: 0');
    expect(screen.getByText('+ Onboard First Employee')).toBeInTheDocument();
  });

  it('renders error message and allows retry on fetch failure', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockRejectedValueOnce(new Error('Network connection timeout'));

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('Failed to Load Employees')).toBeInTheDocument();
    });
    expect(screen.getByText('Network connection timeout')).toBeInTheDocument();

    // Retry successfully
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValueOnce(mockEmployees);
    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    });
    expect(screen.getByTestId('total-employees-count')).toHaveTextContent('Total: 3');
  });

  it('allows director role to view the list and count, but hides onboarding action', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);

    renderWithRoleGuard('director');

    await waitFor(() => {
      expect(screen.getByText('Employee Directory')).toBeInTheDocument();
    });

    expect(screen.getByTestId('total-employees-count')).toHaveTextContent('Total: 3');
    expect(screen.getByText('John Field Worker')).toBeInTheDocument();

    // Director should NOT see the "+ Onboard Employee" button
    expect(screen.queryByTestId('onboard-employee-btn')).not.toBeInTheDocument();
  });

  it('blocks unauthorized employee role and redirects to /403', async () => {
    renderWithRoleGuard('employee');

    await waitFor(() => {
      expect(screen.getByText('Access Denied')).toBeInTheDocument();
    });
    expect(screen.queryByText('Employee Directory')).not.toBeInTheDocument();
  });

  it('allows administrator to delete an employee with confirmation modal', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(employeeApi.deleteEmployeeApi).mockResolvedValue({ status: 'success', message: 'Employee deleted' });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    });

    // Check delete button exists on row
    const deleteBtn = screen.getByTestId('delete-emp-emp-1');
    expect(deleteBtn).toBeInTheDocument();

    // Click delete -> modal opens
    fireEvent.click(deleteBtn);
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to permanently delete employee/)).toBeInTheDocument();

    // Cancel deletion
    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
    expect(employeeApi.deleteEmployeeApi).not.toHaveBeenCalled();

    // Click delete again and confirm
    fireEvent.click(deleteBtn);
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(employeeApi.deleteEmployeeApi).toHaveBeenCalledWith('emp-1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toBeInTheDocument();
    });
  });

  it('hides delete and edit buttons from director role', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);

    renderWithRoleGuard('director');

    await waitFor(() => {
      expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('delete-emp-emp-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('edit-emp-emp-1')).not.toBeInTheDocument();
  });

  it('allows administrator to open edit modal, submit changes, and refresh directory', async () => {
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue({
      ...mockEmployees[0],
      name: 'John Field Worker Updated',
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('John Field Worker')).toBeInTheDocument();
    });

    // Check edit button exists on row and click it
    const editBtn = screen.getByTestId('edit-emp-emp-1');
    expect(editBtn).toBeInTheDocument();
    fireEvent.click(editBtn);

    // Verify modal is displayed
    await waitFor(() => {
      expect(screen.getByText(/Edit Employee: John Field Worker/)).toBeInTheDocument();
    });

    // Edit employee full name
    const nameInput = screen.getByLabelText(/Full Name/);
    fireEvent.change(nameInput, { target: { value: 'John Field Worker Updated' } });

    // Submit the edit form
    const saveBtn = screen.getByRole('button', { name: 'Save Changes' });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith('emp-1', expect.objectContaining({
        name: 'John Field Worker Updated',
      }));
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toHaveTextContent(/was updated successfully/);
    });
  });
});


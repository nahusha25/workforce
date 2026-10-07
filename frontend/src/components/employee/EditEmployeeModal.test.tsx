import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { EditEmployeeModal } from './EditEmployeeModal';
import * as employeeApi from '../../api/employee';
import * as masterDataApi from '../../api/masterData';

vi.mock('../../api/employee', () => ({
  getEmployeesApi: vi.fn(),
  updateEmployeeApi: vi.fn(),
}));

vi.mock('../../api/masterData', () => ({
  getRolesApi: vi.fn(),
  getSitesApi: vi.fn(),
}));

const mockEmployee: employeeApi.EmployeeResponseData = {
  id: 'emp-1',
  user_id: 'user-1',
  employee_code: 'EMP-101',
  mobile_id: '+919876543210',
  name: 'Ramesh Kumar',
  system_role: 'employee',
  supervisor_id: 'sup-1',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  trade_roles: [{ id: 'role-1', name: 'Electrician' }],
  current_rate: {
    id: 'rate-1',
    rate_type: 'daily',
    rate_amount: 550,
    effective_from: '2026-01-01',
  },
  active_sites: [{ id: 'site-1', name: 'Site Alpha' }],
};

const mockRoles = [
  { id: 'role-1', name: 'Electrician' },
  { id: 'role-2', name: 'Plumber' },
];

const mockSites = [
  { id: 'site-1', name: 'Site Alpha', project_id: 'p-1', is_active: true },
  { id: 'site-2', name: 'Site Beta', project_id: 'p-1', is_active: true },
];

const mockSupervisors: employeeApi.EmployeeResponseData[] = [
  {
    id: 'sup-1',
    user_id: 'user-sup',
    employee_code: 'SUP-01',
    mobile_id: '+919999999991',
    name: 'Suresh Supervisor',
    system_role: 'supervisor',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  },
];

describe('EditEmployeeModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(masterDataApi.getRolesApi).mockResolvedValue(mockRoles);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites as any);
    vi.mocked(employeeApi.getEmployeesApi).mockResolvedValue(mockSupervisors);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders prefilled fields when modal is open', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={mockEmployee}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Edit Employee: Ramesh Kumar \(EMP-101\)/)).toBeInTheDocument();
      expect(screen.getByDisplayValue('Ramesh Kumar')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+919876543210')).toBeInTheDocument();
      expect(screen.getByDisplayValue('550')).toBeInTheDocument();
    });

    expect(screen.getByTestId('edit-emp-system-role-select')).toHaveValue('employee');
    expect(screen.getByTestId('edit-emp-supervisor-select')).toHaveValue('sup-1');
    expect(screen.getByTestId('trade-role-role-1')).toBeChecked();
    expect(screen.getByTestId('site-assign-site-1')).toBeChecked();
    expect(screen.getByTestId('edit-emp-active-checkbox')).toBeChecked();
  });

  it('calls onClose when cancel or close button is clicked', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={mockEmployee}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('cancel-edit-emp-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('cancel-edit-emp-btn'));
    expect(handleClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('close-edit-employee-modal-btn'));
    expect(handleClose).toHaveBeenCalledTimes(2);
  });

  it('closes on Escape key press', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={mockEmployee}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Edit Employee: Ramesh Kumar/)).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('submits updated values and calls onSaved', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();
    const updatedEmployee = { ...mockEmployee, name: 'Ramesh K. Sharma', system_role: 'supervisor' as const };

    vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedEmployee);

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={mockEmployee}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-emp-name-input')).toBeInTheDocument();
    });

    // Change name
    fireEvent.change(screen.getByTestId('edit-emp-name-input'), {
      target: { value: 'Ramesh K. Sharma' },
    });
    // Change system role
    fireEvent.change(screen.getByTestId('edit-emp-system-role-select'), {
      target: { value: 'supervisor' },
    });
    // Toggle additional trade role
    fireEvent.click(screen.getByTestId('trade-role-role-2'));
    // Toggle additional site
    fireEvent.click(screen.getByTestId('site-assign-site-2'));

    // Submit
    fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

    await waitFor(() => {
      expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith('emp-1', {
        name: 'Ramesh K. Sharma',
        mobile_number: '+919876543210',
        system_role: 'supervisor',
        trade_role_ids: ['role-1', 'role-2'],
        rate_type: 'daily',
        rate_amount: 550,
        supervisor_id: 'sup-1',
        site_ids: ['site-1', 'site-2'],
        is_active: true,
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedEmployee);
    });
  });

  it('displays API error message when update fails', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();

    vi.mocked(employeeApi.updateEmployeeApi).mockRejectedValue(new Error('Mobile already registered'));

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={mockEmployee}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('save-edit-emp-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

    await waitFor(() => {
      expect(screen.getByText('Mobile already registered')).toBeInTheDocument();
    });
    expect(handleSaved).not.toHaveBeenCalled();
  });
});

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
  classification: 'regular',
  system_role: 'employee',
  supervisor_id: 'sup-1',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  trade_roles: [{ id: 'role-1', name: 'Electrician' }],
  current_rate: {
    id: 'rate-1',
    rate_type: 'monthly',
    rate_amount: 15000,
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
    classification: 'regular',
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
      expect(screen.getByDisplayValue('15000')).toBeInTheDocument();
    });

    expect(screen.getByTestId('edit-emp-classification-select')).toHaveValue('regular');
    expect(screen.getByTestId('edit-emp-system-role-select')).toHaveValue('employee');
    expect(screen.getByTestId('edit-emp-rate-type-select')).toHaveValue('monthly');
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
        classification: 'regular',
        system_role: 'supervisor',
        trade_role_ids: ['role-1', 'role-2'],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: 'sup-1',
        site_ids: ['site-1', 'site-2'],
        is_active: true,
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedEmployee);
    });
  });

  it('requires at least one site when employee is classified as Contract Employee', async () => {
    const handleClose = vi.fn();
    const handleSaved = vi.fn();

    render(
      <EditEmployeeModal
        isOpen={true}
        employee={{ ...mockEmployee, system_role: 'director', classification: 'regular' }}
        onClose={handleClose}
        onSaved={handleSaved}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('edit-emp-classification-select')).toBeInTheDocument();
    });

    // Uncheck currently assigned site
    fireEvent.click(screen.getByTestId('site-assign-site-1'));

    // Switch classification to contract
    fireEvent.change(screen.getByTestId('edit-emp-classification-select'), {
      target: { value: 'contract' },
    });

    // Attempt to save
    fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

    await waitFor(() => {
      expect(
        screen.getByText('Contract employee must be assigned to at least one site/project.')
      ).toBeInTheDocument();
    });

    expect(employeeApi.updateEmployeeApi).not.toHaveBeenCalled();
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

  describe('Conditional Assigned Client Site(s) Validation', () => {
    it('displays required indicator for Employee and Supervisor', async () => {
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
        expect(screen.getByText('Assigned Client Sites * (Select at least one)')).toBeInTheDocument();
      });

      // Switch to supervisor
      fireEvent.change(screen.getByTestId('edit-emp-system-role-select'), {
        target: { value: 'supervisor' },
      });

      expect(screen.getByText('Assigned Client Sites * (Select at least one)')).toBeInTheDocument();
    });

    it('displays optional indicator for Director and Administrator', async () => {
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
        expect(screen.getByTestId('edit-emp-system-role-select')).toBeInTheDocument();
      });

      // Switch to director
      fireEvent.change(screen.getByTestId('edit-emp-system-role-select'), {
        target: { value: 'director' },
      });
      expect(screen.getByText('Assigned Client Sites (Optional)')).toBeInTheDocument();

      // Switch to administrator
      fireEvent.change(screen.getByTestId('edit-emp-system-role-select'), {
        target: { value: 'administrator' },
      });
      expect(screen.getByText('Assigned Client Sites (Optional)')).toBeInTheDocument();
    });

    it('blocks saving Employee when all client sites are deselected', async () => {
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
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
      });

      // Uncheck the currently checked site
      fireEvent.click(screen.getByTestId('site-assign-site-1'));

      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(
          screen.getByText('At least one Client Site must be assigned for Field Worker.')
        ).toBeInTheDocument();
      });

      expect(employeeApi.updateEmployeeApi).not.toHaveBeenCalled();
    });

    it('blocks saving Supervisor when all client sites are deselected', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={{ ...mockEmployee, system_role: 'supervisor' }}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
      });

      // Uncheck site
      fireEvent.click(screen.getByTestId('site-assign-site-1'));

      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(
          screen.getByText('At least one Client Site must be assigned for Supervisor.')
        ).toBeInTheDocument();
      });

      expect(employeeApi.updateEmployeeApi).not.toHaveBeenCalled();
    });

    it('allows saving Director with empty site assignments', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();
      const updatedDir = { ...mockEmployee, system_role: 'director' as const, active_sites: [] };
      vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedDir);

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={{ ...mockEmployee, system_role: 'director' }}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
      });

      // Uncheck site
      fireEvent.click(screen.getByTestId('site-assign-site-1'));

      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith('emp-1', expect.objectContaining({
          system_role: 'director',
          site_ids: [],
        }));
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedDir);
    });

    it('allows saving Administrator with empty site assignments', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();
      const updatedAdmin = { ...mockEmployee, system_role: 'administrator' as const, active_sites: [] };
      vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedAdmin);

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={{ ...mockEmployee, system_role: 'administrator' }}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
      });

      // Uncheck site
      fireEvent.click(screen.getByTestId('site-assign-site-1'));

      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith('emp-1', expect.objectContaining({
          system_role: 'administrator',
          site_ids: [],
        }));
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedAdmin);
    });

    it('requires at least one site when changing role from Director (with 0 sites) to Supervisor', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={{ ...mockEmployee, system_role: 'director', active_sites: [] }}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('edit-emp-system-role-select')).toBeInTheDocument();
      });

      // Change role to supervisor
      fireEvent.change(screen.getByTestId('edit-emp-system-role-select'), {
        target: { value: 'supervisor' },
      });

      // Attempt to save with 0 sites
      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(
          screen.getByText('At least one Client Site must be assigned for Supervisor.')
        ).toBeInTheDocument();
      });

      expect(employeeApi.updateEmployeeApi).not.toHaveBeenCalled();

      // Now select a site
      fireEvent.click(screen.getByTestId('site-assign-site-2'));

      const updatedSup = { ...mockEmployee, system_role: 'supervisor' as const, active_sites: [mockSites[1] as any] };
      vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedSup);

      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith('emp-1', expect.objectContaining({
          system_role: 'supervisor',
          site_ids: ['site-2'],
        }));
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedSup);
    });

    it('allows assigning multiple client sites and submitting both site IDs', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();

      // Michel with initial site-1
      const michel = {
        ...mockEmployee,
        id: 'emp-2',
        name: 'Michel',
        employee_code: 'EMP-2',
        system_role: 'supervisor' as const,
        active_sites: [mockSites[0]],
      };

      const updatedMichel = {
        ...michel,
        active_sites: [mockSites[0], mockSites[1]],
      };
      vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedMichel as any);

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={michel as any}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
        expect(screen.getByTestId('site-assign-site-2')).toBeInTheDocument();
      });

      // Initially site-1 is checked, site-2 is unchecked
      expect(screen.getByTestId('site-assign-site-1')).toBeChecked();
      expect(screen.getByTestId('site-assign-site-2')).not.toBeChecked();

      // Check site-2 so both site-1 and site-2 are selected
      fireEvent.click(screen.getByTestId('site-assign-site-2'));
      expect(screen.getByTestId('site-assign-site-2')).toBeChecked();

      // Click save
      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith(
          'emp-2',
          expect.objectContaining({
            site_ids: expect.arrayContaining(['site-1', 'site-2']),
          })
        );
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedMichel);
    });

    it('allows removing a site when multiple sites are initially assigned', async () => {
      const handleClose = vi.fn();
      const handleSaved = vi.fn();

      const multiSiteEmp = {
        ...mockEmployee,
        id: 'emp-3',
        name: 'Carlos',
        active_sites: [mockSites[0], mockSites[1]],
      };

      const updatedEmp = {
        ...multiSiteEmp,
        active_sites: [mockSites[1]],
      };
      vi.mocked(employeeApi.updateEmployeeApi).mockResolvedValue(updatedEmp as any);

      render(
        <EditEmployeeModal
          isOpen={true}
          employee={multiSiteEmp as any}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('site-assign-site-1')).toBeInTheDocument();
      });

      expect(screen.getByTestId('site-assign-site-1')).toBeChecked();
      expect(screen.getByTestId('site-assign-site-2')).toBeChecked();

      // Uncheck site-1
      fireEvent.click(screen.getByTestId('site-assign-site-1'));
      expect(screen.getByTestId('site-assign-site-1')).not.toBeChecked();
      expect(screen.getByTestId('site-assign-site-2')).toBeChecked();

      // Save
      fireEvent.click(screen.getByTestId('save-edit-emp-btn'));

      await waitFor(() => {
        expect(employeeApi.updateEmployeeApi).toHaveBeenCalledWith(
          'emp-3',
          expect.objectContaining({
            site_ids: ['site-2'],
          })
        );
      });
      expect(handleSaved).toHaveBeenCalledWith(updatedEmp);
    });
  });
});

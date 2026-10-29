import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { OnboardingPage } from './OnboardingPage';
import * as employeeApi from '../api/employee';
import * as masterDataApi from '../api/masterData';

vi.mock('../api/employee', () => ({
  createEmployeeApi: vi.fn(),
  getEmployeesApi: vi.fn(),
}));

vi.mock('../api/masterData', () => ({
  getRolesApi: vi.fn(),
  getSitesApi: vi.fn(),
}));

const mockRoles: masterDataApi.RoleResponseData[] = [
  { id: 'role-tech', name: 'Technician', description: 'Field Technician' },
];

const mockSites: masterDataApi.SiteResponseData[] = [
  { id: 'site-1', name: 'Site Alpha', project_id: 'proj-1', is_active: true },
];

const mockEmployees: employeeApi.EmployeeResponseData[] = [
  {
    id: 'emp-sup-1',
    user_id: 'user-sup-1',
    employee_code: 'SUP-001',
    mobile_id: '+919988776655',
    name: 'Senior Supervisor',
    system_role: 'supervisor',
    supervisor_id: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  },
];

describe('OnboardingPage - Conditional Trade / Job Role Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(masterDataApi.getRolesApi).mockResolvedValue(mockRoles);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(employeeApi.getEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(employeeApi.createEmployeeApi).mockResolvedValue({
      id: 'new-emp-id',
      user_id: 'new-user-id',
      employee_code: 'EMP-999',
      mobile_id: '+919876543210',
      name: 'Test Onboard',
      system_role: 'employee',
      is_active: true,
      created_at: '2026-10-14T00:00:00Z',
      updated_at: '2026-10-14T00:00:00Z',
      trade_roles: [{ id: 'role-tech', name: 'Technician' }],
      active_sites: [{ id: 'site-1', name: 'Site Alpha' }],
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders required indicator for Trade Role when system role is Employee (Field Worker)', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByText('Employee Onboarding')).toBeInTheDocument();
    });

    expect(screen.getByText('Trade / Job Role(s) * (Select at least 1)')).toBeInTheDocument();
  });

  it('rejects onboarding of Employee (Field Worker) without a trade role', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
    });

    // Fill form without selecting trade role
    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Field Worker One' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543210' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'EMP-001' } });
    // Check site
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(
        screen.getByText('At least one Trade Role must be selected for Employee (Field Worker).')
      ).toBeInTheDocument();
    });

    expect(employeeApi.createEmployeeApi).not.toHaveBeenCalled();
  });

  it('successfully onboards Employee (Field Worker) when Technician role is selected', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Field Worker One' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543210' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'EMP-001' } });
    // Select Technician trade role
    fireEvent.click(screen.getByLabelText('Technician'));
    // Select Site
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
        name: 'Field Worker One',
        mobile_number: '+919876543210',
        employee_code: 'EMP-001',
        classification: 'regular',
        system_role: 'employee',
        trade_role_ids: ['role-tech'],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: undefined,
        site_ids: ['site-1'],
      });
    });
  });

  it('displays Trade Role as (Optional) and successfully onboards Supervisor without trade role', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
    });

    // Select Supervisor
    fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'supervisor' } });

    expect(screen.getByText('Trade / Job Role(s) (Optional)')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Supervisor Jane' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543211' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'SUP-002' } });
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
        name: 'Supervisor Jane',
        mobile_number: '+919876543211',
        employee_code: 'SUP-002',
        classification: 'regular',
        system_role: 'supervisor',
        trade_role_ids: [],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: undefined,
        site_ids: ['site-1'],
      });
    });
  });

  it('displays Trade Role as (Optional) and successfully onboards Director without trade role', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
    });

    // Select Director
    fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'director' } });

    expect(screen.getByText('Trade / Job Role(s) (Optional)')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Director Dave' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543212' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'DIR-001' } });
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
        name: 'Director Dave',
        mobile_number: '+919876543212',
        employee_code: 'DIR-001',
        classification: 'regular',
        system_role: 'director',
        trade_role_ids: [],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: undefined,
        site_ids: ['site-1'],
      });
    });
  });

  it('displays Trade Role as (Optional) and successfully onboards Administrator without trade role', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
    });

    // Select Administrator
    fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'administrator' } });

    expect(screen.getByText('Trade / Job Role(s) (Optional)')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Admin Alice' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543213' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'ADM-001' } });
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
        name: 'Admin Alice',
        mobile_number: '+919876543213',
        employee_code: 'ADM-001',
        classification: 'regular',
        system_role: 'administrator',
        trade_role_ids: [],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: undefined,
        site_ids: ['site-1'],
      });
    });
  });

  it('allows non-employee roles to optionally select trade roles', async () => {
    render(<OnboardingPage />);

    await waitFor(() => {
      expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
    });

    // Select Supervisor
    fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'supervisor' } });
    fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Supervisor with Trade' } });
    fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543214' } });
    fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'SUP-003' } });
    // Optionally check Technician
    fireEvent.click(screen.getByLabelText('Technician'));
    fireEvent.click(screen.getByLabelText('Site Alpha'));

    fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

    await waitFor(() => {
      expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
        name: 'Supervisor with Trade',
        mobile_number: '+919876543214',
        employee_code: 'SUP-003',
        classification: 'regular',
        system_role: 'supervisor',
        trade_role_ids: ['role-tech'],
        rate_type: 'monthly',
        rate_amount: 15000,
        supervisor_id: undefined,
        site_ids: ['site-1'],
      });
    });
  });

  describe('Conditional Assigned Client Site(s) Validation', () => {
    it('renders required indicator for Assigned Client Site(s) when system role is Employee (Field Worker)', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByText('Employee Onboarding')).toBeInTheDocument();
      });

      expect(screen.getByText('Assigned Client Site(s) * (Select at least 1)')).toBeInTheDocument();
    });

    it('renders required indicator for Assigned Client Site(s) when system role is Supervisor', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'supervisor' } });

      expect(screen.getByText('Assigned Client Site(s) * (Select at least 1)')).toBeInTheDocument();
    });

    it('renders optional indicator for Assigned Client Site(s) when system role is Director', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'director' } });

      expect(screen.getByText('Assigned Client Site(s) (Optional)')).toBeInTheDocument();
    });

    it('renders optional indicator for Assigned Client Site(s) when system role is Administrator', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'administrator' } });

      expect(screen.getByText('Assigned Client Site(s) (Optional)')).toBeInTheDocument();
    });

    it('rejects onboarding of Employee (Field Worker) without selecting any site', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Field Worker No Site' } });
      fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543220' } });
      fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'EMP-020' } });
      // Select Technician
      fireEvent.click(screen.getByLabelText('Technician'));
      // No site selected

      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(screen.getByText('At least one Client Site must be assigned for Employee (Field Worker).')).toBeInTheDocument();
      });

      expect(employeeApi.createEmployeeApi).not.toHaveBeenCalled();
    });

    it('rejects onboarding of Supervisor without selecting any site', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'supervisor' } });
      fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Supervisor No Site' } });
      fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543221' } });
      fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'SUP-021' } });
      // No site selected

      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(screen.getByText('At least one Client Site must be assigned for Supervisor.')).toBeInTheDocument();
      });

      expect(employeeApi.createEmployeeApi).not.toHaveBeenCalled();
    });

    it('successfully onboards Director without selecting any site', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'director' } });
      fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Director No Site' } });
      fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543222' } });
      fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'DIR-022' } });
      // No site selected

      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
          name: 'Director No Site',
          mobile_number: '+919876543222',
          employee_code: 'DIR-022',
          classification: 'regular',
          system_role: 'director',
          trade_role_ids: [],
          rate_type: 'monthly',
          rate_amount: 15000,
          supervisor_id: undefined,
          site_ids: [],
        });
      });
    });

    it('successfully onboards Administrator without selecting any site', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/System Role/)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'administrator' } });
      fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Admin No Site' } });
      fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543223' } });
      fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'ADM-023' } });
      // No site selected

      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
          name: 'Admin No Site',
          mobile_number: '+919876543223',
          employee_code: 'ADM-023',
          classification: 'regular',
          system_role: 'administrator',
          trade_role_ids: [],
          rate_type: 'monthly',
          rate_amount: 15000,
          supervisor_id: undefined,
          site_ids: [],
        });
      });
    });

    it('requires assigned site for Contract Employee regardless of system role', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Employee Classification/)).toBeInTheDocument();
      });

      // Select Director role (normally doesn't require site) but set classification to Contract
      fireEvent.change(screen.getByLabelText(/System Role/), { target: { value: 'director' } });
      fireEvent.change(screen.getByLabelText(/Employee Classification/), { target: { value: 'contract' } });
      fireEvent.change(screen.getByLabelText(/Full Name/), { target: { value: 'Contract Director' } });
      fireEvent.change(screen.getByLabelText(/Mobile Number/), { target: { value: '9876543224' } });
      fireEvent.change(screen.getByLabelText(/Employee Code/), { target: { value: 'CNT-001' } });

      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(screen.getByText('Contract employee must be assigned to at least one site/project.')).toBeInTheDocument();
      });
      expect(employeeApi.createEmployeeApi).not.toHaveBeenCalled();

      // Now assign a site
      fireEvent.click(screen.getByLabelText('Site Alpha'));
      fireEvent.click(screen.getByRole('button', { name: /Onboard Employee/i }));

      await waitFor(() => {
        expect(employeeApi.createEmployeeApi).toHaveBeenCalledWith({
          name: 'Contract Director',
          mobile_number: '+919876543224',
          employee_code: 'CNT-001',
          classification: 'contract',
          system_role: 'director',
          trade_role_ids: [],
          rate_type: 'monthly',
          rate_amount: 15000,
          supervisor_id: undefined,
          site_ids: ['site-1'],
        });
      });
    });

    it('only provides monthly pay frequency in rate type options', async () => {
      render(<OnboardingPage />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Pay Frequency \/ Rate Type/)).toBeInTheDocument();
      });

      const rateTypeSelect = screen.getByLabelText(/Pay Frequency \/ Rate Type/);
      expect(rateTypeSelect).toHaveValue('monthly');
      expect(screen.queryByText('Daily Rate')).not.toBeInTheDocument();
      expect(screen.queryByText('Weekly Rate')).not.toBeInTheDocument();
      expect(screen.getByText('Monthly Fixed Rate')).toBeInTheDocument();
    });
  });
});

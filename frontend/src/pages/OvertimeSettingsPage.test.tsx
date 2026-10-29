import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { OvertimeSettingsPage } from './OvertimeSettingsPage';
import { AuthContext } from '../context/AuthContext';
import * as payrollSettingsApi from '../api/payrollSettings';
import type { EmployeeProfile, SystemRole } from '../types/auth';

vi.mock('../api/payrollSettings', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/payrollSettings')>();
  return {
    ...actual,
    getOvertimeSettingsHistoryApi: vi.fn(),
    getEffectiveOvertimeSettingApi: vi.fn(),
    createOvertimeSettingApi: vi.fn(),
  };
});

const mockActiveSetting: payrollSettingsApi.PayrollOvertimeSettingsResponse = {
  id: 'ot-curr',
  standard_workday_hours: '7.00',
  overtime_multiplier: '1.50',
  effective_from: '2026-01-01',
  effective_to: null,
  description: 'Standard 2026 Labor Agreement',
  created_at: '2026-01-01T00:00:00Z',
};

const mockHistory: payrollSettingsApi.PayrollOvertimeSettingsResponse[] = [
  {
    id: 'ot-curr',
    standard_workday_hours: '7.00',
    overtime_multiplier: '1.50',
    effective_from: '2026-01-01',
    effective_to: null,
    description: 'Standard 2026 Labor Agreement',
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'ot-past',
    standard_workday_hours: '8.00',
    overtime_multiplier: '1.25',
    effective_from: '2025-01-01',
    effective_to: '2025-12-31',
    description: 'Historical 2025 Standard',
    created_at: '2025-01-01T00:00:00Z',
  },
];

const renderPage = (role: SystemRole = 'administrator') => {
  const user: EmployeeProfile = {
    id: `user-${role}-1`,
    user_id: `u-${role}-1`,
    employee_code: `${role.slice(0, 3).toUpperCase()}001`,
    mobile_id: '+919999999999',
    name: `${role} User`,
    system_role: role,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  };

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
        <OvertimeSettingsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('OvertimeSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockResolvedValue(mockHistory);
    vi.mocked(payrollSettingsApi.getEffectiveOvertimeSettingApi).mockResolvedValue(mockActiveSetting);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders currently effective policy and configuration history for Administrator', async () => {
    renderPage('administrator');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Payroll Overtime Settings' })).toBeInTheDocument();
    });

    // Currently Effective Policy Card
    const policyCard = screen.getByTestId('active-overtime-policy');
    expect(policyCard).toHaveTextContent('7.00 hrs / day');
    expect(policyCard).toHaveTextContent('1.50x');
    expect(policyCard).toHaveTextContent('2026-01-01 to Present');
    expect(policyCard).toHaveTextContent('Standard 2026 Labor Agreement');

    // Admin create form is present
    expect(screen.getByRole('heading', { level: 3, name: 'Create Effective-Dated Configuration' })).toBeInTheDocument();
    expect(screen.getByTestId('input-standard-hours')).toBeInTheDocument();
    expect(screen.getByTestId('input-multiplier')).toBeInTheDocument();
    expect(screen.getByTestId('input-effective-from')).toBeInTheDocument();
    expect(screen.getByTestId('btn-create-overtime-setting')).toBeInTheDocument();

    // History table is rendered with both rows
    const historyTable = screen.getByTestId('overtime-history-table');
    expect(historyTable).toHaveTextContent('2026-01-01 to Present');
    expect(historyTable).toHaveTextContent('2025-01-01 to 2025-12-31');
    expect(historyTable).toHaveTextContent('8.00 hrs');
    expect(historyTable).toHaveTextContent('1.25x');
    expect(historyTable).toHaveTextContent('HISTORICAL');
    expect(historyTable).toHaveTextContent('ACTIVE');

    // Historical entries must be immutable - no delete or edit buttons
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
  });

  it('allows Administrator to create a new effective-dated configuration', async () => {
    const newSetting: payrollSettingsApi.PayrollOvertimeSettingsResponse = {
      id: 'ot-new',
      standard_workday_hours: '6.50',
      overtime_multiplier: '2.00',
      effective_from: '2026-11-01',
      effective_to: null,
      description: 'Peak season adjustment',
      created_at: '2026-10-14T00:00:00Z',
    };
    vi.mocked(payrollSettingsApi.createOvertimeSettingApi).mockResolvedValueOnce(newSetting);

    renderPage('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('btn-create-overtime-setting')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('input-standard-hours'), { target: { value: '6.50' } });
    fireEvent.change(screen.getByTestId('input-multiplier'), { target: { value: '2.00' } });
    fireEvent.change(screen.getByTestId('input-effective-from'), { target: { value: '2026-11-01' } });
    fireEvent.change(screen.getByTestId('input-description'), { target: { value: 'Peak season adjustment' } });

    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));

    await waitFor(() => {
      expect(payrollSettingsApi.createOvertimeSettingApi).toHaveBeenCalledWith({
        standard_workday_hours: 6.5,
        overtime_multiplier: 2.0,
        effective_from: '2026-11-01',
        description: 'Peak season adjustment',
      });
      expect(
        screen.getByText('New overtime setting created successfully, effective from 2026-11-01.')
      ).toBeInTheDocument();
    });
  });

  it('validates client-side constraints on standard hours, multiplier, and effective date', async () => {
    renderPage('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('btn-create-overtime-setting')).toBeInTheDocument();
    });

    // Test invalid standard workday hours (<= 0)
    fireEvent.change(screen.getByTestId('input-standard-hours'), { target: { value: '0' } });
    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));
    expect(screen.getByText('Standard workday hours must be greater than 0 and at most 24.')).toBeInTheDocument();
    expect(payrollSettingsApi.createOvertimeSettingApi).not.toHaveBeenCalled();

    // Test standard workday hours > 24
    fireEvent.change(screen.getByTestId('input-standard-hours'), { target: { value: '25' } });
    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));
    expect(screen.getByText('Standard workday hours must be greater than 0 and at most 24.')).toBeInTheDocument();

    // Reset standard hours to valid value, test invalid multiplier (< 1.0)
    fireEvent.change(screen.getByTestId('input-standard-hours'), { target: { value: '7.0' } });
    fireEvent.change(screen.getByTestId('input-multiplier'), { target: { value: '0.90' } });
    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));
    expect(screen.getByText('Overtime multiplier must be between 1.00 and 5.00.')).toBeInTheDocument();

    // Test multiplier > 5.0
    fireEvent.change(screen.getByTestId('input-multiplier'), { target: { value: '5.50' } });
    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));
    expect(screen.getByText('Overtime multiplier must be between 1.00 and 5.00.')).toBeInTheDocument();

    // Test missing effective date
    fireEvent.change(screen.getByTestId('input-multiplier'), { target: { value: '1.50' } });
    fireEvent.change(screen.getByTestId('input-effective-from'), { target: { value: '' } });
    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));
    expect(screen.getByText('Effective start date is required.')).toBeInTheDocument();
  });

  it('displays API error banner when creating overtime setting fails', async () => {
    vi.mocked(payrollSettingsApi.createOvertimeSettingApi).mockRejectedValueOnce({
      response: {
        data: {
          error: {
            message: 'An overtime setting already exists with this effective date.',
          },
        },
      },
    });

    renderPage('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('btn-create-overtime-setting')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('input-standard-hours'), { target: { value: '7.0' } });
    fireEvent.change(screen.getByTestId('input-multiplier'), { target: { value: '1.5' } });
    fireEvent.change(screen.getByTestId('input-effective-from'), { target: { value: '2026-01-01' } });

    fireEvent.submit(screen.getByTestId('form-create-overtime-setting'));

    await waitFor(() => {
      expect(
        screen.getByText('An overtime setting already exists with this effective date.')
      ).toBeInTheDocument();
    });
  });

  it('displays API error when settings history fails to load', async () => {
    vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockRejectedValueOnce({
      response: { data: { detail: 'Database connection failed' } },
    });

    renderPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Database connection failed')).toBeInTheDocument();
    });
  });

  it('renders Director view as read-only with notification banner and without create form', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByTestId('active-overtime-policy')).toBeInTheDocument();
    });

    // Policy and history are visible to Director
    expect(screen.getByTestId('active-overtime-policy')).toHaveTextContent('7.00 hrs / day');
    expect(screen.getByTestId('overtime-history-table')).toBeInTheDocument();

    // Read-only banner is displayed
    const readOnlyBanner = screen.getByTestId('director-readonly-banner');
    expect(readOnlyBanner).toBeInTheDocument();
    expect(readOnlyBanner).toHaveTextContent(
      'Directors have view-only permissions for overtime policies. Policy modifications require Administrator privileges.'
    );

    // Create form and submit button are NOT rendered
    expect(screen.queryByRole('heading', { level: 3, name: 'Create Effective-Dated Configuration' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('btn-create-overtime-setting')).not.toBeInTheDocument();
  });
});

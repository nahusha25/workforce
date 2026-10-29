import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { EmployeePaymentsPage, getOverlappingOvertimePolicies } from './EmployeePaymentsPage';
import { AuthContext } from '../context/AuthContext';
import * as employeePaymentsApi from '../api/employeePayments';
import * as employeeApi from '../api/employee';
import * as payrollSettingsApi from '../api/payrollSettings';
import type { EmployeeProfile, SystemRole } from '../types/auth';

vi.mock('../api/employeePayments', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employeePayments')>();
  return {
    ...actual,
    listEmployeePaymentsApi: vi.fn(),
    previewEmployeePaymentsApi: vi.fn(),
    generateEmployeePaymentsApi: vi.fn(),
    getEmployeePaymentApi: vi.fn(),
  };
});

vi.mock('../api/employee', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employee')>();
  return {
    ...actual,
    getAllEmployeesApi: vi.fn(),
    getEmployeesApi: vi.fn(),
  };
});

vi.mock('../api/payrollSettings', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/payrollSettings')>();
  return {
    ...actual,
    getEffectiveOvertimeSettingApi: vi.fn(),
    getOvertimeSettingsHistoryApi: vi.fn(),
  };
});

const mockPayments: employeePaymentsApi.EmployeePaymentResponse[] = [
  {
    id: 'pay-1',
    payment_number: 'PAY-20261010-0001',
    idempotency_key: 'idem-1',
    employee_id: 'emp-1',
    employee_name: 'Aarav Sharma',
    period_start: '2026-10-01',
    period_end: '2026-10-07',
    status: 'draft',
    total_amount: 3500.0,
    total_days: 5.0,
    total_quantity: 0.0,
    created_at: '2026-10-08T10:00:00Z',
    updated_at: '2026-10-08T10:00:00Z',
  },
  {
    id: 'pay-2',
    payment_number: 'PAY-20261010-0002',
    idempotency_key: 'idem-2',
    employee_id: 'emp-2',
    employee_name: 'Priya Patel',
    period_start: '2026-10-01',
    period_end: '2026-10-07',
    status: 'approved',
    total_amount: 4200.0,
    total_days: 6.0,
    total_quantity: 0.0,
    created_at: '2026-10-08T10:05:00Z',
    updated_at: '2026-10-08T11:00:00Z',
  },
  {
    id: 'pay-3',
    payment_number: 'PAY-20261010-0003',
    idempotency_key: 'idem-3',
    employee_id: 'emp-1',
    employee_name: 'Aarav Sharma',
    period_start: '2026-09-24',
    period_end: '2026-09-30',
    status: 'paid',
    total_amount: 3500.0,
    total_days: 5.0,
    total_quantity: 0.0,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-02T10:00:00Z',
  },
  {
    id: 'pay-4',
    payment_number: 'PAY-20261010-0004',
    idempotency_key: 'idem-4',
    employee_id: 'emp-3',
    employee_name: 'Rohan Gupta',
    period_start: '2026-09-24',
    period_end: '2026-09-30',
    status: 'cancelled',
    total_amount: 1500.0,
    total_days: 2.0,
    total_quantity: 0.0,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-02T10:00:00Z',
  },
];

const mockEmployees: employeeApi.EmployeeResponseData[] = [
  {
    id: 'emp-1',
    user_id: 'u-1',
    employee_code: 'EMP001',
    mobile_id: '+919876543210',
    name: 'Aarav Sharma',
    system_role: 'employee',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  },
  {
    id: 'emp-2',
    user_id: 'u-2',
    employee_code: 'EMP002',
    mobile_id: '+919876543211',
    name: 'Priya Patel',
    system_role: 'employee',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    trade_roles: [],
    active_sites: [],
  },
];

const mockPreviewResponse: employeePaymentsApi.EmployeePaymentPreviewResponse = {
  period_start: '2026-10-01',
  period_end: '2026-10-07',
  total_employees: 2,
  grand_total_amount: 7700.0,
  items: [
    {
      employee_id: 'emp-1',
      employee_name: 'Aarav Sharma',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      total_days: 5.0,
      total_quantity: 0.0,
      total_amount: 3500.0,
      eligible_attendance_count: 5,
      eligible_work_entry_count: 0,
      rate_band_summaries: [
        {
          rate_type: 'daily',
          rate_amount: 700.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          approved_days: 5.0,
          approved_quantity: 0.0,
          gross_amount: 3500.0,
        },
      ],
    },
    {
      employee_id: 'emp-2',
      employee_name: 'Priya Patel',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      total_days: 6.0,
      total_quantity: 0.0,
      total_amount: 4200.0,
      eligible_attendance_count: 6,
      eligible_work_entry_count: 0,
      rate_band_summaries: [
        {
          rate_type: 'daily',
          rate_amount: 700.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          approved_days: 6.0,
          approved_quantity: 0.0,
          gross_amount: 4200.0,
        },
      ],
    },
  ],
};

const renderPage = (role: SystemRole = 'director') => {
  const user: EmployeeProfile = {
    id: 'user-dir-1',
    user_id: 'u-dir-1',
    employee_code: 'DIR001',
    mobile_id: '+919999999999',
    name: 'Director User',
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
        <EmployeePaymentsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('EmployeePaymentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(employeePaymentsApi.listEmployeePaymentsApi).mockResolvedValue(mockPayments);
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(employeePaymentsApi.previewEmployeePaymentsApi).mockResolvedValue(mockPreviewResponse);
    vi.mocked(employeePaymentsApi.generateEmployeePaymentsApi).mockResolvedValue([mockPayments[0], mockPayments[1]]);
    vi.mocked(payrollSettingsApi.getEffectiveOvertimeSettingApi).mockResolvedValue(null as any);
    vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders page header and action button for director', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Employee Payments' })).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
  });

  it('renders all 5 KPI cards with counts and amounts', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByTestId('kpi-total')).toBeInTheDocument();
    });

    // Total: 4 payments, sum = 3500 + 4200 + 3500 + 1500 = 12700
    const kpiTotal = screen.getByTestId('kpi-total');
    expect(kpiTotal).toHaveTextContent('4');
    expect(kpiTotal).toHaveTextContent('₹12,700.00');

    // Draft: 1 payment, 3500
    const kpiDraft = screen.getByTestId('kpi-draft');
    expect(kpiDraft).toHaveTextContent('1');
    expect(kpiDraft).toHaveTextContent('₹3,500.00');

    // Approved: 1 payment, 4200
    const kpiApproved = screen.getByTestId('kpi-approved');
    expect(kpiApproved).toHaveTextContent('1');
    expect(kpiApproved).toHaveTextContent('₹4,200.00');

    // Paid: 1 payment, 3500
    const kpiPaid = screen.getByTestId('kpi-paid');
    expect(kpiPaid).toHaveTextContent('1');
    expect(kpiPaid).toHaveTextContent('₹3,500.00');

    // Cancelled: 1 payment, 1500
    const kpiCancelled = screen.getByTestId('kpi-cancelled');
    expect(kpiCancelled).toHaveTextContent('1');
    expect(kpiCancelled).toHaveTextContent('₹1,500.00');
  });

  it('renders payments list rows with payment number and badges', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByText('PAY-20261010-0001')).toBeInTheDocument();
    });

    expect(screen.getByText('PAY-20261010-0002')).toBeInTheDocument();
    expect(screen.getByText('PAY-20261010-0003')).toBeInTheDocument();
    expect(screen.getByText('PAY-20261010-0004')).toBeInTheDocument();

    expect(screen.getByText('DRAFT')).toBeInTheDocument();
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
    expect(screen.getByText('PAID')).toBeInTheDocument();
    expect(screen.getByText('CANCELLED')).toBeInTheDocument();
  });

  it('filters payments by status when Filter button is clicked', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByText('PAY-20261010-0001')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.change(statusSelect, { target: { value: 'draft' } });

    const filterButton = screen.getByRole('button', { name: 'Filter' });
    fireEvent.click(filterButton);

    await waitFor(() => {
      expect(employeePaymentsApi.listEmployeePaymentsApi).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'draft' })
      );
    });
  });

  it('resets filters when Reset button is clicked', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByText('PAY-20261010-0001')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.change(statusSelect, { target: { value: 'draft' } });

    const resetButton = screen.getByRole('button', { name: 'Reset' });
    fireEvent.click(resetButton);

    await waitFor(() => {
      expect(statusSelect).toHaveValue('');
      expect(employeePaymentsApi.listEmployeePaymentsApi).toHaveBeenLastCalledWith({
        period_start: undefined,
        period_end: undefined,
        employee_id: undefined,
        status: undefined,
      });
    });
  });

  it('opens Generate modal, previews eligible payments, and generates with client idempotency key', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));

    expect(screen.getByRole('heading', { level: 3, name: 'Generate Employee Payments' })).toBeInTheDocument();
    // Preview has not happened yet
    expect(screen.queryByText('Confirm & Generate Payments')).not.toBeInTheDocument();

    // Step 1: Preview Payments
    const previewBtn = screen.getByRole('button', { name: 'Preview Eligible Payments' });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(employeePaymentsApi.previewEmployeePaymentsApi).toHaveBeenCalled();
    });

    // Check preview display
    expect(await screen.findByText('Eligible Employees')).toBeInTheDocument();
    expect(screen.getByText('₹7,700.00')).toBeInTheDocument();
    expect(screen.getAllByText('daily:')[0]).toBeInTheDocument();

    // Step 2: Confirm Generation button is now enabled
    const confirmBtn = screen.getByRole('button', { name: 'Confirm & Generate Payments' });
    expect(confirmBtn).toBeInTheDocument();

    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(employeePaymentsApi.generateEmployeePaymentsApi).toHaveBeenCalledWith(
        expect.objectContaining({
          period_start: expect.any(String),
          period_end: expect.any(String),
          idempotency_key: expect.any(String),
        })
      );
    });

    // Modal closes and success notification is shown
    await waitFor(() => {
      expect(screen.queryByRole('heading', { level: 3, name: 'Generate Employee Payments' })).not.toBeInTheDocument();
      expect(screen.getByText(/Successfully generated 2 employee payment draft\(s\)/i)).toBeInTheDocument();
    });
  });

  it('displays preview errors inside modal without generating', async () => {
    vi.mocked(employeePaymentsApi.previewEmployeePaymentsApi).mockRejectedValueOnce({
      response: { data: { detail: 'Cannot preview: Invalid date range' } },
    });

    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));

    const previewBtn = screen.getByRole('button', { name: 'Preview Eligible Payments' });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('Cannot preview: Invalid date range')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: 'Confirm & Generate Payments' })).not.toBeInTheDocument();
  });

  it('displays generation errors inside modal and keeps modal open for review', async () => {
    vi.mocked(employeePaymentsApi.generateEmployeePaymentsApi).mockRejectedValueOnce({
      response: { data: { detail: 'Idempotency conflict: run already in progress' } },
    });

    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview Eligible Payments' }));

    const confirmBtn = await screen.findByRole('button', { name: 'Confirm & Generate Payments' });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText('Idempotency conflict: run already in progress')).toBeInTheDocument();
    });

    // Modal remains open
    expect(screen.getByRole('heading', { level: 3, name: 'Generate Employee Payments' })).toBeInTheDocument();
  });

  it('shows empty state message when preview returns 0 items', async () => {
    vi.mocked(employeePaymentsApi.previewEmployeePaymentsApi).mockResolvedValueOnce({
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      total_employees: 0,
      grand_total_amount: 0.0,
      items: [],
    });

    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview Eligible Payments' }));

    await waitFor(() => {
      expect(screen.getByText('No unbilled approved records exist for this period.')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: 'Confirm & Generate Payments' })).not.toBeInTheDocument();
  });

  it('does NOT render separate Overtime Settings navigation button in header', async () => {
    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Overtime Settings' })).not.toBeInTheDocument();
  });

  it('renders preview overtime breakdown, rate basis (daily/weekly/piece), and overtime totals', async () => {
    const mockDetailedPreview: employeePaymentsApi.EmployeePaymentPreviewResponse = {
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      total_employees: 3,
      grand_total_regular_amount: 9600.0,
      grand_total_overtime_hours: 6.0,
      grand_total_overtime_amount: 900.0,
      grand_total_amount: 10500.0,
      items: [
        {
          employee_id: 'emp-daily',
          employee_name: 'Aarav Sharma (Daily)',
          period_start: '2026-10-01',
          period_end: '2026-10-07',
          total_days: 5.0,
          total_quantity: 0.0,
          total_regular_amount: 3500.0,
          total_overtime_hours: 2.0,
          total_overtime_amount: 300.0,
          total_amount: 3800.0,
          eligible_attendance_count: 5,
          eligible_work_entry_count: 0,
          rate_band_summaries: [
            {
              rate_type: 'daily',
              rate_amount: 700.0,
              rate_effective_from: '2026-01-01',
              rate_effective_to: null,
              approved_days: 5.0,
              approved_quantity: 0.0,
              gross_amount: 3800.0,
            },
          ],
        },
        {
          employee_id: 'emp-weekly',
          employee_name: 'Vikram Singh (Weekly)',
          period_start: '2026-10-01',
          period_end: '2026-10-07',
          total_days: 5.0,
          total_quantity: 0.0,
          total_regular_amount: 3500.0,
          total_overtime_hours: 4.0,
          total_overtime_amount: 600.0,
          total_amount: 4100.0,
          eligible_attendance_count: 5,
          eligible_work_entry_count: 0,
          rate_band_summaries: [
            {
              rate_type: 'weekly',
              rate_amount: 4900.0,
              rate_effective_from: '2026-01-01',
              rate_effective_to: null,
              approved_days: 5.0,
              approved_quantity: 0.0,
              gross_amount: 4100.0,
            },
          ],
        },
        {
          employee_id: 'emp-piece',
          employee_name: 'Karan Verma (Piece)',
          period_start: '2026-10-01',
          period_end: '2026-10-07',
          total_days: 0.0,
          total_quantity: 50.0,
          total_regular_amount: 2600.0,
          total_overtime_hours: 0.0,
          total_overtime_amount: 0.0,
          total_amount: 2600.0,
          eligible_attendance_count: 0,
          eligible_work_entry_count: 5,
          rate_band_summaries: [
            {
              rate_type: 'piece',
              rate_amount: 52.0,
              rate_effective_from: '2026-01-01',
              rate_effective_to: null,
              approved_days: 0.0,
              approved_quantity: 50.0,
              gross_amount: 2600.0,
            },
          ],
        },
      ],
    };

    vi.mocked(employeePaymentsApi.previewEmployeePaymentsApi).mockResolvedValueOnce(mockDetailedPreview);

    renderPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview Eligible Payments' }));

    await waitFor(() => {
      expect(screen.getByTestId('preview-regular-total')).toHaveTextContent('₹9,600.00');
    });

    // Check summary metric totals
    expect(screen.getByTestId('preview-overtime-total')).toHaveTextContent('₹900.00');
    expect(screen.getByTestId('preview-overtime-total')).toHaveTextContent('6.00 hrs');
    expect(screen.getByTestId('preview-grand-total')).toHaveTextContent('₹10,500.00');

    // Check Daily worker breakdown
    const dailyRow = screen.getByTestId('preview-row-emp-daily');
    expect(dailyRow).toHaveTextContent('Aarav Sharma (Daily)');
    expect(screen.getByTestId('preview-regular-emp-daily')).toHaveTextContent('₹3,500.00');
    expect(dailyRow).toHaveTextContent('40.00 reg hrs (8.00h/day)');
    expect(screen.getByTestId('preview-overtime-emp-daily')).toHaveTextContent('2.00 OT hrs');
    expect(screen.getByTestId('preview-overtime-emp-daily')).toHaveTextContent('+ ₹300.00');
    expect(screen.getByTestId('preview-total-emp-daily')).toHaveTextContent('₹3,800.00');

    // Check Weekly worker breakdown
    const weeklyRow = screen.getByTestId('preview-row-emp-weekly');
    expect(weeklyRow).toHaveTextContent('Vikram Singh (Weekly)');
    expect(screen.getByTestId('preview-regular-emp-weekly')).toHaveTextContent('₹3,500.00');
    expect(screen.getByTestId('preview-overtime-emp-weekly')).toHaveTextContent('4.00 OT hrs');
    expect(screen.getByTestId('preview-overtime-emp-weekly')).toHaveTextContent('+ ₹600.00');
    expect(screen.getByTestId('preview-total-emp-weekly')).toHaveTextContent('₹4,100.00');

    // Check Piece-rate worker breakdown (overtime excluded)
    const pieceRow = screen.getByTestId('preview-row-emp-piece');
    expect(pieceRow).toHaveTextContent('Karan Verma (Piece)');
    expect(screen.getByTestId('preview-regular-emp-piece')).toHaveTextContent('₹2,600.00');
    expect(screen.getByTestId('preview-overtime-emp-piece')).toHaveTextContent('— (Piece-rate excluded)');
    expect(screen.getByTestId('preview-total-emp-piece')).toHaveTextContent('₹2,600.00');
  });

  describe('Overtime Policy Indicator in Preview', () => {
    it('returns overlapping policies accurately with getOverlappingOvertimePolicies helper', () => {
      const policies: payrollSettingsApi.PayrollOvertimeSettingsResponse[] = [
        {
          id: 'p-1',
          standard_workday_hours: 7.0,
          overtime_multiplier: 1.5,
          effective_from: '2026-01-01',
          effective_to: '2026-10-13',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'p-2',
          standard_workday_hours: 7.0,
          overtime_multiplier: 1.51,
          effective_from: '2026-10-14',
          effective_to: '2026-10-14',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'p-3',
          standard_workday_hours: 8.0,
          overtime_multiplier: 2.0,
          effective_from: '2026-10-15',
          effective_to: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ];

      // Single policy period (Oct 1 to Oct 7) -> only p-1
      const singleRes = getOverlappingOvertimePolicies(policies, '2026-10-01', '2026-10-07');
      expect(singleRes.map((p) => p.id)).toEqual(['p-1']);

      // Spanning p-1 and p-2 (Oct 12 to Oct 14) -> p-1, p-2
      const twoRes = getOverlappingOvertimePolicies(policies, '2026-10-12', '2026-10-14');
      expect(twoRes.map((p) => p.id)).toEqual(['p-1', 'p-2']);

      // Spanning all three (Oct 13 to Oct 16) -> p-1, p-2, p-3
      const allThreeRes = getOverlappingOvertimePolicies(policies, '2026-10-13', '2026-10-16');
      expect(allThreeRes.map((p) => p.id)).toEqual(['p-1', 'p-2', 'p-3']);

      // Future open-ended period (Nov 1 to Nov 7) -> only p-3
      const futureRes = getOverlappingOvertimePolicies(policies, '2026-11-01', '2026-11-07');
      expect(futureRes.map((p) => p.id)).toEqual(['p-3']);
    });

    it('displays single-policy overtime banner when pay period falls within one policy', async () => {
      const mockHistory: payrollSettingsApi.PayrollOvertimeSettingsResponse[] = [
        {
          id: 'ot-policy-1',
          standard_workday_hours: 7.0,
          overtime_multiplier: 1.5,
          effective_from: '2026-01-01',
          effective_to: '2026-10-13',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'ot-policy-2',
          standard_workday_hours: 8.0,
          overtime_multiplier: 2.0,
          effective_from: '2026-10-14',
          effective_to: null,
          created_at: '2026-10-14T00:00:00Z',
        },
      ];

      vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockResolvedValueOnce(mockHistory);

      renderPage('director');

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));

      const dialog = screen.getByRole('dialog');
      // Set period inside the first policy: 2026-10-01 to 2026-10-07
      const startInput = within(dialog).getByLabelText(/Period Start/);
      const endInput = within(dialog).getByLabelText(/Period End/);
      fireEvent.change(startInput, { target: { value: '2026-10-01' } });
      fireEvent.change(endInput, { target: { value: '2026-10-07' } });

      fireEvent.click(within(dialog).getByRole('button', { name: 'Preview Eligible Payments' }));

      await waitFor(() => {
        expect(screen.getByTestId('single-overtime-policy-banner')).toBeInTheDocument();
      });

      const singleBanner = screen.getByTestId('single-overtime-policy-banner');
      expect(singleBanner).toHaveTextContent('Applicable Overtime Policy:');
      expect(singleBanner).toHaveTextContent('7.00 hrs/day standard workday @ 1.50x multiplier');
      expect(singleBanner).toHaveTextContent('Monthly basis: 30-day pro-rated • 8.00 hrs/day std • 1.00x OT • Piece-rate: OT excluded');
      expect(screen.queryByTestId('multiple-overtime-policies-banner')).not.toBeInTheDocument();
    });

    it('displays multiple-policy overtime banner with date ranges when pay period spans multiple policies', async () => {
      const mockHistory: payrollSettingsApi.PayrollOvertimeSettingsResponse[] = [
        {
          id: 'ot-policy-1',
          standard_workday_hours: 7.0,
          overtime_multiplier: 1.5,
          effective_from: '2026-01-01',
          effective_to: '2026-10-13',
          description: 'Standard baseline',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'ot-policy-2',
          standard_workday_hours: 8.0,
          overtime_multiplier: 2.0,
          effective_from: '2026-10-14',
          effective_to: null,
          description: 'New peak rate',
          created_at: '2026-10-14T00:00:00Z',
        },
      ];

      vi.mocked(payrollSettingsApi.getOvertimeSettingsHistoryApi).mockResolvedValueOnce(mockHistory);

      renderPage('director');

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));

      const dialog = screen.getByRole('dialog');
      // Set period spanning both policies: 2026-10-10 to 2026-10-16
      const startInput = within(dialog).getByLabelText(/Period Start/);
      const endInput = within(dialog).getByLabelText(/Period End/);
      fireEvent.change(startInput, { target: { value: '2026-10-10' } });
      fireEvent.change(endInput, { target: { value: '2026-10-16' } });

      fireEvent.click(within(dialog).getByRole('button', { name: 'Preview Eligible Payments' }));

      await waitFor(() => {
        expect(screen.getByTestId('multiple-overtime-policies-banner')).toBeInTheDocument();
      });

      const multiBanner = screen.getByTestId('multiple-overtime-policies-banner');
      expect(multiBanner).toHaveTextContent('Multiple Overtime Policies Applicable:');
      expect(multiBanner).toHaveTextContent('Each attendance date uses its effective policy');
      expect(multiBanner).toHaveTextContent('Monthly basis: 30-day pro-rated • 8.00 hrs/day std • 1.00x OT • Piece-rate: OT excluded');

      // Verify list of overlapping policies with date ranges, hours, and multipliers
      const item1 = screen.getByTestId('overtime-policy-range-ot-policy-1');
      expect(item1).toHaveTextContent('2026-01-01 to 2026-10-13:');
      expect(item1).toHaveTextContent('7.00 hrs/day standard workday @ 1.50x multiplier');
      expect(item1).toHaveTextContent('(Standard baseline)');

      const item2 = screen.getByTestId('overtime-policy-range-ot-policy-2');
      expect(item2).toHaveTextContent('2026-10-14 to Present:');
      expect(item2).toHaveTextContent('8.00 hrs/day standard workday @ 2.00x multiplier');
      expect(item2).toHaveTextContent('(New peak rate)');

      // Verify single-policy banner is NOT rendered
      expect(screen.queryByTestId('single-overtime-policy-banner')).not.toBeInTheDocument();
    });

    it('initializes Generate Payments modal with 1st of month and shows confirmed salary policy', async () => {
      renderPage('director');

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '+ Generate Payments' })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: '+ Generate Payments' }));

      const dialog = screen.getByRole('dialog');
      expect(within(dialog).getByRole('heading', { level: 3, name: 'Generate Employee Payments' })).toBeInTheDocument();

      // Policy subtext is displayed
      expect(
        within(dialog).getByText(/Monthly salary is paid on the 1st of every month for actual days worked: \(Monthly Salary ÷ 30\) × Actual Days Worked\./i)
      ).toBeInTheDocument();

      // Period start defaults to the 1st of the current month
      const now = new Date();
      const expectedStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
      const startInput = within(dialog).getByLabelText(/Period Start/i) as HTMLInputElement;
      expect(startInput.value).toBe(expectedStart);
    });
  });
});

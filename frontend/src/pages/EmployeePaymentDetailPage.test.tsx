import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EmployeePaymentDetailPage } from './EmployeePaymentDetailPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AccessDeniedPage } from './AccessDeniedPage';
import { AuthContext } from '../context/AuthContext';
import * as employeePaymentsApi from '../api/employeePayments';
import type { EmployeeProfile, SystemRole } from '../types/auth';

vi.mock('../api/employeePayments', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employeePayments')>();
  return {
    ...actual,
    getEmployeePaymentApi: vi.fn(),
    approveEmployeePaymentApi: vi.fn(),
    payEmployeePaymentApi: vi.fn(),
    cancelEmployeePaymentApi: vi.fn(),
  };
});

const mockDraftPayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
  id: 'pay-1',
  payment_number: 'PAY-20261010-0001',
  idempotency_key: 'idem-uuid-0001',
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
  lines: [
    {
      id: 'line-1',
      payment_id: 'pay-1',
      source_attendance_id: 'att-1',
      source_daily_work_entry_id: null,
      source_date: '2026-10-01',
      rate_type: 'daily',
      rate_amount: 700.0,
      rate_effective_from: '2026-01-01',
      rate_effective_to: null,
      days: 1.0,
      quantity: 0.0,
      amount: 700.0,
      is_active: true,
      created_at: '2026-10-08T10:00:00Z',
    },
    {
      id: 'line-2',
      payment_id: 'pay-1',
      source_attendance_id: 'att-2',
      source_daily_work_entry_id: null,
      source_date: '2026-10-02',
      rate_type: 'daily',
      rate_amount: 700.0,
      rate_effective_from: '2026-01-01',
      rate_effective_to: null,
      days: 1.0,
      quantity: 0.0,
      amount: 700.0,
      is_active: true,
      created_at: '2026-10-08T10:00:00Z',
    },
  ],
};

const mockApprovedPayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
  ...mockDraftPayment,
  id: 'pay-2',
  payment_number: 'PAY-20261010-0002',
  status: 'approved',
  approved_at: '2026-10-08T11:00:00Z',
};

const mockPaidPayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
  ...mockApprovedPayment,
  id: 'pay-3',
  payment_number: 'PAY-20261010-0003',
  status: 'paid',
  payment_date: '2026-10-09',
  payment_method: 'bank_transfer',
  reference_number: 'UTR-987654321',
  remarks: 'Direct corporate transfer',
  paid_at: '2026-10-09T14:00:00Z',
};

const mockCancelledPayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
  ...mockDraftPayment,
  id: 'pay-4',
  payment_number: 'PAY-20261010-0004',
  status: 'cancelled',
  cancellation_reason: 'Incorrect pay period selected',
  cancelled_at: '2026-10-08T12:00:00Z',
  lines: mockDraftPayment.lines.map((l) => ({ ...l, is_active: false })),
};

const renderDetailPage = (role: SystemRole = 'director', paymentId = 'pay-1') => {
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
      <MemoryRouter initialEntries={[`/employee-payments/${paymentId}`]}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['director', 'administrator']} />}>
            <Route path="/employee-payments/:paymentId" element={<EmployeePaymentDetailPage />} />
          </Route>
          <Route path="/403" element={<AccessDeniedPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('EmployeePaymentDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders payment overview metadata, rate bands, and itemized lines', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockDraftPayment);

    renderDetailPage('director', 'pay-1');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'PAY-20261010-0001' })).toBeInTheDocument();
    });

    // Overview metadata
    expect(screen.getByText('Aarav Sharma')).toBeInTheDocument();
    expect(screen.getByText('2026-10-01 to 2026-10-07')).toBeInTheDocument();
    expect(screen.getAllByText('₹3,500.00')[0]).toBeInTheDocument();
    expect(screen.getByText('idem-uuid-0001')).toBeInTheDocument();

    // Rate Band Summaries
    expect(screen.getByRole('heading', { level: 3, name: 'Rate Band Summaries' })).toBeInTheDocument();
    expect(screen.getAllByText('₹700.00')[0]).toBeInTheDocument();

    // Itemized lines
    expect(screen.getByRole('heading', { level: 3, name: 'Itemized Payment Lines' })).toBeInTheDocument();
    expect(screen.getByText('2026-10-01')).toBeInTheDocument();
    expect(screen.getByText('2026-10-02')).toBeInTheDocument();
    expect(screen.getAllByText('Attendance').length).toBe(2);
    expect(screen.getAllByText('ACTIVE').length).toBe(2);
  });

  it('approves a draft payment and transitions to approved state', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockDraftPayment);
    vi.mocked(employeePaymentsApi.approveEmployeePaymentApi).mockResolvedValueOnce(mockApprovedPayment);

    renderDetailPage('director', 'pay-1');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Approve Payment' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Approve Payment' }));

    // Approve confirmation modal opens
    expect(screen.getByRole('heading', { level: 3, name: 'Approve Employee Payment' })).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to approve payment/i)).toBeInTheDocument();

    // Confirm approval
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Approval' }));

    await waitFor(() => {
      expect(employeePaymentsApi.approveEmployeePaymentApi).toHaveBeenCalledWith('pay-1');
      expect(screen.getByText(/Payment PAY-20261010-0002 approved successfully/i)).toBeInTheDocument();
    });

    // Status updated to APPROVED, action button transitions to Mark Paid
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark Paid' })).toBeInTheDocument();
  });

  it('cancels a draft payment with mandatory reason and releases locks', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockDraftPayment);
    vi.mocked(employeePaymentsApi.cancelEmployeePaymentApi).mockResolvedValueOnce(mockCancelledPayment);

    renderDetailPage('director', 'pay-1');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancel Payment' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancel Payment' }));

    // Cancel modal opens
    expect(screen.getByRole('heading', { level: 3, name: 'Cancel Employee Payment' })).toBeInTheDocument();

    const reasonInput = screen.getByPlaceholderText(/Provide a mandatory reason for cancelling/i);
    const confirmCancelBtn = screen.getByRole('button', { name: 'Confirm Cancellation' });

    // Disabled when empty
    expect(confirmCancelBtn).toBeDisabled();

    // Type valid reason
    fireEvent.change(reasonInput, { target: { value: 'Incorrect pay period selected' } });
    expect(confirmCancelBtn).not.toBeDisabled();

    fireEvent.click(confirmCancelBtn);

    await waitFor(() => {
      expect(employeePaymentsApi.cancelEmployeePaymentApi).toHaveBeenCalledWith('pay-1', {
        cancellation_reason: 'Incorrect pay period selected',
      });
      expect(screen.getByTestId('cancellation-banner')).toBeInTheDocument();
      expect(screen.getByText('Incorrect pay period selected')).toBeInTheDocument();
    });

    // Actions removed in cancelled state
    expect(screen.queryByRole('button', { name: 'Approve Payment' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel Payment' })).not.toBeInTheDocument();
  });

  it('records settlement for approved payment (Mark Paid)', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockApprovedPayment);
    vi.mocked(employeePaymentsApi.payEmployeePaymentApi).mockResolvedValueOnce(mockPaidPayment);

    renderDetailPage('director', 'pay-2');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Mark Paid' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Mark Paid' }));

    // Mark Paid modal opens
    expect(screen.getByRole('heading', { level: 3, name: 'Record Payment Settlement' })).toBeInTheDocument();

    const refInput = screen.getByPlaceholderText(/UTR \/ Cheque \/ Txn Number/i);
    const remarksInput = screen.getByPlaceholderText(/Cleared through bank transfer/i);

    fireEvent.change(refInput, { target: { value: 'UTR-987654321' } });
    fireEvent.change(remarksInput, { target: { value: 'Direct corporate transfer' } });

    fireEvent.click(screen.getByRole('button', { name: 'Confirm & Mark Paid' }));

    await waitFor(() => {
      expect(employeePaymentsApi.payEmployeePaymentApi).toHaveBeenCalledWith(
        'pay-2',
        expect.objectContaining({
          payment_method: 'bank_transfer',
          reference_number: 'UTR-987654321',
          remarks: 'Direct corporate transfer',
        })
      );
      expect(screen.getByTestId('paid-banner')).toBeInTheDocument();
      expect(screen.getByText(/UTR-987654321/i)).toBeInTheDocument();
    });

    // Actions removed in paid state
    expect(screen.queryByRole('button', { name: 'Mark Paid' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel Payment' })).not.toBeInTheDocument();
  });

  it('renders read-only view for paid payment without action buttons', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockPaidPayment);

    renderDetailPage('director', 'pay-3');

    await waitFor(() => {
      expect(screen.getByTestId('paid-banner')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: 'Approve Payment' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark Paid' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel Payment' })).not.toBeInTheDocument();
  });

  it('renders read-only view for cancelled payment without action buttons', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockCancelledPayment);

    renderDetailPage('director', 'pay-4');

    await waitFor(() => {
      expect(screen.getByTestId('cancellation-banner')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: 'Approve Payment' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark Paid' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel Payment' })).not.toBeInTheDocument();
  });

  it('displays API error banner when payment details fail to load', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockRejectedValueOnce({
      response: { data: { detail: 'Payment record not found.' } },
    });

    renderDetailPage('director', 'non-existent-id');

    await waitFor(() => {
      expect(screen.getByText('Payment record not found.')).toBeInTheDocument();
    });
  });

  it('displays error inside approve modal when backend rejects approval', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockDraftPayment);
    vi.mocked(employeePaymentsApi.approveEmployeePaymentApi).mockRejectedValueOnce({
      response: { data: { detail: 'Cannot approve payment with status: cancelled' } },
    });

    renderDetailPage('director', 'pay-1');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Approve Payment' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Approve Payment' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Approval' }));

    await waitFor(() => {
      expect(screen.getByText('Cannot approve payment with status: cancelled')).toBeInTheDocument();
    });

    // Modal remains open
    expect(screen.getByRole('heading', { level: 3, name: 'Approve Employee Payment' })).toBeInTheDocument();
  });

  it('redirects Employee to /403 when accessing detail route', async () => {
    renderDetailPage('employee', 'pay-1');

    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });

    expect(screen.queryByRole('heading', { level: 2, name: 'PAY-20261010-0001' })).not.toBeInTheDocument();
  });

  it('redirects Supervisor to /403 when accessing detail route', async () => {
    renderDetailPage('supervisor', 'pay-1');

    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument();
    });

    expect(screen.queryByRole('heading', { level: 2, name: 'PAY-20261010-0001' })).not.toBeInTheDocument();
  });

  it('displays overview totals for regular amount, overtime hours, and overtime amount from stored snapshot', async () => {
    const mockOvertimePayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
      ...mockDraftPayment,
      id: 'pay-ot-1',
      payment_number: 'PAY-20261010-0099',
      total_regular_amount: 2100.0,
      total_overtime_hours: 3.5,
      total_overtime_amount: 525.0,
      total_amount: 2625.0,
      total_days: 3.0,
      total_quantity: 0.0,
      lines: [
        {
          id: 'line-ot-1',
          payment_id: 'pay-ot-1',
          source_attendance_id: 'att-1',
          source_daily_work_entry_id: null,
          source_date: '2026-10-01',
          rate_type: 'daily',
          rate_amount: 700.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          days: 1.0,
          quantity: 0.0,
          regular_hours: 7.0,
          overtime_hours: 2.0,
          standard_day_hours: 7.0,
          hourly_equivalent_rate: 100.0,
          overtime_multiplier: 1.5,
          regular_amount: 700.0,
          overtime_amount: 300.0,
          amount: 1000.0,
          is_active: true,
          created_at: '2026-10-08T10:00:00Z',
        },
      ],
    };

    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockOvertimePayment);

    renderDetailPage('director', 'pay-ot-1');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'PAY-20261010-0099' })).toBeInTheDocument();
    });

    expect(screen.getByTestId('total-regular-amount')).toHaveTextContent('₹2,100.00');
    expect(screen.getByTestId('total-overtime-hours')).toHaveTextContent('3.50 hrs');
    expect(screen.getByTestId('total-overtime-amount')).toHaveTextContent('₹525.00');
    expect(screen.getByTestId('total-payment-amount')).toHaveTextContent('₹2,625.00');
  });

  it('displays per-line regular/overtime breakdown with standard workday and multiplier snapshots without recalculation', async () => {
    const mockMultiLinePayment: employeePaymentsApi.EmployeePaymentDetailResponse = {
      ...mockDraftPayment,
      id: 'pay-ot-2',
      payment_number: 'PAY-20261010-0100',
      total_regular_amount: 2100.0,
      total_overtime_hours: 3.5,
      total_overtime_amount: 525.0,
      total_amount: 2625.0,
      total_days: 2.0,
      total_quantity: 10.0,
      lines: [
        {
          id: 'line-daily-ot',
          payment_id: 'pay-ot-2',
          source_attendance_id: 'att-1',
          source_daily_work_entry_id: null,
          source_date: '2026-10-01',
          rate_type: 'daily',
          rate_amount: 700.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          days: 1.0,
          quantity: 0.0,
          regular_hours: 7.0,
          overtime_hours: 2.0,
          standard_day_hours: 7.0,
          hourly_equivalent_rate: 100.0,
          overtime_multiplier: 1.5,
          regular_amount: 700.0,
          overtime_amount: 300.0,
          amount: 1000.0,
          is_active: true,
          created_at: '2026-10-08T10:00:00Z',
        },
        {
          id: 'line-weekly-ot',
          payment_id: 'pay-ot-2',
          source_attendance_id: 'att-2',
          source_daily_work_entry_id: null,
          source_date: '2026-10-02',
          rate_type: 'weekly',
          rate_amount: 4900.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          days: 1.0,
          quantity: 0.0,
          regular_hours: 7.0,
          overtime_hours: 1.5,
          standard_day_hours: 7.0,
          hourly_equivalent_rate: 100.0,
          overtime_multiplier: 1.5,
          regular_amount: 700.0,
          overtime_amount: 225.0,
          amount: 925.0,
          is_active: true,
          created_at: '2026-10-08T10:00:00Z',
        },
        {
          id: 'line-piece-entry',
          payment_id: 'pay-ot-2',
          source_attendance_id: null,
          source_daily_work_entry_id: 'dwe-10',
          source_date: '2026-10-03',
          rate_type: 'piece',
          rate_amount: 70.0,
          rate_effective_from: '2026-01-01',
          rate_effective_to: null,
          days: 0.0,
          quantity: 10.0,
          regular_hours: null,
          overtime_hours: 0.0,
          standard_day_hours: null,
          hourly_equivalent_rate: null,
          overtime_multiplier: null,
          regular_amount: 700.0,
          overtime_amount: 0.0,
          amount: 700.0,
          is_active: true,
          created_at: '2026-10-08T10:00:00Z',
        },
      ],
    };

    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce(mockMultiLinePayment);

    renderDetailPage('director', 'pay-ot-2');

    await waitFor(() => {
      expect(screen.getByTestId('itemized-lines-table')).toBeInTheDocument();
    });

    // Daily line with overtime
    const dailyLine = screen.getByTestId('payment-line-line-daily-ot');
    expect(dailyLine).toHaveTextContent('daily');
    expect(dailyLine).toHaveTextContent('7.00 hrs (7.00h std)');
    expect(dailyLine).toHaveTextContent('₹700.00 (1d)');
    expect(dailyLine).toHaveTextContent('2.00 hrs @ 1.50x');
    expect(dailyLine).toHaveTextContent('Equiv: ₹100.00/hr');
    expect(dailyLine).toHaveTextContent('+ ₹300.00');
    expect(dailyLine).toHaveTextContent('₹1,000.00');

    // Weekly line with overtime
    const weeklyLine = screen.getByTestId('payment-line-line-weekly-ot');
    expect(weeklyLine).toHaveTextContent('weekly');
    expect(weeklyLine).toHaveTextContent('7.00 hrs (7.00h std)');
    expect(weeklyLine).toHaveTextContent('₹700.00 (1d)');
    expect(weeklyLine).toHaveTextContent('1.50 hrs @ 1.50x');
    expect(weeklyLine).toHaveTextContent('Equiv: ₹100.00/hr');
    expect(weeklyLine).toHaveTextContent('+ ₹225.00');
    expect(weeklyLine).toHaveTextContent('₹925.00');

    // Piece-rate line without overtime
    const pieceLine = screen.getByTestId('payment-line-line-piece-entry');
    expect(pieceLine).toHaveTextContent('piece');
    expect(pieceLine).toHaveTextContent('10 units');
    expect(pieceLine).toHaveTextContent('— (Piece-rate excluded)');
    expect(pieceLine).toHaveTextContent('₹700.00');

    // Totals row
    const totalsRow = screen.getByTestId('lines-totals-row');
    expect(totalsRow).toHaveTextContent('Total Days: 2');
    expect(totalsRow).toHaveTextContent('Total Qty: 10');
    expect(totalsRow).toHaveTextContent('Total Regular: ₹2,100.00');
    expect(totalsRow).toHaveTextContent('Total Overtime: 3.50 hrs (₹525.00)');
    expect(totalsRow).toHaveTextContent('Grand Total: ₹2,625.00');
  });

  it('defaults Payment Date to 1st of month following period_end when marking approved payment as paid', async () => {
    vi.mocked(employeePaymentsApi.getEmployeePaymentApi).mockResolvedValueOnce({
      ...mockApprovedPayment,
      period_start: '2026-10-01',
      period_end: '2026-10-31',
    });
    vi.mocked(employeePaymentsApi.payEmployeePaymentApi).mockResolvedValueOnce({
      ...mockApprovedPayment,
      status: 'paid',
      payment_date: '2026-11-01',
      payment_method: 'bank_transfer',
      reference_number: 'UTR-123456',
    });

    renderDetailPage('director', 'pay-2');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Mark Paid' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Mark Paid' }));

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('heading', { level: 3, name: 'Record Payment Settlement' })).toBeInTheDocument();

    // Default payment date should be 2026-11-01 (1st of month following period_end 2026-10-31)
    const dateInput = within(dialog).getByLabelText(/Payment Date/i) as HTMLInputElement;
    expect(dateInput.value).toBe('2026-11-01');

    // Fill in reference and submit
    fireEvent.change(within(dialog).getByLabelText(/Reference Number/i), {
      target: { value: 'UTR-123456' },
    });

    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirm & Mark Paid' }));

    await waitFor(() => {
      expect(employeePaymentsApi.payEmployeePaymentApi).toHaveBeenCalledWith(
        'pay-2',
        expect.objectContaining({
          payment_date: '2026-11-01',
          payment_method: 'bank_transfer',
          reference_number: 'UTR-123456',
        })
      );
    });
  });
});

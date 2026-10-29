import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { InvoiceDetailPage } from './InvoiceDetailPage';
import { AuthContext } from '../context/AuthContext';
import * as invoicesApi from '../api/invoices';
import * as clientPaymentsApi from '../api/clientPayments';
import type { SystemRole } from '../types/auth';

vi.mock('../api/invoices', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/invoices')>();
  return {
    ...actual,
    getInvoiceApi: vi.fn(),
    updateDraftInvoiceApi: vi.fn(),
    issueInvoiceApi: vi.fn(),
    cancelInvoiceApi: vi.fn(),
  };
});

vi.mock('../api/clientPayments', () => ({
  listPaymentsForInvoiceApi: vi.fn(),
  recordPaymentApi: vi.fn(),
  voidPaymentApi: vi.fn(),
  getPaymentDetailApi: vi.fn(),
  uploadPaymentReceiptApi: vi.fn(),
  downloadPaymentReceiptBlob: vi.fn(),
  viewPaymentReceipt: vi.fn(),
}));

const mockPayment1: clientPaymentsApi.ClientPaymentResponse = {
  id: 'pay-1',
  payment_number: 'CPAY-20261008-0001',
  idempotency_key: 'idem-pay-1',
  invoice_id: 'inv-issued-1',
  amount: 2500.0,
  payment_date: '2026-10-08',
  payment_method: 'neft',
  reference_number: 'UTR-987654321',
  notes: 'First tranche received',
  receipt_url: null,
  status: 'recorded',
  recorded_by: 'u-dir',
  recorded_by_name: 'Director User',
  voided_by: null,
  voided_by_name: null,
  voided_at: null,
  void_reason: null,
  void_idempotency_key: null,
  created_at: '2026-10-08T11:00:00Z',
  updated_at: '2026-10-08T11:00:00Z',
};

const mockVoidedPayment: clientPaymentsApi.ClientPaymentResponse = {
  ...mockPayment1,
  id: 'pay-void-1',
  payment_number: 'CPAY-20261008-0002',
  amount: 1000.0,
  reference_number: 'CHQ-112233',
  status: 'voided',
  voided_by: 'u-dir',
  voided_by_name: 'Director User',
  voided_at: '2026-10-08T12:00:00Z',
  void_reason: 'Erroneous cheque number entered',
  void_idempotency_key: 'void-idem-1',
};

const mockDraftInvoice: invoicesApi.InvoiceDetailResponse = {
  id: 'inv-draft-1',
  invoice_number: 'INV-20261008-0001',
  idempotency_key: 'idem-1',
  client_id: 'client-1',
  client_name: 'Metro Rail Corp',
  project_id: 'proj-1',
  project_name: 'Line 3 CCTV',
  site_id: 'site-1',
  site_name: 'Station North',
  period_start: '2026-10-01',
  period_end: '2026-10-07',
  status: 'draft',
  subtotal_work: 5000.0,
  subtotal_material: 800.0,
  tax_amount: 0.0,
  total_amount: 5800.0,
  paid_amount: 0.0,
  client_po_number: 'PO-ORIGINAL',
  notes: 'Standard weekly billing',
  created_at: '2026-10-08T10:00:00Z',
  updated_at: '2026-10-08T10:00:00Z',
  lines: [
    {
      id: 'line-work-1',
      invoice_id: 'inv-draft-1',
      line_type: 'work',
      source_daily_work_entry_id: 'dwe-1',
      source_date: '2026-10-05',
      item_description: 'Cable Pulling',
      quantity: 50,
      uom: 'metre',
      standard_rate: 100,
      unit_rate: 100,
      line_amount: 5000,
      rate_override_reason: null,
      is_active: true,
      created_at: '2026-10-08T10:00:00Z',
    },
    {
      id: 'line-mat-1',
      invoice_id: 'inv-draft-1',
      line_type: 'material',
      source_material_transaction_id: 'mt-1',
      source_date: '2026-10-05',
      item_description: 'RJ45 Connectors',
      quantity: 2,
      uom: 'pack',
      standard_rate: 400,
      unit_rate: 400,
      line_amount: 800,
      rate_override_reason: null,
      is_active: true,
      created_at: '2026-10-08T10:00:00Z',
    },
  ],
};

const mockIssuedInvoice: invoicesApi.InvoiceDetailResponse = {
  ...mockDraftInvoice,
  id: 'inv-issued-1',
  invoice_number: 'INV-20261008-0002',
  status: 'issued',
  issue_date: '2026-10-08',
  due_date: '2026-10-22',
};

const mockCancelledInvoice: invoicesApi.InvoiceDetailResponse = {
  ...mockDraftInvoice,
  id: 'inv-can-1',
  invoice_number: 'INV-20261008-0003',
  status: 'cancelled',
  cancellation_reason: 'Client requested scope recalculation',
};

const renderInvoiceDetail = (invoiceId: string, role: SystemRole = 'director') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'u-dir',
          user_id: 'u-dir',
          employee_code: 'DIR-01',
          mobile_id: '+919876543210',
          name: 'Director User',
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
      <MemoryRouter initialEntries={[`/invoices/${invoiceId}`]}>
        <Routes>
          <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};

describe('InvoiceDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders draft invoice details, line items, and totals', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockDraftInvoice);

    renderInvoiceDetail('inv-draft-1', 'director');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0001')).toBeInTheDocument();
      expect(screen.getByText('Metro Rail Corp')).toBeInTheDocument();
      expect(screen.getByText('Cable Pulling')).toBeInTheDocument();
      expect(screen.getByText('RJ45 Connectors')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save Draft/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Issue Invoice/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Cancel Invoice/i })).toBeInTheDocument();
    });
  });

  it('allows director to edit tax and save draft', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockDraftInvoice);
    vi.mocked(invoicesApi.updateDraftInvoiceApi).mockResolvedValue({
      ...mockDraftInvoice,
      tax_amount: 500,
      total_amount: 6300,
    });

    renderInvoiceDetail('inv-draft-1', 'director');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0001')).toBeInTheDocument();
    });

    const saveBtn = screen.getByRole('button', { name: /Save Draft/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(invoicesApi.updateDraftInvoiceApi).toHaveBeenCalledWith('inv-draft-1', {
        client_po_number: 'PO-ORIGINAL',
        notes: 'Standard weekly billing',
        remarks: null,
        tax_amount: 0,
        rate_overrides: undefined,
      });
      expect(screen.getByText(/Invoice draft updated successfully/i)).toBeInTheDocument();
    });
  });

  it('enforces mandatory override reason when unit rate is changed by Director', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockDraftInvoice);

    renderInvoiceDetail('inv-draft-1', 'director');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0001')).toBeInTheDocument();
    });

    // Change unit rate from 100 to 125
    const rateInput = screen.getAllByRole('spinbutton')[0];
    fireEvent.change(rateInput, { target: { value: '125' } });

    // Save without providing reason
    const saveBtn = screen.getByRole('button', { name: /Save Draft/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/Rate override reason is mandatory for line/i)).toBeInTheDocument();
      expect(invoicesApi.updateDraftInvoiceApi).not.toHaveBeenCalled();
    });

    // Provide reason
    const reasonInput = screen.getByPlaceholderText(/\* Mandatory reason for override/i);
    fireEvent.change(reasonInput, { target: { value: 'Special height allowance approved' } });

    vi.mocked(invoicesApi.updateDraftInvoiceApi).mockResolvedValue({
      ...mockDraftInvoice,
      subtotal_work: 6250,
      total_amount: 7050,
    });

    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(invoicesApi.updateDraftInvoiceApi).toHaveBeenCalledWith('inv-draft-1', {
        client_po_number: 'PO-ORIGINAL',
        notes: 'Standard weekly billing',
        remarks: null,
        tax_amount: 0,
        rate_overrides: [
          {
            source_id: 'dwe-1',
            unit_rate: 125,
            rate_override_reason: 'Special height allowance approved',
          },
        ],
      });
    });
  });

  it('issues invoice via confirmation modal and transitions to issued state', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockDraftInvoice);
    vi.mocked(invoicesApi.issueInvoiceApi).mockResolvedValue(mockIssuedInvoice);

    renderInvoiceDetail('inv-draft-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Issue Invoice/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Issue Invoice/i }));

    expect(screen.getByText(/Once issued, this invoice and all rates, quantities, descriptions, and amounts become permanently frozen/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Issue Invoice/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(invoicesApi.issueInvoiceApi).toHaveBeenCalledWith('inv-draft-1', {
        issue_date: expect.any(String),
        due_date: undefined,
      });
      expect(screen.getByText(/Financial amounts are now permanently frozen/i)).toBeInTheDocument();
    });
  });

  it('cancels invoice via modal with mandatory reason and displays cancelled banner', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockDraftInvoice);
    vi.mocked(invoicesApi.cancelInvoiceApi).mockResolvedValue(mockCancelledInvoice);

    renderInvoiceDetail('inv-draft-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Cancel Invoice/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Cancel Invoice/i }));

    const reasonInput = screen.getByPlaceholderText(/State mandatory reason for cancellation/i);
    fireEvent.change(reasonInput, { target: { value: 'Client cancelled installation contract' } });

    const confirmBtn = screen.getByRole('button', { name: /Confirm Cancellation/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(invoicesApi.cancelInvoiceApi).toHaveBeenCalledWith('inv-draft-1', {
        cancellation_reason: 'Client cancelled installation contract',
      });
      expect(screen.getByText(/Invoice cancelled\. All associated work and material records have been unlocked/i)).toBeInTheDocument();
      expect(screen.getByText(/Invoice Cancelled:/i)).toBeInTheDocument();
    });
  });

  it('renders read-only mode for issued invoices without edit inputs', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0002')).toBeInTheDocument();
    });

    // Save Draft and Issue Invoice buttons should NOT exist
    expect(screen.queryByRole('button', { name: /Save Draft/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Issue Invoice/i })).not.toBeInTheDocument();

    // Inputs should be read-only text
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('renders payment history table with recorded and voided payments, statuses, and details', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue({
      ...mockIssuedInvoice,
      status: 'partially_paid',
      paid_amount: 2500,
    });
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([mockPayment1, mockVoidedPayment]);

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByText(/Payments & Receipts/i)).toBeInTheDocument();
      expect(screen.getByText('CPAY-20261008-0001')).toBeInTheDocument();
      expect(screen.getByText('UTR-987654321')).toBeInTheDocument();
      expect(screen.getByText('CPAY-20261008-0002')).toBeInTheDocument();
      expect(screen.getByText('CHQ-112233')).toBeInTheDocument();
      expect(screen.getByText(/Reason: Erroneous cheque number entered/i)).toBeInTheDocument();
    });
  });

  it('allows director to record a payment and updates balance and status', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([]);
    vi.mocked(clientPaymentsApi.recordPaymentApi).mockResolvedValue(mockPayment1);

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Record Payment$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Record Payment$/i }));

    expect(screen.getByRole('heading', { name: /Record Client Payment/i })).toBeInTheDocument();
    expect(screen.getByText(/Outstanding balance:/i)).toBeInTheDocument();

    // Fill in amount
    const amountInput = screen.getByLabelText(/Payment Amount \(₹\) \*/i);
    fireEvent.change(amountInput, { target: { value: '2500.00' } });

    // Select method
    const methodSelect = screen.getByLabelText(/Payment Method \*/i);
    fireEvent.change(methodSelect, { target: { value: 'neft' } });

    // Fill in reference
    const refInput = screen.getByLabelText(/Reference \/ UTR \/ Cheque Number/i);
    fireEvent.change(refInput, { target: { value: 'UTR-987654321' } });

    // Confirm & Record Payment
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Record Payment/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(clientPaymentsApi.recordPaymentApi).toHaveBeenCalledWith({
        invoice_id: 'inv-issued-1',
        amount: 2500,
        payment_date: expect.any(String),
        payment_method: 'neft',
        reference_number: 'UTR-987654321',
        notes: undefined,
        idempotency_key: expect.any(String),
      });
      expect(screen.getByText(/Payment CPAY-20261008-0001 of ₹2,500\.00 recorded successfully\./i)).toBeInTheDocument();
    });
  });

  it('validates payment amount > 0 and rejects overpayment in the modal', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice); // balance is 5800

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Record Payment$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Record Payment$/i }));

    const amountInput = screen.getByLabelText(/Payment Amount \(₹\) \*/i);
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Record Payment/i });

    // Test zero amount
    fireEvent.change(amountInput, { target: { value: '0' } });
    expect(confirmBtn).toBeDisabled();

    // Test overpayment > balanceDue (5800)
    fireEvent.change(amountInput, { target: { value: '9999.00' } });
    expect(confirmBtn).not.toBeDisabled();
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Payment amount cannot exceed outstanding balance of ₹5,800\.00/i)).toBeInTheDocument();
      expect(clientPaymentsApi.recordPaymentApi).not.toHaveBeenCalled();
    });
  });

  it('allows administrator to void an active payment with mandatory audit reason >= 10 characters', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([mockPayment1]);
    vi.mocked(clientPaymentsApi.voidPaymentApi).mockResolvedValue(mockVoidedPayment);

    renderInvoiceDetail('inv-issued-1', 'administrator');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Void$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Void$/i }));

    expect(screen.getByRole('heading', { name: /Void Payment/i })).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to void payment/i)).toBeInTheDocument();

    const reasonInput = screen.getByPlaceholderText(/State mandatory audit reason \(at least 10 characters\)/i);
    const confirmVoidBtn = screen.getByRole('button', { name: /Confirm & Void Payment/i });

    // Under 10 characters -> button disabled
    fireEvent.change(reasonInput, { target: { value: 'Short' } });
    expect(confirmVoidBtn).toBeDisabled();

    // 10+ characters
    fireEvent.change(reasonInput, { target: { value: 'Incorrect UTR number provided by client' } });
    expect(confirmVoidBtn).not.toBeDisabled();

    fireEvent.click(confirmVoidBtn);

    await waitFor(() => {
      expect(clientPaymentsApi.voidPaymentApi).toHaveBeenCalledWith('pay-1', {
        void_idempotency_key: expect.any(String),
        void_reason: 'Incorrect UTR number provided by client',
      });
      expect(screen.getByText(/Payment CPAY-20261008-0002 voided successfully\./i)).toBeInTheDocument();
    });
  });

  it('respects RBAC: hides Record Payment and Void buttons for employee role', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([mockPayment1]);

    renderInvoiceDetail('inv-issued-1', 'employee');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0002')).toBeInTheDocument();
    });

    // Record Payment and Void buttons should not be rendered
    expect(screen.queryByRole('button', { name: /Record Payment/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Void$/i })).not.toBeInTheDocument();
  });

  it('handles backend error on record payment gracefully and displays in modal', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.recordPaymentApi).mockRejectedValue({
      response: {
        data: {
          detail: 'Payment amount exceeds remaining balance.',
        },
      },
    });

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Record Payment$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Record Payment$/i }));

    const amountInput = screen.getByLabelText(/Payment Amount \(₹\) \*/i);
    fireEvent.change(amountInput, { target: { value: '1000.00' } });

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Record Payment/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Payment amount exceeds remaining balance\./i)).toBeInTheDocument();
    });
  });

  it('allows director to record payment with optional receipt upload', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([]);
    vi.mocked(clientPaymentsApi.recordPaymentApi).mockResolvedValue(mockPayment1);
    vi.mocked(clientPaymentsApi.uploadPaymentReceiptApi).mockResolvedValue({
      ...mockPayment1,
      receipt_url: '/api/v1/client-payments/pay-1/receipt',
    });

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Record Payment$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Record Payment$/i }));

    const amountInput = screen.getByLabelText(/Payment Amount \(₹\) \*/i);
    fireEvent.change(amountInput, { target: { value: '2500.00' } });

    // Select optional receipt file
    const file = new File(['%PDF-1.4 test receipt'], 'receipt.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByLabelText(/Receipt \/ Bank Slip \(Optional\)/i);
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/Selected: receipt\.pdf/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Record Payment/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(clientPaymentsApi.recordPaymentApi).toHaveBeenCalledWith(
        expect.objectContaining({
          invoice_id: 'inv-issued-1',
          amount: 2500,
        })
      );
      expect(clientPaymentsApi.uploadPaymentReceiptApi).toHaveBeenCalledWith('pay-1', file);
      expect(screen.getByText(/recorded and receipt attached successfully/i)).toBeInTheDocument();
    });
  });

  it('shows clear error state when payment succeeds but receipt upload fails', async () => {
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([]);
    vi.mocked(clientPaymentsApi.recordPaymentApi).mockResolvedValue(mockPayment1);
    vi.mocked(clientPaymentsApi.uploadPaymentReceiptApi).mockRejectedValue({
      response: {
        data: {
          detail: 'Unsupported file format or storage error',
        },
      },
    });

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Record Payment$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Record Payment$/i }));

    const amountInput = screen.getByLabelText(/Payment Amount \(₹\) \*/i);
    fireEvent.change(amountInput, { target: { value: '2500.00' } });

    const file = new File(['invalid text'], 'notes.txt', { type: 'text/plain' });
    const fileInput = screen.getByLabelText(/Receipt \/ Bank Slip \(Optional\)/i);
    fireEvent.change(fileInput, { target: { files: [file] } });

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Record Payment/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      // Payment recorded, modal closed, and prominent error displayed
      expect(clientPaymentsApi.recordPaymentApi).toHaveBeenCalled();
      expect(
        screen.getByText(/recorded successfully, but receipt upload failed: Unsupported file format or storage error/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/You can attach the receipt from the payments table/i)).toBeInTheDocument();
    });
  });

  it('renders View Receipt button for payments with receipt and calls viewPaymentReceipt', async () => {
    const paymentWithReceipt: clientPaymentsApi.ClientPaymentResponse = {
      ...mockPayment1,
      receipt_url: '/api/v1/client-payments/pay-1/receipt',
    };
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([paymentWithReceipt]);
    vi.mocked(clientPaymentsApi.viewPaymentReceipt).mockResolvedValue(undefined);

    renderInvoiceDetail('inv-issued-1', 'director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /View Receipt/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /View Receipt/i }));
    expect(clientPaymentsApi.viewPaymentReceipt).toHaveBeenCalledWith('pay-1');
  });

  it('allows attaching receipt later via Attach Receipt modal', async () => {
    const paymentWithoutReceipt: clientPaymentsApi.ClientPaymentResponse = {
      ...mockPayment1,
      receipt_url: null,
    };
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([paymentWithoutReceipt]);
    vi.mocked(clientPaymentsApi.uploadPaymentReceiptApi).mockResolvedValue({
      ...paymentWithoutReceipt,
      receipt_url: '/api/v1/client-payments/pay-1/receipt',
    });

    renderInvoiceDetail('inv-issued-1', 'administrator');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Attach Receipt/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Attach Receipt/i }));

    expect(screen.getByRole('heading', { name: /Attach Receipt/i })).toBeInTheDocument();

    const file = new File(['%PDF-1.4 slip'], 'deposit_slip.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByLabelText(/Select File \(PDF, JPG, PNG, WebP — Max 10MB\) \*/i);
    fireEvent.change(fileInput, { target: { files: [file] } });

    const uploadBtn = screen.getByRole('button', { name: /^Upload Receipt$/i });
    fireEvent.click(uploadBtn);

    await waitFor(() => {
      expect(clientPaymentsApi.uploadPaymentReceiptApi).toHaveBeenCalledWith('pay-1', file);
      expect(screen.getByText(/Receipt attached successfully for payment/i)).toBeInTheDocument();
    });
  });

  it('does not show receipt actions or header to employee or supervisor', async () => {
    const paymentWithReceipt: clientPaymentsApi.ClientPaymentResponse = {
      ...mockPayment1,
      receipt_url: '/api/v1/client-payments/pay-1/receipt',
    };
    vi.mocked(invoicesApi.getInvoiceApi).mockResolvedValue(mockIssuedInvoice);
    vi.mocked(clientPaymentsApi.listPaymentsForInvoiceApi).mockResolvedValue([paymentWithReceipt]);

    // 1. Employee
    renderInvoiceDetail('inv-issued-1', 'employee');
    await waitFor(() => {
      expect(screen.getByText(mockIssuedInvoice.invoice_number)).toBeInTheDocument();
    });
    expect(screen.queryByRole('columnheader', { name: /^Receipt$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /View Receipt/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Attach Receipt/i })).not.toBeInTheDocument();
    cleanup();

    // 2. Supervisor
    renderInvoiceDetail('inv-issued-1', 'supervisor');
    await waitFor(() => {
      expect(screen.getByText(mockIssuedInvoice.invoice_number)).toBeInTheDocument();
    });
    expect(screen.queryByRole('columnheader', { name: /^Receipt$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /View Receipt/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Attach Receipt/i })).not.toBeInTheDocument();
  });
});

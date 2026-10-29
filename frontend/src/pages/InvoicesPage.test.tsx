import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { InvoicesPage } from './InvoicesPage';
import { AuthContext } from '../context/AuthContext';
import * as invoicesApi from '../api/invoices';
import * as masterDataApi from '../api/masterData';
import type { SystemRole } from '../types/auth';

vi.mock('../api/invoices', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/invoices')>();
  return {
    ...actual,
    listInvoicesApi: vi.fn(),
    previewInvoiceApi: vi.fn(),
    generateInvoiceApi: vi.fn(),
  };
});

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getClientsApi: vi.fn(),
    getProjectsApi: vi.fn(),
    getSitesApi: vi.fn(),
  };
});

const mockInvoices: invoicesApi.InvoiceResponse[] = [
  {
    id: 'inv-1',
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
    created_at: '2026-10-08T10:00:00Z',
    updated_at: '2026-10-08T10:00:00Z',
  },
  {
    id: 'inv-2',
    invoice_number: 'INV-20261008-0002',
    idempotency_key: 'idem-2',
    client_id: 'client-1',
    client_name: 'Metro Rail Corp',
    project_id: 'proj-1',
    project_name: 'Line 3 CCTV',
    site_id: 'site-1',
    site_name: 'Station North',
    period_start: '2026-09-24',
    period_end: '2026-09-30',
    status: 'issued',
    subtotal_work: 12000.0,
    subtotal_material: 1500.0,
    tax_amount: 0.0,
    total_amount: 13500.0,
    paid_amount: 0.0,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-01T10:00:00Z',
  },
  {
    id: 'inv-3',
    invoice_number: 'INV-20261008-0003',
    idempotency_key: 'idem-3',
    client_id: 'client-1',
    client_name: 'Metro Rail Corp',
    project_id: 'proj-1',
    project_name: 'Line 3 CCTV',
    site_id: 'site-1',
    site_name: 'Station North',
    period_start: '2026-09-17',
    period_end: '2026-09-23',
    status: 'partially_paid',
    subtotal_work: 10000.0,
    subtotal_material: 1000.0,
    tax_amount: 0.0,
    total_amount: 11000.0,
    paid_amount: 5000.0,
    created_at: '2026-09-24T10:00:00Z',
    updated_at: '2026-09-25T10:00:00Z',
  },
  {
    id: 'inv-4',
    invoice_number: 'INV-20261008-0004',
    idempotency_key: 'idem-4',
    client_id: 'client-1',
    client_name: 'Metro Rail Corp',
    project_id: 'proj-1',
    project_name: 'Line 3 CCTV',
    site_id: 'site-1',
    site_name: 'Station North',
    period_start: '2026-09-10',
    period_end: '2026-09-16',
    status: 'paid',
    subtotal_work: 8000.0,
    subtotal_material: 500.0,
    tax_amount: 0.0,
    total_amount: 8500.0,
    paid_amount: 8500.0,
    created_at: '2026-09-17T10:00:00Z',
    updated_at: '2026-09-18T10:00:00Z',
  },
  {
    id: 'inv-5',
    invoice_number: 'INV-20261008-0005',
    idempotency_key: 'idem-5',
    client_id: 'client-1',
    client_name: 'Metro Rail Corp',
    project_id: 'proj-1',
    project_name: 'Line 3 CCTV',
    site_id: 'site-1',
    site_name: 'Station North',
    period_start: '2026-09-03',
    period_end: '2026-09-09',
    status: 'cancelled',
    subtotal_work: 6000.0,
    subtotal_material: 400.0,
    tax_amount: 0.0,
    total_amount: 6400.0,
    paid_amount: 0.0,
    created_at: '2026-09-10T10:00:00Z',
    updated_at: '2026-09-11T10:00:00Z',
  },
];

const mockClients = [{ id: 'client-1', name: 'Metro Rail Corp', is_active: true, created_at: '' }];
const mockProjects = [{ id: 'proj-1', name: 'Line 3 CCTV', client_id: 'client-1', status: 'in_progress' }];
const mockSites = [{ id: 'site-1', name: 'Station North', project_id: 'proj-1', is_active: true }];

const renderInvoicesPage = (role: SystemRole = 'director') => {
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
      <MemoryRouter>
        <InvoicesPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};

describe('InvoicesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoicesApi.listInvoicesApi).mockResolvedValue(mockInvoices);
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue(mockClients);
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders invoices list with KPI summary cards covering all statuses', async () => {
    renderInvoicesPage('director');

    await waitFor(() => {
      expect(screen.getByText('Client Invoices')).toBeInTheDocument();
      expect(screen.getByText('INV-20261008-0001')).toBeInTheDocument();
      expect(screen.getByText('INV-20261008-0002')).toBeInTheDocument();
      expect(screen.getByText('INV-20261008-0003')).toBeInTheDocument();
      expect(screen.getByText('INV-20261008-0004')).toBeInTheDocument();
      expect(screen.getByText('INV-20261008-0005')).toBeInTheDocument();
    });

    // Check all KPI card titles
    expect(within(screen.getByTestId('kpi-total')).getByText('Total Invoices')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-draft')).getByText('Draft Invoices')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-issued')).getByText('Issued (Pending)')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-partially-paid')).getByText('Partially Paid')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-paid')).getByText('Fully Paid')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-cancelled')).getByText('Cancelled')).toBeInTheDocument();

    // Verify values via data-testid
    expect(within(screen.getByTestId('kpi-total')).getByText('5')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-draft')).getByText('1')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-issued')).getByText('1')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-partially-paid')).getByText('1')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-paid')).getByText('1')).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-cancelled')).getByText('1')).toBeInTheDocument();
  });

  it('reconciles status KPI counts with total invoice count across all statuses', async () => {
    // 2 draft, 3 issued, 2 partially_paid, 4 paid, 1 cancelled = 12 total
    const variedInvoices: invoicesApi.InvoiceResponse[] = [
      ...Array.from({ length: 2 }, (_, i) => ({ ...mockInvoices[0], id: `d-${i}`, status: 'draft' as const })),
      ...Array.from({ length: 3 }, (_, i) => ({ ...mockInvoices[1], id: `i-${i}`, status: 'issued' as const })),
      ...Array.from({ length: 2 }, (_, i) => ({ ...mockInvoices[2], id: `pp-${i}`, status: 'partially_paid' as const })),
      ...Array.from({ length: 4 }, (_, i) => ({ ...mockInvoices[3], id: `p-${i}`, status: 'paid' as const })),
      ...Array.from({ length: 1 }, (_, i) => ({ ...mockInvoices[4], id: `c-${i}`, status: 'cancelled' as const })),
    ];
    vi.mocked(invoicesApi.listInvoicesApi).mockResolvedValueOnce(variedInvoices);

    renderInvoicesPage('director');

    await waitFor(() => {
      expect(within(screen.getByTestId('kpi-total')).getByText('12')).toBeInTheDocument();
    });

    const draft = 2;
    const issued = 3;
    const partiallyPaid = 2;
    const paid = 4;
    const cancelled = 1;
    const total = 12;

    expect(within(screen.getByTestId('kpi-draft')).getByText(String(draft))).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-issued')).getByText(String(issued))).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-partially-paid')).getByText(String(partiallyPaid))).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-paid')).getByText(String(paid))).toBeInTheDocument();
    expect(within(screen.getByTestId('kpi-cancelled')).getByText(String(cancelled))).toBeInTheDocument();

    // Verify reconciliation
    expect(draft + issued + partiallyPaid + paid + cancelled).toBe(total);
  });

  it('applies filters and calls listInvoicesApi with query params', async () => {
    renderInvoicesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('INV-20261008-0001')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.change(statusSelect, { target: { value: 'draft' } });

    const filterBtn = screen.getByRole('button', { name: /filter/i });
    fireEvent.click(filterBtn);

    await waitFor(() => {
      expect(invoicesApi.listInvoicesApi).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'draft',
        }),
      );
    });
  });

  it('opens preview modal and displays unbilled records summary', async () => {
    vi.mocked(invoicesApi.previewInvoiceApi).mockResolvedValue({
      client_id: 'client-1',
      client_name: 'Metro Rail Corp',
      project_id: 'proj-1',
      project_name: 'Line 3 CCTV',
      site_id: 'site-1',
      site_name: 'Station North',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      billable_work_count: 1,
      billable_material_count: 1,
      subtotal_work: 5000.0,
      subtotal_material: 800.0,
      estimated_tax: 0.0,
      estimated_total: 5800.0,
      items: [
        {
          source_type: 'work',
          source_id: 'dwe-1',
          source_date: '2026-10-05',
          item_description: 'Cable Pulling',
          quantity: 50,
          uom: 'metre',
          standard_rate: 100,
          unit_rate: 100,
          line_amount: 5000,
        },
      ],
    });

    renderInvoicesPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /\+ New Invoice/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /\+ New Invoice/i }));

    expect(screen.getByText('Preview & Generate Invoice')).toBeInTheDocument();

    // Select Client, Project, Site
    fireEvent.change(screen.getByLabelText(/Client \*/i), { target: { value: 'client-1' } });
    fireEvent.change(screen.getByLabelText(/Project \*/i), { target: { value: 'proj-1' } });
    fireEvent.change(screen.getByLabelText(/Site \*/i), { target: { value: 'site-1' } });

    const previewBtn = screen.getByRole('button', { name: /1\. Preview Billable Records/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(invoicesApi.previewInvoiceApi).toHaveBeenCalledWith({
        client_id: 'client-1',
        project_id: 'proj-1',
        site_id: 'site-1',
        period_start: expect.any(String),
        period_end: expect.any(String),
      });
      expect(screen.getByText('Billable Work Entries')).toBeInTheDocument();
      expect(screen.getByText('Cable Pulling')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /2\. Generate Draft Invoice/i })).toBeInTheDocument();
    });
  });

  it('generates a draft invoice from preview and handles conflict errors gracefully', async () => {
    vi.mocked(invoicesApi.previewInvoiceApi).mockResolvedValue({
      client_id: 'client-1',
      client_name: 'Metro Rail Corp',
      project_id: 'proj-1',
      project_name: 'Line 3 CCTV',
      site_id: 'site-1',
      site_name: 'Station North',
      period_start: '2026-10-01',
      period_end: '2026-10-07',
      billable_work_count: 1,
      billable_material_count: 0,
      subtotal_work: 5000.0,
      subtotal_material: 0.0,
      estimated_tax: 0.0,
      estimated_total: 5000.0,
      items: [
        {
          source_type: 'work',
          source_id: 'dwe-1',
          source_date: '2026-10-05',
          item_description: 'Cable Pulling',
          quantity: 50,
          uom: 'metre',
          standard_rate: 100,
          unit_rate: 100,
          line_amount: 5000,
        },
      ],
    });

    vi.mocked(invoicesApi.generateInvoiceApi).mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: 'Concurrency conflict: source records have already been locked by another invoice.' },
      },
    });

    renderInvoicesPage('director');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /\+ New Invoice/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /\+ New Invoice/i }));

    fireEvent.change(screen.getByLabelText(/Client \*/i), { target: { value: 'client-1' } });
    fireEvent.change(screen.getByLabelText(/Project \*/i), { target: { value: 'proj-1' } });
    fireEvent.change(screen.getByLabelText(/Site \*/i), { target: { value: 'site-1' } });

    fireEvent.click(screen.getByRole('button', { name: /1\. Preview Billable Records/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /2\. Generate Draft Invoice/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /2\. Generate Draft Invoice/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Concurrency conflict: source records have already been locked by another invoice./i),
      ).toBeInTheDocument();
    });
  });
});

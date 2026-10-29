import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AssetDetailPage } from './AssetDetailPage';
import { AuthContext } from '../context/AuthContext';
import * as assetsApi from '../api/assets';
import * as masterDataApi from '../api/masterData';
import * as employeeApi from '../api/employee';
import type { SystemRole } from '../types/auth';

vi.mock('../api/assets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/assets')>();
  return {
    ...actual,
    getAssetApi: vi.fn(),
    issueAssetApi: vi.fn(),
    returnAssetApi: vi.fn(),
    reassignAssetApi: vi.fn(),
    getAssetDestinationSitesApi: vi.fn(),
    getAssetSitesApi: vi.fn(),
  };
});

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn(),
  };
});

vi.mock('../api/employee', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/employee')>();
  return {
    ...actual,
    getAllEmployeesApi: vi.fn(),
  };
});

const mockSites: masterDataApi.SiteResponseData[] = [
  {
    id: 'site-1',
    name: 'Metro Line 1 Station',
    project_id: 'p1',
    is_active: true,
  },
  {
    id: 'site-2',
    name: 'Substation South',
    project_id: 'p1',
    is_active: true,
  },
];

const mockEmployees: any[] = [
  {
    id: 'emp-1',
    first_name: 'Rahul',
    last_name: 'Sharma',
    employee_id: 'EMP-101',
    is_active: true,
    active_sites: [{ id: 'site-1', name: 'Metro Line 1 Station' }],
  },
];

const mockAssetDetail: assetsApi.AssetDetailResponse = {
  id: 'ast-detail-1',
  asset_tag: 'AST-2026-0042',
  name: 'Optical Time Domain Reflectometer (OTDR)',
  category: 'Fiber Optics',
  serial_number: 'OTDR-9921-X',
  manufacturer: 'EXFO',
  model_number: 'FTB-1v2',
  purchase_date: '2026-01-10',
  purchase_cost: 185000,
  warranty_expiry_date: '2027-01-10',
  condition: 'good',
  status: 'available',
  location_type: 'site',
  current_site_id: 'site-1',
  current_site_name: 'Metro Line 1 Station',
  current_custodian_id: null,
  current_custodian_name: null,
  description: 'Precision fiber testing equipment for metro line backbone.',
  is_active: true,
  created_at: '2026-01-10T09:00:00Z',
  updated_at: '2026-01-15T14:30:00Z',
  transactions: [
    {
      id: 'tx-1',
      asset_id: 'ast-detail-1',
      transaction_type: 'register',
      from_location_type: null,
      to_location_type: 'warehouse',
      from_site_id: null,
      to_site_id: null,
      from_site_name: null,
      to_site_name: null,
      from_employee_id: null,
      to_employee_id: null,
      from_employee_name: null,
      to_employee_name: null,
      condition_before: null,
      condition_after: 'new',
      transaction_date: '2026-01-10T09:00:00Z',
      performed_by: 'Admin User',
      remarks: 'Initial inventory registration',
      created_at: '2026-01-10T09:00:00Z',
    },
    {
      id: 'tx-2',
      asset_id: 'ast-detail-1',
      transaction_type: 'reassign',
      from_location_type: 'warehouse',
      to_location_type: 'site',
      from_site_id: null,
      to_site_id: 'site-1',
      from_site_name: null,
      to_site_name: 'Metro Line 1 Station',
      from_employee_id: null,
      to_employee_id: null,
      from_employee_name: null,
      to_employee_name: null,
      condition_before: 'new',
      condition_after: 'good',
      transaction_date: '2026-01-12T11:00:00Z',
      performed_by: 'Admin User',
      remarks: 'Dispatched to station site',
      created_at: '2026-01-12T11:00:00Z',
    },
  ],
};

const mockAssetDetailIssued: assetsApi.AssetDetailResponse = {
  ...mockAssetDetail,
  id: 'ast-detail-2',
  status: 'issued_employee',
  current_custodian_id: 'emp-1',
  current_custodian_name: 'Rahul Sharma',
  transactions: [
    ...mockAssetDetail.transactions,
    {
      id: 'tx-3',
      asset_id: 'ast-detail-2',
      transaction_type: 'issue',
      from_location_type: 'site',
      to_location_type: 'site',
      from_site_id: 'site-1',
      to_site_id: 'site-1',
      from_site_name: 'Metro Line 1 Station',
      to_site_name: 'Metro Line 1 Station',
      from_employee_id: null,
      to_employee_id: 'emp-1',
      from_employee_name: null,
      to_employee_name: 'Rahul Sharma',
      condition_before: 'good',
      condition_after: 'good',
      transaction_date: '2026-01-15T14:30:00Z',
      performed_by: 'Supervisor User',
      remarks: 'Issued for fiber splice testing',
      created_at: '2026-01-15T14:30:00Z',
    },
  ],
};

const renderAssetDetailPage = (assetId: string = 'ast-detail-1', role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'user-1',
          user_id: 'user-1',
          employee_code: 'EMP-01',
          mobile_id: '+919876543210',
          name: 'Admin User',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        role,
        accessToken: 'fake-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={[`/assets/${assetId}`]}>
        <Routes>
          <Route path="/assets/:assetId" element={<AssetDetailPage />} />
          <Route path="/assets" element={<div>Assets Listing Page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};

describe('AssetDetailPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.getAssetSitesApi).mockResolvedValue(mockSites);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(assetsApi.getAssetDestinationSitesApi).mockResolvedValue(mockSites);
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(assetsApi.getAssetApi).mockResolvedValue(mockAssetDetail);
  });

  afterEach(() => {
    cleanup();
  });

  describe('Specifications & Location Details', () => {
    it('renders asset specifications, location, warranty, and transaction audit ledger', async () => {
      renderAssetDetailPage('ast-detail-1', 'administrator');

      expect(screen.getByText('Loading asset details...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('Optical Time Domain Reflectometer (OTDR)')).toBeInTheDocument();
      });

      // Specifications
      expect(screen.getAllByText('AST-2026-0042')[0]).toBeInTheDocument();
      expect(screen.getByText('Fiber Optics')).toBeInTheDocument();
      expect(screen.getAllByText('OTDR-9921-X')[0]).toBeInTheDocument();
      expect(screen.getByText('EXFO')).toBeInTheDocument();
      expect(screen.getByText('FTB-1v2')).toBeInTheDocument();
      expect(screen.getByText(/Precision fiber testing equipment/)).toBeInTheDocument();

      // Current Location & Custody
      expect(screen.getAllByText('Metro Line 1 Station')[0]).toBeInTheDocument();
      expect(screen.getByText('None (In Stock)')).toBeInTheDocument();
      expect(screen.getByText('Active Inventory')).toBeInTheDocument();

      // Financials & Warranty
      expect(screen.getByText('₹1,85,000.00')).toBeInTheDocument();
      expect(screen.getByText('2026-01-10')).toBeInTheDocument();
      expect(screen.getByText('2027-01-10')).toBeInTheDocument();

      // Transactions Ledger
      expect(screen.getByTestId('transactions-table')).toBeInTheDocument();
      expect(screen.getByText('Initial inventory registration')).toBeInTheDocument();
      expect(screen.getByText('Dispatched to station site')).toBeInTheDocument();
      expect(screen.getByText('Registered')).toBeInTheDocument();
      expect(screen.getByText('Reassigned')).toBeInTheDocument();
    });

    it('renders 403 or error state gracefully when user does not have permission', async () => {
      vi.mocked(assetsApi.getAssetApi).mockRejectedValueOnce({
        response: {
          status: 403,
          data: {
            detail: 'Forbidden: You do not have access to assets outside your supervised sites.',
          },
        },
      });

      renderAssetDetailPage('ast-unauthorized', 'supervisor');

      await waitFor(() => {
        expect(
          screen.getByText('Forbidden: You do not have access to assets outside your supervised sites.'),
        ).toBeInTheDocument();
      });

      // Back button works
      const backBtn = screen.getByRole('button', { name: /back to assets/i });
      fireEvent.click(backBtn);
      expect(screen.getByText('Assets Listing Page')).toBeInTheDocument();
    });
  });

  describe('Action Buttons & Modals in Detail View', () => {
    it('shows Issue and Reassign buttons for available site asset and hides Return', async () => {
      renderAssetDetailPage('ast-detail-1', 'administrator');

      await waitFor(() => {
        expect(screen.getAllByText('AST-2026-0042')[0]).toBeInTheDocument();
      });

      expect(screen.getByTestId('detail-issue-btn')).toBeInTheDocument();
      expect(screen.getByTestId('detail-reassign-btn')).toBeInTheDocument();
      expect(screen.queryByTestId('detail-return-btn')).not.toBeInTheDocument();
    });

    it('shows Return button for issued asset and hides Issue and Reassign', async () => {
      vi.mocked(assetsApi.getAssetApi).mockResolvedValue(mockAssetDetailIssued);

      renderAssetDetailPage('ast-detail-2', 'administrator');

      await waitFor(() => {
        expect(screen.getAllByText('AST-2026-0042')[0]).toBeInTheDocument();
      });

      expect(screen.getByTestId('detail-return-btn')).toBeInTheDocument();
      expect(screen.queryByTestId('detail-issue-btn')).not.toBeInTheDocument();
      expect(screen.queryByTestId('detail-reassign-btn')).not.toBeInTheDocument();
    });

    it('allows issuing asset from detail page and refreshes data upon success', async () => {
      vi.mocked(assetsApi.issueAssetApi).mockResolvedValueOnce(mockAssetDetailIssued);

      renderAssetDetailPage('ast-detail-1', 'administrator');

      await waitFor(() => {
        expect(screen.getByTestId('detail-issue-btn')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('detail-issue-btn'));

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Issue Asset to Employee/i })).toBeInTheDocument();
      });

      const employeeSelect = screen.getByLabelText(/Recipient Employee/i);
      fireEvent.change(employeeSelect, { target: { value: 'emp-1' } });

      fireEvent.click(screen.getByRole('button', { name: /Confirm Issue/i }));

      await waitFor(() => {
        expect(assetsApi.issueAssetApi).toHaveBeenCalledWith(
          'ast-detail-1',
          expect.objectContaining({ employee_id: 'emp-1' }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/successfully issued/i)).toBeInTheDocument();
      });
    });

    it('allows returning asset from detail page and refreshes data upon success', async () => {
      vi.mocked(assetsApi.getAssetApi).mockResolvedValue(mockAssetDetailIssued);
      vi.mocked(assetsApi.returnAssetApi).mockResolvedValueOnce(mockAssetDetail);

      renderAssetDetailPage('ast-detail-2', 'administrator');

      await waitFor(() => {
        expect(screen.getByTestId('detail-return-btn')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('detail-return-btn'));

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Return Issued Asset/i })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Confirm Return/i }));

      await waitFor(() => {
        expect(assetsApi.returnAssetApi).toHaveBeenCalledWith(
          'ast-detail-2',
          expect.objectContaining({ employee_id: 'emp-1' }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/successfully returned/i)).toBeInTheDocument();
      });
    });

    it('allows supervisor to view asset details and supported actions (issue and reassign) without site restriction', async () => {
      renderAssetDetailPage('ast-detail-1', 'supervisor');

      await waitFor(() => {
        expect(screen.getAllByText('AST-2026-0042')[0]).toBeInTheDocument();
      });

      // Supervisor sees full details
      expect(screen.getByText('Optical Time Domain Reflectometer (OTDR)')).toBeInTheDocument();
      expect(screen.getByText('Registered')).toBeInTheDocument();
      expect(screen.getByText('Reassigned')).toBeInTheDocument();

      // Supervisor sees Issue and Reassign action buttons identical to Administrator
      expect(screen.getByTestId('detail-issue-btn')).toBeInTheDocument();
      expect(screen.getByTestId('detail-reassign-btn')).toBeInTheDocument();
    });
  });
});

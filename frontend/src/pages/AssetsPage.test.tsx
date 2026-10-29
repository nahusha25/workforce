import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { AssetsPage } from './AssetsPage';
import { AuthContext } from '../context/AuthContext';
import * as assetsApi from '../api/assets';
import * as masterDataApi from '../api/masterData';
import * as employeeApi from '../api/employee';
import type { SystemRole } from '../types/auth';

vi.mock('../api/assets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/assets')>();
  return {
    ...actual,
    listAssetsApi: vi.fn(),
    registerAssetApi: vi.fn(),
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
  {
    id: 'emp-2',
    first_name: 'Priya',
    last_name: 'Verma',
    employee_id: 'EMP-102',
    is_active: true,
    active_sites: [{ id: 'site-2', name: 'Substation South' }],
  },
];

const mockAssetAvailableSite: assetsApi.AssetResponse = {
  id: 'ast-1',
  asset_tag: 'AST-2026-0001',
  name: 'Rotary Hammer Drill',
  category: 'Power Tools',
  serial_number: 'SN-HD-9988',
  manufacturer: 'Bosch',
  model_number: 'GBH 2-26',
  purchase_date: '2026-01-15',
  purchase_cost: 14500,
  warranty_expiry_date: '2027-01-15',
  condition: 'good',
  status: 'available',
  location_type: 'site',
  current_site_id: 'site-1',
  current_site_name: 'Metro Line 1 Station',
  current_custodian_id: null,
  current_custodian_name: null,
  description: 'Heavy duty drill',
  is_active: true,
  created_at: '2026-01-15T10:00:00Z',
  updated_at: '2026-01-15T10:00:00Z',
};

const mockAssetIssued: assetsApi.AssetResponse = {
  id: 'ast-2',
  asset_tag: 'AST-2026-0002',
  name: 'Fluke Multimeter',
  category: 'Testing Equipment',
  serial_number: 'FLU-1122',
  manufacturer: 'Fluke',
  model_number: '179 True-RMS',
  purchase_date: '2026-02-01',
  purchase_cost: 22000,
  warranty_expiry_date: '2028-02-01',
  condition: 'new',
  status: 'issued_employee',
  location_type: 'site',
  current_site_id: 'site-1',
  current_site_name: 'Metro Line 1 Station',
  current_custodian_id: 'emp-1',
  current_custodian_name: 'Rahul Sharma',
  description: 'High precision digital multimeter',
  is_active: true,
  created_at: '2026-02-01T10:00:00Z',
  updated_at: '2026-02-01T10:00:00Z',
};

const mockAssetWarehouse: assetsApi.AssetResponse = {
  id: 'ast-3',
  asset_tag: 'AST-2026-0003',
  name: 'Safety Harness Full Body',
  category: 'Safety Gear',
  serial_number: null,
  manufacturer: 'Karam',
  model_number: 'PN-56',
  purchase_date: '2026-03-01',
  purchase_cost: 3500,
  warranty_expiry_date: null,
  condition: 'new',
  status: 'available',
  location_type: 'warehouse',
  current_site_id: null,
  current_site_name: null,
  current_custodian_id: null,
  current_custodian_name: null,
  description: 'Fall arrest harness',
  is_active: true,
  created_at: '2026-03-01T10:00:00Z',
  updated_at: '2026-03-01T10:00:00Z',
};

const renderAssetsPage = (role: SystemRole = 'administrator') => {
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
      <MemoryRouter>
        <AssetsPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
};

describe('AssetsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(assetsApi.getAssetSitesApi).mockResolvedValue(mockSites);
    vi.mocked(assetsApi.getAssetDestinationSitesApi).mockResolvedValue(mockSites);
    vi.mocked(employeeApi.getAllEmployeesApi).mockResolvedValue(mockEmployees);
    vi.mocked(assetsApi.listAssetsApi).mockResolvedValue({
      items: [mockAssetAvailableSite, mockAssetIssued, mockAssetWarehouse],
      total: 3,
      skip: 0,
      limit: 15,
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('Registry Rendering & KPI Summary', () => {
    it('renders page header, KPI cards, and asset rows', async () => {
      renderAssetsPage('administrator');

      expect(screen.getByRole('heading', { name: /asset management registry/i })).toBeInTheDocument();
      expect(screen.getByText('Loading asset inventory...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0001')).toBeInTheDocument();
      });

      // Verify KPI Metrics
      expect(screen.getByText('Total Registered')).toBeInTheDocument();
      expect(screen.getByText('In Central Warehouse')).toBeInTheDocument();
      expect(screen.getByText('Allocated to Sites')).toBeInTheDocument();
      expect(screen.getByText('Currently Issued')).toBeInTheDocument();

      // Verify Asset Details in Table
      expect(screen.getByText('Rotary Hammer Drill')).toBeInTheDocument();
      expect(screen.getByText('Power Tools')).toBeInTheDocument();
      expect(screen.getByText('SN-HD-9988')).toBeInTheDocument();
      expect(screen.getAllByText('Metro Line 1 Station')[0]).toBeInTheDocument();

      // Verify Issued Asset Details
      expect(screen.getByText('Fluke Multimeter')).toBeInTheDocument();
      expect(screen.getByText('Rahul Sharma')).toBeInTheDocument();

      // Verify Central Warehouse Asset
      expect(screen.getAllByText('Central Warehouse').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Safety Harness Full Body')).toBeInTheDocument();
    });

    it('renders empty state when no assets match', async () => {
      vi.mocked(assetsApi.listAssetsApi).mockResolvedValue({
        items: [],
        total: 0,
        skip: 0,
        limit: 15,
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText(/no assets found matching/i)).toBeInTheDocument();
      });
    });

    it('renders error state and retries successfully', async () => {
      vi.mocked(assetsApi.listAssetsApi).mockRejectedValueOnce(new Error('Network error connecting to API'));

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('Network error connecting to API')).toBeInTheDocument();
      });

      const retryBtn = screen.getByRole('button', { name: /retry/i });
      expect(retryBtn).toBeInTheDocument();

      vi.mocked(assetsApi.listAssetsApi).mockResolvedValue({
        items: [mockAssetAvailableSite],
        total: 1,
        skip: 0,
        limit: 15,
      });

      fireEvent.click(retryBtn);

      await waitFor(() => {
        expect(screen.getByText('Rotary Hammer Drill')).toBeInTheDocument();
      });
    });
  });

  describe('Search and Filtering', () => {
    it('filters by search input', async () => {
      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('Rotary Hammer Drill')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/tag, name, serial/i);
      fireEvent.change(searchInput, { target: { value: 'Drill' } });

      await waitFor(() => {
        expect(assetsApi.listAssetsApi).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'Drill',
          }),
        );
      });
    });

    it('filters by status and condition selects', async () => {
      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('Rotary Hammer Drill')).toBeInTheDocument();
      });

      const statusSelect = screen.getByLabelText(/operational status/i);
      fireEvent.change(statusSelect, { target: { value: 'available' } });

      await waitFor(() => {
        expect(assetsApi.listAssetsApi).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'available',
          }),
        );
      });

      const conditionSelect = screen.getByLabelText(/^condition$/i);
      fireEvent.change(conditionSelect, { target: { value: 'good' } });

      await waitFor(() => {
        expect(assetsApi.listAssetsApi).toHaveBeenCalledWith(
          expect.objectContaining({
            condition: 'good',
          }),
        );
      });
    });
  });

  describe('Registration Modal & Validation', () => {
    it('shows Register button for administrator, director, and supervisor', async () => {
      const { unmount } = renderAssetsPage('administrator');
      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });
      unmount();

      const { unmount: unmountDir } = renderAssetsPage('director');
      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });
      unmountDir();

      const { unmount: unmountSup } = renderAssetsPage('supervisor');
      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });
      unmountSup();
    });

    it('opens registration modal, validates required fields, and submits successfully', async () => {
      vi.mocked(assetsApi.registerAssetApi).mockResolvedValueOnce({
        ...mockAssetAvailableSite,
        id: 'ast-new-1',
        asset_tag: 'AST-AUTO-999',
        name: 'Angle Grinder 4 Inch',
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('register-asset-button'));

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Register New Asset/i })).toBeInTheDocument();
      });

      // Attempt to submit empty form
      fireEvent.click(screen.getByRole('button', { name: 'Register Asset' }));

      expect(screen.getByText('Asset display name is required.')).toBeInTheDocument();
      expect(screen.getByText('Category is required.')).toBeInTheDocument();

      // Fill in valid fields
      fireEvent.change(screen.getByLabelText(/asset name/i), {
        target: { value: 'Angle Grinder 4 Inch' },
      });
      fireEvent.change(screen.getByLabelText(/category/i), {
        target: { value: 'Power Tools' },
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: 'Register Asset' }));

      await waitFor(() => {
        expect(assetsApi.registerAssetApi).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Angle Grinder 4 Inch',
            category: 'Power Tools',
            location_type: 'warehouse',
          }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/successfully registered/i)).toBeInTheDocument();
      });
    });

    it('requires site selection when location type is site', async () => {
      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('register-asset-button'));

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Register New Asset/i })).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/asset name/i), {
        target: { value: 'Angle Grinder' },
      });
      fireEvent.change(screen.getByLabelText(/category/i), {
        target: { value: 'Power Tools' },
      });
      fireEvent.change(screen.getByLabelText(/initial location/i), {
        target: { value: 'site' },
      });

      fireEvent.click(screen.getByRole('button', { name: 'Register Asset' }));

      expect(screen.getByText('Please select an assigned site.')).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    });

    it('displays backend API error when registration fails', async () => {
      vi.mocked(assetsApi.registerAssetApi).mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Asset tag "AST-DUPLICATE" already exists.',
          },
        },
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByTestId('register-asset-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('register-asset-button'));

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Register New Asset/i })).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/asset name/i), {
        target: { value: 'Angle Grinder' },
      });
      fireEvent.change(screen.getByLabelText(/category/i), {
        target: { value: 'Power Tools' },
      });

      fireEvent.click(screen.getByRole('button', { name: 'Register Asset' }));

      await waitFor(() => {
        expect(screen.getByText('Asset tag "AST-DUPLICATE" already exists.')).toBeInTheDocument();
      });
    });
  });

  describe('Issue, Return, and Reassign Action Modals', () => {
    it('opens Issue modal for available site asset and issues to active employee', async () => {
      vi.mocked(assetsApi.issueAssetApi).mockResolvedValueOnce({
        ...mockAssetAvailableSite,
        status: 'issued_employee',
        current_custodian_id: 'emp-1',
        current_custodian_name: 'Rahul Sharma',
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0001')).toBeInTheDocument();
      });

      const issueBtn = screen.getByTestId(`issue-btn-${mockAssetAvailableSite.id}`);
      expect(issueBtn).toBeInTheDocument();

      fireEvent.click(issueBtn);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /issue asset to employee/i })).toBeInTheDocument();
      });
      expect(screen.getAllByText(/Rotary Hammer Drill/).length).toBeGreaterThanOrEqual(1);

      // Select assigned employee
      const employeeSelect = screen.getByLabelText(/recipient employee/i);
      fireEvent.change(employeeSelect, { target: { value: 'emp-1' } });

      fireEvent.click(screen.getByRole('button', { name: /confirm issue/i }));

      await waitFor(() => {
        expect(assetsApi.issueAssetApi).toHaveBeenCalledWith(
          mockAssetAvailableSite.id,
          expect.objectContaining({
            employee_id: 'emp-1',
          }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/successfully issued/i)).toBeInTheDocument();
      });
    });

    it('opens Return modal for issued asset and completes return', async () => {
      vi.mocked(assetsApi.returnAssetApi).mockResolvedValueOnce({
        ...mockAssetIssued,
        status: 'available',
        current_custodian_id: null,
        current_custodian_name: null,
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0002')).toBeInTheDocument();
      });

      const returnBtn = screen.getByTestId(`return-btn-${mockAssetIssued.id}`);
      expect(returnBtn).toBeInTheDocument();

      fireEvent.click(returnBtn);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /return issued asset/i })).toBeInTheDocument();
      });
      expect(screen.getByText(/Recorded Custodian/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /confirm return/i }));

      await waitFor(() => {
        expect(assetsApi.returnAssetApi).toHaveBeenCalledWith(
          mockAssetIssued.id,
          expect.objectContaining({
            employee_id: 'emp-1',
            condition: 'good',
          }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/successfully returned/i)).toBeInTheDocument();
      });
    });

    it('opens Reassign modal for available asset and completes site reassignment', async () => {
      vi.mocked(assetsApi.reassignAssetApi).mockResolvedValueOnce({
        ...mockAssetAvailableSite,
        current_site_id: 'site-2',
        current_site_name: 'Substation South',
      });

      renderAssetsPage('administrator');

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0001')).toBeInTheDocument();
      });

      const reassignBtn = screen.getByTestId(`reassign-btn-${mockAssetAvailableSite.id}`);
      expect(reassignBtn).toBeInTheDocument();

      fireEvent.click(reassignBtn);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /reassign asset location/i })).toBeInTheDocument();
      });

      // Change target site
      const siteSelect = screen.getByLabelText(/destination site/i);
      fireEvent.change(siteSelect, { target: { value: 'site-2' } });

      fireEvent.click(screen.getByRole('button', { name: /confirm reassignment/i }));

      await waitFor(() => {
        expect(assetsApi.reassignAssetApi).toHaveBeenCalledWith(
          mockAssetAvailableSite.id,
          expect.objectContaining({
            target_location_type: 'site',
            target_site_id: 'site-2',
          }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/location reassigned/i)).toBeInTheDocument();
      });
    });

    it('allows supervisor to reassign asset to authorized project site or warehouse', async () => {
      vi.mocked(assetsApi.reassignAssetApi).mockResolvedValueOnce({
        ...mockAssetAvailableSite,
        current_site_id: 'site-2',
        current_site_name: 'Substation South',
      });

      renderAssetsPage('supervisor');

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0001')).toBeInTheDocument();
      });

      const reassignBtn = screen.getByTestId(`reassign-btn-${mockAssetAvailableSite.id}`);
      fireEvent.click(reassignBtn);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /reassign asset location/i })).toBeInTheDocument();
      });

      // Supervisor has Central Warehouse option just like Administrator
      const locationTypeSelect = screen.getByLabelText(/destination location type/i);
      expect(locationTypeSelect.querySelector('option[value="warehouse"]')).not.toBeNull();

      // Destination site dropdown contains authorized project sites
      const siteSelect = screen.getByLabelText(/destination site/i);
      fireEvent.change(siteSelect, { target: { value: 'site-2' } });

      fireEvent.click(screen.getByRole('button', { name: /confirm reassignment/i }));

      await waitFor(() => {
        expect(assetsApi.reassignAssetApi).toHaveBeenCalledWith(
          mockAssetAvailableSite.id,
          expect.objectContaining({
            target_location_type: 'site',
            target_site_id: 'site-2',
          }),
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/location reassigned/i)).toBeInTheDocument();
      });
    });

    it('allows supervisor to view register button, open register modal, and view all site filter options', async () => {
      renderAssetsPage('supervisor');

      await waitFor(() => {
        expect(screen.getByText('AST-2026-0001')).toBeInTheDocument();
      });

      // Supervisor sees + Register Asset button
      const registerBtn = screen.getByTestId('register-asset-button');
      expect(registerBtn).toBeInTheDocument();

      // Site filter dropdown contains all active sites
      const siteFilterSelect = screen.getByLabelText(/site/i);
      const siteFilterOptions = Array.from(siteFilterSelect.querySelectorAll('option')).map((o) => o.textContent);
      expect(siteFilterOptions).toContain('Metro Line 1 Station');
      expect(siteFilterOptions).toContain('Substation South');

      // Click register button opens modal
      fireEvent.click(registerBtn);
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Register New Asset/i })).toBeInTheDocument();
      });
    });
  });
});

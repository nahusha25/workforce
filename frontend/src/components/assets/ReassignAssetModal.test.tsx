import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { ReassignAssetModal } from './ReassignAssetModal';
import { AuthContext } from '../../context/AuthContext';
import * as assetsApi from '../../api/assets';
import * as masterDataApi from '../../api/masterData';
import type { SystemRole } from '../../types/auth';

vi.mock('../../api/assets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/assets')>();
  return {
    ...actual,
    reassignAssetApi: vi.fn(),
    getAssetDestinationSitesApi: vi.fn(),
    getAssetSitesApi: vi.fn(),
  };
});

vi.mock('../../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn(),
  };
});

const mockAsset: assetsApi.AssetResponse = {
  id: 'ast-100',
  asset_tag: 'AST-000100',
  name: 'Total Station Survey Equipment',
  category: 'Survey',
  condition: 'good',
  status: 'available',
  location_type: 'site',
  current_site_id: 'site-alpha',
  current_site_name: 'Site Alpha Tech Park',
  current_custodian_id: null,
  current_custodian_name: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockAuthorizedSites: masterDataApi.SiteResponseData[] = [
  {
    id: 'site-beta',
    name: 'Site Beta Metro Junction',
    project_id: 'proj-1',
    is_active: true,
  },
  {
    id: 'site-gamma',
    name: 'Site Gamma Highline',
    project_id: 'proj-2',
    is_active: true,
  },
];

const renderModal = (
  role: SystemRole,
  asset: assetsApi.AssetResponse = mockAsset,
  onSuccess = vi.fn(),
  onClose = vi.fn(),
) => {
  const mockAuthContext = {
    user: {
      id: 'user-1',
      user_id: 'u-1',
      employee_code: 'EMP001',
      mobile_id: '+919876543210',
      name: role === 'supervisor' ? 'Supervisor John' : 'Admin Jane',
      system_role: role,
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      trade_roles: [],
      active_sites: [{ id: 'site-alpha', name: 'Site Alpha Tech Park' }],
    },
    role,
    accessToken: 'mock-token',
    isAuthenticated: true,
    isLoading: false,
    error: null,
    requestOtp: vi.fn(),
    verifyOtp: vi.fn(),
    logout: vi.fn(),
    clearError: vi.fn(),
  };

  return render(
    <AuthContext.Provider value={mockAuthContext}>
      <ReassignAssetModal
        isOpen={true}
        asset={asset}
        onClose={onClose}
        onSuccess={onSuccess}
      />
    </AuthContext.Provider>,
  );
};

describe('ReassignAssetModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.getAssetSitesApi).mockResolvedValue(mockAuthorizedSites);
    vi.mocked(assetsApi.getAssetDestinationSitesApi).mockResolvedValue(mockAuthorizedSites);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockAuthorizedSites);
  });

  afterEach(() => {
    cleanup();
  });

  it('allows administrator to see all destination sites and the central warehouse option', async () => {
    renderModal('administrator');

    expect(screen.getByRole('heading', { name: /reassign asset location/i })).toBeInTheDocument();

    // Check Destination Location Type options
    const locationTypeSelect = screen.getByLabelText(/destination location type/i);
    const options = Array.from(locationTypeSelect.querySelectorAll('option')).map((o) => o.value);
    expect(options).toContain('site');
    expect(options).toContain('warehouse');

    // Wait for sites to load
    await waitFor(() => {
      const siteSelect = screen.getByLabelText(/destination site/i);
      expect(siteSelect).toBeInTheDocument();
      const siteOptions = Array.from(siteSelect.querySelectorAll('option')).map((o) => o.textContent);
      expect(siteOptions).toContain('Site Beta Metro Junction');
      expect(siteOptions).toContain('Site Gamma Highline');
    });

    // Reassign to Warehouse
    fireEvent.change(locationTypeSelect, { target: { value: 'warehouse' } });

    vi.mocked(assetsApi.reassignAssetApi).mockResolvedValueOnce({
      ...mockAsset,
      location_type: 'warehouse',
      current_site_id: null,
      current_site_name: null,
    });

    fireEvent.click(screen.getByRole('button', { name: /confirm reassignment/i }));

    await waitFor(() => {
      expect(assetsApi.reassignAssetApi).toHaveBeenCalledWith(
        mockAsset.id,
        expect.objectContaining({
          target_location_type: 'warehouse',
          target_site_id: null,
        }),
      );
    });
  });

  it('allows supervisor to reassign to warehouse or project sites with full actions', async () => {
    const handleSuccess = vi.fn();
    renderModal('supervisor', mockAsset, handleSuccess);

    expect(screen.getByRole('heading', { name: /reassign asset location/i })).toBeInTheDocument();

    // Warehouse option is present for supervisor
    const locationTypeSelect = screen.getByLabelText(/destination location type/i);
    const options = Array.from(locationTypeSelect.querySelectorAll('option')).map((o) => o.value);
    expect(options).toContain('site');
    expect(options).toContain('warehouse');

    // Supervisor should see all authorized project sites for this client (not just their own site)
    await waitFor(() => {
      const siteSelect = screen.getByLabelText(/destination site/i);
      expect(siteSelect).toBeInTheDocument();
      const siteOptions = Array.from(siteSelect.querySelectorAll('option')).map((o) => o.textContent);
      expect(siteOptions).toContain('Site Beta Metro Junction');
      expect(siteOptions).toContain('Site Gamma Highline');
      expect(siteOptions).not.toContain('Site Alpha Tech Park'); // Current site excluded
    });

    // Select authorized destination site
    const siteSelect = screen.getByLabelText(/destination site/i);
    fireEvent.change(siteSelect, { target: { value: 'site-beta' } });

    // Enter remarks
    const remarksInput = screen.getByLabelText(/reassignment rationale/i);
    fireEvent.change(remarksInput, { target: { value: 'Relocated for metro tunneling kickoff' } });

    vi.mocked(assetsApi.reassignAssetApi).mockResolvedValueOnce({
      ...mockAsset,
      current_site_id: 'site-beta',
      current_site_name: 'Site Beta Metro Junction',
    });

    fireEvent.click(screen.getByRole('button', { name: /confirm reassignment/i }));

    await waitFor(() => {
      expect(assetsApi.reassignAssetApi).toHaveBeenCalledWith(
        mockAsset.id,
        expect.objectContaining({
          target_location_type: 'site',
          target_site_id: 'site-beta',
          remarks: 'Relocated for metro tunneling kickoff',
        }),
      );
      expect(handleSuccess).toHaveBeenCalled();
    });
  });

  it('displays backend error message when unauthorized transfer is rejected', async () => {
    renderModal('supervisor');

    await waitFor(() => {
      expect(screen.getByLabelText(/destination site/i)).toBeInTheDocument();
    });

    const siteSelect = screen.getByLabelText(/destination site/i);
    fireEvent.change(siteSelect, { target: { value: 'site-beta' } });

    vi.mocked(assetsApi.reassignAssetApi).mockRejectedValueOnce({
      response: {
        status: 403,
        data: {
          detail: 'Supervisors are only authorized to transfer assets to project sites belonging to the same client.',
        },
      },
    });

    fireEvent.click(screen.getByRole('button', { name: /confirm reassignment/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          'Supervisors are only authorized to transfer assets to project sites belonging to the same client.',
        ),
      ).toBeInTheDocument();
    });
  });

  it('disables reassignment when asset is currently issued to an employee', () => {
    const issuedAsset: assetsApi.AssetResponse = {
      ...mockAsset,
      status: 'issued_employee',
      current_custodian_id: 'emp-99',
      current_custodian_name: 'Worker 99',
    };

    renderModal('supervisor', issuedAsset);

    expect(
      screen.getByText(/this asset is currently issued to an employee. it must be returned/i),
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /confirm reassignment/i });
    expect(submitBtn).toBeDisabled();
  });
});

import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { InventoryPage } from './InventoryPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AuthContext } from '../context/AuthContext';
import type { SystemRole } from '../types/auth';
import { getSitesApi } from '../api/masterData';
import { getMaterialsCatalogue } from '../api/dailyWork';
import {
  getSiteInventoryApi,
  getInventorySitesApi,
  recordStockInwardApi,
  getMaterialStockMovementsApi,
} from '../api/inventory';

vi.mock('../api/masterData', () => ({
  getSitesApi: vi.fn(),
}));

vi.mock('../api/dailyWork', () => ({
  getMaterialsCatalogue: vi.fn(),
}));

vi.mock('../api/inventory', () => ({
  getSiteInventoryApi: vi.fn(),
  getInventorySitesApi: vi.fn(),
  recordStockInwardApi: vi.fn(),
  getMaterialStockMovementsApi: vi.fn(),
}));

const mockSites = [
  {
    id: 'site-1',
    name: 'Alpha Tower',
    project_id: 'proj-1',
    supervisor_id: 'user-sup',
    permitted_radius_m: 500,
    is_active: true,
  },
  {
    id: 'site-2',
    name: 'Beta Plaza',
    project_id: 'proj-1',
    supervisor_id: 'user-other',
    permitted_radius_m: 500,
    is_active: true,
  },
];

const mockCatalogue = [
  {
    id: 'mat-1',
    material_code: 'MAT-CAT6',
    name: 'Cat6 Cable 30m',
    unit_of_measure: 'roll',
    category: 'cable',
    purchase_approval_limit: 5000,
    is_active: true,
  },
  {
    id: 'mat-2',
    material_code: 'MAT-RJ45',
    name: 'RJ45 Connectors Box',
    unit_of_measure: 'box',
    category: 'consumable',
    purchase_approval_limit: 1500,
    is_active: true,
  },
];

const mockInventoryAlpha = {
  items: [
    {
      site_id: 'site-1',
      site_name: 'Alpha Tower',
      material_id: 'mat-1',
      material_code: 'MAT-CAT6',
      material_name: 'Cat6 Cable 30m',
      unit_of_measure: 'roll',
      category: 'cable',
      quantity_available: 10.0,
      last_movement_at: '2026-10-15T10:00:00Z',
    },
    {
      site_id: 'site-1',
      site_name: 'Alpha Tower',
      material_id: 'mat-2',
      material_code: 'MAT-RJ45',
      material_name: 'RJ45 Connectors Box',
      unit_of_measure: 'box',
      category: 'consumable',
      quantity_available: 0.0,
      last_movement_at: null,
    },
  ],
  total: 2,
};

const renderWithRole = (role: SystemRole = 'administrator', userId: string = 'user-admin') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: userId,
          user_id: userId,
          employee_code: 'EMP-001',
          mobile_id: '+919999999999',
          name: 'Test User',
          system_role: role,
          trade_roles: [],
          active_sites: role === 'supervisor' ? [{ id: 'site-1', name: 'Alpha Tower' }] : [],
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
      <MemoryRouter initialEntries={['/inventory']}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['supervisor', 'administrator', 'director']} />}>
            <Route path="/inventory" element={<InventoryPage />} />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('InventoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getInventorySitesApi as any).mockResolvedValue(mockSites);
    (getSitesApi as any).mockResolvedValue(mockSites);
    (getMaterialsCatalogue as any).mockResolvedValue(mockCatalogue);
    (getSiteInventoryApi as any).mockResolvedValue(mockInventoryAlpha);
  });

  afterEach(() => {
    cleanup();
  });

  it('denies access to employees and redirects to 403', async () => {
    renderWithRole('employee', 'user-emp');
    expect(await screen.findByTestId('forbidden-page')).toBeInTheDocument();
  });

  it('allows access to administrators and displays all sites', async () => {
    renderWithRole('administrator', 'user-admin');

    expect(await screen.findByText('Material Inventory')).toBeInTheDocument();

    await waitFor(() => {
      const siteSelect = screen.getByLabelText(/Site/i) as HTMLSelectElement;
      expect(siteSelect).toBeInTheDocument();
      expect(siteSelect.options.length).toBe(2);
      expect(siteSelect.options[0].text).toBe('Alpha Tower');
      expect(siteSelect.options[1].text).toBe('Beta Plaza');
    });
  });

  it('restricts supervisors to their supervised sites', async () => {
    (getInventorySitesApi as any).mockResolvedValue([mockSites[0]]);
    renderWithRole('supervisor', 'user-sup');

    expect(await screen.findByText('Material Inventory')).toBeInTheDocument();

    await waitFor(() => {
      const siteSelect = screen.getByLabelText(/Site/i) as HTMLSelectElement;
      expect(siteSelect).toBeInTheDocument();
      // user-sup only supervises site-1
      expect(siteSelect.options.length).toBe(1);
      expect(siteSelect.options[0].text).toBe('Alpha Tower');
    });
  });

  it('shows empty state without error banner when supervisor has no site assignments', async () => {
    (getInventorySitesApi as any).mockResolvedValue([]);
    renderWithRole('supervisor', 'user-sup-unassigned');

    expect(await screen.findByText('Material Inventory')).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText('No authorized sites available for inventory tracking.')
      ).toBeInTheDocument();
      const siteSelect = screen.getByLabelText(/Site/i) as HTMLSelectElement;
      expect(siteSelect).toBeDisabled();
      expect(siteSelect.options[0].text).toBe('No authorized sites available');
      expect(screen.queryByText(/Not enough permissions/i)).not.toBeInTheDocument();
    });
  });

  it('displays authorization error when site listing fails with 403', async () => {
    (getInventorySitesApi as any).mockRejectedValue({
      response: { data: { detail: 'Not enough permissions' } },
      message: 'Not enough permissions',
    });
    renderWithRole('supervisor', 'user-sup');

    expect(await screen.findByText('Not enough permissions')).toBeInTheDocument();
    expect(
      screen.getByText('No authorized sites available for inventory tracking.')
    ).toBeInTheDocument();
  });


  it('renders inventory table with material details, balances, and last movement', async () => {
    renderWithRole('administrator');

    expect(await screen.findByText('Cat6 Cable 30m')).toBeInTheDocument();
    expect(screen.getByText('MAT-CAT6')).toBeInTheDocument();
    expect(screen.getByText('10.00 roll')).toBeInTheDocument();

    expect(screen.getByText('RJ45 Connectors Box')).toBeInTheDocument();
    expect(screen.getByText('0.00 box')).toBeInTheDocument();
  });

  it('filters inventory by search query', async () => {
    renderWithRole('administrator');

    await screen.findByText('Cat6 Cable 30m');

    const searchInput = screen.getByPlaceholderText(/Search by name or code/i);
    fireEvent.change(searchInput, { target: { value: 'RJ45' } });

    await waitFor(() => {
      expect(getSiteInventoryApi).toHaveBeenCalledWith(
        'site-1',
        expect.objectContaining({ search: 'RJ45' })
      );
    });
  });

  it('displays empty state when no inventory items found', async () => {
    (getSiteInventoryApi as any).mockResolvedValue({ items: [], total: 0 });

    renderWithRole('administrator');

    expect(
      await screen.findByText('No material inventory records found matching your filters.')
    ).toBeInTheDocument();
  });

  it('opens Stock Inward modal, submits inward stock, and refreshes inventory', async () => {
    (recordStockInwardApi as any).mockResolvedValue({
      movement_id: 'mvt-new',
      site_id: 'site-1',
      material_id: 'mat-1',
      material_name: 'Cat6 Cable 30m',
      movement_type: 'inward',
      quantity: 5.0,
      balance_after: 15.0,
      unit_of_measure: 'roll',
      created_at: '2026-10-15T12:00:00Z',
    });

    renderWithRole('administrator');

    await screen.findByText('Cat6 Cable 30m');

    const inwardBtn = screen.getByRole('button', { name: /Record Stock Inward/i });
    fireEvent.click(inwardBtn);

    expect(screen.getByRole('dialog', { name: /Stock Inward/i })).toBeInTheDocument();

    // Select material
    const matSelect = screen.getByLabelText(/Catalogue Material \*/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    // Enter quantity
    const qtyInput = screen.getByLabelText(/Quantity Received/i);
    fireEvent.change(qtyInput, { target: { value: '5.00' } });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: 'Record Inward' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(recordStockInwardApi).toHaveBeenCalledWith(
        expect.objectContaining({
          site_id: 'site-1',
          material_id: 'mat-1',
          quantity: 5.0,
          idempotency_key: expect.stringMatching(/^INW-/),
        })
      );
    });

    // Check success banner
    expect(await screen.findByText(/Stock Received Successfully/i)).toBeInTheDocument();
    expect(screen.getByText(/New available balance:/i)).toBeInTheDocument();

    // Close modal
    fireEvent.click(screen.getByRole('button', { name: 'Done' }));

    // Inventory should be refetched
    await waitFor(() => {
      expect(getSiteInventoryApi).toHaveBeenCalledTimes(2);
    });
  });

  it('opens Movement History modal and displays ledger records', async () => {
    (getMaterialStockMovementsApi as any).mockResolvedValue({
      site_id: 'site-1',
      material_id: 'mat-1',
      total: 2,
      items: [
        {
          movement_id: 'mvt-1',
          site_id: 'site-1',
          material_id: 'mat-1',
          movement_type: 'inward',
          quantity: 15.0,
          balance_after: 15.0,
          idempotency_key: 'INW-1',
          remarks: 'Delivery challan #101',
          created_by: 'user-admin',
          actor_name: 'Admin User',
          created_at: '2026-10-14T10:00:00Z',
        },
        {
          movement_id: 'mvt-2',
          site_id: 'site-1',
          material_id: 'mat-1',
          movement_type: 'consumed',
          quantity: 5.0,
          balance_after: 10.0,
          idempotency_key: 'CON-1',
          remarks: 'Cabling work',
          created_by: 'user-emp',
          actor_name: 'John Doe',
          created_at: '2026-10-15T09:00:00Z',
        },
      ],
    });

    renderWithRole('administrator');

    await screen.findByText('Cat6 Cable 30m');

    const historyBtn = screen.getByRole('button', { name: /View movements for Cat6 Cable 30m/i });
    fireEvent.click(historyBtn);

    expect(await screen.findByText('Stock Movement History: Cat6 Cable 30m')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Inward')).toBeInTheDocument();
      expect(screen.getByText('Consumed')).toBeInTheDocument();
      expect(screen.getByText('+15.00 roll')).toBeInTheDocument();
      expect(screen.getByText('-5.00 roll')).toBeInTheDocument();
      expect(screen.getByText('Delivery challan #101')).toBeInTheDocument();
    });

    // Close modal
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() => {
      expect(screen.queryByText('Stock Movement History: Cat6 Cable 30m')).not.toBeInTheDocument();
    });
  });

  it('handles API error when loading inventory gracefully', async () => {
    (getSiteInventoryApi as any).mockRejectedValue(new Error('Network error loading stock'));

    renderWithRole('administrator');

    expect(await screen.findByText('Network error loading stock')).toBeInTheDocument();
  });

  it('displays error when supervisor encounters 403 on site inventory fetch', async () => {
    (getInventorySitesApi as any).mockResolvedValue([mockSites[0]]);
    (getSiteInventoryApi as any).mockRejectedValue({
      response: { data: { detail: 'Supervisor is not authorized to view inventory for this site.' } },
      message: 'Supervisor is not authorized to view inventory for this site.',
    });

    renderWithRole('supervisor', 'user-sup');

    expect(
      await screen.findByText('Supervisor is not authorized to view inventory for this site.')
    ).toBeInTheDocument();
  });
});


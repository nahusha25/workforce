import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MaterialsPage } from './MaterialsPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AuthContext } from '../context/AuthContext';
import type { SystemRole } from '../types/auth';
import {
  getMaterialsApi,
  getMaterialByIdApi,
  createMaterialApi,
  updateMaterialApi,
} from '../api/masterData';

// Mock API module
vi.mock('../api/masterData', () => ({
  getMaterialsApi: vi.fn(),
  getMaterialByIdApi: vi.fn(),
  createMaterialApi: vi.fn(),
  updateMaterialApi: vi.fn(),
}));

const mockMaterials = [
  {
    id: 'mat-1',
    name: 'RJ45 Connectors (Pack of 100)',
    material_code: 'MAT-RJ45-100',
    description: 'Cat6 unshielded modular plugs',
    unit_of_measure: 'box',
    category: 'consumable',
    purchase_approval_limit: 1200.0,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'mat-2',
    name: 'Heavy Duty Rotary Hammer Drill',
    material_code: 'TOOL-DRILL-01',
    description: 'Site rotary hammer drill',
    unit_of_measure: 'piece',
    category: 'tool',
    purchase_approval_limit: 8000.0,
    is_active: false,
    created_at: '2026-01-02T00:00:00Z',
  },
];

const renderWithRoleGuard = (role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'user-1',
          user_id: 'u-1',
          employee_code: 'EMP-001',
          mobile_id: '+919999999999',
          name: 'Test Admin',
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
      <MemoryRouter initialEntries={['/admin/materials']}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['administrator', 'director']} />}>
            <Route path="/admin/materials" element={<MaterialsPage />} />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('MaterialsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getMaterialsApi as any).mockResolvedValue(mockMaterials);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders list view showing key fields and active/inactive status badges', async () => {
    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('RJ45 Connectors (Pack of 100)')).toBeInTheDocument();
      expect(screen.getByText('Heavy Duty Rotary Hammer Drill')).toBeInTheDocument();
    });

    expect(screen.getByText('MAT-RJ45-100')).toBeInTheDocument();
    expect(screen.getByText('TOOL-DRILL-01')).toBeInTheDocument();
    expect(screen.getByText('box')).toBeInTheDocument();
    expect(screen.getByText('piece')).toBeInTheDocument();
    expect(screen.getByText('₹1200.00')).toBeInTheDocument();
    expect(screen.getByTestId('materials-table')).toBeInTheDocument();
  });

  it('successfully creates a new material via POST', async () => {
    (createMaterialApi as any).mockResolvedValue({
      id: 'mat-3',
      name: 'Cat6 Cable Drum 305m',
      material_code: 'MAT-CAT6-305',
      unit_of_measure: 'drum',
      category: 'cable',
      purchase_approval_limit: 6500.0,
      is_active: true,
      created_at: '2026-01-03T00:00:00Z',
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('add-material-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('add-material-btn'));

    fireEvent.change(screen.getByTestId('material-name-input'), {
      target: { value: 'Cat6 Cable Drum 305m' },
    });
    fireEvent.change(screen.getByTestId('material-code-input'), {
      target: { value: 'MAT-CAT6-305' },
    });
    fireEvent.change(screen.getByTestId('category-select'), {
      target: { value: 'cable' },
    });
    fireEvent.change(screen.getByTestId('uom-input'), {
      target: { value: 'drum' },
    });
    fireEvent.change(screen.getByTestId('limit-input'), {
      target: { value: '6500.00' },
    });

    fireEvent.click(screen.getByTestId('save-material-btn'));

    await waitFor(() => {
      expect(createMaterialApi).toHaveBeenCalledWith({
        name: 'Cat6 Cable Drum 305m',
        material_code: 'MAT-CAT6-305',
        category: 'cable',
        unit_of_measure: 'drum',
        purchase_approval_limit: 6500.0,
        description: undefined,
        is_active: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Material "Cat6 Cable Drum 305m" created successfully!/i)).toBeInTheDocument();
    });
  });

  it('successfully loads existing material via GET and updates via PUT', async () => {
    (getMaterialByIdApi as any).mockResolvedValue(mockMaterials[0]);
    (updateMaterialApi as any).mockResolvedValue({
      ...mockMaterials[0],
      name: 'RJ45 Connectors (Pack of 200)',
      purchase_approval_limit: 2200.0,
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn-mat-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('edit-btn-mat-1'));

    await waitFor(() => {
      expect(getMaterialByIdApi).toHaveBeenCalledWith('mat-1');
      expect(screen.getByDisplayValue('RJ45 Connectors (Pack of 100)')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('material-name-input'), {
      target: { value: 'RJ45 Connectors (Pack of 200)' },
    });
    fireEvent.change(screen.getByTestId('limit-input'), {
      target: { value: '2200.00' },
    });

    fireEvent.click(screen.getByTestId('save-material-btn'));

    await waitFor(() => {
      expect(updateMaterialApi).toHaveBeenCalledWith(
        'mat-1',
        expect.objectContaining({
          name: 'RJ45 Connectors (Pack of 200)',
          purchase_approval_limit: 2200.0,
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Material "RJ45 Connectors \(Pack of 200\)" updated successfully!/i)).toBeInTheDocument();
    });
  });

  it('deactivates an active material via PUT without hard delete', async () => {
    (updateMaterialApi as any).mockResolvedValue({
      ...mockMaterials[0],
      is_active: false,
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('deactivate-btn-mat-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('deactivate-btn-mat-1'));

    await waitFor(() => {
      expect(updateMaterialApi).toHaveBeenCalledWith('mat-1', { is_active: false });
      expect(screen.getByText(/Material "RJ45 Connectors \(Pack of 100\)" deactivated successfully/i)).toBeInTheDocument();
    });
  });

  it('enforces RoleGuard blocking non-admin/director role from accessing page', async () => {
    renderWithRoleGuard('employee');

    await waitFor(() => {
      expect(screen.getByTestId('forbidden-page')).toBeInTheDocument();
      expect(screen.queryByText('Material Master Management')).not.toBeInTheDocument();
    });
  });

  it('allows director role to access page per BE-021 requirements', async () => {
    renderWithRoleGuard('director');

    await waitFor(() => {
      expect(screen.getByText('Material Master Management')).toBeInTheDocument();
      expect(screen.queryByTestId('forbidden-page')).not.toBeInTheDocument();
    });
  });
});

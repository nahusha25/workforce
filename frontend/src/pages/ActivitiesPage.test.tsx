import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ActivitiesPage } from './ActivitiesPage';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AuthContext } from '../context/AuthContext';
import type { SystemRole } from '../types/auth';
import {
  getActivitiesApi,
  getActivityByIdApi,
  createActivityApi,
  updateActivityApi,
} from '../api/masterData';

// Mock API module
vi.mock('../api/masterData', () => ({
  getActivitiesApi: vi.fn(),
  getActivityByIdApi: vi.fn(),
  createActivityApi: vi.fn(),
  updateActivityApi: vi.fn(),
}));

const mockActivities = [
  {
    id: 'act-1',
    name: 'Cable Pulling & Laying',
    category: 'cable',
    unit_of_measure: 'metre',
    approved_rate: 25.5,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'act-2',
    name: 'Camera Device Mounting',
    category: 'device',
    unit_of_measure: 'device',
    approved_rate: 150.0,
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
      <MemoryRouter initialEntries={['/admin/activities']}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['administrator', 'director']} />}>
            <Route path="/admin/activities" element={<ActivitiesPage />} />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('ActivitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getActivitiesApi as any).mockResolvedValue(mockActivities);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders list view showing key fields and active/inactive status badges', async () => {
    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByText('Cable Pulling & Laying')).toBeInTheDocument();
      expect(screen.getByText('Camera Device Mounting')).toBeInTheDocument();
    });

    expect(screen.getByText('metre')).toBeInTheDocument();
    expect(screen.getAllByText('device').length).toBeGreaterThan(0);
    expect(screen.getByText('₹25.50')).toBeInTheDocument();
    expect(screen.getByTestId('activities-table')).toBeInTheDocument();
  });

  it('successfully creates a new activity via POST', async () => {
    (createActivityApi as any).mockResolvedValue({
      id: 'act-3',
      name: 'Wall Drilling',
      category: 'drilling',
      unit_of_measure: 'hole',
      approved_rate: 40.0,
      is_active: true,
      created_at: '2026-01-03T00:00:00Z',
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('add-activity-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('add-activity-btn'));

    fireEvent.change(screen.getByTestId('activity-name-input'), {
      target: { value: 'Wall Drilling' },
    });
    fireEvent.change(screen.getByTestId('category-select'), {
      target: { value: 'drilling' },
    });
    fireEvent.change(screen.getByTestId('uom-input'), {
      target: { value: 'hole' },
    });
    fireEvent.change(screen.getByTestId('rate-input'), {
      target: { value: '40.00' },
    });

    fireEvent.click(screen.getByTestId('save-activity-btn'));

    await waitFor(() => {
      expect(createActivityApi).toHaveBeenCalledWith({
        name: 'Wall Drilling',
        category: 'drilling',
        unit_of_measure: 'hole',
        approved_rate: 40.0,
        is_active: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Activity "Wall Drilling" created successfully!/i)).toBeInTheDocument();
    });
  });

  it('successfully loads existing activity via GET and updates via PUT', async () => {
    (getActivityByIdApi as any).mockResolvedValue(mockActivities[0]);
    (updateActivityApi as any).mockResolvedValue({
      ...mockActivities[0],
      name: 'Cable Pulling & Laying (Enhanced)',
      approved_rate: 30.0,
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('edit-btn-act-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('edit-btn-act-1'));

    await waitFor(() => {
      expect(getActivityByIdApi).toHaveBeenCalledWith('act-1');
      expect(screen.getByDisplayValue('Cable Pulling & Laying')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('activity-name-input'), {
      target: { value: 'Cable Pulling & Laying (Enhanced)' },
    });
    fireEvent.change(screen.getByTestId('rate-input'), {
      target: { value: '30.00' },
    });

    fireEvent.click(screen.getByTestId('save-activity-btn'));

    await waitFor(() => {
      expect(updateActivityApi).toHaveBeenCalledWith(
        'act-1',
        expect.objectContaining({
          name: 'Cable Pulling & Laying (Enhanced)',
          approved_rate: 30.0,
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Activity "Cable Pulling & Laying \(Enhanced\)" updated successfully!/i)).toBeInTheDocument();
    });
  });

  it('deactivates an active activity via PUT without hard delete', async () => {
    (updateActivityApi as any).mockResolvedValue({
      ...mockActivities[0],
      is_active: false,
    });

    renderWithRoleGuard('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('deactivate-btn-act-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('deactivate-btn-act-1'));

    await waitFor(() => {
      expect(updateActivityApi).toHaveBeenCalledWith('act-1', { is_active: false });
      expect(screen.getByText(/Activity "Cable Pulling & Laying" deactivated successfully/i)).toBeInTheDocument();
    });
  });

  it('enforces RoleGuard blocking non-admin/director role from accessing page', async () => {
    renderWithRoleGuard('employee');

    await waitFor(() => {
      expect(screen.getByTestId('forbidden-page')).toBeInTheDocument();
      expect(screen.queryByText('Activity Catalog Management')).not.toBeInTheDocument();
    });
  });

  it('allows director role to access page per BE-021 requirements', async () => {
    renderWithRoleGuard('director');

    await waitFor(() => {
      expect(screen.getByText('Activity Catalog Management')).toBeInTheDocument();
      expect(screen.queryByTestId('forbidden-page')).not.toBeInTheDocument();
    });
  });
});

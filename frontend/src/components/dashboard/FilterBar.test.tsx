import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { FilterBar } from './FilterBar';
import * as masterDataApi from '../../api/masterData';
import * as employeeApi from '../../api/employee';
import type { DashboardFilters } from '../../api/dashboard';

afterEach(() => {
  cleanup();
});

vi.mock('../../api/masterData', () => ({
  getClientsApi: vi.fn(),
  getSitesApi: vi.fn(),
}));

vi.mock('../../api/employee', () => ({
  getEmployeesApi: vi.fn(),
}));

describe('FilterBar', () => {
  const initialFilters: DashboardFilters = {
    date_from: '2026-09-01',
    date_to: '2026-09-30',
    client_id: null,
    site_id: null,
    employee_id: null,
    supervisor_id: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(masterDataApi.getClientsApi).mockResolvedValue([
      { id: 'client-1', name: 'Apex Infra', is_active: true, created_at: '2026-01-01' },
    ]);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue([
      { id: 'site-1', name: 'Metro Line', is_active: true, project_id: 'proj-1' },
    ]);
    vi.mocked(employeeApi.getEmployeesApi).mockResolvedValue([
      {
        id: 'emp-1',
        user_id: 'u-1',
        employee_code: 'EMP-001',
        mobile_id: 'mob-1',
        name: 'Ravi Kumar',
        system_role: 'supervisor',
        is_active: true,
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
        trade_roles: [],
        active_sites: [],
      },
    ]);
  });

  it('renders date inputs and populated dropdowns', async () => {
    const handleFilterChange = vi.fn();
    render(<FilterBar filters={initialFilters} onFilterChange={handleFilterChange} />);

    expect(screen.getByTestId('filter-date-from')).toBeTruthy();
    expect(screen.getByTestId('filter-date-to')).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText('Apex Infra')).toBeTruthy();
      expect(screen.getByText('Metro Line')).toBeTruthy();
      expect(screen.getAllByText('Ravi Kumar (EMP-001)').length).toBe(2);
    });
  });

  it('calls onFilterChange when dates change', () => {
    const handleFilterChange = vi.fn();
    render(<FilterBar filters={initialFilters} onFilterChange={handleFilterChange} />);

    const dateFrom = screen.getByTestId('filter-date-from');
    fireEvent.change(dateFrom, { target: { value: '2026-08-15' } });
    expect(handleFilterChange).toHaveBeenCalledWith({ date_from: '2026-08-15' });

    const dateTo = screen.getByTestId('filter-date-to');
    fireEvent.change(dateTo, { target: { value: '2026-08-30' } });
    expect(handleFilterChange).toHaveBeenCalledWith({ date_to: '2026-08-30' });
  });

  it('shows validation error when date_from > date_to', async () => {
    const handleFilterChange = vi.fn();
    render(
      <FilterBar
        filters={{ ...initialFilters, date_from: '2026-10-05', date_to: '2026-10-01' }}
        onFilterChange={handleFilterChange}
      />
    );

    expect(
      screen.getByText(/From date must be earlier than or equal to To date/i)
    ).toBeTruthy();
  });

  it('shows validation error when range exceeds 365 days', async () => {
    const handleFilterChange = vi.fn();
    render(
      <FilterBar
        filters={{ ...initialFilters, date_from: '2024-01-01', date_to: '2025-06-01' }}
        onFilterChange={handleFilterChange}
      />
    );

    expect(screen.getByText(/Date range cannot exceed 365 days/i)).toBeTruthy();
  });

  it('calls onReset or default filter reset when reset button clicked', () => {
    const handleFilterChange = vi.fn();
    const handleReset = vi.fn();
    render(
      <FilterBar
        filters={initialFilters}
        onFilterChange={handleFilterChange}
        onReset={handleReset}
      />
    );

    fireEvent.click(screen.getByTestId('filter-reset-btn'));
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});

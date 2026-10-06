import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { DashboardCharts } from './DashboardCharts';
import type { DashboardMetricsResponse } from '../../api/dashboard';

afterEach(() => {
  cleanup();
});

vi.mock('recharts', async (importOriginal) => {
  const original = await importOriginal<typeof import('recharts')>();
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="mock-responsive-container">{children}</div>
    ),
  };
});

describe('DashboardCharts', () => {
  const mockData: DashboardMetricsResponse = {
    period: { from: '2026-09-01', to: '2026-09-30' },
    manpower: { total_distinct_employees: 3 },
    working_hours: { total_hours: 80.0, average_per_employee: 26.7 },
    site_progress: [
      {
        site_id: 's-1',
        site_name: 'Metro Line',
        total_quantity: 450.0,
        category_breakdown: { cable: 400.0, device: 50.0 },
      },
    ],
    cable_metres: { total: 400.0 },
    devices_installed: { total: 50.0 },
    employee_productivity: [
      {
        employee_id: 'emp-1',
        employee_name: 'Amit Sharma',
        total_approved_hours: 40.0,
        by_category: [
          {
            category: 'cable',
            uom: 'm',
            total_quantity: 400.0,
            ratio: 10.0,
            ratio_label: '10.00 m/hr',
          },
          {
            category: 'device',
            uom: 'devices',
            total_quantity: 20.0,
            ratio: 0.5,
            ratio_label: '0.50 dev/hr',
          },
        ],
      },
    ],
    material_cost: { total_amount: 15400.0, currency: 'INR' },
    approval_status: {
      attendance: { approved: 10, submitted: 2, draft: 1, rejected: 0, correction_required: 0 },
      work_entries: { approved: 8, submitted: 3, draft: 0, rejected: 1, correction_required: 0 },
      materials: { approved: 5, submitted: 1, draft: 0, rejected: 0, correction_required: 0 },
    },
  };

  it('renders all 3 chart containers', () => {
    render(<DashboardCharts data={mockData} />);

    expect(screen.getByTestId('site-progress-chart')).toBeTruthy();
    expect(screen.getByTestId('employee-productivity-chart')).toBeTruthy();
    expect(screen.getByTestId('approval-status-chart')).toBeTruthy();
  });

  it('renders productivity by_category breakdown without flattening', () => {
    render(<DashboardCharts data={mockData} />);

    // Must show the top employee
    expect(screen.getByText('Amit Sharma')).toBeTruthy();

    // Must render individual category breakdowns with their specific units and labels
    expect(screen.getByText(/cable:/i)).toBeTruthy();
    expect(screen.getByText(/400 m \(10.00 m\/hr\)/i)).toBeTruthy();

    expect(screen.getByText(/device:/i)).toBeTruthy();
    expect(screen.getByText(/20 devices \(0.50 dev\/hr\)/i)).toBeTruthy();
  });

  it('allows filtering productivity view by specific category', () => {
    render(<DashboardCharts data={mockData} />);

    const select = screen.getByTestId('productivity-category-select') as HTMLSelectElement;
    expect(select).toBeTruthy();

    // Verify category options exist
    expect(screen.getByRole('option', { name: /ALL CATEGORIES/i })).toBeTruthy();
    expect(screen.getByRole('option', { name: /CABLE/i })).toBeTruthy();
    expect(screen.getByRole('option', { name: /DEVICE/i })).toBeTruthy();

    fireEvent.change(select, { target: { value: 'cable' } });
    expect(select.value).toBe('cable');
  });

  it('renders loading state when isLoading is true', () => {
    render(<DashboardCharts data={mockData} isLoading={true} />);
    expect(screen.getByTestId('dashboard-charts-loading')).toBeTruthy();
  });
});

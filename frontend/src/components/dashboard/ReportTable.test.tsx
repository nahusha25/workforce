import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { ReportTable } from './ReportTable';

afterEach(() => {
  cleanup();
});

describe('ReportTable', () => {
  it('renders attendance report rows correctly', () => {
    const handlePageChange = vi.fn();
    const rows = [
      {
        attendance_id: 'att-1',
        employee_id: 'emp-1',
        employee_name: 'Rajesh Kumar',
        site_id: 'site-1',
        site_name: 'Metro Site',
        date: '2026-09-25',
        check_in_time: '2026-09-25T09:00:00Z',
        check_out_time: '2026-09-25T17:00:00Z',
        working_hours: 8.0,
        overtime_hours: 1.5,
        status: 'approved',
        is_within_geofence: true,
      },
    ];

    render(
      <ReportTable
        reportType="attendance"
        data={rows}
        total={1}
        page={1}
        pageSize={50}
        onPageChange={handlePageChange}
      />
    );

    expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    expect(screen.getByText('Metro Site')).toBeTruthy();
    expect(screen.getByText('8.00h')).toBeTruthy();
    expect(screen.getByText('1.50h')).toBeTruthy();
    expect(screen.getByText('Inside')).toBeTruthy();
    expect(screen.getByText('approved')).toBeTruthy();
  });

  it('renders materials report rows formatting currency with formatDecimal', () => {
    const rows = [
      {
        transaction_id: 'tx-1',
        employee_id: 'emp-1',
        employee_name: 'Priya Sharma',
        site_id: 'site-1',
        site_name: 'Tower Site',
        item_name: 'Copper Cable 4mm',
        transaction_type: 'purchased',
        quantity: 100,
        amount: 15420.5, // Check 2-decimal format: ₹15420.50
        is_high_value: true,
        status: 'approved',
        created_at: '2026-09-25T10:00:00Z',
      },
    ];

    render(
      <ReportTable
        reportType="materials"
        data={rows}
        total={1}
        page={1}
        pageSize={50}
        onPageChange={vi.fn()}
      />
    );

    expect(screen.getByText('Priya Sharma')).toBeTruthy();
    expect(screen.getByText('Copper Cable 4mm')).toBeTruthy();
    expect(screen.getByText('₹15420.50')).toBeTruthy();
    expect(screen.getByText('High Value')).toBeTruthy();
  });

  it('renders productivity report with un-flattened by_category breakdown', () => {
    const rows = [
      {
        employee_id: 'emp-1',
        employee_name: 'Amit Patel',
        total_approved_hours: 40.0,
        by_category: [
          {
            category: 'cable',
            uom: 'm',
            total_quantity: 600,
            ratio: 15.0,
            ratio_label: '15.00 m/hr',
          },
          {
            category: 'device',
            uom: 'devices',
            total_quantity: 12,
            ratio: 0.3,
            ratio_label: '0.30 dev/hr',
          },
        ],
      },
    ];

    render(
      <ReportTable
        reportType="productivity"
        data={rows}
        total={1}
        page={1}
        pageSize={50}
        onPageChange={vi.fn()}
      />
    );

    expect(screen.getByText('Amit Patel')).toBeTruthy();
    expect(screen.getByText('40.00 hrs')).toBeTruthy();

    // Verify both categories appear with separate UOM and ratio labels
    expect(screen.getByTestId('cat-tag-cable')).toBeTruthy();
    expect(screen.getByText(/600 m \(15.00 m\/hr\)/i)).toBeTruthy();

    expect(screen.getByTestId('cat-tag-device')).toBeTruthy();
    expect(screen.getByText(/12 devices \(0.30 dev\/hr\)/i)).toBeTruthy();
  });

  it('renders payment summary report with disclaimer banner and formatDecimal amounts', () => {
    const rows = [
      {
        employee_id: 'emp-1',
        employee_name: 'Ravi Kumar',
        rate_type: 'daily',
        rate_effective_from: '2026-09-01',
        rate_effective_to: '2026-09-15',
        approved_days: 10,
        approved_quantity: 0,
        effective_rate: 650.0,
        estimated_gross: 6500.0,
      },
    ];

    render(
      <ReportTable
        reportType="payment-summary"
        data={rows}
        total={1}
        page={1}
        pageSize={50}
        onPageChange={vi.fn()}
      />
    );

    expect(screen.getByTestId('payment-disclaimer-banner')).toBeTruthy();
    expect(screen.getByText(/Preview Only:/i)).toBeTruthy();
    expect(screen.getByText('₹650.00')).toBeTruthy();
    expect(screen.getByText('₹6500.00')).toBeTruthy();
  });

  it('handles empty state and pagination navigation', () => {
    const handlePageChange = vi.fn();
    const { rerender } = render(
      <ReportTable
        reportType="attendance"
        data={[]}
        total={0}
        page={1}
        pageSize={50}
        onPageChange={handlePageChange}
      />
    );

    expect(screen.getByTestId('report-table-empty')).toBeTruthy();

    // With pagination
    rerender(
      <ReportTable
        reportType="attendance"
        data={[{ attendance_id: '1', employee_name: 'A', site_name: 'S', date: '2026-09-01', check_in_time: null, check_out_time: null, working_hours: null, overtime_hours: null, status: 'approved', is_within_geofence: null }]}
        total={100}
        page={1}
        pageSize={50}
        onPageChange={handlePageChange}
      />
    );

    const nextBtn = screen.getByTestId('next-page-btn') as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(false);
    fireEvent.click(nextBtn);
    expect(handlePageChange).toHaveBeenCalledWith(2);
  });
});

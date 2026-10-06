import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ExportButtonGroup } from './ExportButtonGroup';
import * as dashboardApi from '../../api/dashboard';

vi.mock('../../api/dashboard', () => ({
  downloadReportExport: vi.fn(),
}));

afterEach(() => {
  cleanup();
});

describe('ExportButtonGroup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('triggers downloadReportExport with exact active filters on Excel click', async () => {
    vi.mocked(dashboardApi.downloadReportExport).mockResolvedValue(undefined);

    const activeFilters = {
      date_from: '2026-08-01',
      date_to: '2026-08-31',
      site_id: 'site-xyz',
      is_high_value: true,
    };

    render(<ExportButtonGroup reportType="materials" filters={activeFilters} />);

    const excelBtn = screen.getByTestId('export-excel-btn');
    fireEvent.click(excelBtn);

    await waitFor(() => {
      expect(dashboardApi.downloadReportExport).toHaveBeenCalledWith(
        'materials',
        'xlsx',
        activeFilters
      );
    });
  });

  it('triggers downloadReportExport with exact active filters on PDF click', async () => {
    vi.mocked(dashboardApi.downloadReportExport).mockResolvedValue(undefined);

    const activeFilters = {
      date_from: '2026-09-01',
      date_to: '2026-09-30',
      client_id: 'client-abc',
      status: 'approved',
    };

    render(<ExportButtonGroup reportType="attendance" filters={activeFilters} />);

    const pdfBtn = screen.getByTestId('export-pdf-btn');
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(dashboardApi.downloadReportExport).toHaveBeenCalledWith(
        'attendance',
        'pdf',
        activeFilters
      );
    });
  });

  it('shows error banner when export download fails', async () => {
    vi.mocked(dashboardApi.downloadReportExport).mockRejectedValue(
      new Error('Network export error')
    );

    render(
      <ExportButtonGroup
        reportType="work"
        filters={{ date_from: '2026-09-01', date_to: '2026-09-10' }}
      />
    );

    fireEvent.click(screen.getByTestId('export-excel-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('export-error-alert')).toBeTruthy();
      expect(screen.getByText(/Network export error/i)).toBeTruthy();
    });
  });
});

import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useReportData,
  type ReportType,
  type ReportQueryParams,
} from '../api/dashboard';
import { FilterBar, getDefaultFilterDates } from '../components/dashboard/FilterBar';
import { ReportTable } from '../components/dashboard/ReportTable';
import { ExportButtonGroup } from '../components/dashboard/ExportButtonGroup';
import styles from './ReportPage.module.css';

const VALID_REPORT_TYPES: Record<
  ReportType,
  { title: string; subtitle: string }
> = {
  attendance: {
    title: 'Attendance History Report',
    subtitle: 'Verified daily employee attendance, working hours, and check-in geolocation',
  },
  work: {
    title: 'Daily Work Progress Report',
    subtitle: 'Detailed task output, quantities, and activity tracking across sites',
  },
  materials: {
    title: 'Material Transactions Report',
    subtitle: 'Purchased and consumed material audit log with high-value tracking',
  },
  productivity: {
    title: 'Employee Productivity Report',
    subtitle: 'Output-per-hour metrics broken down strictly by activity category',
  },
  'payment-summary': {
    title: 'Estimated Payment Summary',
    subtitle: 'Read-only preview using effective-dated rates from employee rate history',
  },
  'invoice-summary': {
    title: 'Client & Site Invoice Summary',
    subtitle: 'Aggregated labour days, total quantities, and material expenses for billing',
  },
};

export const ReportPage: React.FC = () => {
  const { type } = useParams<{ type: string }>();
  const navigate = useNavigate();

  // Validate report type or fallback to attendance
  const activeReportType: ReportType = useMemo(() => {
    if (type && type in VALID_REPORT_TYPES) {
      return type as ReportType;
    }
    return 'attendance';
  }, [type]);

  // Shared filters state
  const [filters, setFilters] = useState<ReportQueryParams>(() => ({
    ...getDefaultFilterDates(),
    client_id: null,
    site_id: null,
    employee_id: null,
    supervisor_id: null,
    page: 1,
    page_size: 50,
    status: activeReportType === 'attendance' ? 'approved' : null,
    transaction_type: null,
    is_high_value: null,
    sort_category: null,
  }));

  // Reset page to 1 when report type changes
  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      status: activeReportType === 'attendance' ? 'approved' : null,
      transaction_type: null,
      is_high_value: null,
      sort_category: null,
    }));
  }, [activeReportType]);

  const { data, isLoading, isError, error, refetch } = useReportData(
    activeReportType,
    filters
  );

  const handleFilterChange = (partial: Partial<ReportQueryParams>) => {
    setFilters((prev) => ({ ...prev, ...partial, page: 1 }));
  };

  const handleReset = () => {
    setFilters({
      ...getDefaultFilterDates(),
      client_id: null,
      site_id: null,
      employee_id: null,
      supervisor_id: null,
      page: 1,
      page_size: 50,
      status: activeReportType === 'attendance' ? 'approved' : null,
      transaction_type: null,
      is_high_value: null,
      sort_category: null,
    });
  };

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  const handlePageSizeChange = (newSize: number) => {
    setFilters((prev) => ({ ...prev, page_size: newSize, page: 1 }));
  };

  const meta = VALID_REPORT_TYPES[activeReportType];

  return (
    <div className={styles.pageContainer} data-testid="report-page">
      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>{meta.title}</h1>
          <p className={styles.subtitle}>{meta.subtitle}</p>
        </div>

        {/* Export Buttons: Reuses the EXACT active filters applied on screen */}
        <ExportButtonGroup
          reportType={activeReportType}
          filters={filters}
          disabled={isLoading}
        />
      </div>

      {/* Tabs navigation for 6 report types */}
      <div className={styles.tabsContainer} role="tablist">
        {(Object.keys(VALID_REPORT_TYPES) as ReportType[]).map((tabKey) => (
          <button
            key={tabKey}
            type="button"
            role="tab"
            aria-selected={activeReportType === tabKey}
            className={`${styles.tabBtn} ${
              activeReportType === tabKey ? styles.activeTab : ''
            }`}
            onClick={() => navigate(`/reports/${tabKey}`)}
            data-testid={`tab-${tabKey}`}
          >
            {VALID_REPORT_TYPES[tabKey].title.replace(' Report', '')}
          </button>
        ))}
      </div>

      {/* Filter Bar with report-specific extra controls */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleReset}
        isLoading={isLoading}
      >
        {/* Report-specific filters */}
        {activeReportType === 'attendance' && (
          <div className={styles.customFilterGroup}>
            <label htmlFor="filter-status">Status:</label>
            <select
              id="filter-status"
              className={styles.customSelect}
              value={filters.status || ''}
              onChange={(e) => handleFilterChange({ status: e.target.value || null })}
              data-testid="filter-attendance-status"
            >
              <option value="">All Statuses</option>
              <option value="approved">Approved</option>
              <option value="submitted">Submitted</option>
              <option value="draft">Draft</option>
              <option value="rejected">Rejected</option>
              <option value="correction_required">Correction Required</option>
            </select>
          </div>
        )}

        {activeReportType === 'materials' && (
          <>
            <div className={styles.customFilterGroup}>
              <label htmlFor="filter-tx-type">Transaction:</label>
              <select
                id="filter-tx-type"
                className={styles.customSelect}
                value={filters.transaction_type || ''}
                onChange={(e) => handleFilterChange({ transaction_type: e.target.value || null })}
                data-testid="filter-materials-tx-type"
              >
                <option value="">All Types</option>
                <option value="purchased">Purchased</option>
                <option value="consumed">Consumed</option>
              </select>
            </div>

            <div className={styles.customFilterGroup}>
              <label htmlFor="filter-high-value">
                <input
                  id="filter-high-value"
                  type="checkbox"
                  checked={Boolean(filters.is_high_value)}
                  onChange={(e) => handleFilterChange({ is_high_value: e.target.checked ? true : null })}
                  data-testid="filter-materials-high-value"
                />{' '}
                High Value Only
              </label>
            </div>
          </>
        )}

        {activeReportType === 'productivity' && (
          <div className={styles.customFilterGroup}>
            <label htmlFor="filter-sort-category">Sort Category:</label>
            <select
              id="filter-sort-category"
              className={styles.customSelect}
              value={filters.sort_category || ''}
              onChange={(e) => handleFilterChange({ sort_category: e.target.value || null })}
              data-testid="filter-productivity-sort-category"
            >
              <option value="">Default (Approved Hours)</option>
              <option value="cable">Cable Ratio</option>
              <option value="device">Device Ratio</option>
              <option value="drilling">Drilling Ratio</option>
              <option value="mounting">Mounting Ratio</option>
              <option value="testing">Testing Ratio</option>
              <option value="commissioning">Commissioning Ratio</option>
            </select>
          </div>
        )}
      </FilterBar>

      {/* Error state */}
      {isError && (
        <div className={styles.errorBanner} role="alert" data-testid="report-error-banner">
          <div>
            <strong>Failed to fetch report data:</strong>{' '}
            {error?.message || 'Please check your connection and try again.'}
          </div>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* Report Table */}
      <ReportTable
        reportType={activeReportType}
        data={data?.data || []}
        total={data?.total || 0}
        page={filters.page || 1}
        pageSize={filters.page_size || 50}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        isLoading={isLoading}
      />
    </div>
  );
};

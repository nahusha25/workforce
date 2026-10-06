import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Users,
  Clock,
  Layers,
  Cpu,
  IndianRupee,
  CheckCircle,
  FileText,
  Activity,
  ArrowRight,
} from 'lucide-react';
import {
  useDashboardMetrics,
  type DashboardFilters,
} from '../api/dashboard';
import { formatDecimal } from '../components/MaterialTransactionEntry';
import { MetricCard } from '../components/dashboard/MetricCard';
import { FilterBar, getDefaultFilterDates } from '../components/dashboard/FilterBar';
import { DashboardCharts } from '../components/dashboard/DashboardCharts';
import styles from './DirectorDashboardPage.module.css';

export const DirectorDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<DashboardFilters>(() => ({
    ...getDefaultFilterDates(),
    client_id: null,
    site_id: null,
    employee_id: null,
    supervisor_id: null,
  }));

  const { data, isLoading, isError, error, refetch } = useDashboardMetrics(filters);

  const handleFilterChange = (partial: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  };

  const handleResetFilters = () => {
    setFilters({
      ...getDefaultFilterDates(),
      client_id: null,
      site_id: null,
      employee_id: null,
      supervisor_id: null,
    });
  };

  const attendanceApproved = data?.approval_status?.attendance?.approved ?? 0;
  const workApproved = data?.approval_status?.work_entries?.approved ?? 0;
  const materialsApproved = data?.approval_status?.materials?.approved ?? 0;

  return (
    <div className={styles.pageContainer} data-testid="director-dashboard-page">
      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Director Operations Dashboard</h1>
          <p className={styles.subtitle}>
            Aggregated operational progress, verified attendance, and resource metrics
          </p>
        </div>
      </div>

      {/* Global Filter Bar */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        isLoading={isLoading}
      />

      {/* Error Banner */}
      {isError && (
        <div className={styles.errorBanner} role="alert" data-testid="dashboard-error-banner">
          <div>
            <strong>Failed to load dashboard metrics:</strong>{' '}
            {error?.message || 'Please check your connection and try again.'}
          </div>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* 8 Aggregated Metric Cards */}
      <div className={styles.metricsGrid} data-testid="metrics-grid">
        {/* 1. Manpower */}
        <MetricCard
          title="Active Workforce"
          value={data ? `${data.manpower.total_distinct_employees}` : null}
          subtitle="Distinct active employees"
          icon={<Users size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/attendance')}
          testId="metric-card-manpower"
        />

        {/* 2. Total Working Hours */}
        <MetricCard
          title="Approved Hours"
          value={data ? `${Number(data.working_hours.total_hours).toFixed(1)}h` : null}
          subtitle={
            data?.working_hours.average_per_employee !== null && data?.working_hours.average_per_employee !== undefined
              ? `Avg ${Number(data.working_hours.average_per_employee).toFixed(1)}h / employee`
              : 'Verified hours'
          }
          icon={<Clock size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/attendance')}
          testId="metric-card-hours"
        />

        {/* 3. Cable Metres Installed */}
        <MetricCard
          title="Cable Installed"
          value={data ? `${Number(data.cable_metres.total).toFixed(1)} m` : null}
          subtitle="Total cable runs completed"
          icon={<Layers size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/work')}
          testId="metric-card-cable"
        />

        {/* 4. Devices Installed */}
        <MetricCard
          title="Devices Installed"
          value={data ? `${Number(data.devices_installed.total)} units` : null}
          subtitle="Verified device installations"
          icon={<Cpu size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/work')}
          testId="metric-card-devices"
        />

        {/* 5. Material Cost (using formatDecimal) */}
        <MetricCard
          title="Material Spend"
          value={data ? `₹${formatDecimal(data.material_cost.total_amount)}` : null}
          subtitle="Approved material transactions"
          icon={<IndianRupee size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/materials')}
          testId="metric-card-materials-cost"
        />

        {/* 6. Approved Attendance */}
        <MetricCard
          title="Approved Attendance"
          value={data ? `${attendanceApproved}` : null}
          subtitle={`Pending: ${data?.approval_status?.attendance?.submitted ?? 0}`}
          icon={<CheckCircle size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/attendance')}
          testId="metric-card-attendance-approved"
        />

        {/* 7. Approved Work Entries */}
        <MetricCard
          title="Approved Work Entries"
          value={data ? `${workApproved}` : null}
          subtitle={`Pending: ${data?.approval_status?.work_entries?.submitted ?? 0}`}
          icon={<Activity size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/work')}
          testId="metric-card-work-approved"
        />

        {/* 8. Approved Materials */}
        <MetricCard
          title="Approved Materials"
          value={data ? `${materialsApproved}` : null}
          subtitle={`Pending: ${data?.approval_status?.materials?.submitted ?? 0}`}
          icon={<FileText size={20} />}
          isLoading={isLoading}
          isError={isError}
          onClick={() => navigate('/reports/materials')}
          testId="metric-card-materials-approved"
        />
      </div>

      {/* Quick Navigation to Reports */}
      <div className={styles.sectionTitle}>Detailed Reports & Previews</div>
      <div className={styles.reportsQuickNav}>
        <Link to="/reports/attendance" className={styles.quickNavBtn}>
          <span>Attendance History</span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/reports/work" className={styles.quickNavBtn}>
          <span>Work Progress</span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/reports/materials" className={styles.quickNavBtn}>
          <span>Material Transactions</span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/reports/productivity" className={styles.quickNavBtn}>
          <span>Productivity Breakdown</span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/reports/payment-summary" className={styles.quickNavBtn}>
          <span>Payment Summary (Preview)</span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/reports/invoice-summary" className={styles.quickNavBtn}>
          <span>Invoice Summary</span>
          <ArrowRight size={16} />
        </Link>
      </div>

      {/* Recharts Analytics Charts */}
      {data && <DashboardCharts data={data} isLoading={isLoading} />}
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  generateEmployeePaymentsApi,
  listEmployeePaymentsApi,
  previewEmployeePaymentsApi,
  type EmployeePaymentPreviewResponse,
  type EmployeePaymentResponse,
} from '../api/employeePayments';
import {
  getEffectiveOvertimeSettingApi,
  getOvertimeSettingsHistoryApi,
  type PayrollOvertimeSettingsResponse,
} from '../api/payrollSettings';
import { getAllEmployeesApi, type EmployeeResponseData } from '../api/employee';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { getLocalISODate } from '../utils/date';
import styles from './EmployeePaymentsPage.module.css';

export const formatCurrency = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || isNaN(Number(amount))) return '₹0.00';
  return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export function getOverlappingOvertimePolicies(
  policies: PayrollOvertimeSettingsResponse[],
  periodStart: string,
  periodEnd: string
): PayrollOvertimeSettingsResponse[] {
  if (!policies || policies.length === 0) return [];

  const overlapping = policies.filter((p) => {
    const startsBeforePeriodEnd = !p.effective_from || p.effective_from <= periodEnd;
    const endsAfterPeriodStart = !p.effective_to || p.effective_to >= periodStart;
    return startsBeforePeriodEnd && endsAfterPeriodStart;
  });

  return overlapping.sort((a, b) => (a.effective_from || '').localeCompare(b.effective_from || ''));
}

const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export const EmployeePaymentsPage: React.FC = () => {
  const { role } = useAuth();
  const isDirectorOrAdmin = role === 'director' || role === 'administrator';

  // Data states
  const [payments, setPayments] = useState<EmployeePaymentResponse[]>([]);
  const [employees, setEmployees] = useState<EmployeeResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Filter states
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');
  const [filterEmployeeId, setFilterEmployeeId] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Applied filter params (so table only updates when user submits or resets)
  const [appliedFilters, setAppliedFilters] = useState<{
    startDate: string;
    endDate: string;
    employeeId: string;
    status: string;
  }>({
    startDate: '',
    endDate: '',
    employeeId: '',
    status: '',
  });

  // Generate Modal states
  const [showGenerateModal, setShowGenerateModal] = useState<boolean>(false);
  const [genPeriodStart, setGenPeriodStart] = useState<string>(() => {
    const d = new Date();
    return getLocalISODate(new Date(d.getFullYear(), d.getMonth(), 1));
  });
  const [genPeriodEnd, setGenPeriodEnd] = useState<string>(() => getLocalISODate(new Date()));
  const [genEmployeeId, setGenEmployeeId] = useState<string>('');

  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<EmployeePaymentPreviewResponse | null>(null);
  const [previewSetting, setPreviewSetting] = useState<PayrollOvertimeSettingsResponse | null>(null);
  const [overlappingPolicies, setOverlappingPolicies] = useState<PayrollOvertimeSettingsResponse[]>([]);

  const [generating, setGenerating] = useState<boolean>(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Fetch employees once for filter & modal dropdowns
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const empList = await getAllEmployeesApi();
        setEmployees(empList);
      } catch (err) {
        console.error('Failed to load employee directory for payments:', err);
      }
    };
    fetchEmployees();
  }, []);

  // Fetch payments based on applied filters
  const fetchPayments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listEmployeePaymentsApi({
        period_start: appliedFilters.startDate || undefined,
        period_end: appliedFilters.endDate || undefined,
        employee_id: appliedFilters.employeeId || undefined,
        status: appliedFilters.status || undefined,
      });
      setPayments(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load employee payments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [appliedFilters]);

  // Apply filters handler
  const handleApplyFilters = () => {
    setAppliedFilters({
      startDate: filterStartDate,
      endDate: filterEndDate,
      employeeId: filterEmployeeId,
      status: filterStatus,
    });
  };

  // Reset filters handler
  const handleResetFilters = () => {
    setFilterStartDate('');
    setFilterEndDate('');
    setFilterEmployeeId('');
    setFilterStatus('');
    setAppliedFilters({
      startDate: '',
      endDate: '',
      employeeId: '',
      status: '',
    });
  };

  // Open modal handler
  const handleOpenGenerateModal = () => {
    const now = new Date();
    const defaultStart = new Date(now.getFullYear(), now.getMonth(), 1);
    setGenPeriodStart(getLocalISODate(defaultStart));
    setGenPeriodEnd(getLocalISODate(now));
    setGenEmployeeId('');
    setPreviewData(null);
    setPreviewSetting(null);
    setOverlappingPolicies([]);
    setPreviewError(null);
    setGenerateError(null);
    setShowGenerateModal(true);
  };

  // Step 1: Preview Payments handler
  const handlePreview = async () => {
    if (!genPeriodStart || !genPeriodEnd) {
      setPreviewError('Period Start and Period End dates are required.');
      return;
    }
    if (genPeriodEnd < genPeriodStart) {
      setPreviewError('Period End must be greater than or equal to Period Start.');
      return;
    }

    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);
    setPreviewSetting(null);
    setOverlappingPolicies([]);
    setGenerateError(null);

    try {
      const [res, historyData] = await Promise.all([
        previewEmployeePaymentsApi({
          period_start: genPeriodStart,
          period_end: genPeriodEnd,
          employee_id: genEmployeeId || undefined,
        }),
        getOvertimeSettingsHistoryApi().catch(() => [] as PayrollOvertimeSettingsResponse[]),
      ]);

      let history = historyData;
      if (!history || history.length === 0) {
        try {
          const single = await getEffectiveOvertimeSettingApi(genPeriodStart);
          if (single) {
            history = [single];
          }
        } catch {
          // ignore fallback error
        }
      }

      const overlapping = getOverlappingOvertimePolicies(history, genPeriodStart, genPeriodEnd);

      setPreviewData(res);
      setOverlappingPolicies(overlapping);
      setPreviewSetting(overlapping[0] || null);
    } catch (err: any) {
      setPreviewError(err?.response?.data?.detail || err?.message || 'Failed to preview employee payments');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Step 2: Confirm Generation handler
  const handleGenerate = async () => {
    if (!previewData || previewData.items.length === 0) return;
    setGenerating(true);
    setGenerateError(null);

    const idempotencyKey = generateUUID();

    try {
      const createdPayments = await generateEmployeePaymentsApi({
        period_start: genPeriodStart,
        period_end: genPeriodEnd,
        idempotency_key: idempotencyKey,
        employee_id: genEmployeeId || undefined,
      });

      setShowGenerateModal(false);
      setSuccessBanner(`Successfully generated ${createdPayments.length} employee payment draft(s).`);
      await fetchPayments();
    } catch (err: any) {
      setGenerateError(err?.response?.data?.detail || err?.message || 'Failed to generate employee payments');
    } finally {
      setGenerating(false);
    }
  };

  // KPI Calculations
  const totalCount = payments.length;
  const totalSum = payments.reduce((acc, p) => acc + (Number(p.total_amount) || 0), 0);

  const draftPayments = payments.filter((p) => p.status === 'draft');
  const draftCount = draftPayments.length;
  const draftSum = draftPayments.reduce((acc, p) => acc + (Number(p.total_amount) || 0), 0);

  const approvedPayments = payments.filter((p) => p.status === 'approved');
  const approvedCount = approvedPayments.length;
  const approvedSum = approvedPayments.reduce((acc, p) => acc + (Number(p.total_amount) || 0), 0);

  const paidPayments = payments.filter((p) => p.status === 'paid');
  const paidCount = paidPayments.length;
  const paidSum = paidPayments.reduce((acc, p) => acc + (Number(p.total_amount) || 0), 0);

  const cancelledPayments = payments.filter((p) => p.status === 'cancelled');
  const cancelledCount = cancelledPayments.length;
  const cancelledSum = cancelledPayments.reduce((acc, p) => acc + (Number(p.total_amount) || 0), 0);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Employee Payments</h2>
          <p>Generate, review, and manage workforce payments backed by verified attendance and work records.</p>
        </div>
        {isDirectorOrAdmin && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Button variant="primary" onClick={handleOpenGenerateModal}>
              + Generate Payments
            </Button>
          </div>
        )}
      </div>

      {/* Success Notification */}
      {successBanner && (
        <div className={styles.successMessage} role="status">
          {successBanner}
        </div>
      )}

      {/* Error message */}
      {error && <ErrorMessage message={error} />}

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard} data-testid="kpi-total">
          <span className={styles.kpiTitle}>Total Payments</span>
          <div className={styles.kpiValueRow}>
            <span className={styles.kpiCount}>{totalCount}</span>
            <span className={styles.kpiAmount}>{formatCurrency(totalSum)}</span>
          </div>
        </div>

        <div className={styles.kpiCard} data-testid="kpi-draft">
          <span className={styles.kpiTitle}>Draft</span>
          <div className={styles.kpiValueRow}>
            <span className={styles.kpiCount}>{draftCount}</span>
            <span className={styles.kpiAmount}>{formatCurrency(draftSum)}</span>
          </div>
        </div>

        <div className={styles.kpiCard} data-testid="kpi-approved">
          <span className={styles.kpiTitle}>Approved</span>
          <div className={styles.kpiValueRow}>
            <span className={styles.kpiCount}>{approvedCount}</span>
            <span className={styles.kpiAmount}>{formatCurrency(approvedSum)}</span>
          </div>
        </div>

        <div className={styles.kpiCard} data-testid="kpi-paid">
          <span className={styles.kpiTitle}>Paid</span>
          <div className={styles.kpiValueRow}>
            <span className={styles.kpiCount}>{paidCount}</span>
            <span className={styles.kpiAmount}>{formatCurrency(paidSum)}</span>
          </div>
        </div>

        <div className={styles.kpiCard} data-testid="kpi-cancelled">
          <span className={styles.kpiTitle}>Cancelled</span>
          <div className={styles.kpiValueRow}>
            <span className={styles.kpiCount}>{cancelledCount}</span>
            <span className={styles.kpiAmount}>{formatCurrency(cancelledSum)}</span>
          </div>
        </div>
      </div>

      {/* Filter Card */}
      <Card className={styles.filterCard}>
        <div className={styles.filterGrid}>
          <Input
            label="Period Start"
            type="date"
            value={filterStartDate}
            onChange={(e) => setFilterStartDate(e.target.value)}
          />

          <Input
            label="Period End"
            type="date"
            value={filterEndDate}
            onChange={(e) => setFilterEndDate(e.target.value)}
          />

          <Select
            label="Employee"
            value={filterEmployeeId}
            onChange={(e) => setFilterEmployeeId(e.target.value)}
            options={[
              { value: '', label: 'All Employees' },
              ...employees.map((emp) => ({
                value: emp.id,
                label: `${emp.name} (${emp.employee_code})`,
              })),
            ]}
          />

          <Select
            label="Status"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            options={[
              { value: '', label: 'All Statuses' },
              { value: 'draft', label: 'Draft' },
              { value: 'approved', label: 'Approved' },
              { value: 'paid', label: 'Paid' },
              { value: 'cancelled', label: 'Cancelled' },
            ]}
          />

          <div className={styles.filterActions}>
            <Button variant="primary" onClick={handleApplyFilters}>
              Filter
            </Button>
            <Button variant="outline" onClick={handleResetFilters}>
              Reset
            </Button>
          </div>
        </div>
      </Card>

      {/* Main Payments Table */}
      {loading ? (
        <LoadingSpinner />
      ) : payments.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No employee payment records found for the selected filters.</p>
          </div>
        </Card>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Payment #</th>
                <th>Employee</th>
                <th>Pay Period</th>
                <th>Days</th>
                <th>Quantity</th>
                <th>Total Amount</th>
                <th>Status</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/employee-payments/${p.id}`} className={styles.paymentNumberLink}>
                      {p.payment_number}
                    </Link>
                  </td>
                  <td>{p.employee_name || '—'}</td>
                  <td>
                    {p.period_start} to {p.period_end}
                  </td>
                  <td>{p.total_days}</td>
                  <td>{p.total_quantity}</td>
                  <td style={{ fontWeight: 600 }}>{formatCurrency(p.total_amount)}</td>
                  <td>
                    <StatusBadge status={p.status} label={p.status.toUpperCase()} />
                  </td>
                  <td>{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Two-Step Generate Payments Modal */}
      {showGenerateModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3 id="modal-title">Generate Employee Payments</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowGenerateModal(false)}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            {previewError && <ErrorMessage message={previewError} />}
            {generateError && <ErrorMessage message={generateError} />}

            {/* Step 1: Configuration & Preview */}
            <div className={styles.stepSection}>
              <div className={styles.stepHeader}>
                <span className={styles.stepBadge}>1</span>
                <div>
                  <span>Select Pay Period & Scope</span>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.8125rem', color: 'var(--color-neutral-600)', fontWeight: 400 }}>
                    Monthly salary is paid on the 1st of every month for actual days worked: (Monthly Salary ÷ 30) × Actual Days Worked.
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                <Input
                  label="Period Start *"
                  type="date"
                  value={genPeriodStart}
                  onChange={(e) => {
                    setGenPeriodStart(e.target.value);
                    setPreviewData(null);
                    setOverlappingPolicies([]);
                  }}
                />

                <Input
                  label="Period End *"
                  type="date"
                  value={genPeriodEnd}
                  onChange={(e) => {
                    setGenPeriodEnd(e.target.value);
                    setPreviewData(null);
                    setOverlappingPolicies([]);
                  }}
                />

                <Select
                  label="Employee (Optional)"
                  value={genEmployeeId}
                  onChange={(e) => {
                    setGenEmployeeId(e.target.value);
                    setPreviewData(null);
                  }}
                  options={[
                    { value: '', label: 'All Eligible Employees' },
                    ...employees.map((emp) => ({
                      value: emp.id,
                      label: `${emp.name} (${emp.employee_code})`,
                    })),
                  ]}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: '8px' }}>
                <Button
                  variant="secondary"
                  onClick={handlePreview}
                  disabled={previewLoading || !genPeriodStart || !genPeriodEnd}
                >
                  {previewLoading ? 'Inspecting Records...' : 'Preview Eligible Payments'}
                </Button>
              </div>
            </div>

            {/* Preview Results Display */}
            {previewData && (
              <div className={styles.stepSection}>
                <div className={styles.stepHeader}>
                  <span className={styles.stepBadge}>2</span>
                  <span>Review Preview & Confirm Generation</span>
                </div>

                <div className={styles.previewSummaryCard}>
                  <div className={styles.previewMetrics}>
                    <div className={styles.metricItem}>
                      <span className={styles.metricLabel}>Eligible Employees</span>
                      <span className={styles.metricVal}>{previewData.total_employees}</span>
                    </div>
                    <div className={styles.metricItem}>
                      <span className={styles.metricLabel}>Regular Pay Total</span>
                      <span className={styles.metricVal} data-testid="preview-regular-total">
                        {formatCurrency(previewData.grand_total_regular_amount ?? 0)}
                      </span>
                    </div>
                    <div className={styles.metricItem}>
                      <span className={styles.metricLabel}>Overtime Total</span>
                      <span className={styles.metricVal} data-testid="preview-overtime-total">
                        {formatCurrency(previewData.grand_total_overtime_amount ?? 0)}
                        <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '4px', color: 'var(--color-neutral-600)' }}>
                          ({Number(previewData.grand_total_overtime_hours ?? 0).toFixed(2)} hrs)
                        </span>
                      </span>
                    </div>
                    <div className={styles.metricItem}>
                      <span className={styles.metricLabel}>Grand Total Amount</span>
                      <span className={styles.metricVal} data-testid="preview-grand-total" style={{ color: 'var(--color-primary-700, #1d4ed8)' }}>
                        {formatCurrency(previewData.grand_total_amount)}
                      </span>
                    </div>
                  </div>

                  {overlappingPolicies.length > 1 ? (
                    <div
                      data-testid="multiple-overtime-policies-banner"
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        background: '#f8fafc',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.8125rem',
                        color: 'var(--color-neutral-700)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                        <div>
                          <strong style={{ color: 'var(--color-neutral-900, #0f172a)' }}>Multiple Overtime Policies Applicable: </strong>
                          <span>This pay period spans multiple overtime policies. Each attendance date uses its effective policy:</span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>
                          Monthly basis: 30-day pro-rated • 8.00 hrs/day std • 1.00x OT • Piece-rate: OT excluded
                        </span>
                      </div>
                      <ul
                        data-testid="multiple-overtime-policies-list"
                        style={{ margin: '4px 0 0 0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}
                      >
                        {overlappingPolicies.map((p) => {
                          const range = `${p.effective_from} to ${p.effective_to || 'Present'}`;
                          const stdHours = Number(p.standard_workday_hours).toFixed(2);
                          const mult = Number(p.overtime_multiplier).toFixed(2);
                          return (
                            <li key={p.id} data-testid={`overtime-policy-range-${p.id}`} style={{ lineHeight: '1.4' }}>
                              <strong>{range}:</strong> {stdHours} hrs/day standard workday @ {mult}x multiplier
                              {p.description ? (
                                <span style={{ color: 'var(--color-neutral-500)', marginLeft: '6px' }}>({p.description})</span>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ) : (
                    <div
                      data-testid="single-overtime-policy-banner"
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: '#f8fafc',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.8125rem',
                        color: 'var(--color-neutral-700)',
                        flexWrap: 'wrap',
                        gap: '8px',
                      }}
                    >
                      <div>
                        <strong>Applicable Overtime Policy: </strong>
                        {overlappingPolicies.length === 1 ? (
                          <span>
                            {Number(overlappingPolicies[0].standard_workday_hours).toFixed(2)} hrs/day standard workday @ {Number(overlappingPolicies[0].overtime_multiplier).toFixed(2)}x multiplier
                          </span>
                        ) : previewSetting ? (
                          <span>
                            {Number(previewSetting.standard_workday_hours).toFixed(2)} hrs/day standard workday @ {Number(previewSetting.overtime_multiplier).toFixed(2)}x multiplier
                          </span>
                        ) : (
                          <span>8.00 hrs/day standard workday @ 1.00x multiplier (Standard)</span>
                        )}
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>
                        Monthly basis: 30-day pro-rated • 8.00 hrs/day std • 1.00x OT • Piece-rate: OT excluded
                      </span>
                    </div>
                  )}

                  {previewData.items.length === 0 ? (
                    <p style={{ margin: 0, color: 'var(--color-neutral-600, #4b5563)' }}>
                      No unbilled approved records exist for this period.
                    </p>
                  ) : (
                    <>
                      <div className={styles.previewTableWrapper}>
                        <table className={styles.dataTable} data-testid="preview-table">
                          <thead>
                            <tr>
                              <th>Employee</th>
                              <th>Rate Band & Policy Basis</th>
                              <th>Regular Pay</th>
                              <th>Overtime Pay</th>
                              <th>Total Payable</th>
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.items.map((item) => {
                              const stdHours = previewSetting ? Number(previewSetting.standard_workday_hours) : 8.0;
                              const otMult = previewSetting ? Number(previewSetting.overtime_multiplier) : 1.0;
                              const hasAttendance = item.total_days > 0;
                              const isPieceOnly = !hasAttendance && item.total_quantity > 0;
                              const hasOvertime = Number(item.total_overtime_hours ?? 0) > 0;

                              return (
                                <tr key={item.employee_id} data-testid={`preview-row-${item.employee_id}`}>
                                  <td style={{ fontWeight: 600 }}>
                                    <div>{item.employee_name}</div>
                                    <div style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--color-neutral-600)' }}>
                                      {item.total_days} days / {item.total_quantity} qty
                                      <br />
                                      ({item.eligible_attendance_count} att / {item.eligible_work_entry_count} work)
                                    </div>
                                  </td>
                                  <td>
                                    <div className={styles.rateBandList}>
                                      {item.rate_band_summaries.map((rbs, idx) => {
                                        const isDaily = rbs.rate_type === 'daily';
                                        const isWeekly = rbs.rate_type === 'weekly';
                                        const isMonthly = rbs.rate_type === 'monthly';
                                        const isPiece = rbs.rate_type === 'piece';

                                        const equivRate = isDaily
                                          ? Number(rbs.rate_amount) / stdHours
                                          : isWeekly
                                          ? (Number(rbs.rate_amount) / 7) / stdHours
                                          : isMonthly
                                          ? (Number(rbs.rate_amount) / 30) / stdHours
                                          : null;

                                        return (
                                          <div key={idx} className={styles.rateBandPill}>
                                            <span className={styles.rateBandType}>{rbs.rate_type}:</span>
                                            <span>{formatCurrency(rbs.rate_amount)}</span>
                                            {isPiece ? (
                                              <span style={{ color: 'var(--color-neutral-600)' }}>
                                                ({rbs.approved_quantity} units) [No OT]
                                              </span>
                                            ) : (
                                              <span style={{ color: 'var(--color-neutral-600)' }}>
                                                ({rbs.approved_days}d | {stdHours.toFixed(2)}h std | equiv: {formatCurrency(equivRate)}/hr | {otMult.toFixed(2)}x)
                                              </span>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </td>
                                  <td>
                                    <div style={{ fontWeight: 600 }} data-testid={`preview-regular-${item.employee_id}`}>
                                      {formatCurrency(item.total_regular_amount ?? (item.total_amount - (item.total_overtime_amount || 0)))}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)' }}>
                                      {hasAttendance ? (
                                        <span>
                                          {Number(item.total_days * stdHours).toFixed(2)} reg hrs ({stdHours.toFixed(2)}h/day)
                                        </span>
                                      ) : (
                                        <span>{item.total_quantity} units approved</span>
                                      )}
                                    </div>
                                  </td>
                                  <td>
                                    {isPieceOnly ? (
                                      <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }} data-testid={`preview-overtime-${item.employee_id}`}>
                                        — (Piece-rate excluded)
                                      </span>
                                    ) : hasOvertime ? (
                                      <div data-testid={`preview-overtime-${item.employee_id}`}>
                                        <div>
                                          <strong style={{ color: '#b45309' }}>
                                            {Number(item.total_overtime_hours).toFixed(2)} OT hrs
                                          </strong>
                                          <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)', marginLeft: '4px' }}>
                                            @ {otMult.toFixed(2)}x
                                          </span>
                                        </div>
                                        <div style={{ fontWeight: 600, color: '#b45309' }}>
                                          + {formatCurrency(item.total_overtime_amount ?? 0)}
                                        </div>
                                      </div>
                                    ) : (
                                      <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }} data-testid={`preview-overtime-${item.employee_id}`}>
                                        0.00 hrs (₹0.00)
                                      </span>
                                    )}
                                  </td>
                                  <td style={{ fontWeight: 700 }} data-testid={`preview-total-${item.employee_id}`}>
                                    {formatCurrency(item.total_amount)}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      <div style={{ marginTop: '8px', fontSize: '0.875rem', color: 'var(--color-neutral-700)' }}>
                        Generating will lock eligible verified records into draft payment records with a client idempotency key.
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div className={styles.modalFooter}>
              <Button variant="outline" onClick={() => setShowGenerateModal(false)} disabled={generating}>
                Cancel
              </Button>
              {previewData && previewData.items.length > 0 && (
                <Button variant="primary" onClick={handleGenerate} disabled={generating}>
                  {generating ? 'Generating Drafts...' : 'Confirm & Generate Payments'}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

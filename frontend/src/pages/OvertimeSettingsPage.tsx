import React, { useEffect, useState } from 'react';
import {
  createOvertimeSettingApi,
  getEffectiveOvertimeSettingApi,
  getOvertimeSettingsHistoryApi,
  type PayrollOvertimeSettingsResponse,
} from '../api/payrollSettings';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { getLocalISODate } from '../utils/date';
import styles from './OvertimeSettingsPage.module.css';

export const OvertimeSettingsPage: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';

  const [history, setHistory] = useState<PayrollOvertimeSettingsResponse[]>([]);
  const [activeSetting, setActiveSetting] = useState<PayrollOvertimeSettingsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states (Admin create)
  const [standardHours, setStandardHours] = useState<string>('8.00');
  const [multiplier, setMultiplier] = useState<string>('1.00');
  const [effectiveFrom, setEffectiveFrom] = useState<string>(() => getLocalISODate(new Date()));
  const [description, setDescription] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const [historyData, effectiveData] = await Promise.all([
        getOvertimeSettingsHistoryApi(),
        getEffectiveOvertimeSettingApi().catch(() => null),
      ]);
      setHistory(historyData);
      setActiveSetting(effectiveData);
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.response?.data?.detail || err?.message || 'Failed to load overtime settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleCreateSetting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;

    setFormError(null);
    setSuccessMsg(null);

    const parsedHours = parseFloat(standardHours);
    if (isNaN(parsedHours) || parsedHours <= 0 || parsedHours > 24) {
      setFormError('Standard workday hours must be greater than 0 and at most 24.');
      return;
    }

    const parsedMultiplier = parseFloat(multiplier);
    if (isNaN(parsedMultiplier) || parsedMultiplier < 1.0 || parsedMultiplier > 5.0) {
      setFormError('Overtime multiplier must be between 1.00 and 5.00.');
      return;
    }

    if (!effectiveFrom) {
      setFormError('Effective start date is required.');
      return;
    }

    setSubmitting(true);
    try {
      await createOvertimeSettingApi({
        standard_workday_hours: parsedHours,
        overtime_multiplier: parsedMultiplier,
        effective_from: effectiveFrom,
        description: description.trim() || undefined,
      });

      setSuccessMsg(`New overtime setting created successfully, effective from ${effectiveFrom}.`);
      setDescription('');
      await fetchSettings();
    } catch (err: any) {
      const msg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to create overtime setting';
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Payroll Overtime Settings</h2>
          <p>Configure company-wide standard workday thresholds, overtime pay multipliers, and effective-date revisions.</p>
        </div>
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className={styles.alertSuccess} role="status">
          {successMsg}
        </div>
      )}

      {/* Error message */}
      {error && <ErrorMessage message={error} onRetry={fetchSettings} />}

      {/* Active Effective Policy Card */}
      <div className={styles.activePolicyCard} data-testid="active-overtime-policy">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '1.125rem', color: 'var(--color-primary-900, #1e3a8a)' }}>
            Currently Effective Overtime Policy
          </h3>
          <StatusBadge status="active" label="IN EFFECT" />
        </div>

        {activeSetting ? (
          <div className={styles.activePolicyGrid}>
            <div className={styles.activeMetric}>
              <span className={styles.metricLabel}>Standard Workday</span>
              <span className={styles.metricValue}>
                {Number(activeSetting.standard_workday_hours).toFixed(2)} hrs / day
              </span>
            </div>
            <div className={styles.activeMetric}>
              <span className={styles.metricLabel}>Overtime Multiplier</span>
              <span className={styles.metricValue}>
                {Number(activeSetting.overtime_multiplier).toFixed(2)}x
              </span>
            </div>
            <div className={styles.activeMetric}>
              <span className={styles.metricLabel}>Effective Range</span>
              <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-neutral-800)' }}>
                {activeSetting.effective_from} to {activeSetting.effective_to || 'Present'}
              </span>
            </div>
            {activeSetting.description && (
              <div className={styles.activeMetric}>
                <span className={styles.metricLabel}>Policy Description</span>
                <span style={{ fontSize: '0.875rem', color: 'var(--color-neutral-700)' }}>
                  {activeSetting.description}
                </span>
              </div>
            )}
          </div>
        ) : (
          <p style={{ margin: '12px 0 0', color: 'var(--color-neutral-600)' }}>
            No active overtime setting found for the current date.
          </p>
        )}
      </div>

      {/* Create New Configuration (Administrator Only) */}
      {isAdmin ? (
        <Card>
          <h3 style={{ margin: '0 0 16px', fontSize: '1.125rem' }}>Create Effective-Dated Configuration</h3>
          {formError && <ErrorMessage message={formError} />}

          <form data-testid="form-create-overtime-setting" onSubmit={handleCreateSetting} noValidate>
            <div className={styles.formGrid}>
              <Input
                label="Standard Workday Hours *"
                type="number"
                step="0.01"
                min="0.01"
                max="24.00"
                value={standardHours}
                onChange={(e) => setStandardHours(e.target.value)}
                required
                data-testid="input-standard-hours"
              />
              <Input
                label="Overtime Multiplier *"
                type="number"
                step="0.01"
                min="1.00"
                max="5.00"
                value={multiplier}
                onChange={(e) => setMultiplier(e.target.value)}
                required
                data-testid="input-multiplier"
              />
              <Input
                label="Effective Start Date *"
                type="date"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                required
                data-testid="input-effective-from"
              />
              <Input
                label="Description / Policy Justification"
                type="text"
                placeholder="e.g. Standard labor contract 2026"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={255}
                data-testid="input-description"
              />
            </div>

            <div className={styles.formActions}>
              <Button type="submit" variant="primary" disabled={submitting} data-testid="btn-create-overtime-setting">
                {submitting ? 'Saving Configuration...' : 'Create Configuration'}
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <div className={styles.readOnlyBanner} data-testid="director-readonly-banner">
          <span>ℹ️</span>
          <span>
            Directors have view-only permissions for overtime policies. Policy modifications require Administrator privileges.
          </span>
        </div>
      )}

      {/* History Timeline Card */}
      <Card>
        <h3 style={{ margin: '0 0 16px', fontSize: '1.125rem' }}>Configuration History & Timeline</h3>

        {history.length === 0 ? (
          <div className={styles.emptyState}>No overtime settings records found.</div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable} data-testid="overtime-history-table">
              <thead>
                <tr>
                  <th>Effective Range</th>
                  <th>Standard Workday</th>
                  <th>Multiplier</th>
                  <th>Status</th>
                  <th>Description</th>
                  <th>Created On</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => {
                  const today = getLocalISODate(new Date());
                  const isFuture = item.effective_from > today;
                  const isPast = item.effective_to !== null && item.effective_to !== undefined && item.effective_to < today;
                  const isCurrent = !isFuture && !isPast;

                  return (
                    <tr key={item.id} data-testid={`history-row-${item.id}`}>
                      <td style={{ fontWeight: 600 }}>
                        {item.effective_from} to {item.effective_to || 'Present'}
                      </td>
                      <td>{Number(item.standard_workday_hours).toFixed(2)} hrs</td>
                      <td style={{ fontWeight: 600 }}>{Number(item.overtime_multiplier).toFixed(2)}x</td>
                      <td>
                        {isCurrent && <StatusBadge status="active" label="ACTIVE" />}
                        {isFuture && <StatusBadge status="pending" label="SCHEDULED" />}
                        {isPast && <StatusBadge status="inactive" label="HISTORICAL" />}
                      </td>
                      <td>{item.description || '—'}</td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)' }}>
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

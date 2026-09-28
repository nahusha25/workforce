import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getVerificationSummary, type VerificationSummaryItem, type VerificationSummaryResponse } from '../api/verification';
import { getSitesApi, type SiteResponseData } from '../api/masterData';
import { ExceptionBadge, type ExceptionFlagType } from '../components/ui/ExceptionBadge';
import { StatusBadge, mapAttendanceStatusToBadge } from '../components/ui/StatusBadge';
import { formatDecimal } from '../components/MaterialTransactionEntry';
import { getLocalISODate, isValidISODate } from '../utils/date';
import {
  Calendar,
  Building2,
  RefreshCw,
  AlertCircle,
  Clock,
  ChevronRight,
  ShieldAlert,
  Loader2,
  CheckCircle,
} from 'lucide-react';
import styles from './SupervisorVerificationQueuePage.module.css';

// Re-export getLocalISODate so any existing importers continue working without breaking changes
export { getLocalISODate };

const CRITICAL_FLAGS = new Set([
  'out_of_location',
  'missing_checkout',
  'attendance_without_work',
  'work_without_attendance',
]);

export function hasCriticalException(item: VerificationSummaryItem): boolean {
  return item.exception_flags?.some((f) => CRITICAL_FLAGS.has(f)) ?? false;
}

/**
 * Distinguishes queue item review states when has_pending_verification is false:
 * - 'pending': has_pending_verification is true
 * - 'reviewed': attendance has been verified/rejected and has no pending/draft work entries (work_entry_count === 0 && material_count === 0)
 * - 'nothing_pending': neutral state when nothing was submitted or entries may remain in draft
 */
export function getQueueItemReviewState(
  item: VerificationSummaryItem
): 'pending' | 'reviewed' | 'nothing_pending' {
  if (item.has_pending_verification) {
    return 'pending';
  }
  if (
    (item.attendance_status === 'verified' || item.attendance_status === 'rejected') &&
    item.work_entry_count === 0 &&
    item.material_count === 0
  ) {
    return 'reviewed';
  }
  return 'nothing_pending';
}

/**
 * Sorts verification queue items:
 * 1. Priority items (has_pending_verification === true OR any critical exception flag) come first.
 * 2. Alphabetically by employee_name within each priority tier.
 */
export function sortQueueItems(items: VerificationSummaryItem[]): VerificationSummaryItem[] {
  return [...items].sort((a, b) => {
    const aPriority = a.has_pending_verification || hasCriticalException(a);
    const bPriority = b.has_pending_verification || hasCriticalException(b);

    if (aPriority && !bPriority) return -1;
    if (!aPriority && bPriority) return 1;

    return a.employee_name.localeCompare(b.employee_name, undefined, { sensitivity: 'base' });
  });
}

export const SupervisorVerificationQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const queryDate = searchParams.get('date');
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return isValidISODate(queryDate) ? (queryDate as string) : getLocalISODate();
  });
  const [selectedSiteId, setSelectedSiteId] = useState<string>('');
  const [sites, setSites] = useState<SiteResponseData[]>([]);

  const [queueData, setQueueData] = useState<VerificationSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load available sites once
  useEffect(() => {
    let isMounted = true;
    getSitesApi()
      .then((data) => {
        if (isMounted) setSites(data);
      })
      .catch(() => {
        // Non-blocking: site filter will fall back to options present in queue
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getVerificationSummary(selectedDate, selectedSiteId || undefined);
      setQueueData(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load verification queue';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    setLoading(true);
    setError(null);

    getVerificationSummary(selectedDate, selectedSiteId || undefined)
      .then((data) => {
        if (!ignore) {
          setQueueData(data);
          setLoading(false);
        }
      })
      .catch((err: any) => {
        if (!ignore) {
          const msg = err.response?.data?.detail || err.message || 'Failed to load verification queue';
          setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [selectedDate, selectedSiteId]);

  const handleDateChange = (newDate: string) => {
    setSelectedDate(newDate);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (newDate) {
        next.set('date', newDate);
      } else {
        next.delete('date');
      }
      return next;
    });
  };

  // Combine fetched sites with any site found in queue items
  const siteOptions = useMemo(() => {
    const map = new Map<string, string>();
    sites.forEach((s) => map.set(s.id, s.name));
    if (queueData?.items) {
      queueData.items.forEach((item) => {
        if (item.site_id && item.site_name && !map.has(item.site_id)) {
          map.set(item.site_id, item.site_name);
        }
      });
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [sites, queueData]);

  const sortedItems = useMemo(() => sortQueueItems(queueData?.items || []), [queueData]);

  const handleRowClick = (employeeId: string) => {
    navigate(`/verification/${employeeId}?date=${selectedDate}`);
  };

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h1>Supervisor Verification Queue</h1>
          <p>Review end-of-day attendance, daily work entries, materials, and active exceptions.</p>
        </div>
      </div>

      {/* ── Filter Controls ── */}
      <div className={styles.controlsBar}>
        <div className={styles.controlGroup}>
          <label htmlFor="verification-date">
            <Calendar size={16} />
            Date:
          </label>
          <input
            id="verification-date"
            type="date"
            className={styles.dateInput}
            value={selectedDate}
            onChange={(e) => handleDateChange(e.target.value)}
          />
        </div>

        <div className={styles.controlGroup}>
          <label htmlFor="verification-site">
            <Building2 size={16} />
            Site:
          </label>
          <select
            id="verification-site"
            className={styles.selectInput}
            value={selectedSiteId}
            onChange={(e) => setSelectedSiteId(e.target.value)}
          >
            <option value="">All Sites</option>
            {siteOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className={styles.refreshBtn}
          onClick={fetchQueue}
          disabled={loading}
          aria-label="Refresh verification queue"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : undefined} />
          Refresh
        </button>
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className={styles.errorBanner} role="alert" data-testid="queue-error">
          <div className={styles.errorContent}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
          <button type="button" className={styles.retryBtn} onClick={fetchQueue}>
            Retry
          </button>
        </div>
      )}

      {/* ── Summary Stats ── */}
      {queueData && (
        <div className={styles.statsRow}>
          <div className={styles.statCard}>
            <span className={styles.statValue}>{queueData.total_employees}</span>
            <span className={styles.statLabel}>Total Employees</span>
          </div>
          <div className={`${styles.statCard} ${queueData.pending_verification_count > 0 ? styles.statCardPending : ''}`}>
            <span className={styles.statValue}>{queueData.pending_verification_count}</span>
            <span className={styles.statLabel}>Pending Verification</span>
          </div>
        </div>
      )}

      {/* ── Loading State ── */}
      {loading && (
        <div className={styles.loadingContainer} data-testid="queue-loading">
          <Loader2 size={32} className="animate-spin" style={{ color: 'var(--color-primary-600)' }} />
          <p>Loading verification queue…</p>
        </div>
      )}

      {/* ── Empty State ── */}
      {!loading && queueData && queueData.items.length === 0 && (
        <div className={styles.emptyState} data-testid="queue-empty-state">
          <Clock size={40} style={{ color: 'var(--color-neutral-400)' }} />
          <h3>No verification records found</h3>
          <p>No submitted work, attendance, or materials were found for this date and site selection.</p>
        </div>
      )}

      {/* ── Queue List ── */}
      {!loading && queueData && sortedItems.length > 0 && (
        <div className={styles.queueList} role="feed" aria-label="Employees pending verification">
          {sortedItems.map((item) => (
            <div
              key={item.employee_id}
              className={styles.queueRow}
              data-testid="queue-row"
              onClick={() => handleRowClick(item.employee_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleRowClick(item.employee_id);
                }
              }}
              aria-label={`Verify records for ${item.employee_name}`}
            >
              {/* Row Header */}
              <div className={styles.rowHeader}>
                <div className={styles.employeeInfo}>
                  <span className={styles.employeeName}>{item.employee_name}</span>
                  <span className={styles.employeeCode}>{item.employee_code}</span>
                  {item.site_name && <span className={styles.siteTag}>{item.site_name}</span>}
                </div>

                <div className={styles.rowActions}>
                  {(() => {
                    const reviewState = getQueueItemReviewState(item);
                    if (reviewState === 'pending') {
                      return (
                        <span className={styles.pendingBadge} data-testid="pending-badge">
                          <span className={styles.pendingDot} />
                          Pending Review
                        </span>
                      );
                    }
                    if (reviewState === 'reviewed') {
                      return (
                        <span className={styles.reviewedBadge} data-testid="reviewed-badge">
                          <CheckCircle size={14} />
                          Reviewed
                        </span>
                      );
                    }
                    return (
                      <span className={styles.neutralBadge} data-testid="nothing-pending-badge">
                        <Clock size={14} />
                        Nothing pending
                      </span>
                    );
                  })()}
                  <ChevronRight size={18} style={{ color: 'var(--color-neutral-400)' }} />
                </div>
              </div>

              {/* Metrics Grid */}
              <div className={styles.metricsGrid}>
                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Attendance</span>
                  <span className={styles.metricValue}>
                    {item.attendance_status ? (
                      <StatusBadge status={mapAttendanceStatusToBadge(item.attendance_status)} />
                    ) : (
                      'None'
                    )}
                  </span>
                </div>

                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Hours</span>
                  <span className={styles.metricValue}>
                    {item.working_hours != null ? `${item.working_hours}h` : '—'}
                  </span>
                </div>

                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Work Entries</span>
                  <span className={styles.metricValue}>{item.work_entry_count}</span>
                </div>

                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Photos</span>
                  <span className={styles.metricValue}>{item.photo_count}</span>
                </div>

                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Materials</span>
                  <span className={styles.metricValue}>{item.material_count}</span>
                </div>

                <div className={styles.metricItem}>
                  <span className={styles.metricLabel}>Material Spend</span>
                  <span className={styles.metricValue}>₹{formatDecimal(item.total_material_cost)}</span>
                </div>
              </div>

              {/* Exception Badges */}
              {item.exception_flags && item.exception_flags.length > 0 && (
                <div className={styles.exceptionsList} data-testid="exceptions-list">
                  <span className={styles.exceptionsLabel}>
                    <ShieldAlert size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '4px' }} />
                    Exceptions:
                  </span>
                  {item.exception_flags.map((flag) => (
                    <ExceptionBadge key={flag} flag={flag} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

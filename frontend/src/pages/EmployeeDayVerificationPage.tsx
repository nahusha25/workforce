import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  getEmployeeDayDetail,
  approveEntity,
  rejectEntity,
  returnEntity,
  generateIdempotencyKey,
  type EmployeeDayDetailResponse,
  type EmployeeDayPhotoDetail,
  type EntityType,
} from '../api/verification';
import { VerificationRemarksModal } from '../components/verification/VerificationRemarksModal';
import { ExceptionBadge } from '../components/ui/ExceptionBadge';
import { StatusBadge, mapAttendanceStatusToBadge } from '../components/ui/StatusBadge';
import { AuditHistoryTimeline } from '../components/verification/AuditHistoryTimeline';
import { formatDecimal } from '../components/MaterialTransactionEntry';
import { getLocalISODate, isValidISODate } from '../utils/date';
import {
  ArrowLeft,
  Calendar,
  Building2,
  Clock,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  X,
  FileText,
  Package,
  Camera,
  ImageOff,
  MessageSquare,
} from 'lucide-react';
import styles from './EmployeeDayVerificationPage.module.css';

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Format ISO datetime string into "26 Sep, 6:15 PM".
 */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    const datePart = `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`;
    const timePart = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    return `${datePart}, ${timePart}`;
  } catch {
    return '—';
  }
}

/**
 * Determine if check-out falls on a different calendar day than check-in in local timezone.
 */
export function isNextDay(
  checkInIso: string | null | undefined,
  checkOutIso: string | null | undefined
): boolean {
  if (!checkInIso || !checkOutIso) return false;
  try {
    const inDate = new Date(checkInIso);
    const outDate = new Date(checkOutIso);
    if (isNaN(inDate.getTime()) || isNaN(outDate.getTime())) return false;
    return (
      inDate.getFullYear() !== outDate.getFullYear() ||
      inDate.getMonth() !== outDate.getMonth() ||
      inDate.getDate() !== outDate.getDate()
    );
  } catch {
    return false;
  }
}

/**
 * Format ISO datetime string into local time e.g. "09:30 AM" (retained for backward compatibility).
 */
export function formatLocalTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
}

interface ActiveActionState {
  targetId: string;
  entityType: EntityType;
  action: 'approve' | 'reject' | 'return';
  entityDescription: string;
  isHighValue?: boolean;
  isReopen?: boolean;
  idempotencyKey: string;
  remarks: string;
}

export const EmployeeDayVerificationPage: React.FC = () => {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [searchParams] = useSearchParams();
  const { role } = useAuth();
  const isAdminOrDirector = role === 'administrator' || role === 'director';

  const queryDate = searchParams.get('date');
  const selectedDate = useMemo(() => {
    return isValidISODate(queryDate) ? (queryDate as string) : getLocalISODate();
  }, [queryDate]);

  const [detail, setDetail] = useState<EmployeeDayDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<{ status?: number; message: string } | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  // Notices
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [conflictNotice, setConflictNotice] = useState<string | null>(null);

  // Action State
  const [activeAction, setActiveAction] = useState<ActiveActionState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [lastFailedAction, setLastFailedAction] = useState<ActiveActionState | null>(null);

  // Lightbox state
  const [activeLightboxImage, setActiveLightboxImage] = useState<string | null>(null);
  const [lightboxError, setLightboxError] = useState<boolean>(false);

  // Set of image IDs/URLs that failed to load
  const [brokenImages, setBrokenImages] = useState<Set<string>>(new Set());

  const handleRetry = () => {
    setReloadKey((k) => k + 1);
  };

  const openLightbox = (url: string) => {
    setLightboxError(false);
    setActiveLightboxImage(url);
  };

  const closeLightbox = () => {
    setActiveLightboxImage(null);
    setLightboxError(false);
  };

  useEffect(() => {
    let ignore = false;
    // Only show full-page loading spinner on initial mount when detail is not yet loaded.
    // When refreshing after an action, keep content DOM mounted to preserve scroll position.
    if (!detail) {
      setLoading(true);
    }
    setError(null);

    if (employeeId) {
      const scrollYBefore = typeof window !== 'undefined' ? window.scrollY : 0;
      getEmployeeDayDetail(employeeId, selectedDate)
        .then((data) => {
          if (!ignore) {
            setDetail(data);
            setLoading(false);
            if (scrollYBefore > 0 && typeof window !== 'undefined') {
              window.scrollTo(0, scrollYBefore);
            }
          }
        })
        .catch((err: any) => {
          if (!ignore) {
            const status = err.response?.status;
            const msg = err.response?.data?.detail || err.message || 'Failed to load employee verification details';
            setError({
              status,
              message: typeof msg === 'string' ? msg : JSON.stringify(msg),
            });
            setLoading(false);
          }
        });
    } else {
      setLoading(false);
    }

    return () => {
      ignore = true;
    };
  }, [employeeId, selectedDate, reloadKey]);

  // Lightbox keyboard Esc listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeLightbox();
      }
    };
    if (activeLightboxImage) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeLightboxImage]);

  const handleImageError = (imgKey: string) => {
    setBrokenImages((prev) => new Set(prev).add(imgKey));
  };

  const openAction = (
    targetId: string,
    entityType: EntityType,
    action: 'approve' | 'reject' | 'return',
    entityDescription: string,
    isHighValue: boolean = false,
    isReopen: boolean = false
  ) => {
    setSuccessNotice(null);
    setConflictNotice(null);
    setActionError(null);
    setActiveAction({
      targetId,
      entityType,
      action,
      entityDescription,
      isHighValue,
      isReopen,
      idempotencyKey: generateIdempotencyKey(),
      remarks: '',
    });
  };

  const executeAction = async (actionState: ActiveActionState, remarksToUse?: string) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setActionError(null);
    const finalRemarks = (remarksToUse ?? actionState.remarks ?? '').trim();

    try {
      if (actionState.action === 'approve') {
        await approveEntity(actionState.targetId, {
          entity_type: actionState.entityType,
          idempotency_key: actionState.idempotencyKey,
          remarks: finalRemarks.length > 0 ? finalRemarks : null,
        });
      } else if (actionState.action === 'reject') {
        await rejectEntity(actionState.targetId, {
          entity_type: actionState.entityType,
          idempotency_key: actionState.idempotencyKey,
          remarks: finalRemarks,
        });
      } else {
        await returnEntity(actionState.targetId, {
          entity_type: actionState.entityType,
          idempotency_key: actionState.idempotencyKey,
          remarks: finalRemarks,
        });
      }

      // Success
      setActiveAction(null);
      setActionError(null);
      setLastFailedAction(null);
      const actionLabel =
        actionState.action === 'approve'
          ? 'approved'
          : actionState.action === 'reject'
          ? 'rejected'
          : actionState.isReopen
          ? 'reopened'
          : 'returned for correction';
      setSuccessNotice(`${actionState.entityDescription} ${actionLabel} successfully.`);
      setConflictNotice(null);
      setReloadKey((k) => k + 1);
    } catch (err: any) {
      const status = err.response?.status;
      const detailMsg = err.response?.data?.detail;
      const detailStr = typeof detailMsg === 'string' ? detailMsg : JSON.stringify(detailMsg || '');

      const isConflict =
        status === 409 ||
        (status === 400 &&
          (detailStr.includes('Target must be submitted') ||
            detailStr.includes('Cannot approve record with status') ||
            detailStr.includes('Cannot reject record with status') ||
            detailStr.includes('Cannot correction_required record with status')));

      if (isConflict) {
        setActiveAction(null);
        setActionError(null);
        setLastFailedAction(null);
        setConflictNotice('This record changed; refreshed');
        setSuccessNotice(null);
        setReloadKey((k) => k + 1);
      } else if (status === 422) {
        // 422 validation error: keep modal open, preserve remarks, show error in modal
        const errorMsg =
          typeof detailMsg === 'string'
            ? detailMsg
            : err.message || 'Validation error. Please check remarks and try again.';
        setActionError(errorMsg);
        // keep activeAction open so remarks are preserved in modal
      } else {
        // Network or server error: close modal, display page-level retryable error
        const errorMsg =
          typeof detailMsg === 'string'
            ? detailMsg
            : err.message || 'Action failed. Please try again.';
        setActiveAction(null);
        setActionError(errorMsg);
        setLastFailedAction(actionState);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const backUrl = `/verification?date=${selectedDate}`;

  return (
    <div className={styles.container}>
      {/* ── Back Navigation ── */}
      <Link to={backUrl} className={styles.backLink} data-testid="back-link">
        <ArrowLeft size={16} />
        Back to Verification Queue
      </Link>

      {/* ── Action Success Notice ── */}
      {successNotice && (
        <div className={styles.successNotice} data-testid="success-notice" role="status">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} />
            <span>{successNotice}</span>
          </div>
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => setSuccessNotice(null)}
            aria-label="Dismiss success notice"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ── State Conflict Notice ── */}
      {conflictNotice && (
        <div className={styles.conflictBanner} data-testid="conflict-notice" role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            <span>{conflictNotice}</span>
          </div>
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => setConflictNotice(null)}
            aria-label="Dismiss conflict notice"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ── Page-Level Action Error with Retry ── */}
      {actionError && !activeAction && (
        <div className={styles.actionErrorNotice} data-testid="page-action-error" role="alert">
          <AlertTriangle size={18} />
          <span style={{ flex: 1 }}>{actionError}</span>
          {lastFailedAction && (
            <button
              type="button"
              className={styles.inlineRetryBtn}
              data-testid="action-retry-btn"
              onClick={() => executeAction(lastFailedAction)}
              disabled={isSubmitting}
            >
              Retry
            </button>
          )}
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => setActionError(null)}
            aria-label="Dismiss action error"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ── Loading State ── */}
      {loading && (
        <div className={styles.loadingContainer} data-testid="detail-loading">
          <Loader2 size={36} className="animate-spin" style={{ color: 'var(--color-primary-600)' }} />
          <p>Loading verification details…</p>
        </div>
      )}

      {/* ── Error State (403 / 404 / Generic) ── */}
      {!loading && error && (
        <div className={styles.errorState} data-testid="detail-error" role="alert">
          {error.status === 403 || error.status === 404 ? (
            <>
              <ShieldAlert size={44} style={{ color: 'var(--color-neutral-400)' }} />
              <h3>
                {error.status === 404 ? 'Employee Record Not Found' : 'Access Denied'}
              </h3>
              <p>
                {error.status === 404
                  ? 'No employee day verification record was found for this date and identifier.'
                  : 'You do not have supervisor or administrator permissions to review this employee.'}
              </p>
              <Link to={backUrl} className={styles.retryBtn} style={{ textDecoration: 'none' }}>
                Return to Queue
              </Link>
            </>
          ) : (
            <>
              <AlertTriangle size={44} style={{ color: '#ef4444' }} />
              <h3>Failed to load verification detail</h3>
              <p>{error.message}</p>
              <button type="button" className={styles.retryBtn} onClick={handleRetry}>
                Retry
              </button>
            </>
          )}
        </div>
      )}

      {/* ── Empty Day State ── */}
      {!loading && !error && detail && !detail.attendance && detail.work_entries.length === 0 && (
        <div className={styles.emptyState} data-testid="detail-empty-day">
          <Clock size={44} style={{ color: 'var(--color-neutral-400)' }} />
          <h3>No records for this date</h3>
          <p>
            No attendance, daily work entries, or material transactions were logged for {detail.employee_name} on{' '}
            {detail.date}.
          </p>
          <Link to={backUrl} className={styles.retryBtn} style={{ textDecoration: 'none' }}>
            Back to Queue
          </Link>
        </div>
      )}

      {/* ── Content View ── */}
      {!loading && !error && detail && (detail.attendance || detail.work_entries.length > 0) && (
        <>
          {/* ── Header Card ── */}
          <div className={styles.headerCard} data-testid="detail-header">
            <div className={styles.headerMain}>
              <div className={styles.employeeTitle}>
                <div className={styles.employeeName}>
                  {detail.employee_name}
                  <span className={styles.employeeCode}>{detail.employee_code}</span>
                </div>
                <div className={styles.headerMeta}>
                  <span className={styles.metaItem}>
                    <Calendar size={14} />
                    {detail.date}
                  </span>
                  <span className={styles.metaItem}>
                    <Building2 size={14} />
                    {detail.site_name || 'No site assigned'}
                  </span>
                </div>
              </div>

              {detail.all_verified && (
                <div className={styles.allVerifiedBadge} data-testid="all-verified-badge">
                  <CheckCircle2 size={14} />
                  All Verified
                </div>
              )}
            </div>

            {/* Exception Badges */}
            {detail.exception_flags && detail.exception_flags.length > 0 && (
              <div className={styles.exceptionsBar} data-testid="detail-exceptions-bar">
                <span className={styles.exceptionsLabel}>
                  <ShieldAlert size={14} />
                  Active Exceptions:
                </span>
                {detail.exception_flags.map((flag) => (
                  <ExceptionBadge key={flag} flag={flag} />
                ))}
              </div>
            )}
          </div>

          {/* ── Attendance Section ── */}
          {detail.attendance && (
            <div className={styles.sectionCard} data-testid="attendance-section">
              <div className={styles.sectionHeader}>
                <h2>
                  <Clock size={18} />
                  Attendance Record
                </h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <StatusBadge status={mapAttendanceStatusToBadge(detail.attendance.status)} />

                  {/* Attendance Actions: if session is still open (no check_out_time), show "Session still open" */}
                  {!detail.attendance.check_out_time ? (
                    <span className={styles.notSubmittedNote} data-testid="attendance-open-session-note">
                      Session still open
                    </span>
                  ) : ['submitted', 'flagged', 'draft'].includes(detail.attendance.status) ? (
                    <div className={styles.actionsGroup}>
                      <button
                        type="button"
                        className={styles.btnApprove}
                        data-testid="approve-attendance-btn"
                        disabled={isSubmitting}
                        onClick={() =>
                          openAction(
                            detail.attendance!.id,
                            'attendance',
                            'approve',
                            `Attendance Record (${detail.date})`
                          )
                        }
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className={styles.btnReject}
                        data-testid="reject-attendance-btn"
                        disabled={isSubmitting}
                        onClick={() =>
                          openAction(
                            detail.attendance!.id,
                            'attendance',
                            'reject',
                            `Attendance Record (${detail.date})`
                          )
                        }
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className={styles.btnReturn}
                        data-testid="return-attendance-btn"
                        disabled={isSubmitting}
                        onClick={() =>
                          openAction(
                            detail.attendance!.id,
                            'attendance',
                            'return',
                            `Attendance Record (${detail.date})`
                          )
                        }
                      >
                        Return
                      </button>
                    </div>
                  ) : null}

                  {/* Admin Reopen for verified attendance */}
                  {isAdminOrDirector && detail.attendance.status === 'verified' && (
                    <div className={styles.actionsGroup}>
                      <button
                        type="button"
                        className={styles.btnReopen}
                        data-testid="reopen-attendance-btn"
                        disabled={isSubmitting}
                        onClick={() =>
                          openAction(
                            detail.attendance!.id,
                            'attendance',
                            'return',
                            `Attendance Record (${detail.date})`,
                            false,
                            true
                          )
                        }
                      >
                        Reopen
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {detail.attendance.override_by && (
                <div className={styles.overrideBanner} data-testid="override-banner">
                  <ShieldAlert size={16} />
                  Supervisor override applied
                </div>
              )}

              <div className={styles.detailsGrid}>
                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Check-in</span>
                  <span className={styles.detailValue} data-testid="check-in-time">
                    {formatDateTime(detail.attendance.check_in_time)}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Check-out</span>
                  <span className={styles.detailValue} data-testid="check-out-time">
                    {formatDateTime(detail.attendance.check_out_time)}
                    {isNextDay(detail.attendance.check_in_time, detail.attendance.check_out_time) && (
                      <span className={styles.nextDayTag} data-testid="next-day-tag">
                        next day
                      </span>
                    )}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Hours Worked</span>
                  <span className={styles.detailValue}>
                    {detail.attendance.working_hours != null ? `${detail.attendance.working_hours}h` : '—'}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Overtime</span>
                  <span className={styles.detailValue}>
                    {detail.attendance.overtime_hours != null ? `${detail.attendance.overtime_hours}h` : '—'}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Check-in Distance</span>
                  <span className={styles.detailValue}>
                    {detail.attendance.check_in_distance_m != null
                      ? `${Math.round(detail.attendance.check_in_distance_m)}m from site`
                      : '—'}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Check-out Distance</span>
                  <span className={styles.detailValue}>
                    {detail.attendance.check_out_distance_m != null
                      ? `${Math.round(detail.attendance.check_out_distance_m)}m from site`
                      : '—'}
                  </span>
                </div>

                <div className={styles.detailField}>
                  <span className={styles.detailLabel}>Geofence Compliance</span>
                  <span className={styles.detailValue}>
                    {detail.attendance.is_within_geofence === true && (
                      <span className={styles.geofenceInside} data-testid="geofence-inside">
                        <CheckCircle2 size={14} />
                        Inside Geofence
                      </span>
                    )}
                    {detail.attendance.is_within_geofence === false && (
                      <span className={styles.geofenceOutside} data-testid="geofence-outside">
                        <AlertTriangle size={14} />
                        Outside Geofence
                      </span>
                    )}
                    {detail.attendance.is_within_geofence == null && 'Unknown'}
                  </span>
                </div>
              </div>

              {/* Attendance Audit History */}
              <div className={styles.timelineSection}>
                <h4 className={styles.timelineTitle}>Attendance Audit History</h4>
                <AuditHistoryTimeline events={detail.attendance.history || []} />
              </div>
            </div>
          )}

          {/* ── Daily Work Entries Section ── */}
          <div className={styles.sectionCard} data-testid="work-entries-section">
            <div className={styles.sectionHeader}>
              <h2>
                <FileText size={18} />
                Daily Work Entries ({detail.work_entries.length})
              </h2>
            </div>

            {detail.work_entries.length === 0 ? (
              <p style={{ color: 'var(--color-neutral-600)', fontSize: 'var(--font-size-sm)' }}>
                No daily work entries submitted for this date.
              </p>
            ) : (
              <div className={styles.workEntriesList}>
                {detail.work_entries.map((entry) => (
                  <div key={entry.id} className={styles.workEntryCard} data-testid="work-entry-card">
                    {/* Entry Header */}
                    <div className={styles.workEntryHeader}>
                      <div className={styles.workEntryTitle}>
                        <span className={styles.activityName}>{entry.activity_name}</span>
                        {entry.activity_category && (
                          <span className={styles.categoryTag}>{entry.activity_category}</span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <StatusBadge status={entry.status} />

                        {entry.status === 'draft' && (
                          <span className={styles.notSubmittedNote} data-testid={`draft-note-${entry.id}`}>
                            Not submitted yet
                          </span>
                        )}

                        {entry.status === 'submitted' && (
                          <div className={styles.actionsGroup}>
                            <button
                              type="button"
                              className={styles.btnApprove}
                              data-testid={`approve-work-entry-${entry.id}`}
                              disabled={isSubmitting}
                              onClick={() =>
                                openAction(
                                  entry.id,
                                  'daily_work',
                                  'approve',
                                  `Work Entry: ${entry.activity_name}`
                                )
                              }
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className={styles.btnReject}
                              data-testid={`reject-work-entry-${entry.id}`}
                              disabled={isSubmitting}
                              onClick={() =>
                                openAction(
                                  entry.id,
                                  'daily_work',
                                  'reject',
                                  `Work Entry: ${entry.activity_name}`
                                )
                              }
                            >
                              Reject
                            </button>
                            <button
                              type="button"
                              className={styles.btnReturn}
                              data-testid={`return-work-entry-${entry.id}`}
                              disabled={isSubmitting}
                              onClick={() =>
                                openAction(
                                  entry.id,
                                  'daily_work',
                                  'return',
                                  `Work Entry: ${entry.activity_name}`
                                )
                              }
                            >
                              Return
                            </button>
                          </div>
                        )}

                        {isAdminOrDirector && entry.status === 'approved' && (
                          <div className={styles.actionsGroup}>
                            <button
                              type="button"
                              className={styles.btnReopen}
                              data-testid={`reopen-work-entry-${entry.id}`}
                              disabled={isSubmitting}
                              onClick={() =>
                                openAction(
                                  entry.id,
                                  'daily_work',
                                  'return',
                                  `Work Entry: ${entry.activity_name}`,
                                  false,
                                  true
                                )
                              }
                            >
                              Reopen
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Entry Meta Fields */}
                    <div className={styles.detailsGrid}>
                      <div className={styles.detailField}>
                        <span className={styles.detailLabel}>Quantity</span>
                        <span className={styles.detailValue} data-testid="entry-quantity">
                          {entry.quantity} {entry.uom}
                        </span>
                      </div>

                      <div className={styles.detailField}>
                        <span className={styles.detailLabel}>Work Order</span>
                        <span className={styles.detailValue}>
                          {entry.work_order_number || '—'}
                        </span>
                      </div>

                      <div className={styles.detailField}>
                        <span className={styles.detailLabel}>Remarks</span>
                        <span className={styles.detailValue}>{entry.remarks || '—'}</span>
                      </div>
                    </div>

                    {/* Photos */}
                    {entry.photos && entry.photos.length > 0 && (
                      <div className={styles.photosContainer}>
                        <span className={styles.photosTitle}>
                          <Camera size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '4px' }} />
                          Work Photos ({entry.photos.length})
                        </span>
                        <div className={styles.photoGrid}>
                          {entry.photos.map((photo) => {
                            const isBroken = brokenImages.has(photo.id);
                            return isBroken ? (
                              <div
                                key={photo.id}
                                className={styles.brokenImageFallback}
                                data-testid="broken-image-fallback"
                              >
                                <ImageOff size={20} />
                                <span>Image failed</span>
                                <a
                                  href={photo.image_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  data-testid="open-original-link"
                                >
                                  Open original
                                </a>
                              </div>
                            ) : (
                              <img
                                key={photo.id}
                                src={photo.thumbnail_url || photo.image_url}
                                alt="Work site capture"
                                className={styles.photoThumb}
                                data-testid="photo-thumbnail"
                                onClick={() => openLightbox(photo.image_url)}
                                onError={() => handleImageError(photo.id)}
                              />
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Materials */}
                    {entry.materials && entry.materials.length > 0 && (
                      <div className={styles.materialsContainer}>
                        <span className={styles.photosTitle}>
                          <Package size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '4px' }} />
                          Materials Logged ({entry.materials.length})
                        </span>
                        <div className={styles.materialsList}>
                          {entry.materials.map((mat) => {
                            const isBillBroken = brokenImages.has(`bill-${mat.id}`);
                            return (
                              <div key={mat.id} className={styles.materialRow} data-testid="material-row">
                                <div className={styles.materialHeader}>
                                  <span className={styles.materialName}>
                                    {mat.item_name}
                                    {mat.is_high_value && (
                                      <span
                                        className={styles.highValueBadge}
                                        data-testid="high-value-badge"
                                      >
                                        High Value
                                      </span>
                                    )}
                                  </span>

                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                    <StatusBadge status={mat.status} />

                                    {mat.status === 'draft' && (
                                      <span className={styles.notSubmittedNote} data-testid={`draft-note-${mat.id}`}>
                                        Not submitted yet
                                      </span>
                                    )}

                                    {mat.status === 'submitted' && (
                                      <div className={styles.actionsGroup}>
                                        <button
                                          type="button"
                                          className={styles.btnApprove}
                                          data-testid={`approve-material-${mat.id}`}
                                          disabled={isSubmitting}
                                          onClick={() =>
                                            openAction(
                                              mat.id,
                                              'material',
                                              'approve',
                                              `Material: ${mat.item_name}`,
                                              mat.is_high_value
                                            )
                                          }
                                        >
                                          Approve
                                        </button>
                                        <button
                                          type="button"
                                          className={styles.btnReject}
                                          data-testid={`reject-material-${mat.id}`}
                                          disabled={isSubmitting}
                                          onClick={() =>
                                            openAction(
                                              mat.id,
                                              'material',
                                              'reject',
                                              `Material: ${mat.item_name}`
                                            )
                                          }
                                        >
                                          Reject
                                        </button>
                                        <button
                                          type="button"
                                          className={styles.btnReturn}
                                          data-testid={`return-material-${mat.id}`}
                                          disabled={isSubmitting}
                                          onClick={() =>
                                            openAction(
                                              mat.id,
                                              'material',
                                              'return',
                                              `Material: ${mat.item_name}`
                                            )
                                          }
                                        >
                                          Return
                                        </button>
                                      </div>
                                    )}

                                    {isAdminOrDirector && mat.status === 'approved' && (
                                      <div className={styles.actionsGroup}>
                                        <button
                                          type="button"
                                          className={styles.btnReopen}
                                          data-testid={`reopen-material-${mat.id}`}
                                          disabled={isSubmitting}
                                          onClick={() =>
                                            openAction(
                                              mat.id,
                                              'material',
                                              'return',
                                              `Material: ${mat.item_name}`,
                                              false,
                                              true
                                            )
                                          }
                                        >
                                          Reopen
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div className={styles.materialDetailsRow}>
                                  <span>
                                    Type: <strong>{mat.transaction_type}</strong>
                                  </span>
                                  <span>
                                    Quantity: <strong>{mat.quantity}</strong>
                                  </span>
                                  <span data-testid="material-amount">
                                    Amount: <strong>₹{formatDecimal(mat.amount)}</strong>
                                  </span>
                                  {mat.bill_image_url && (
                                    <>
                                      {isBillBroken ? (
                                        <div
                                          className={styles.brokenImageFallback}
                                          style={{ width: 'auto', height: 'auto', padding: '2px 6px' }}
                                          data-testid="broken-bill-fallback"
                                        >
                                          <ImageOff size={14} />
                                          <span>Bill image failed</span>
                                          <a
                                            href={mat.bill_image_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            data-testid="open-original-bill"
                                          >
                                            Open original
                                          </a>
                                        </div>
                                      ) : (
                                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                          <img
                                            src={mat.bill_image_url}
                                            alt={`Bill for ${mat.item_name}`}
                                            className={styles.billThumb}
                                            data-testid="bill-thumbnail"
                                            onError={() => handleImageError(`bill-${mat.id}`)}
                                            onClick={() => openLightbox(mat.bill_image_url!)}
                                          />
                                          <button
                                            type="button"
                                            className={styles.billImageLink}
                                            data-testid="bill-image-btn"
                                            onClick={() => openLightbox(mat.bill_image_url!)}
                                          >
                                            <Camera size={12} />
                                            View Bill Image
                                          </button>
                                        </div>
                                      )}
                                    </>
                                  )}
                                </div>

                                {/* Material Audit History */}
                                <div className={styles.timelineSection}>
                                  <h4 className={styles.timelineTitle}>Material Audit History</h4>
                                  <AuditHistoryTimeline events={mat.history || []} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Work Entry Audit History */}
                    <div className={styles.timelineSection}>
                      <h4 className={styles.timelineTitle}>Work Entry Audit History</h4>
                      <AuditHistoryTimeline events={entry.history || []} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Approve Confirmation Modal ── */}
      {activeAction && activeAction.action === 'approve' && (
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="approve-modal-title"
          data-testid="approve-confirm-modal"
        >
          <div className={styles.modalPanel}>
            <div className={styles.modalHeader}>
              <h2 id="approve-modal-title" className={styles.modalTitle}>
                {activeAction.isHighValue ? 'Approve High-Value Material' : 'Confirm Approval'}
              </h2>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => {
                  if (!isSubmitting) setActiveAction(null);
                }}
                disabled={isSubmitting}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className={styles.modalBody}>
              <div className={styles.modalEntityContext}>
                <MessageSquare size={14} />
                <span>{activeAction.entityDescription}</span>
              </div>

              {activeAction.isHighValue && (
                <div className={styles.highValueWarning} data-testid="high-value-warning">
                  <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <strong style={{ display: 'block', marginBottom: '2px' }}>Approval Limit Warning</strong>
                    <span>This purchase exceeds the approval limit</span>
                  </div>
                </div>
              )}

              <p className={styles.modalPromptText}>
                Are you sure you want to approve this{' '}
                {activeAction.entityType === 'attendance'
                  ? 'attendance record'
                  : activeAction.entityType === 'daily_work'
                  ? 'work entry'
                  : 'material transaction'}?
              </p>

              <div className={styles.optionalRemarksGroup}>
                <label htmlFor="approve-remarks" className={styles.optionalRemarksLabel}>
                  Remarks (Optional)
                </label>
                <textarea
                  id="approve-remarks"
                  rows={2}
                  className={styles.remarksTextarea}
                  placeholder="Add optional notes for this approval…"
                  value={activeAction.remarks}
                  onChange={(e) =>
                    setActiveAction((prev) => (prev ? { ...prev, remarks: e.target.value } : null))
                  }
                  disabled={isSubmitting}
                />
              </div>

              {actionError && (
                <div className={styles.actionErrorBanner} data-testid="modal-action-error" role="alert">
                  <AlertTriangle size={16} />
                  <span style={{ flex: 1 }}>{actionError}</span>
                  <button
                    type="button"
                    className={styles.inlineRetryBtn}
                    data-testid="modal-retry-btn"
                    onClick={() => executeAction(activeAction)}
                    disabled={isSubmitting}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>

            <div className={styles.modalFooter}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() => setActiveAction(null)}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className={styles.btnPrimaryApprove}
                data-testid="confirm-approve-btn"
                onClick={() => executeAction(activeAction)}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Approving…
                  </>
                ) : (
                  'Confirm Approval'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Reject / Return Remarks Modal ── */}
      {activeAction && (activeAction.action === 'reject' || activeAction.action === 'return') && (
        <VerificationRemarksModal
          action={activeAction.isReopen ? 'reopen' : (activeAction.action as 'reject' | 'return')}
          entityDescription={activeAction.entityDescription}
          remarks={activeAction.remarks}
          onRemarksChange={(val) =>
            setActiveAction((prev) => (prev ? { ...prev, remarks: val } : null))
          }
          onConfirm={(trimmedRemarks) => executeAction(activeAction, trimmedRemarks)}
          onCancel={() => {
            if (!isSubmitting) setActiveAction(null);
          }}
          isSubmitting={isSubmitting}
          error={actionError}
        />
      )}

      {/* ── Photo Lightbox Modal ── */}
      {activeLightboxImage && (
        <div
          className={styles.lightboxBackdrop}
          data-testid="lightbox-backdrop"
          onClick={closeLightbox}
          role="dialog"
          aria-modal="true"
        >
          <div
            className={styles.lightboxContent}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className={styles.lightboxCloseBtn}
              data-testid="lightbox-close-btn"
              onClick={closeLightbox}
              aria-label="Close lightbox preview"
            >
              <X size={18} />
            </button>
            {lightboxError ? (
              <div
                className={styles.lightboxErrorFallback}
                data-testid="lightbox-error-fallback"
              >
                <ImageOff size={32} />
                <span>Failed to load full-size image</span>
                <a
                  href={activeLightboxImage}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="lightbox-open-original"
                >
                  Open original
                </a>
              </div>
            ) : (
              <img
                src={activeLightboxImage}
                alt="Enlarged verification preview"
                className={styles.lightboxImage}
                data-testid="lightbox-image"
                onError={() => setLightboxError(true)}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

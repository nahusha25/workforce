import React from 'react';
import { CheckCircle2, XCircle, RotateCcw, Clock } from 'lucide-react';
import styles from './AuditHistoryTimeline.module.css';

/**
 * A single verification action event.
 *
 * These are assembled from the inline `verification_action` / `verification_remarks`
 * fields present on each entity in the VER-002 EmployeeDayDetailResponse.
 * VER-002 does NOT return a standalone audit history array; callers must derive
 * events from entity-level fields and pass them here.
 *
 * If the backend adds a dedicated history endpoint in future, this same shape
 * remains compatible — callers just map from the API type.
 */
export interface VerificationEvent {
  /** Unique key for React list rendering */
  id: string;
  /** Verification action performed */
  action: 'approved' | 'rejected' | 'correction_required' | string;
  /** Optional human-readable label for the entity that was acted on */
  entityLabel?: string;
  /** Verifier user UUID */
  verified_by: string;
  /** Display name of the supervisor / administrator who acted */
  verified_by_name?: string | null;
  /** ISO datetime string of when the action occurred */
  verified_at: string;
  /** Remarks, required for rejected / correction_required */
  remarks?: string | null;
}

export interface AuditHistoryTimelineProps {
  events: VerificationEvent[];
  /** Optional loading state */
  isLoading?: boolean;
}

function ActionIcon({ action }: { action: string }) {
  switch (action) {
    case 'approved':
      return <CheckCircle2 size={16} className={styles.iconApproved} aria-label="Approved" />;
    case 'rejected':
      return <XCircle size={16} className={styles.iconRejected} aria-label="Rejected" />;
    case 'correction_required':
      return <RotateCcw size={16} className={styles.iconCorrection} aria-label="Returned for correction" />;
    default:
      return <Clock size={16} className={styles.iconDefault} aria-label={action} />;
  }
}

function actionLabel(action: string): string {
  switch (action) {
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'correction_required':
      return 'Returned for Correction';
    default:
      return action;
  }
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export const AuditHistoryTimeline: React.FC<AuditHistoryTimelineProps> = ({
  events,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className={styles.emptyState} aria-busy="true">
        <Clock size={28} className={styles.emptyIcon} />
        <p>Loading history…</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className={styles.emptyState} data-testid="audit-timeline-empty">
        <Clock size={28} className={styles.emptyIcon} />
        <p>No verification actions recorded yet.</p>
      </div>
    );
  }

  // Chronological order (oldest first)
  const sorted = [...events].sort(
    (a, b) => new Date(a.verified_at).getTime() - new Date(b.verified_at).getTime(),
  );

  return (
    <ol className={styles.timeline} aria-label="Verification audit history">
      {sorted.map((event, idx) => (
        <li key={event.id} className={styles.item}>
          {/* ── Connector spine ── */}
          <div className={styles.spineLine}>
            <div className={`${styles.dot} ${styles[`dot_${event.action}`] ?? styles.dot_default}`}>
              <ActionIcon action={event.action} />
            </div>
            {idx < sorted.length - 1 && <div className={styles.connector} aria-hidden="true" />}
          </div>

          {/* ── Event card ── */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <span className={`${styles.actionLabel} ${styles[`action_${event.action}`] ?? styles.action_default}`}>
                {actionLabel(event.action)}
              </span>
              {event.entityLabel && <span className={styles.entityLabel}>{event.entityLabel}</span>}
            </div>
            <time className={styles.timestamp} dateTime={event.verified_at}>
              {formatDateTime(event.verified_at)}
            </time>
            {event.verified_by_name && (
              <span className={styles.actor}>by {event.verified_by_name}</span>
            )}
            {event.remarks && (
              <blockquote className={styles.remarks}>{event.remarks}</blockquote>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
};

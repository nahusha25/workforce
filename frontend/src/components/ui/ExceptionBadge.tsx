import React from 'react';
import styles from './ExceptionBadge.module.css';
import { AlertTriangle, AlertOctagon } from 'lucide-react';

/**
 * Exception flag types produced by the backend exception engine (BE-026).
 * Severity mapping:
 *   critical — flags that indicate a fundamental attendance/work integrity failure
 *              the supervisor must actively resolve before approval can proceed.
 *   warning  — compliance reminders that surface data quality issues but do not
 *              block the approval workflow on their own.
 */
export type ExceptionFlagType =
  | 'out_of_location'
  | 'missing_checkout'
  | 'attendance_without_work'
  | 'work_without_attendance'
  | 'no_photograph'
  | 'high_value_material';

type Severity = 'critical' | 'warning';

interface FlagMeta {
  label: string;
  severity: Severity;
}

const FLAG_META: Record<ExceptionFlagType, FlagMeta> = {
  out_of_location: {
    label: 'Out of Location',
    severity: 'critical',
  },
  missing_checkout: {
    label: 'Missing Check-out',
    severity: 'critical',
  },
  attendance_without_work: {
    label: 'No Work Logged',
    severity: 'critical',
  },
  work_without_attendance: {
    label: 'Work Without Attendance',
    severity: 'critical',
  },
  no_photograph: {
    label: 'No Photo',
    severity: 'warning',
  },
  high_value_material: {
    label: 'High-Value Material',
    severity: 'warning',
  },
};

export interface ExceptionBadgeProps {
  flag: ExceptionFlagType | string;
  /** Override the auto-derived label */
  label?: string;
}

export const ExceptionBadge: React.FC<ExceptionBadgeProps> = ({ flag, label }) => {
  const meta = FLAG_META[flag as ExceptionFlagType];
  const severity: Severity = meta?.severity ?? 'warning';
  const displayLabel = label ?? meta?.label ?? flag;
  const Icon = severity === 'critical' ? AlertOctagon : AlertTriangle;

  return (
    <span
      className={`${styles.badge} ${severity === 'critical' ? styles.critical : styles.warning}`}
      title={`Exception: ${displayLabel}`}
      data-flag={flag}
      data-severity={severity}
    >
      <Icon size={11} aria-hidden="true" />
      {displayLabel}
    </span>
  );
};

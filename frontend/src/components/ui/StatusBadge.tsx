import React from 'react';
import styles from './StatusBadge.module.css';

export type StatusType =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'verified'
  | 'rejected'
  | 'correction'
  | 'correction_required'
  | 'active'
  | 'inactive'
  | 'flagged';

export type AttendanceStatus =
  | 'draft'
  | 'submitted'
  | 'flagged'
  | 'verified'
  | 'rejected'
  | 'correction_required';

export function mapAttendanceStatusToBadge(status: string | null | undefined): StatusType {
  switch (status) {
    case 'draft':
      return 'draft';
    case 'submitted':
      return 'submitted';
    case 'flagged':
      return 'flagged';
    case 'verified':
      return 'verified';
    case 'rejected':
      return 'rejected';
    case 'correction_required':
      return 'correction_required';
    default:
      // Do NOT silently fall back to 'draft' — that hides mapping gaps.
      // Warn loudly and pass the raw string through so it is visibly wrong.
      console.warn(`[mapAttendanceStatusToBadge] Unrecognized attendance status: ${JSON.stringify(status)}`);
      return (status ?? 'unknown') as StatusType;
  }
}

export interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const normalizedStatus = status.toLowerCase() as StatusType;
  const statusClass = styles[normalizedStatus] || styles.draft;

  return <span className={`${styles.badge} ${statusClass}`}>{label || status}</span>;
};

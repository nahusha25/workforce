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

export type AttendanceStatus = 'draft' | 'flagged' | 'verified' | 'rejected' | 'correction_required';

export function mapAttendanceStatusToBadge(status: string | null | undefined): StatusType {
  switch (status) {
    case 'draft':
      return 'draft';
    case 'flagged':
      return 'flagged';
    case 'verified':
      return 'verified';
    case 'rejected':
      return 'rejected';
    case 'correction_required':
      return 'correction_required';
    default:
      return 'draft';
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

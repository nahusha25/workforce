import React, { useId } from 'react';
import { X, AlertCircle, MessageSquare } from 'lucide-react';
import { Button } from '../ui/Button';
import styles from './VerificationRemarksModal.module.css';

export type RemarksAction = 'reject' | 'return' | 'reopen';

export interface VerificationRemarksModalProps {
  /** Which verification action this modal is collecting remarks for */
  action: RemarksAction;
  /** Free-form context shown in the modal body (e.g. "Attendance — 2024-09-28") */
  entityDescription: string;
  /** Current value of the remarks textarea, controlled externally */
  remarks: string;
  /** Called on every keystroke */
  onRemarksChange: (value: string) => void;
  /** Called when the user confirms — receives the trimmed remarks string */
  onConfirm: (trimmedRemarks: string) => void;
  /** Called when the user cancels or clicks the × button */
  onCancel: () => void;
  /** While the parent is submitting; disables controls and shows spinner */
  isSubmitting?: boolean;
  /** Error message from the parent (e.g. API error) */
  error?: string | null;
}

const ACTION_LABELS: Record<RemarksAction, { title: string; submitLabel: string }> = {
  reject: {
    title: 'Reject — Mandatory Remarks',
    submitLabel: 'Confirm Rejection',
  },
  return: {
    title: 'Return for Correction — Mandatory Remarks',
    submitLabel: 'Send for Correction',
  },
  reopen: {
    title: 'Reopen — Mandatory Remarks',
    submitLabel: 'Confirm Reopen',
  },
};

/** Minimum trimmed character count, matching the backend CHECK constraint. */
const MIN_REMARKS_LENGTH = 10;

export const VerificationRemarksModal: React.FC<VerificationRemarksModalProps> = ({
  action,
  entityDescription,
  remarks,
  onRemarksChange,
  onConfirm,
  onCancel,
  isSubmitting = false,
  error = null,
}) => {
  const textareaId = useId();
  const { title, submitLabel } = ACTION_LABELS[action];

  const trimmedLength = remarks.trim().length;
  const isValid = trimmedLength >= MIN_REMARKS_LENGTH;
  const showLengthError = remarks.length > 0 && !isValid;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isSubmitting) return;
    onConfirm(remarks.trim());
  };

  const handleCancel = () => {
    if (isSubmitting) return;
    onCancel();
  };

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-labelledby="remarks-modal-title"
    >
      <div className={styles.panel}>
        {/* ── Header ── */}
        <div className={styles.header}>
          <h2 id="remarks-modal-title" className={styles.title}>
            {title}
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={handleCancel}
            disabled={isSubmitting}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className={styles.body}>
            {/* Entity context */}
            <div className={styles.entityContext}>
              <MessageSquare size={14} className={styles.contextIcon} />
              <span>{entityDescription}</span>
            </div>

            {/* API error */}
            {error && (
              <div className={styles.errorBanner} role="alert">
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
            )}

            {/* Remarks textarea */}
            <div className={styles.formGroup}>
              <label htmlFor={textareaId} className={styles.label}>
                Remarks <span className={styles.required}>*</span>
              </label>
              <textarea
                id={textareaId}
                className={`${styles.textarea} ${showLengthError ? styles.textareaError : ''}`}
                rows={4}
                placeholder={
                  action === 'reopen'
                    ? `Provide a specific reason for reopening (minimum ${MIN_REMARKS_LENGTH} characters after trimming — whitespace padding does not count)...`
                    : action === 'reject'
                    ? `Provide a specific reason for rejection (minimum ${MIN_REMARKS_LENGTH} characters after trimming — whitespace padding does not count)...`
                    : `Provide a specific reason for correction (minimum ${MIN_REMARKS_LENGTH} characters after trimming — whitespace padding does not count)...`
                }
                value={remarks}
                onChange={(e) => onRemarksChange(e.target.value)}
                disabled={isSubmitting}
                required
                aria-describedby={`${textareaId}-hint`}
              />
              <div id={`${textareaId}-hint`} className={styles.charRow}>
                <span className={showLengthError ? styles.charCountError : styles.charCount}>
                  {trimmedLength} / {MIN_REMARKS_LENGTH} characters minimum (trimmed)
                </span>
                {showLengthError && (
                  <span className={styles.charCountError}>
                    Need {MIN_REMARKS_LENGTH - trimmedLength} more
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ── Footer ── */}
          <div className={styles.footer}>
            <Button
              type="button"
              variant="ghost"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={isSubmitting || !isValid}
            >
              {submitLabel}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

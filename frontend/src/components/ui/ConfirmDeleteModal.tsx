import React, { useEffect } from 'react';
import { Button } from './Button';
import styles from './ConfirmDeleteModal.module.css';

export interface ConfirmDeleteModalProps {
  isOpen: boolean;
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  isDeleting?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Delete Permanently',
  cancelLabel = 'Cancel',
  isDeleting = false,
  onConfirm,
  onCancel,
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isDeleting) {
        onCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isDeleting, onCancel]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={styles.modalOverlay}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-delete-title"
      data-testid="confirm-delete-modal"
    >
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <div className={styles.titleArea}>
            <div className={styles.warningIcon} aria-hidden="true">
              !
            </div>
            <h3 id="confirm-delete-title" className={styles.modalTitle}>
              {title}
            </h3>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onCancel}
            disabled={isDeleting}
            aria-label="Close modal"
          >
            &times;
          </button>
        </div>

        <div className={styles.modalBody}>
          <div>{message}</div>
          <div className={styles.warningNotice}>
            <span>⚠️</span>
            <span>
              <strong>Irreversible Action:</strong> This item and any cascading references will be permanently removed.
            </span>
          </div>
        </div>

        <div className={styles.modalFooter}>
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isDeleting}
            data-testid="cancel-delete-btn"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirm}
            isLoading={isDeleting}
            data-testid="confirm-delete-btn"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
};

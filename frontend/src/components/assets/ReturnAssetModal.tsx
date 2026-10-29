import React, { useState } from 'react';
import {
  returnAssetApi,
  type AssetConditionType,
  type AssetResponse,
  type AssetStatusType,
} from '../../api/assets';
import { Button } from '../ui/Button';
import styles from './AssetModals.module.css';

interface ReturnAssetModalProps {
  isOpen: boolean;
  asset: AssetResponse | null;
  onClose: () => void;
  onSuccess: (updatedAsset: AssetResponse) => void;
}

export const ReturnAssetModal: React.FC<ReturnAssetModalProps> = ({
  isOpen,
  asset,
  onClose,
  onSuccess,
}) => {
  const [condition, setCondition] = useState<AssetConditionType>('good');
  const [statusOverride, setStatusOverride] = useState<string>('');
  const [remarks, setRemarks] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !asset) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!asset.current_custodian_id) {
      setErrorMessage('Asset does not have a recorded custodian.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = {
        employee_id: asset.current_custodian_id,
        condition,
        status: statusOverride ? (statusOverride as Exclude<AssetStatusType, 'issued_employee'>) : null,
        remarks: remarks.trim() ? remarks.trim() : null,
        idempotency_key: `return-${asset.id}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      };

      const res = await returnAssetApi(asset.id, payload);
      onSuccess(res);
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to return asset';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="return-title">
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3 id="return-title">Return Issued Asset</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {errorMessage && <div className={styles.alertError}>{errorMessage}</div>}

        <div className={styles.assetSummaryBadge}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Asset Tag</span>
            <span className={styles.summaryValue}>{asset.asset_tag}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Asset Name</span>
            <span className={styles.summaryValue}>{asset.name}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Recorded Custodian</span>
            <span className={styles.summaryValue}>{asset.current_custodian_name || 'Assigned Custodian'}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Returning to Site</span>
            <span className={styles.summaryValue}>{asset.current_site_name || 'Original Assigned Site'}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.formGrid}>
          {/* Condition Assessment */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="return-condition">
              Condition Assessment Upon Return <span className={styles.required}>*</span>
            </label>
            <select
              id="return-condition"
              className={styles.select}
              value={condition}
              onChange={(e) => setCondition(e.target.value as AssetConditionType)}
            >
              <option value="good">Good (Normal wear)</option>
              <option value="new">New (Like new)</option>
              <option value="fair">Fair (Minor wear, fully functional)</option>
              <option value="damaged">Damaged (Requires repair / inspection)</option>
              <option value="unusable">Unusable (Severely broken / scrap)</option>
            </select>
            <span className={styles.helpText}>
              Note: Assessing as &quot;Damaged&quot; or &quot;Unusable&quot; automatically updates operational status to &quot;Damaged&quot;.
            </span>
          </div>

          {/* Optional Status Override */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="return-status">
              Target Status (Optional)
            </label>
            <select
              id="return-status"
              className={styles.select}
              value={statusOverride}
              onChange={(e) => setStatusOverride(e.target.value)}
            >
              <option value="">Auto (Available if sound, Damaged if broken)</option>
              <option value="available">Available</option>
              <option value="under_maintenance">Under Maintenance</option>
              <option value="damaged">Damaged</option>
              <option value="lost">Lost</option>
              <option value="retired">Retired</option>
            </select>
          </div>

          {/* Remarks */}
          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="return-remarks">
              Inspection Notes / Remarks
            </label>
            <textarea
              id="return-remarks"
              className={styles.textarea}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Returned after completing excavation work. Cleaned and checked..."
            />
          </div>

          <div className={`${styles.modalFooter} ${styles.fullWidth}`}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Processing Return...' : 'Confirm Return'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

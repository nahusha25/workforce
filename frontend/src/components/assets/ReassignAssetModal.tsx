import React, { useEffect, useState } from 'react';
import {
  getAssetDestinationSitesApi,
  getAssetSitesApi,
  reassignAssetApi,
  type AssetReassignRequest,
  type AssetResponse,
  type LocationType,
} from '../../api/assets';
import { getSitesApi, type SiteResponseData } from '../../api/masterData';
import { Button } from '../ui/Button';
import styles from './AssetModals.module.css';

interface ReassignAssetModalProps {
  isOpen: boolean;
  asset: AssetResponse | null;
  onClose: () => void;
  onSuccess: (updatedAsset: AssetResponse) => void;
}

export const ReassignAssetModal: React.FC<ReassignAssetModalProps> = ({
  isOpen,
  asset,
  onClose,
  onSuccess,
}) => {

  const [targetLocationType, setTargetLocationType] = useState<LocationType>('site');
  const [targetSiteId, setTargetSiteId] = useState('');
  const [remarks, setRemarks] = useState('');
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [loadingSites, setLoadingSites] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && asset) {
      setLoadingSites(true);
      setTargetSiteId('');
      setRemarks('');
      setErrorMessage(null);

      // Default target location: if currently warehouse, target site; otherwise site
      setTargetLocationType(asset.location_type === 'warehouse' ? 'site' : 'site');

      getAssetDestinationSitesApi(asset.id)
        .then((res) => {
          setSites(res.filter((s) => s.is_active));
        })
        .catch((err) => {
          // Fallback to getAssetSitesApi or getSitesApi for backward compatibility
          getAssetSitesApi()
            .then((res) => {
              setSites(res.filter((s) => s.is_active));
            })
            .catch(() => {
              getSitesApi()
                .then((res) => {
                  setSites(res.filter((s) => s.is_active));
                })
                .catch(() => {
                  console.error('Failed to load sites for reassignment', err);
                });
            });
        })
        .finally(() => {
          setLoadingSites(false);
        });
    }
  }, [isOpen, asset?.id]);

  if (!isOpen || !asset) return null;

  // Filter available destination sites (exclude current site)
  const availableSites = sites.filter((s) => s.id !== asset.current_site_id);

  const isIssued = asset.status === 'issued_employee';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isIssued) {
      setErrorMessage('Cannot reassign asset while issued to an employee. Return the asset first.');
      return;
    }

    if (targetLocationType === 'site' && !targetSiteId) {
      setErrorMessage('Please select a destination site.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload: AssetReassignRequest = {
        target_location_type: targetLocationType,
        target_site_id: targetLocationType === 'site' ? targetSiteId : null,
        remarks: remarks.trim() ? remarks.trim() : null,
        idempotency_key: `reassign-${asset.id}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      };

      const res = await reassignAssetApi(asset.id, payload);
      onSuccess(res);
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to reassign asset';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="reassign-title">
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3 id="reassign-title">Reassign Asset Location</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {errorMessage && <div className={styles.alertError}>{errorMessage}</div>}

        {isIssued && (
          <div className={styles.alertError}>
            <strong>Cannot Reassign:</strong> This asset is currently issued to an employee. It must be returned to the site inventory before reassignment.
          </div>
        )}

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
            <span className={styles.summaryLabel}>Current Location</span>
            <span className={styles.summaryValue}>
              {asset.location_type === 'warehouse'
                ? 'Central Warehouse'
                : asset.current_site_name || 'Assigned Site'}
            </span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Current Status</span>
            <span className={styles.summaryValue} style={{ textTransform: 'capitalize' }}>
              {asset.status.replace('_', ' ')}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.formGrid}>
          {/* Target Location Type */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="reassign-location-type">
              Destination Location Type <span className={styles.required}>*</span>
            </label>
            <select
              id="reassign-location-type"
              className={styles.select}
              value={targetLocationType}
              onChange={(e) => setTargetLocationType(e.target.value as LocationType)}
              disabled={isIssued || isSubmitting}
            >
              <option value="site">Project Site</option>
              <option value="warehouse" disabled={asset.location_type === 'warehouse'}>
                Central Warehouse {asset.location_type === 'warehouse' ? '(Already here)' : ''}
              </option>
            </select>
          </div>

          {/* Destination Site Dropdown (only if target is site) */}
          {targetLocationType === 'site' && (
            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="reassign-target-site">
                Destination Site <span className={styles.required}>*</span>
              </label>
              <select
                id="reassign-target-site"
                className={styles.select}
                value={targetSiteId}
                onChange={(e) => setTargetSiteId(e.target.value)}
                disabled={isIssued || loadingSites || isSubmitting}
                required
              >
                <option value="">-- Choose destination site --</option>
                {availableSites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Remarks */}
          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="reassign-remarks">
              Reassignment Rationale / Remarks
            </label>
            <textarea
              id="reassign-remarks"
              className={styles.textarea}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Relocated for piling phase kickoff at Site Gamma..."
              disabled={isIssued || isSubmitting}
            />
          </div>

          <div className={`${styles.modalFooter} ${styles.fullWidth}`}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={
                isIssued ||
                isSubmitting ||
                (targetLocationType === 'site' && !targetSiteId)
              }
            >
              {isSubmitting ? 'Reassigning...' : 'Confirm Reassignment'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

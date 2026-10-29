import React, { useState } from 'react';
import { X, ArrowDownRight, CheckCircle2 } from 'lucide-react';
import type { AxiosError } from 'axios';
import { recordStockInwardApi, type StockInwardResponse } from '../../api/inventory';
import type { CatalogueMaterial } from '../../api/dailyWork';
import type { SiteResponseData } from '../../api/masterData';
import { Button } from '../ui/Button';
import { ErrorMessage } from '../ui/ErrorMessage';
import { normalizeError } from '../../api/client';
import styles from './StockInwardModal.module.css';

export interface StockInwardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (res: StockInwardResponse) => void;
  sites: SiteResponseData[];
  selectedSiteId: string;
  catalogueMaterials: CatalogueMaterial[];
}

export const StockInwardModal: React.FC<StockInwardModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  sites,
  selectedSiteId,
  catalogueMaterials,
}) => {
  const [siteId, setSiteId] = useState<string>(selectedSiteId);
  const [materialId, setMaterialId] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('1.00');
  const [remarks, setRemarks] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<StockInwardResponse | null>(null);

  if (!isOpen) return null;

  const activeMaterials = catalogueMaterials.filter((m) => m.is_active);
  const selectedMaterial = activeMaterials.find((m) => m.id === materialId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const targetSite = siteId || selectedSiteId;
    if (!targetSite) {
      setErrorMsg('Please select a site.');
      return;
    }
    if (!materialId) {
      setErrorMsg('Please select a material.');
      return;
    }

    const numQty = parseFloat(quantity);
    if (isNaN(numQty) || numQty <= 0) {
      setErrorMsg('Quantity must be a positive number greater than 0.');
      return;
    }

    setSubmitting(true);
    try {
      const idempotencyKey = `INW-${crypto.randomUUID()}`;
      const res = await recordStockInwardApi({
        site_id: targetSite,
        material_id: materialId,
        quantity: numQty,
        idempotency_key: idempotencyKey,
        remarks: remarks.trim() || undefined,
      });

      setSuccessResult(res);
      onSuccess(res);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to record stock inward.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setSuccessResult(null);
    setErrorMsg(null);
    setMaterialId('');
    setQuantity('1.00');
    setRemarks('');
    onClose();
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="inward-modal-title">
      <div className={styles.modalCard}>
        <div className={styles.modalHeader}>
          <h2 id="inward-modal-title" className={styles.modalTitle}>
            <ArrowDownRight size={20} color="#059669" />
            Stock Inward
          </h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {successResult ? (
          <div>
            <div className={styles.successBanner} role="status">
              <div className={styles.successTitle}>
                <CheckCircle2 size={20} color="#059669" />
                Stock Received Successfully
              </div>
              <div className={styles.successText}>
                Added <strong>{Number(successResult.quantity).toFixed(2)} {successResult.unit_of_measure}</strong> of{' '}
                <strong>{successResult.material_name}</strong> to site inventory.
              </div>
              <div className={styles.successText}>
                New available balance: <strong>{Number(successResult.balance_after).toFixed(2)} {successResult.unit_of_measure}</strong>
              </div>
            </div>
            <div className={styles.modalFooter}>
              <Button variant="primary" onClick={handleClose}>
                Done
              </Button>
            </div>
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            {errorMsg && <ErrorMessage message={errorMsg} />}

            {/* Site Selector */}
            <div className={styles.field}>
              <label htmlFor="inward-site" className={styles.label}>
                Destination Site *
              </label>
              <select
                id="inward-site"
                className={styles.select}
                value={siteId || selectedSiteId}
                onChange={(e) => setSiteId(e.target.value)}
                disabled={submitting}
                required
              >
                <option value="">-- Select Destination Site --</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Material Selector */}
            <div className={styles.field}>
              <label htmlFor="inward-material" className={styles.label}>
                Catalogue Material *
              </label>
              <select
                id="inward-material"
                className={styles.select}
                value={materialId}
                onChange={(e) => setMaterialId(e.target.value)}
                disabled={submitting}
                required
              >
                <option value="">-- Select Catalogue Material --</option>
                {activeMaterials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.unit_of_measure}) - {m.category}
                  </option>
                ))}
              </select>
            </div>

            {/* Quantity */}
            <div className={styles.field}>
              <label htmlFor="inward-quantity" className={styles.label}>
                Quantity Received{selectedMaterial ? ` (${selectedMaterial.unit_of_measure})` : ''} *
              </label>
              <input
                id="inward-quantity"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="e.g. 10.00"
                className={styles.input}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                disabled={submitting}
                required
              />
            </div>

            {/* Remarks */}
            <div className={styles.field}>
              <label htmlFor="inward-remarks" className={styles.label}>
                Remarks / Delivery Reference
              </label>
              <input
                id="inward-remarks"
                type="text"
                maxLength={500}
                placeholder="e.g. Supplier invoice #1042 or delivery challan"
                className={styles.input}
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div className={styles.modalFooter}>
              <Button type="button" variant="secondary" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={submitting}>
                Record Inward
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

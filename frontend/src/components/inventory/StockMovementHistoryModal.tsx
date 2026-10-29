import React, { useEffect, useState } from 'react';
import { X, History, Loader2, AlertCircle } from 'lucide-react';
import type { AxiosError } from 'axios';
import {
  getMaterialStockMovementsApi,
  type StockMovementItem,
} from '../../api/inventory';
import { Button } from '../ui/Button';
import { ErrorMessage } from '../ui/ErrorMessage';
import { normalizeError } from '../../api/client';
import styles from './StockMovementHistoryModal.module.css';

export interface StockMovementHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  siteId: string;
  siteName: string;
  materialId: string;
  materialName: string;
  materialCode?: string | null;
  unitOfMeasure: string;
  availableQuantity: number;
}

export const StockMovementHistoryModal: React.FC<StockMovementHistoryModalProps> = ({
  isOpen,
  onClose,
  siteId,
  siteName,
  materialId,
  materialName,
  materialCode,
  unitOfMeasure,
  availableQuantity,
}) => {
  const [movements, setMovements] = useState<StockMovementItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !siteId || !materialId) return;

    let isMounted = true;
    const fetchMovements = async () => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const res = await getMaterialStockMovementsApi(siteId, materialId, { limit: 100 });
        if (isMounted) {
          setMovements(res.items);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const norm = normalizeError(err as AxiosError<any>);
          setErrorMsg(norm.message || 'Failed to load stock movements.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchMovements();
    return () => {
      isMounted = false;
    };
  }, [isOpen, siteId, materialId]);

  if (!isOpen) return null;

  const renderBadge = (type: string) => {
    switch (type) {
      case 'inward':
        return <span className={styles.typeBadgeInward}>Inward</span>;
      case 'consumed':
        return <span className={styles.typeBadgeConsumed}>Consumed</span>;
      case 'returned':
        return <span className={styles.typeBadgeReturned}>Returned</span>;
      default:
        return <span className={styles.typeBadgeOther}>{type}</span>;
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="movement-history-title">
      <div className={styles.modalCard}>
        <div className={styles.modalHeader}>
          <h2 id="movement-history-title" className={styles.modalTitle}>
            <History size={20} color="#2563eb" />
            Stock Movement History: {materialName}
          </h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className={styles.metaBar}>
          <div className={styles.metaItem}>
            Site: <strong>{siteName}</strong>
          </div>
          <div className={styles.metaItem}>
            Code: <strong>{materialCode || '—'}</strong>
          </div>
          <div className={styles.metaItem}>
            Available Stock: <strong>{Number(availableQuantity).toFixed(2)} {unitOfMeasure}</strong>
          </div>
        </div>

        <div className={styles.body}>
          {errorMsg && <ErrorMessage message={errorMsg} />}

          {loading ? (
            <div className={styles.loadingState}>
              <Loader2 size={24} className="animate-spin" />
              <span>Loading movement ledger...</span>
            </div>
          ) : movements.length === 0 ? (
            <div className={styles.emptyState}>
              <AlertCircle size={32} style={{ marginBottom: 8, opacity: 0.5 }} />
              <p>No stock movements recorded for this material at this site yet.</p>
            </div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Date & Time</th>
                    <th className={styles.th}>Type</th>
                    <th className={styles.th}>Quantity</th>
                    <th className={styles.th}>Balance After</th>
                    <th className={styles.th}>Actor</th>
                    <th className={styles.th}>Remarks / Ref</th>
                  </tr>
                </thead>
                <tbody>
                  {movements.map((m) => (
                    <tr key={m.movement_id} className={styles.tr}>
                      <td className={styles.td}>{formatDate(m.created_at)}</td>
                      <td className={styles.td}>{renderBadge(m.movement_type)}</td>
                      <td className={styles.td}>
                        {m.movement_type === 'consumed' ? '-' : '+'}
                        {Number(m.quantity).toFixed(2)} {unitOfMeasure}
                      </td>
                      <td className={styles.td}>
                        <strong>{Number(m.balance_after).toFixed(2)} {unitOfMeasure}</strong>
                      </td>
                      <td className={styles.td}>{m.actor_name || m.created_by.slice(0, 8)}</td>
                      <td className={styles.td}>{m.remarks || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className={styles.modalFooter}>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

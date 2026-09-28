import React, { useState, useEffect, useRef } from 'react';
import type { AxiosError } from 'axios';
import {
  Package,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  X,
  FileText,
  Upload,
  ShoppingBag,
  Wrench,
} from 'lucide-react';
import {
  getMaterialTransactions,
  createMaterialTransaction,
  deleteMaterialTransaction,
  type MaterialTransaction,
  type MaterialTransactionPayload,
} from '../api/dailyWork';
import { StatusBadge } from './ui/StatusBadge';
import { normalizeError } from '../api/client';
import { compressImage } from '../utils/imageCompression';
import styles from './MaterialTransactionEntry.module.css';

export interface MaterialTransactionEntryProps {
  dailyWorkEntryId: string | null;
  status: string; // 'draft' | 'correction_required' | 'submitted' | 'approved'
  initialMaterials?: MaterialTransaction[];
  onMaterialAdded?: (transaction: MaterialTransaction) => void;
  onMaterialDeleted?: (transactionId: string) => void;
  onMaterialsLoaded?: (materials: MaterialTransaction[]) => void;
}

export const formatDecimal = (val: number | string | null | undefined): string => {
  if (val === null || val === undefined || val === '') return '0.00';
  const num = Number(val);
  return isNaN(num) ? '0.00' : num.toFixed(2);
};

export const MaterialTransactionEntry: React.FC<MaterialTransactionEntryProps> = ({
  dailyWorkEntryId,
  status,
  initialMaterials,
  onMaterialAdded,
  onMaterialDeleted,
  onMaterialsLoaded,
}) => {
  const [materials, setMaterials] = useState<MaterialTransaction[]>(initialMaterials || []);
  const [loadingList, setLoadingList] = useState<boolean>(false);
  const [showAddForm, setShowAddForm] = useState<boolean>(false);

  // Form Fields
  const [transactionType, setTransactionType] = useState<'consumed' | 'purchased'>('consumed');
  const [itemName, setItemName] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('1.00');
  const [amount, setAmount] = useState<string>('0.00');
  const [billFile, setBillFile] = useState<File | null>(null);
  const [billPreview, setBillPreview] = useState<string | null>(null);

  // Action states
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const isEditable =
    Boolean(dailyWorkEntryId) && (status === 'draft' || status === 'correction_required');

  // Load materials whenever dailyWorkEntryId changes and initialMaterials wasn't provided
  useEffect(() => {
    if (!dailyWorkEntryId) {
      setMaterials([]);
      return;
    }

    if (initialMaterials && initialMaterials.length > 0) {
      setMaterials(initialMaterials);
      setLoadingList(false);
      return;
    }

    let isMounted = true;
    const fetchMaterials = async () => {
      setLoadingList(true);
      setErrorMsg(null);
      try {
        const data = await getMaterialTransactions(dailyWorkEntryId);
        if (isMounted) {
          setMaterials(data);
          onMaterialsLoaded?.(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const norm = normalizeError(err as AxiosError<any>);
          setErrorMsg(norm.message);
        }
      } finally {
        if (isMounted) {
          setLoadingList(false);
        }
      }
    };

    fetchMaterials();

    return () => {
      isMounted = false;
    };
  }, [dailyWorkEntryId, initialMaterials]);

  const handleBillSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    e.target.value = '';

    try {
      // Compress bill image client-side via native canvas utility
      const compressed = await compressImage(file, {
        maxWidth: 1920,
        maxHeight: 1080,
        quality: 0.8,
      });
      setBillFile(compressed);
      setBillPreview(URL.createObjectURL(compressed));
    } catch {
      setBillFile(file);
      setBillPreview(URL.createObjectURL(file));
    }
  };

  const handleRemoveBill = () => {
    setBillFile(null);
    if (billPreview) {
      URL.revokeObjectURL(billPreview);
      setBillPreview(null);
    }
  };

  const handleResetForm = () => {
    setItemName('');
    setQuantity('1.00');
    setAmount('0.00');
    setTransactionType('consumed');
    handleRemoveBill();
    setShowAddForm(false);
    setErrorMsg(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dailyWorkEntryId || !isEditable) return;

    const trimmedName = itemName.trim();
    if (!trimmedName) {
      setErrorMsg('Item name is required.');
      return;
    }

    const numQty = Number(quantity);
    if (isNaN(numQty) || numQty <= 0) {
      setErrorMsg('Quantity must be greater than zero.');
      return;
    }

    const numAmount = Number(amount);
    if (isNaN(numAmount) || numAmount < 0) {
      setErrorMsg('Amount must be a valid non-negative number.');
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);

    const payload: MaterialTransactionPayload = {
      transaction_type: transactionType,
      item_name: trimmedName,
      quantity: numQty,
      amount: numAmount,
      bill_file: billFile,
    };

    try {
      const newTx = await createMaterialTransaction(dailyWorkEntryId, payload);
      setMaterials((prev) => (prev.some((m) => m.id === newTx.id) ? prev : [...prev, newTx]));
      setLoadingList(false);
      onMaterialAdded?.(newTx);
      handleResetForm();
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to record material transaction.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (transactionId: string) => {
    if (!isEditable || deletingId) return;

    setDeletingId(transactionId);
    setErrorMsg(null);

    try {
      await deleteMaterialTransaction(transactionId);
      setMaterials((prev) => prev.filter((m) => m.id !== transactionId));
      onMaterialDeleted?.(transactionId);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to delete material transaction.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className={styles.materialSection}>
      <div className={styles.headerRow}>
        <h4 className={styles.sectionTitle}>
          <Package size={18} />
          Material Transactions
          <span className={styles.countBadge}>{materials.length}</span>
        </h4>

        {isEditable && (
          <button
            type="button"
            className={styles.toggleFormBtn}
            onClick={() => setShowAddForm((prev) => !prev)}
            aria-label={showAddForm ? 'Cancel adding material' : 'Add Material'}
          >
            {showAddForm ? (
              <>
                <X size={15} />
                Cancel
              </>
            ) : (
              <>
                <Plus size={15} />
                Add Material
              </>
            )}
          </button>
        )}
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div className={styles.errorBanner} role="alert">
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Inline Entry Form */}
      {isEditable && showAddForm && (
        <form onSubmit={handleSubmit} className={styles.formCard} data-testid="material-form">
          {/* Type Toggle */}
          <div className={styles.typeToggleGroup}>
            <button
              type="button"
              className={`${styles.typeBtn} ${transactionType === 'consumed' ? styles.active : ''}`}
              onClick={() => {
                setTransactionType('consumed');
                handleRemoveBill();
              }}
              aria-label="Consumed Material"
            >
              <Wrench size={16} />
              Consumed on Site
            </button>
            <button
              type="button"
              className={`${styles.typeBtn} ${transactionType === 'purchased' ? styles.active : ''}`}
              onClick={() => setTransactionType('purchased')}
              aria-label="Purchased Material"
            >
              <ShoppingBag size={16} />
              Purchased Locally
            </button>
          </div>

          <div className={styles.inputsRow}>
            {/* Free-text Item Name */}
            <div className={styles.inputField}>
              <label htmlFor="material-item-name">Item Name *</label>
              <input
                id="material-item-name"
                type="text"
                placeholder="e.g. Cat6 Cable Box, RJ45 Connectors..."
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                disabled={submitting}
                required
              />
            </div>

            {/* Quantity */}
            <div className={styles.inputField}>
              <label htmlFor="material-quantity">Quantity *</label>
              <input
                id="material-quantity"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="1.00"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                disabled={submitting}
                required
              />
            </div>

            {/* Amount */}
            <div className={styles.inputField}>
              <label htmlFor="material-amount">Amount (Cost)</label>
              <input
                id="material-amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>

          {/* Optional Bill Upload for Purchased Items */}
          {transactionType === 'purchased' && (
            <div className={styles.billUploadRow}>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                aria-label="Attach bill receipt photo"
                className={styles.hiddenInput}
                onChange={handleBillSelect}
                disabled={submitting}
              />

              {!billPreview ? (
                <button
                  type="button"
                  className={styles.billUploadBtn}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={submitting}
                >
                  <Upload size={14} />
                  Attach Bill / Receipt Photo (Optional)
                </button>
              ) : (
                <div className={styles.billPreviewContainer}>
                  <img src={billPreview} alt="Receipt Preview" className={styles.billThumb} />
                  <span>{billFile?.name || 'Receipt photo attached'}</span>
                  <button
                    type="button"
                    className={styles.removeBillBtn}
                    onClick={handleRemoveBill}
                    aria-label="Remove bill attachment"
                    title="Remove bill"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}
            </div>
          )}

          <div className={styles.formActions}>
            <button
              type="button"
              className={styles.cancelBtn}
              onClick={handleResetForm}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={submitting || !itemName.trim()}
              aria-label="Record Material"
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Plus size={16} />
                  Record Material
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* When no entry draft exists yet */}
      {!dailyWorkEntryId && (
        <div className={styles.hintBanner}>
          Save a work entry draft before logging material usage or purchases.
        </div>
      )}

      {/* Loading state for materials */}
      {loadingList && (
        <div className={styles.hintBanner} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <Loader2 size={16} className="animate-spin" />
          Loading material transactions...
        </div>
      )}

      {/* Empty State */}
      {!loadingList && dailyWorkEntryId && materials.length === 0 && !showAddForm && (
        <div className={styles.hintBanner}>
          No materials recorded for today yet. Tap &ldquo;Add Material&rdquo; to record items.
        </div>
      )}

      {/* Material List */}
      {!loadingList && materials.length > 0 && (
        <div className={styles.materialsList} data-testid="materials-list">
          {materials.map((tx) => (
            <div key={tx.id} className={styles.materialCard} data-testid={`material-item-${tx.id}`}>
              <div className={styles.materialInfo}>
                <div className={styles.materialTitleRow}>
                  <span className={styles.materialName}>{tx.item_name}</span>
                  <span
                    className={`${styles.typePill} ${
                      tx.transaction_type === 'purchased' ? styles.typePurchased : styles.typeConsumed
                    }`}
                  >
                    {tx.transaction_type}
                  </span>

                  {/* High Value Badge matching SupervisorAttendancePage pattern */}
                  {tx.is_high_value && (
                    <StatusBadge status="flagged" label="High Value" />
                  )}
                </div>

                <div className={styles.materialMetaRow}>
                  <span className={styles.metaItem}>
                    Qty: <strong>{formatDecimal(tx.quantity)}</strong>
                  </span>
                  <span className={styles.metaItem}>
                    Amount: <strong>{formatDecimal(tx.amount)}</strong>
                  </span>

                  {tx.bill_image_url && (
                    <a
                      href={tx.bill_image_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.billLink}
                      title="View Bill Receipt"
                    >
                      <FileText size={14} />
                      Receipt
                    </a>
                  )}
                </div>
              </div>

              {isEditable && (
                <button
                  type="button"
                  className={styles.deleteBtn}
                  onClick={() => handleDelete(tx.id)}
                  disabled={deletingId === tx.id}
                  aria-label="Delete material"
                  title="Delete material"
                >
                  {deletingId === tx.id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

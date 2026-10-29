import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  getMaterialsCatalogue,
  type Activity,
  type CatalogueMaterial,
  type MaterialTransaction,
  type MaterialTransactionPayload,
} from '../api/dailyWork';
import { getMaterialStockAvailabilityApi } from '../api/inventory';
import { findMatchingCatalogueMaterial } from '../utils/materialMapping';
import { StatusBadge } from './ui/StatusBadge';
import { normalizeError } from '../api/client';
import { compressImage } from '../utils/imageCompression';
import styles from './MaterialTransactionEntry.module.css';

export interface MaterialTransactionEntryProps {
  dailyWorkEntryId: string | null;
  status: string; // 'draft' | 'correction_required' | 'submitted' | 'approved'
  siteId?: string;
  initialMaterials?: MaterialTransaction[];
  onMaterialAdded?: (transaction: MaterialTransaction) => void;
  onMaterialDeleted?: (transactionId: string) => void;
  onMaterialsLoaded?: (materials: MaterialTransaction[]) => void;
  activity?: Activity | null;
  measurementTotal?: number;
  catalogueMaterialsList?: CatalogueMaterial[];
}

export const formatDecimal = (val: number | string | null | undefined): string => {
  if (val === null || val === undefined || val === '') return '0.00';
  const num = Number(val);
  return isNaN(num) ? '0.00' : num.toFixed(2);
};

export const MaterialTransactionEntry: React.FC<MaterialTransactionEntryProps> = ({
  dailyWorkEntryId,
  status,
  siteId,
  initialMaterials,
  onMaterialAdded,
  onMaterialDeleted,
  onMaterialsLoaded,
  activity,
  measurementTotal = 0,
  catalogueMaterialsList,
}) => {
  const [materials, setMaterials] = useState<MaterialTransaction[]>(initialMaterials || []);
  const [loadingList, setLoadingList] = useState<boolean>(() =>
    Boolean(dailyWorkEntryId && initialMaterials === undefined)
  );
  const [retryTrigger, setRetryTrigger] = useState<number>(0);
  const fetchedEntryIdRef = useRef<string | null>(null);
  const onMaterialsLoadedRef = useRef(onMaterialsLoaded);

  useEffect(() => {
    onMaterialsLoadedRef.current = onMaterialsLoaded;
  }, [onMaterialsLoaded]);

  const [showAddForm, setShowAddForm] = useState<boolean>(false);

  // Default quantity derives from measurement total if positive, else 1.00
  const derivedDefaultQuantity = measurementTotal > 0 ? formatDecimal(measurementTotal) : '1.00';

  // Form Fields
  const [transactionType, setTransactionType] = useState<'consumed' | 'purchased'>('consumed');
  const [itemName, setItemName] = useState<string>('');
  const [quantity, setQuantity] = useState<string>(derivedDefaultQuantity);
  const [amount, setAmount] = useState<string>('0.00');
  const [billFile, setBillFile] = useState<File | null>(null);
  const [billPreview, setBillPreview] = useState<string | null>(null);

  // Catalogue Materials & Availability
  const [catalogueMaterials, setCatalogueMaterials] = useState<CatalogueMaterial[]>(
    catalogueMaterialsList || []
  );
  const [selectedMaterialId, setSelectedMaterialId] = useState<string>('');
  const [availableStock, setAvailableStock] = useState<number | null>(null);
  const [stockUom, setStockUom] = useState<string>('');
  const [loadingStock, setLoadingStock] = useState<boolean>(false);

  // Sync catalogue materials if passed as prop
  useEffect(() => {
    if (catalogueMaterialsList && catalogueMaterialsList.length > 0) {
      setCatalogueMaterials(catalogueMaterialsList);
    }
  }, [catalogueMaterialsList]);

  // Activity to catalogue material mapping
  const mappingResult = React.useMemo(
    () => findMatchingCatalogueMaterial(activity, catalogueMaterials),
    [activity, catalogueMaterials]
  );

  // When Add Material is opened or activity changes, auto-populate mapped material and measurement total
  useEffect(() => {
    if (showAddForm && transactionType === 'consumed') {
      if (measurementTotal > 0) {
        setQuantity(formatDecimal(measurementTotal));
      }
      if (!selectedMaterialId && mappingResult.material) {
        setSelectedMaterialId(mappingResult.material.id);
        setItemName(mappingResult.material.name);
      }
    }
  }, [showAddForm, transactionType, measurementTotal, selectedMaterialId, mappingResult.material]);

  // Keep quantity synchronized with measurementTotal when form is open for consumed material
  useEffect(() => {
    if (showAddForm && transactionType === 'consumed' && measurementTotal > 0) {
      setQuantity(formatDecimal(measurementTotal));
    }
  }, [measurementTotal, showAddForm, transactionType]);

  // Sync materials when parent updates initialMaterials
  useEffect(() => {
    if (initialMaterials !== undefined) {
      setMaterials(initialMaterials);
    }
  }, [initialMaterials]);

  const selectedCatalogueMaterial = catalogueMaterials.find((m) => m.id === selectedMaterialId);
  const selectedMaterialUom =
    transactionType === 'consumed' && selectedCatalogueMaterial
      ? selectedCatalogueMaterial.unit_of_measure
      : '';

  const getMaterialUom = (tx: MaterialTransaction): string => {
    if ((tx as any).unit_of_measure) return (tx as any).unit_of_measure;
    if ((tx as any).uom) return (tx as any).uom;
    if (tx.material_id) {
      const mat = catalogueMaterials.find((m) => m.id === tx.material_id);
      if (mat?.unit_of_measure) return mat.unit_of_measure;
    }
    if (tx.item_name) {
      const mat = catalogueMaterials.find(
        (m) => m.name.toLowerCase() === tx.item_name.toLowerCase()
      );
      if (mat?.unit_of_measure) return mat.unit_of_measure;
    }
    return '';
  };

  // Action states
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const isEditable =
    Boolean(dailyWorkEntryId) && (status === 'draft' || status === 'correction_required');

  // Load materials catalogue on mount
  useEffect(() => {
    let isMounted = true;
    const fetchCatalogue = async () => {
      try {
        const data = await getMaterialsCatalogue();
        if (isMounted) {
          setCatalogueMaterials(data);
        }
      } catch {
        // Fallback gracefully
      }
    };
    fetchCatalogue();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch available stock for selected catalogue material at site
  const fetchStock = useCallback(async (matId: string, site?: string) => {
    if (!matId || !site) {
      setAvailableStock(null);
      return;
    }
    setLoadingStock(true);
    try {
      const data = await getMaterialStockAvailabilityApi(site, matId);
      setAvailableStock(Number(data.quantity_available));
      setStockUom(data.unit_of_measure || '');
    } catch {
      // Graceful fallback if availability check fails or unauthorized
      setAvailableStock(null);
    } finally {
      setLoadingStock(false);
    }
  }, []);

  useEffect(() => {
    if (transactionType === 'consumed' && selectedMaterialId && siteId) {
      fetchStock(selectedMaterialId, siteId);
    } else {
      setAvailableStock(null);
    }
  }, [transactionType, selectedMaterialId, siteId, fetchStock]);


  // Load materials whenever dailyWorkEntryId changes or initialMaterials updates
  useEffect(() => {
    if (!dailyWorkEntryId) {
      setMaterials([]);
      setLoadingList(false);
      fetchedEntryIdRef.current = null;
      return;
    }

    // If initialMaterials is provided (including empty array []), sync it without fetching
    if (initialMaterials !== undefined) {
      setMaterials(initialMaterials);
      setLoadingList(false);
      fetchedEntryIdRef.current = dailyWorkEntryId;
      return;
    }

    // Only fetch if initialMaterials is undefined and we haven't fetched for this entry yet
    if (fetchedEntryIdRef.current === dailyWorkEntryId) {
      return;
    }

    let isMounted = true;
    fetchedEntryIdRef.current = dailyWorkEntryId;

    const fetchMaterials = async () => {
      setLoadingList(true);
      setErrorMsg(null);
      try {
        const data = await getMaterialTransactions(dailyWorkEntryId);
        if (isMounted) {
          setMaterials(data);
          onMaterialsLoadedRef.current?.(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const norm = normalizeError(err as AxiosError<any>);
          setErrorMsg(norm.message);
          fetchedEntryIdRef.current = null; // Allow retry on failure
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
  }, [dailyWorkEntryId, initialMaterials, retryTrigger]);

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
    setSelectedMaterialId('');
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

    if (transactionType === 'consumed' && !selectedMaterialId) {
      setErrorMsg('Please select a material from the catalogue.');
      return;
    }

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
      material_id: transactionType === 'consumed' && selectedMaterialId ? selectedMaterialId : undefined,
      bill_file: billFile,
    };

    try {
      const newTx = await createMaterialTransaction(dailyWorkEntryId, payload);
      setMaterials((prev) => (prev.some((m) => m.id === newTx.id) ? prev.map((m) => (m.id === newTx.id ? newTx : m)) : [...prev, newTx]));
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
            data-testid="add-material-btn"
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
          {initialMaterials === undefined && dailyWorkEntryId && (
            <button
              type="button"
              className={styles.retryBtn}
              onClick={() => {
                setErrorMsg(null);
                fetchedEntryIdRef.current = null;
                setRetryTrigger((c) => c + 1);
              }}
              style={{
                marginLeft: 'auto',
                marginRight: '8px',
                fontSize: '0.8rem',
                textDecoration: 'underline',
                background: 'none',
                border: 'none',
                color: 'inherit',
                cursor: 'pointer',
              }}
            >
              Retry
            </button>
          )}
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
                if (selectedMaterialId) {
                  const mat = catalogueMaterials.find((m) => m.id === selectedMaterialId);
                  if (mat) setItemName(mat.name);
                } else {
                  setItemName('');
                }
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

          {transactionType === 'consumed' && activity && (
            mappingResult.isMapped ? (
              <div className={styles.mappingNotice} data-testid="mapping-status-notice">
                <span>✓ Auto-linked to activity: {activity.name} ({formatDecimal(measurementTotal || 0)} {activity.unit_of_measure})</span>
              </div>
            ) : (
              <div className={styles.mappingNoticeWarning} data-testid="mapping-warning-notice">
                <span>⚠️ {mappingResult.reason}</span>
              </div>
            )
          )}

          <div className={styles.inputsRow}>
            {transactionType === 'consumed' ? (
              <div className={styles.inputField}>
                <label htmlFor="material-select">Catalogue Material *</label>
                <select
                  id="material-select"
                  aria-label="Catalogue Material"
                  value={selectedMaterialId}
                  onChange={(e) => {
                    const matId = e.target.value;
                    setSelectedMaterialId(matId);
                    const mat = catalogueMaterials.find((m) => m.id === matId);
                    if (mat) {
                      setItemName(mat.name);
                    } else {
                      setItemName('');
                    }
                  }}
                  disabled={submitting}
                  required
                >
                  <option value="">-- Select Material from Catalogue --</option>
                  {catalogueMaterials.map((mat) => (
                    <option key={mat.id} value={mat.id}>
                      {mat.name} ({mat.unit_of_measure})
                    </option>
                  ))}
                </select>
                {loadingStock && <span className={styles.stockAvailableBadge}>Checking stock...</span>}
                {!loadingStock && availableStock !== null && (
                  availableStock > 0 ? (
                    <span className={styles.stockAvailableBadge} aria-label="Available Stock">
                      Available: {formatDecimal(availableStock)} {stockUom || selectedMaterialUom}
                    </span>
                  ) : (
                    <span className={styles.stockZeroBadge} aria-label="Available Stock">
                      Available: 0.00 {stockUom || selectedMaterialUom}
                    </span>
                  )
                )}
              </div>
            ) : (
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
            )}

            {/* Quantity */}
            <div className={styles.inputField}>
              <label htmlFor="material-quantity">
                Quantity{selectedMaterialUom ? ` (${selectedMaterialUom})` : ''} *
              </label>
              <div className={styles.quantityInputRow}>
                <input
                  id="material-quantity"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="1.00"
                  className={styles.quantityInput}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  disabled={submitting}
                  required
                  data-testid="material-form-quantity"
                />
                {selectedMaterialUom && (
                  <span
                    className={styles.uomBadge}
                    title="Material Unit of Measure"
                    data-testid="material-uom-badge"
                  >
                    {selectedMaterialUom}
                  </span>
                )}
              </div>
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

          {/* Stock Warning */}
          {transactionType === 'consumed' && availableStock !== null && (
            (availableStock <= 0 || (parseFloat(quantity) || 0) > availableStock) && (
              <div className={styles.stockWarning} role="alert" aria-label="Stock Warning">
                <span className={styles.warningIcon}>⚠️</span>
                <span>
                  {availableStock <= 0
                    ? `Warning: Zero available stock for this material at site. Approval will be blocked unless stock is replenished.`
                    : `Warning: Entered quantity (${quantity}) exceeds available stock (${formatDecimal(availableStock)} ${stockUom || selectedMaterialUom}). Approval requires sufficient stock.`}
                </span>
              </div>
            )
          )}

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
              disabled={submitting || !itemName.trim() || (transactionType === 'consumed' && !selectedMaterialId)}
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
            <div key={tx.id} className={styles.materialCard} data-testid="material-tx-row" data-item-id={tx.id}>
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
                    Qty: <strong data-testid="material-tx-quantity">{formatDecimal(tx.quantity)}</strong>
                    {getMaterialUom(tx) ? (
                      <span className={styles.uomText} data-testid="material-tx-uom">
                        {' '}{getMaterialUom(tx)}
                      </span>
                    ) : null}
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

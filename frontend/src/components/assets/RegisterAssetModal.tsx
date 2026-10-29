import React, { useEffect, useState } from 'react';
import {
  getAssetSitesApi,
  registerAssetApi,
  type AssetConditionType,
  type AssetRegisterRequest,
  type AssetResponse,
  type AssetStatusType,
  type LocationType,
} from '../../api/assets';
import { getSitesApi, type SiteResponseData } from '../../api/masterData';
import { Button } from '../ui/Button';
import styles from './AssetModals.module.css';

interface RegisterAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newAsset: AssetResponse) => void;
}

export const RegisterAssetModal: React.FC<RegisterAssetModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [assetTag, setAssetTag] = useState('');
  const [locationType, setLocationType] = useState<LocationType>('warehouse');
  const [currentSiteId, setCurrentSiteId] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [modelNumber, setModelNumber] = useState('');
  const [condition, setCondition] = useState<AssetConditionType>('new');
  const [status, setStatus] = useState<Exclude<AssetStatusType, 'issued_employee'>>('available');
  const [purchaseDate, setPurchaseDate] = useState('');
  const [purchaseCost, setPurchaseCost] = useState('');
  const [warrantyExpiryDate, setWarrantyExpiryDate] = useState('');
  const [description, setDescription] = useState('');
  const [remarks, setRemarks] = useState('');

  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [loadingSites, setLoadingSites] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen) {
      setLoadingSites(true);
      getAssetSitesApi()
        .then((res) => {
          setSites(res.filter((s) => s.is_active));
        })
        .catch(() => {
          getSitesApi()
            .then((res) => {
              setSites(res.filter((s) => s.is_active));
            })
            .catch((err) => {
              console.error('Failed to load sites for asset registration', err);
            });
        })
        .finally(() => {
          setLoadingSites(false);
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!name.trim()) {
      errors.name = 'Asset display name is required.';
    }
    if (!category.trim()) {
      errors.category = 'Category is required.';
    }
    if (locationType === 'site' && !currentSiteId) {
      errors.currentSiteId = 'Please select an assigned site.';
    }
    if (purchaseCost && (isNaN(Number(purchaseCost)) || Number(purchaseCost) < 0)) {
      errors.purchaseCost = 'Purchase cost must be a non-negative number.';
    }
    if (purchaseDate && warrantyExpiryDate && warrantyExpiryDate < purchaseDate) {
      errors.warrantyExpiryDate = 'Warranty expiry cannot precede purchase date.';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: AssetRegisterRequest = {
        name: name.trim(),
        category: category.trim(),
        asset_tag: assetTag.trim() ? assetTag.trim() : null,
        location_type: locationType,
        current_site_id: locationType === 'site' ? currentSiteId : null,
        serial_number: serialNumber.trim() ? serialNumber.trim() : null,
        manufacturer: manufacturer.trim() ? manufacturer.trim() : null,
        model_number: modelNumber.trim() ? modelNumber.trim() : null,
        condition,
        status,
        purchase_date: purchaseDate || null,
        purchase_cost: purchaseCost ? Number(purchaseCost) : null,
        warranty_expiry_date: warrantyExpiryDate || null,
        description: description.trim() ? description.trim() : null,
        remarks: remarks.trim() ? remarks.trim() : null,
        idempotency_key: `reg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      };

      const res = await registerAssetApi(payload);
      onSuccess(res);
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to register asset';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="reg-title">
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3 id="reg-title">Register New Asset</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {errorMessage && <div className={styles.alertError}>{errorMessage}</div>}

        <form onSubmit={handleSubmit} className={styles.formGrid} noValidate>
          {/* Asset Name */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-name">
              Asset Name <span className={styles.required}>*</span>
            </label>
            <input
              id="asset-name"
              className={styles.input}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Total Station TS16, 500L Concrete Mixer"
            />
            {validationErrors.name && <span className={styles.fieldError}>{validationErrors.name}</span>}
          </div>

          {/* Category */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-category">
              Category <span className={styles.required}>*</span>
            </label>
            <input
              id="asset-category"
              className={styles.input}
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. survey_tools, heavy_machinery, power_tools"
            />
            {validationErrors.category && <span className={styles.fieldError}>{validationErrors.category}</span>}
          </div>

          {/* Asset Tag (Optional) */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-tag">
              Asset Tag / Barcode
            </label>
            <input
              id="asset-tag"
              className={styles.input}
              type="text"
              value={assetTag}
              onChange={(e) => setAssetTag(e.target.value)}
              placeholder="Leave blank for automatic tag (e.g. AST-000001)"
            />
            <span className={styles.helpText}>Leave blank to auto-generate from the system sequence.</span>
          </div>

          {/* Location Assignment */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-location-type">
              Initial Location <span className={styles.required}>*</span>
            </label>
            <select
              id="asset-location-type"
              className={styles.select}
              value={locationType}
              onChange={(e) => setLocationType(e.target.value as LocationType)}
            >
              <option value="warehouse">Central Warehouse</option>
              <option value="site">Assigned to Specific Site</option>
            </select>
          </div>

          {/* Assigned Site Dropdown (only if location is site) */}
          {locationType === 'site' && (
            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="asset-site-id">
                Select Site <span className={styles.required}>*</span>
              </label>
              <select
                id="asset-site-id"
                className={styles.select}
                value={currentSiteId}
                onChange={(e) => setCurrentSiteId(e.target.value)}
                disabled={loadingSites}
              >
                <option value="">-- Choose active site --</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              {validationErrors.currentSiteId && (
                <span className={styles.fieldError}>{validationErrors.currentSiteId}</span>
              )}
            </div>
          )}

          {/* Condition */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-condition">
              Physical Condition
            </label>
            <select
              id="asset-condition"
              className={styles.select}
              value={condition}
              onChange={(e) => setCondition(e.target.value as AssetConditionType)}
            >
              <option value="new">New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="damaged">Damaged</option>
              <option value="unusable">Unusable</option>
            </select>
          </div>

          {/* Operational Status (Excludes issued_employee) */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-status">
              Operational Status
            </label>
            <select
              id="asset-status"
              className={styles.select}
              value={status}
              onChange={(e) => setStatus(e.target.value as Exclude<AssetStatusType, 'issued_employee'>)}
            >
              <option value="available">Available</option>
              <option value="under_maintenance">Under Maintenance</option>
              <option value="damaged">Damaged</option>
              <option value="lost">Lost</option>
              <option value="retired">Retired</option>
            </select>
          </div>

          {/* Serial Number */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-serial">
              Serial Number
            </label>
            <input
              id="asset-serial"
              className={styles.input}
              type="text"
              value={serialNumber}
              onChange={(e) => setSerialNumber(e.target.value)}
              placeholder="e.g. SN-883921"
            />
          </div>

          {/* Manufacturer & Model */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-manufacturer">
              Manufacturer
            </label>
            <input
              id="asset-manufacturer"
              className={styles.input}
              type="text"
              value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
              placeholder="e.g. Leica, Caterpillar, Bosch"
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-model">
              Model Number
            </label>
            <input
              id="asset-model"
              className={styles.input}
              type="text"
              value={modelNumber}
              onChange={(e) => setModelNumber(e.target.value)}
              placeholder="e.g. TS16-R1000"
            />
          </div>

          {/* Purchase Details */}
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-purchase-date">
              Purchase Date
            </label>
            <input
              id="asset-purchase-date"
              className={styles.input}
              type="date"
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-cost">
              Purchase Cost (INR ₹)
            </label>
            <input
              id="asset-cost"
              className={styles.input}
              type="number"
              step="0.01"
              min="0"
              value={purchaseCost}
              onChange={(e) => setPurchaseCost(e.target.value)}
              placeholder="0.00"
            />
            {validationErrors.purchaseCost && (
              <span className={styles.fieldError}>{validationErrors.purchaseCost}</span>
            )}
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="asset-warranty">
              Warranty Expiry Date
            </label>
            <input
              id="asset-warranty"
              className={styles.input}
              type="date"
              value={warrantyExpiryDate}
              onChange={(e) => setWarrantyExpiryDate(e.target.value)}
            />
            {validationErrors.warrantyExpiryDate && (
              <span className={styles.fieldError}>{validationErrors.warrantyExpiryDate}</span>
            )}
          </div>

          {/* Description & Remarks */}
          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="asset-description">
              Specifications & Description
            </label>
            <textarea
              id="asset-description"
              className={styles.textarea}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional asset description, technical specifications, or maintenance notes..."
            />
          </div>

          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="asset-remarks">
              Registration Remarks
            </label>
            <input
              id="asset-remarks"
              className={styles.input}
              type="text"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Initial acquisition notes or CAPEX remarks..."
            />
          </div>

          <div className={`${styles.modalFooter} ${styles.fullWidth}`}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Registering...' : 'Register Asset'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

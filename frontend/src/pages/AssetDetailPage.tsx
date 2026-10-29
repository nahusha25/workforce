import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  getAssetApi,
  type AssetDetailResponse,
  type AssetResponse,
  type AssetTransactionResponse,
} from '../api/assets';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { IssueAssetModal } from '../components/assets/IssueAssetModal';
import { ReturnAssetModal } from '../components/assets/ReturnAssetModal';
import { ReassignAssetModal } from '../components/assets/ReassignAssetModal';
import styles from './AssetDetailPage.module.css';

const formatCurrencyINR = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || amount === '') return '-';
  const num = typeof amount === 'number' ? amount : parseFloat(amount);
  if (isNaN(num)) return '-';
  return `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const AssetDetailPage: React.FC = () => {
  const { assetId } = useParams<{ assetId: string }>();
  const navigate = useNavigate();

  const [asset, setAsset] = useState<AssetDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modals
  const [showIssueModal, setShowIssueModal] = useState<boolean>(false);
  const [showReturnModal, setShowReturnModal] = useState<boolean>(false);
  const [showReassignModal, setShowReassignModal] = useState<boolean>(false);

  const fetchAsset = useCallback(async () => {
    if (!assetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAssetApi(assetId);
      setAsset(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load asset details');
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    fetchAsset();
  }, [fetchAsset]);

  if (loading) {
    return <LoadingSpinner fullScreen label="Loading asset details..." />;
  }

  if (!asset) {
    return (
      <div className={styles.container}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate('/assets')}
          aria-label="Back to Assets"
        >
          &larr; Back to Assets
        </button>
        <ErrorMessage message={error || 'Asset not found or access restricted.'} />
      </div>
    );
  }

  // Action availability (accessible to administrators and supervisors alike)
  const canIssue =
    asset.location_type === 'site' &&
    asset.status === 'available' &&
    asset.is_active;

  const canReturn =
    asset.status === 'issued_employee' &&
    asset.is_active;

  const canReassign =
    asset.status !== 'issued_employee' &&
    asset.is_active;

  const handleActionSuccess = (_updated: AssetResponse, message: string) => {
    setSuccessMessage(message);
    fetchAsset();
    setTimeout(() => {
      setSuccessMessage(null);
    }, 6000);
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <span className={`${styles.statusBadge} ${styles.statusAvailable}`}>Available</span>;
      case 'issued_employee':
        return <span className={`${styles.statusBadge} ${styles.statusIssued}`}>Issued to Employee</span>;
      case 'under_maintenance':
        return <span className={`${styles.statusBadge} ${styles.statusMaintenance}`}>Under Maintenance</span>;
      case 'damaged':
        return <span className={`${styles.statusBadge} ${styles.statusDamaged}`}>Damaged</span>;
      case 'lost':
        return <span className={`${styles.statusBadge} ${styles.statusLost}`}>Lost</span>;
      case 'retired':
        return <span className={`${styles.statusBadge} ${styles.statusRetired}`}>Retired</span>;
      default:
        return <span className={styles.statusBadge}>{status}</span>;
    }
  };

  const renderConditionBadge = (condition: string) => {
    switch (condition) {
      case 'new':
        return <span className={`${styles.conditionBadge} ${styles.conditionNew}`}>New</span>;
      case 'good':
        return <span className={`${styles.conditionBadge} ${styles.conditionGood}`}>Good</span>;
      case 'fair':
        return <span className={`${styles.conditionBadge} ${styles.conditionFair}`}>Fair</span>;
      case 'damaged':
        return <span className={`${styles.conditionBadge} ${styles.conditionDamaged}`}>Damaged</span>;
      case 'unusable':
        return <span className={`${styles.conditionBadge} ${styles.conditionUnusable}`}>Unusable</span>;
      default:
        return <span className={styles.conditionBadge}>{condition}</span>;
    }
  };

  const renderTxBadge = (txType: string) => {
    switch (txType.toLowerCase()) {
      case 'register':
        return <span className={`${styles.txBadge} ${styles.txRegister}`}>Registered</span>;
      case 'issue':
        return <span className={`${styles.txBadge} ${styles.txIssue}`}>Issued</span>;
      case 'return':
        return <span className={`${styles.txBadge} ${styles.txReturn}`}>Returned</span>;
      case 'reassign':
        return <span className={`${styles.txBadge} ${styles.txReassign}`}>Reassigned</span>;
      default:
        return <span className={`${styles.txBadge} ${styles.txOther}`}>{txType}</span>;
    }
  };

  return (
    <div className={styles.container}>
      <button
        type="button"
        className={styles.backBtn}
        onClick={() => navigate('/assets')}
        aria-label="Back to Assets"
      >
        &larr; Back to Assets
      </button>

      {/* Header Row */}
      <div className={styles.headerRow}>
        <div className={styles.headerLeft}>
          <div className={styles.titleWithBadge}>
            <h1 className={styles.title}>{asset.name}</h1>
            <span className={styles.tagPill}>{asset.asset_tag}</span>
            {renderStatusBadge(asset.status)}
            {renderConditionBadge(asset.condition)}
          </div>
          <p className={styles.categorySubtitle}>
            Category: <strong>{asset.category}</strong>
            {asset.serial_number && (
              <> &bull; Serial: <code>{asset.serial_number}</code></>
            )}
          </p>
        </div>

        <div className={styles.headerActions}>
          {canIssue && (
            <Button
              variant="primary"
              onClick={() => setShowIssueModal(true)}
              data-testid="detail-issue-btn"
            >
              Issue Asset
            </Button>
          )}

          {canReturn && (
            <Button
              variant="secondary"
              onClick={() => setShowReturnModal(true)}
              data-testid="detail-return-btn"
            >
              Return Asset
            </Button>
          )}

          {canReassign && (
            <Button
              variant="outline"
              onClick={() => setShowReassignModal(true)}
              data-testid="detail-reassign-btn"
            >
              Reassign Location
            </Button>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div className={styles.successAlert}>
          <span>{successMessage}</span>
          <Button variant="ghost" size="sm" onClick={() => setSuccessMessage(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Error Message */}
      {error && <ErrorMessage message={error} />}

      {/* Current Location & Custody Card */}
      <Card>
        <h2 className={styles.cardSectionTitle}>Current Location & Custody</h2>
        <div className={styles.metaGrid}>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Location Type</span>
            <span className={styles.metaValue}>
              {asset.location_type === 'warehouse' ? (
                <span className={`${styles.locationBadge} ${styles.locationWarehouse}`}>
                  Central Warehouse
                </span>
              ) : (
                <span className={`${styles.locationBadge} ${styles.locationSite}`}>
                  Assigned Site
                </span>
              )}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Assigned Site</span>
            <span className={styles.metaValueStrong}>
              {asset.location_type === 'site'
                ? asset.current_site_name || asset.current_site_id || 'Unknown Site'
                : 'Central Warehouse (No Site Assigned)'}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Current Custodian</span>
            <span className={styles.metaValueStrong}>
              {asset.current_custodian_name ? (
                <span style={{ color: '#7e22ce' }}>
                  {asset.current_custodian_name}
                </span>
              ) : (
                <span style={{ color: '#64748b' }}>None (In Stock)</span>
              )}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Operating Status</span>
            <span className={styles.metaValue}>
              {asset.is_active ? 'Active Inventory' : 'Archived / Deactivated'}
            </span>
          </div>
        </div>
      </Card>

      {/* Specifications Card */}
      <Card>
        <h2 className={styles.cardSectionTitle}>Specifications & Identification</h2>
        <div className={styles.metaGrid}>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Asset Tag</span>
            <span className={styles.metaValue}><code>{asset.asset_tag}</code></span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Serial Number</span>
            <span className={styles.metaValue}>{asset.serial_number || '-'}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Manufacturer</span>
            <span className={styles.metaValue}>{asset.manufacturer || '-'}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Model Number</span>
            <span className={styles.metaValue}>{asset.model_number || '-'}</span>
          </div>

          <div className={styles.metaField} style={{ gridColumn: '1 / -1' }}>
            <span className={styles.metaLabel}>Description</span>
            <span className={styles.metaValue}>{asset.description || 'No description provided.'}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Created On</span>
            <span className={styles.metaValue}>
              {new Date(asset.created_at).toLocaleString()}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Last Updated</span>
            <span className={styles.metaValue}>
              {new Date(asset.updated_at).toLocaleString()}
            </span>
          </div>
        </div>
      </Card>

      {/* Financial & Warranty Details */}
      <Card>
        <h2 className={styles.cardSectionTitle}>Purchase & Warranty Information</h2>
        <div className={styles.metaGrid}>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Purchase Cost</span>
            <span className={styles.metaValueStrong}>
              {formatCurrencyINR(asset.purchase_cost)}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Purchase Date</span>
            <span className={styles.metaValue}>{asset.purchase_date || '-'}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Warranty Expiry Date</span>
            <span className={styles.metaValue}>
              {asset.warranty_expiry_date ? (
                <span>
                  {asset.warranty_expiry_date}
                  {new Date(asset.warranty_expiry_date) < new Date() && (
                    <span style={{ color: '#b91c1c', marginLeft: '6px', fontSize: '0.8rem', fontWeight: 600 }}>
                      (Expired)
                    </span>
                  )}
                </span>
              ) : (
                '-'
              )}
            </span>
          </div>
        </div>
      </Card>

      {/* Chronological Transaction History */}
      <Card>
        <div className={styles.cardSectionTitle}>
          <span>Transaction History & Audit Ledger</span>
          <span style={{ fontSize: '0.875rem', fontWeight: 400, color: 'var(--color-neutral-500)' }}>
            {(asset.transactions || []).length} recorded action(s)
          </span>
        </div>

        {(!asset.transactions || asset.transactions.length === 0) ? (
          <div className={styles.emptyTransactions}>
            No transaction records found for this asset.
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable} data-testid="transactions-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Movement (From &rarr; To)</th>
                  <th>Custody (From &rarr; To)</th>
                  <th>Condition</th>
                  <th>Performed By</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {asset.transactions.map((tx: AssetTransactionResponse) => {
                  const fromLoc = tx.from_site_name
                    ? tx.from_site_name
                    : tx.from_location_type === 'warehouse'
                    ? 'Central Warehouse'
                    : tx.from_location_type || '-';

                  const toLoc = tx.to_site_name
                    ? tx.to_site_name
                    : tx.to_location_type === 'warehouse'
                    ? 'Central Warehouse'
                    : tx.to_location_type || '-';

                  const fromEmp = tx.from_employee_name || '-';
                  const toEmp = tx.to_employee_name || '-';

                  return (
                    <tr key={tx.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        {new Date(tx.created_at || tx.transaction_date).toLocaleString()}
                      </td>
                      <td>{renderTxBadge(tx.transaction_type)}</td>
                      <td>
                        {fromLoc === '-' && toLoc === '-' ? (
                          '-'
                        ) : (
                          <span>
                            {fromLoc} &rarr; <strong>{toLoc}</strong>
                          </span>
                        )}
                      </td>
                      <td>
                        {fromEmp === '-' && toEmp === '-' ? (
                          '-'
                        ) : (
                          <span>
                            {fromEmp} &rarr; <strong>{toEmp}</strong>
                          </span>
                        )}
                      </td>
                      <td>
                        {tx.condition_before || tx.condition_after ? (
                          <span>
                            {tx.condition_before || '-'} &rarr; <strong>{tx.condition_after || '-'}</strong>
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>{tx.performed_by || '-'}</td>
                      <td>{tx.remarks || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Action Modals */}
      <IssueAssetModal
        isOpen={showIssueModal}
        asset={asset}
        onClose={() => setShowIssueModal(false)}
        onSuccess={(updated) => {
          setShowIssueModal(false);
          handleActionSuccess(updated, `Asset ${asset.asset_tag} successfully issued.`);
        }}
      />

      <ReturnAssetModal
        isOpen={showReturnModal}
        asset={asset}
        onClose={() => setShowReturnModal(false)}
        onSuccess={(updated) => {
          setShowReturnModal(false);
          handleActionSuccess(updated, `Asset ${asset.asset_tag} successfully returned.`);
        }}
      />

      <ReassignAssetModal
        isOpen={showReassignModal}
        asset={asset}
        onClose={() => setShowReassignModal(false)}
        onSuccess={(updated) => {
          setShowReassignModal(false);
          handleActionSuccess(updated, `Asset ${asset.asset_tag} location reassigned.`);
        }}
      />
    </div>
  );
};

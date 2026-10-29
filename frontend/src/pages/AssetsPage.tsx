import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  getAssetSitesApi,
  listAssetsApi,
  type AssetResponse,
  type LocationType,
} from '../api/assets';
import { getSitesApi, type SiteResponseData } from '../api/masterData';
import { IssueAssetModal } from '../components/assets/IssueAssetModal';
import { ReassignAssetModal } from '../components/assets/ReassignAssetModal';
import { RegisterAssetModal } from '../components/assets/RegisterAssetModal';
import { ReturnAssetModal } from '../components/assets/ReturnAssetModal';
import { Button } from '../components/ui/Button';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useAuth } from '../context/AuthContext';
import styles from './AssetsPage.module.css';

const PAGE_SIZE = 15;

export const formatCurrency = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || isNaN(Number(amount))) return '—';
  return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const AssetsPage: React.FC = () => {
  const { role } = useAuth();
  const canRegister = role === 'administrator' || role === 'director' || role === 'supervisor';
  const navigate = useNavigate();

  // Data states
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(0);
  const [sites, setSites] = useState<SiteResponseData[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [locationTypeFilter, setLocationTypeFilter] = useState<LocationType | ''>('');
  const [siteFilter, setSiteFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [conditionFilter, setConditionFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Modals state
  const [showRegisterModal, setShowRegisterModal] = useState<boolean>(false);
  const [actionAsset, setActionAsset] = useState<AssetResponse | null>(null);
  const [modalType, setModalType] = useState<'issue' | 'return' | 'reassign' | null>(null);

  // Load Sites for filter
  useEffect(() => {
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
            console.error('Failed to load sites for filter', err);
          });
      });
  }, []);

  const fetchAssets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAssetsApi({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: search.trim() || undefined,
        location_type: locationTypeFilter || undefined,
        site_id: siteFilter || undefined,
        status: statusFilter || undefined,
        condition: conditionFilter || undefined,
        category: categoryFilter.trim() || undefined,
      });
      setAssets(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to fetch assets';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  }, [page, search, locationTypeFilter, siteFilter, statusFilter, conditionFilter, categoryFilter]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchAssets();
  };

  const handleResetFilters = () => {
    setSearch('');
    setLocationTypeFilter('');
    setSiteFilter('');
    setStatusFilter('');
    setConditionFilter('');
    setCategoryFilter('');
    setPage(0);
  };

  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleOpenAction = (asset: AssetResponse, type: 'issue' | 'return' | 'reassign') => {
    setActionAsset(asset);
    setModalType(type);
  };

  const handleCloseModal = () => {
    setActionAsset(null);
    setModalType(null);
  };

  const handleMutationSuccess = (updatedAsset?: AssetResponse) => {
    fetchAssets();
    const tag = updatedAsset?.asset_tag ? ` ${updatedAsset.asset_tag}` : '';
    if (modalType === 'issue') {
      setSuccessMessage(`Asset${tag} successfully issued.`);
    } else if (modalType === 'return') {
      setSuccessMessage(`Asset${tag} successfully returned.`);
    } else if (modalType === 'reassign') {
      setSuccessMessage(`Asset${tag} location reassigned.`);
    }
    setTimeout(() => setSuccessMessage(null), 6000);
  };

  const handleRegisterSuccess = (newAsset: AssetResponse) => {
    fetchAssets();
    setSuccessMessage(`Asset ${newAsset.asset_tag} successfully registered.`);
    setTimeout(() => setSuccessMessage(null), 6000);
  };

  // Status badge styling helper
  const renderStatusBadge = (status: string) => {
    let cls = styles.statusAvailable;
    if (status === 'issued_employee') cls = styles.statusIssued;
    else if (status === 'under_maintenance') cls = styles.statusMaintenance;
    else if (status === 'damaged') cls = styles.statusDamaged;
    else if (status === 'lost') cls = styles.statusLost;
    else if (status === 'retired') cls = styles.statusRetired;

    const label = status === 'issued_employee' ? 'Issued' : status.replace('_', ' ');
    return <span className={`${styles.statusBadge} ${cls}`}>{label}</span>;
  };

  // Location badge helper
  const renderLocationBadge = (asset: AssetResponse) => {
    if (asset.location_type === 'warehouse') {
      return <span className={`${styles.locationBadge} ${styles.locationWarehouse}`}>Central Warehouse</span>;
    }
    return (
      <span className={`${styles.locationBadge} ${styles.locationSite}`}>
        {asset.current_site_name || 'Project Site'}
      </span>
    );
  };

  // Simple KPI aggregations from current assets/total
  const warehouseCount = assets.filter((a) => a.location_type === 'warehouse').length;
  const siteCount = assets.filter((a) => a.location_type === 'site').length;
  const issuedCount = assets.filter((a) => a.status === 'issued_employee').length;

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Asset Management Registry</h2>
          <p>Register, track, issue, return, and reassign physical machinery, tools, and equipment.</p>
        </div>
        {canRegister && (
          <Button
            variant="primary"
            onClick={() => setShowRegisterModal(true)}
            data-testid="register-asset-button"
          >
            + Register Asset
          </Button>
        )}
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div style={{ padding: '12px 16px', backgroundColor: '#ecfdf5', color: '#065f46', border: '1px solid #a7f3d0', borderRadius: '8px', fontSize: '0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{successMessage}</span>
          <Button variant="ghost" size="sm" onClick={() => setSuccessMessage(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Total Registered</span>
          <span className={styles.kpiValue}>{total}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>In Central Warehouse</span>
          <span className={styles.kpiValue}>{warehouseCount}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Allocated to Sites</span>
          <span className={styles.kpiValue}>{siteCount}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiTitle}>Currently Issued</span>
          <span className={styles.kpiValue} style={{ color: '#2563eb' }}>
            {issuedCount}
          </span>
        </div>
      </div>

      {/* Filters Card */}
      <div className={styles.filterCard}>
        <form onSubmit={handleSearchSubmit} className={styles.filterGrid}>
          <div>
            <label className={styles.kpiTitle} htmlFor="asset-search-input">
              Search
            </label>
            <input
              id="asset-search-input"
              type="text"
              className={styles.dataTable}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.875rem',
              }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tag, name, serial, model..."
            />
          </div>

          <div>
            <label className={styles.kpiTitle} htmlFor="filter-location-type">
              Location Type
            </label>
            <select
              id="filter-location-type"
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.875rem',
                backgroundColor: '#ffffff',
              }}
              value={locationTypeFilter}
              onChange={(e) => {
                setLocationTypeFilter(e.target.value as LocationType | '');
                setPage(0);
              }}
            >
              <option value="">All Locations</option>
              <option value="warehouse">Central Warehouse</option>
              <option value="site">Project Sites</option>
            </select>
          </div>

          <div>
            <label className={styles.kpiTitle} htmlFor="filter-site">
              Specific Site
            </label>
            <select
              id="filter-site"
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.875rem',
                backgroundColor: '#ffffff',
              }}
              value={siteFilter}
              onChange={(e) => {
                setSiteFilter(e.target.value);
                setPage(0);
              }}
            >
              <option value="">All Sites</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={styles.kpiTitle} htmlFor="filter-status">
              Operational Status
            </label>
            <select
              id="filter-status"
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.875rem',
                backgroundColor: '#ffffff',
              }}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
            >
              <option value="">All Statuses</option>
              <option value="available">Available</option>
              <option value="issued_employee">Issued to Employee</option>
              <option value="under_maintenance">Under Maintenance</option>
              <option value="damaged">Damaged</option>
              <option value="lost">Lost</option>
              <option value="retired">Retired</option>
            </select>
          </div>

          <div>
            <label className={styles.kpiTitle} htmlFor="filter-condition">
              Condition
            </label>
            <select
              id="filter-condition"
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.875rem',
                backgroundColor: '#ffffff',
              }}
              value={conditionFilter}
              onChange={(e) => {
                setConditionFilter(e.target.value);
                setPage(0);
              }}
            >
              <option value="">All Conditions</option>
              <option value="new">New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="damaged">Damaged</option>
              <option value="unusable">Unusable</option>
            </select>
          </div>

          <div className={styles.filterActions}>
            <Button variant="secondary" type="submit">
              Filter
            </Button>
            <Button variant="outline" type="button" onClick={handleResetFilters}>
              Reset
            </Button>
          </div>
        </form>
      </div>

      {/* Error state */}
      {error && (
        <ErrorMessage
          message={error}
          onRetry={fetchAssets}
        />
      )}

      {/* Table Data */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '48px' }}>
          <LoadingSpinner label="Loading asset inventory..." />
        </div>
      ) : assets.length === 0 ? (
        <div className={styles.tableWrapper}>
          <div className={styles.emptyState}>
            <p>No assets found matching the specified search or filter criteria.</p>
            {canRegister && (
              <Button
                variant="primary"
                onClick={() => setShowRegisterModal(true)}
                style={{ marginTop: '12px' }}
              >
                Register an Asset
              </Button>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable} aria-label="Assets table">
            <thead>
              <tr>
                <th>Asset Tag</th>
                <th>Name & Category</th>
                <th>Serial / Model</th>
                <th>Current Location</th>
                <th>Status</th>
                <th>Condition</th>
                <th>Custodian</th>
                <th>Cost</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => {
                const isIssued = asset.status === 'issued_employee';
                const isAvailableSite = asset.status === 'available' && asset.location_type === 'site';

                return (
                  <tr key={asset.id} data-testid={`asset-row-${asset.id}`}>
                    <td>
                      <Link to={`/assets/${asset.id}`} className={styles.tagLink}>
                        {asset.asset_tag}
                      </Link>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{asset.name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{asset.category}</div>
                    </td>
                    <td>
                      <div>{asset.serial_number || '—'}</div>
                      {asset.model_number && (
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{asset.model_number}</div>
                      )}
                    </td>
                    <td>{renderLocationBadge(asset)}</td>
                    <td>{renderStatusBadge(asset.status)}</td>
                    <td>
                      <span className={styles.conditionBadge}>{asset.condition}</span>
                    </td>
                    <td>
                      {isIssued ? (
                        <div style={{ fontWeight: 600, color: '#1d4ed8' }}>
                          {asset.current_custodian_name || 'Assigned Custodian'}
                        </div>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>—</span>
                      )}
                    </td>
                    <td>{formatCurrency(asset.purchase_cost)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className={styles.actionCell} style={{ justifyContent: 'flex-end' }}>
                        {isAvailableSite && (
                          <button
                            type="button"
                            className={`${styles.actionBtn} ${styles.btnIssue}`}
                            onClick={() => handleOpenAction(asset, 'issue')}
                            data-testid={`issue-btn-${asset.id}`}
                            title="Issue asset to a site employee"
                          >
                            Issue
                          </button>
                        )}
                        {isIssued && (
                          <button
                            type="button"
                            className={`${styles.actionBtn} ${styles.btnReturn}`}
                            onClick={() => handleOpenAction(asset, 'return')}
                            data-testid={`return-btn-${asset.id}`}
                            title="Return asset from custodian"
                          >
                            Return
                          </button>
                        )}
                        {!isIssued && (
                          <button
                            type="button"
                            className={`${styles.actionBtn} ${styles.btnReassign}`}
                            onClick={() => handleOpenAction(asset, 'reassign')}
                            data-testid={`reassign-btn-${asset.id}`}
                            title="Reassign site or warehouse location"
                          >
                            Reassign
                          </button>
                        )}
                        <button
                          type="button"
                          className={`${styles.actionBtn} ${styles.btnView}`}
                          onClick={() => navigate(`/assets/${asset.id}`)}
                          data-testid={`view-btn-${asset.id}`}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Pagination */}
          <div className={styles.pagination}>
            <span className={styles.pageInfo}>
              Showing {assets.length > 0 ? page * PAGE_SIZE + 1 : 0} to{' '}
              {Math.min((page + 1) * PAGE_SIZE, total)} of {total} assets
            </span>
            <div className={styles.pageControls}>
              <Button
                variant="outline"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              <span style={{ fontSize: '0.875rem', padding: '0 8px' }}>
                Page {page + 1} of {Math.max(1, totalPages)}
              </span>
              <Button
                variant="outline"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Action Modals */}
      <RegisterAssetModal
        isOpen={showRegisterModal}
        onClose={() => setShowRegisterModal(false)}
        onSuccess={handleRegisterSuccess}
      />

      <IssueAssetModal
        isOpen={modalType === 'issue'}
        asset={actionAsset}
        onClose={handleCloseModal}
        onSuccess={handleMutationSuccess}
      />

      <ReturnAssetModal
        isOpen={modalType === 'return'}
        asset={actionAsset}
        onClose={handleCloseModal}
        onSuccess={handleMutationSuccess}
      />

      <ReassignAssetModal
        isOpen={modalType === 'reassign'}
        asset={actionAsset}
        onClose={handleCloseModal}
        onSuccess={handleMutationSuccess}
      />
    </div>
  );
};

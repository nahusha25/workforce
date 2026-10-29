import React, { useCallback, useEffect, useState } from 'react';
import {
  Boxes,
  Plus,
  RefreshCw,
  History,
  AlertCircle,
  Loader2,
  PackageCheck,
} from 'lucide-react';
import type { AxiosError } from 'axios';
import {
  getSiteInventoryApi,
  getInventorySitesApi,
  type SiteInventoryItem,
} from '../api/inventory';
import { getSitesApi, type SiteResponseData } from '../api/masterData';
import { getMaterialsCatalogue, type CatalogueMaterial } from '../api/dailyWork';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { StockInwardModal } from '../components/inventory/StockInwardModal';
import { StockMovementHistoryModal } from '../components/inventory/StockMovementHistoryModal';
import { normalizeError } from '../api/client';
import styles from './InventoryPage.module.css';

export const InventoryPage: React.FC = () => {
  const { user, role } = useAuth();
  const isSupervisor = role === 'supervisor';

  // Site state
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>('');
  const [loadingSites, setLoadingSites] = useState<boolean>(true);

  // Catalogue Materials
  const [catalogueMaterials, setCatalogueMaterials] = useState<CatalogueMaterial[]>([]);

  // Inventory Table state
  const [inventoryItems, setInventoryItems] = useState<SiteInventoryItem[]>([]);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [loadingInventory, setLoadingInventory] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Modals state
  const [showInwardModal, setShowInwardModal] = useState<boolean>(false);
  const [historyItem, setHistoryItem] = useState<SiteInventoryItem | null>(null);

  // 1. Load Sites on Mount
  useEffect(() => {
    let isMounted = true;
    const loadSites = async () => {
      setLoadingSites(true);
      setErrorMsg(null);
      try {
        let allowedSites: SiteResponseData[] = [];
        if (typeof getInventorySitesApi === 'function') {
          allowedSites = await getInventorySitesApi();
        } else if (typeof getSitesApi === 'function') {
          const allSites = await getSitesApi();
          const activeSites = allSites.filter((s) => s.is_active);
          if (isSupervisor && user) {
            const userSiteIds = new Set((user.active_sites || []).map((s) => s.id));
            allowedSites = activeSites.filter(
              (s) => s.supervisor_id === user.id || userSiteIds.has(s.id)
            );
          } else {
            allowedSites = activeSites;
          }
        }
        if (!isMounted) return;

        setSites(allowedSites);
        if (allowedSites.length > 0) {
          setSelectedSiteId((prev) =>
            prev && allowedSites.some((s) => s.id === prev) ? prev : allowedSites[0].id
          );
        } else {
          setSelectedSiteId('');
        }
      } catch (err: unknown) {
        if (isMounted) {
          const norm = normalizeError(err as AxiosError<any>);
          setErrorMsg(norm.message || 'Failed to load sites.');
        }
      } finally {
        if (isMounted) {
          setLoadingSites(false);
        }
      }
    };

    loadSites();
    return () => {
      isMounted = false;
    };
  }, [isSupervisor, user]);

  // 2. Load Catalogue Materials
  useEffect(() => {
    let isMounted = true;
    getMaterialsCatalogue()
      .then((mats) => {
        if (isMounted) setCatalogueMaterials(mats);
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  // 3. Load Site Inventory
  const fetchInventory = useCallback(async () => {
    if (!selectedSiteId) return;

    setLoadingInventory(true);
    setErrorMsg(null);
    try {
      const res = await getSiteInventoryApi(selectedSiteId, {
        search: searchTerm.trim() || undefined,
        category: categoryFilter || undefined,
        limit: 100,
      });
      setInventoryItems(res.items);
      setTotalItems(res.total);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to load site inventory.');
    } finally {
      setLoadingInventory(false);
    }
  }, [selectedSiteId, searchTerm, categoryFilter]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  const selectedSite = sites.find((s) => s.id === selectedSiteId);

  const categories = Array.from(
    new Set(
      catalogueMaterials
        .map((m) => m.category)
        .filter((c): c is string => Boolean(c))
    )
  );

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>
            <Boxes size={28} color="#2563eb" />
            Material Inventory
          </h1>
          <p className={styles.subtitle}>
            Track consumable material stock balances and inward receipts per client site.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            onClick={fetchInventory}
            disabled={loadingInventory || !selectedSiteId}
            aria-label="Refresh inventory"
          >
            <RefreshCw size={16} className={loadingInventory ? 'animate-spin' : ''} />
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={() => setShowInwardModal(true)}
            disabled={!selectedSiteId || sites.length === 0}
            aria-label="Record Stock Inward"
          >
            <Plus size={16} />
            Record Stock Inward
          </Button>
        </div>
      </div>

      {errorMsg && <ErrorMessage message={errorMsg} onRetry={fetchInventory} />}

      {/* Filter / Selector Bar */}
      <div className={styles.filterCard}>
        {/* Site Selector */}
        <div className={styles.filterGroup}>
          <label htmlFor="site-selector" className={styles.filterLabel}>
            Site
          </label>
          <select
            id="site-selector"
            className={styles.select}
            value={selectedSiteId}
            onChange={(e) => setSelectedSiteId(e.target.value)}
            disabled={loadingSites || sites.length === 0}
          >
            {sites.length === 0 ? (
              <option value="">No authorized sites available</option>
            ) : (
              sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Search Input */}
        <div className={styles.filterGroup}>
          <label htmlFor="search-input" className={styles.filterLabel}>
            Search Materials
          </label>
          <input
            id="search-input"
            type="text"
            placeholder="Search by name or code..."
            className={styles.input}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Category Filter */}
        <div className={styles.filterGroup}>
          <label htmlFor="category-selector" className={styles.filterLabel}>
            Category
          </label>
          <select
            id="category-selector"
            className={styles.select}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Inventory Table */}
      <div className={styles.tableCard}>
        {loadingInventory ? (
          <div className={styles.loadingState}>
            <Loader2 size={24} className="animate-spin" />
            <span>Loading site inventory...</span>
          </div>
        ) : sites.length === 0 ? (
          <div className={styles.emptyState}>
            <AlertCircle size={36} color="#94a3b8" />
            <p>No authorized sites available for inventory tracking.</p>
          </div>
        ) : inventoryItems.length === 0 ? (
          <div className={styles.emptyState}>
            <PackageCheck size={36} color="#94a3b8" />
            <p>No material inventory records found matching your filters.</p>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>Material Name</th>
                  <th className={styles.th}>Code</th>
                  <th className={styles.th}>Category</th>
                  <th className={styles.th}>Unit of Measure</th>
                  <th className={styles.th}>Available Stock</th>
                  <th className={styles.th}>Last Movement</th>
                  <th className={styles.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {inventoryItems.map((item) => {
                  const qty = Number(item.quantity_available);
                  const isPositive = qty > 0;
                  return (
                    <tr key={item.material_id} className={styles.tr}>
                      <td className={styles.td}>
                        <div className={styles.materialName}>{item.material_name}</div>
                      </td>
                      <td className={styles.td}>
                        <span className={styles.codeBadge}>{item.material_code || '—'}</span>
                      </td>
                      <td className={styles.td}>
                        <span style={{ textTransform: 'capitalize' }}>{item.category || '—'}</span>
                      </td>
                      <td className={styles.td}>{item.unit_of_measure}</td>
                      <td className={styles.td}>
                        <span className={isPositive ? styles.stockBadgePositive : styles.stockBadgeZero}>
                          {qty.toFixed(2)} {item.unit_of_measure}
                        </span>
                      </td>
                      <td className={styles.td}>{formatDate(item.last_movement_at)}</td>
                      <td className={styles.td}>
                        <button
                          type="button"
                          className={styles.actionBtn}
                          onClick={() => setHistoryItem(item)}
                          aria-label={`View movements for ${item.material_name}`}
                        >
                          <History size={14} />
                          Movements
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pagination}>
          <span>
            Showing {inventoryItems.length} of {totalItems} items
          </span>
          <span>Site: {selectedSite ? selectedSite.name : '—'}</span>
        </div>
      </div>

      {/* Stock Inward Modal */}
      <StockInwardModal
        isOpen={showInwardModal}
        onClose={() => setShowInwardModal(false)}
        onSuccess={() => {
          fetchInventory();
        }}
        sites={sites}
        selectedSiteId={selectedSiteId}
        catalogueMaterials={catalogueMaterials}
      />

      {/* Stock Movement History Modal */}
      {historyItem && (
        <StockMovementHistoryModal
          isOpen={Boolean(historyItem)}
          onClose={() => setHistoryItem(null)}
          siteId={selectedSiteId}
          siteName={selectedSite ? selectedSite.name : ''}
          materialId={historyItem.material_id}
          materialName={historyItem.material_name}
          materialCode={historyItem.material_code}
          unitOfMeasure={historyItem.unit_of_measure}
          availableQuantity={Number(historyItem.quantity_available)}
        />
      )}
    </div>
  );
};

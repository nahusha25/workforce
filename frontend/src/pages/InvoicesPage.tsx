import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  generateInvoiceApi,
  listInvoicesApi,
  previewInvoiceApi,
  type InvoicePreviewResponse,
  type InvoiceResponse,
} from '../api/invoices';
import {
  getClientsApi,
  getProjectsApi,
  getSitesApi,
  type ClientResponseData,
  type ProjectResponseData,
  type SiteResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { getLocalISODate } from '../utils/date';
import styles from './InvoicesPage.module.css';

export const formatCurrency = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || isNaN(Number(amount))) return '₹0.00';
  return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const InvoicesPage: React.FC = () => {
  const { role } = useAuth();
  const isDirectorOrAdmin = role === 'director' || role === 'administrator';
  const navigate = useNavigate();

  // Data states
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [sites, setSites] = useState<SiteResponseData[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [filterClient, setFilterClient] = useState<string>('');
  const [filterProject, setFilterProject] = useState<string>('');
  const [filterSite, setFilterSite] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');

  // Modal / Generation state
  const [showGenerateModal, setShowGenerateModal] = useState<boolean>(false);
  const [genClientId, setGenClientId] = useState<string>('');
  const [genProjectId, setGenProjectId] = useState<string>('');
  const [genSiteId, setGenSiteId] = useState<string>('');
  const [genPeriodStart, setGenPeriodStart] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return getLocalISODate(d);
  });
  const [genPeriodEnd, setGenPeriodEnd] = useState<string>(() => getLocalISODate(new Date()));
  const [genClientPo, setGenClientPo] = useState<string>('');
  const [genNotes, setGenNotes] = useState<string>('');

  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<InvoicePreviewResponse | null>(null);

  const [generating, setGenerating] = useState<boolean>(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [invRes, clientsRes, projectsRes, sitesRes] = await Promise.allSettled([
        listInvoicesApi({
          client_id: filterClient || undefined,
          project_id: filterProject || undefined,
          site_id: filterSite || undefined,
          status: filterStatus || undefined,
          period_start: filterStartDate || undefined,
          period_end: filterEndDate || undefined,
        }),
        getClientsApi(),
        getProjectsApi(),
        getSitesApi(),
      ]);

      if (invRes.status === 'fulfilled') {
        setInvoices(invRes.value);
      } else {
        setError(invRes.reason?.response?.data?.detail || invRes.reason?.message || 'Failed to load invoices');
      }

      if (clientsRes.status === 'fulfilled') setClients(clientsRes.value);
      if (projectsRes.status === 'fulfilled') setProjects(projectsRes.value);
      if (sitesRes.status === 'fulfilled') setSites(sitesRes.value);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApplyFilters = () => {
    fetchData();
  };

  const handleResetFilters = () => {
    setFilterClient('');
    setFilterProject('');
    setFilterSite('');
    setFilterStatus('');
    setFilterStartDate('');
    setFilterEndDate('');
    listInvoicesApi()
      .then(setInvoices)
      .catch((err) => setError(err.message || 'Failed to load invoices'));
  };

  // Preview unbilled records
  const handlePreview = async () => {
    if (!genClientId || !genProjectId || !genSiteId || !genPeriodStart || !genPeriodEnd) {
      setPreviewError('Please select client, project, site, and valid billing period.');
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);
    try {
      const res = await previewInvoiceApi({
        client_id: genClientId,
        project_id: genProjectId,
        site_id: genSiteId,
        period_start: genPeriodStart,
        period_end: genPeriodEnd,
      });
      setPreviewData(res);
    } catch (err: any) {
      setPreviewError(err?.response?.data?.detail || err.message || 'Failed to preview invoice');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Generate invoice
  const handleGenerate = async () => {
    if (!genClientId || !genProjectId || !genSiteId || !genPeriodStart || !genPeriodEnd) return;
    setGenerating(true);
    setGenerateError(null);
    const idempotencyKey = `inv_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    try {
      const res = await generateInvoiceApi({
        client_id: genClientId,
        project_id: genProjectId,
        site_id: genSiteId,
        period_start: genPeriodStart,
        period_end: genPeriodEnd,
        idempotency_key: idempotencyKey,
        client_po_number: genClientPo.trim() || undefined,
        notes: genNotes.trim() || undefined,
      });
      setShowGenerateModal(false);
      navigate(`/invoices/${res.id}`);
    } catch (err: any) {
      setGenerateError(err?.response?.data?.detail || err.message || 'Failed to generate invoice');
    } finally {
      setGenerating(false);
    }
  };

  // Dynamic project/site lists in modal
  const modalProjects = projects.filter((p) => !genClientId || p.client_id === genClientId);
  const modalSites = sites.filter((s) => !genProjectId || s.project_id === genProjectId);

  // Stats calculation
  const totalInvoices = invoices.length;
  const draftCount = invoices.filter((i) => i.status === 'draft').length;
  const issuedCount = invoices.filter((i) => i.status === 'issued').length;
  const partiallyPaidCount = invoices.filter((i) => i.status === 'partially_paid').length;
  const paidCount = invoices.filter((i) => i.status === 'paid').length;
  const cancelledCount = invoices.filter((i) => i.status === 'cancelled').length;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Client Invoices</h2>
          <p>Generate, issue, and manage client billings with strict operational source locks.</p>
        </div>
        {isDirectorOrAdmin && (
          <Button
            variant="primary"
            onClick={() => {
              setPreviewData(null);
              setPreviewError(null);
              setGenerateError(null);
              setShowGenerateModal(true);
            }}
          >
            + New Invoice
          </Button>
        )}
      </div>

      {/* KPI Cards */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard} data-testid="kpi-total">
          <span className={styles.kpiTitle}>Total Invoices</span>
          <span className={styles.kpiValue}>{totalInvoices}</span>
        </div>
        <div className={styles.kpiCard} data-testid="kpi-draft">
          <span className={styles.kpiTitle}>Draft Invoices</span>
          <span className={styles.kpiValue}>{draftCount}</span>
        </div>
        <div className={styles.kpiCard} data-testid="kpi-issued">
          <span className={styles.kpiTitle}>Issued (Pending)</span>
          <span className={styles.kpiValue}>{issuedCount}</span>
        </div>
        <div className={styles.kpiCard} data-testid="kpi-partially-paid">
          <span className={styles.kpiTitle}>Partially Paid</span>
          <span className={styles.kpiValue}>{partiallyPaidCount}</span>
        </div>
        <div className={styles.kpiCard} data-testid="kpi-paid">
          <span className={styles.kpiTitle}>Fully Paid</span>
          <span className={styles.kpiValue}>{paidCount}</span>
        </div>
        <div className={styles.kpiCard} data-testid="kpi-cancelled">
          <span className={styles.kpiTitle}>Cancelled</span>
          <span className={styles.kpiValue}>{cancelledCount}</span>
        </div>
      </div>

      {/* Filter Card */}
      <Card className={styles.filterCard}>
        <div className={styles.filterGrid}>
          {clients.length > 0 ? (
            <Select
              label="Client"
              value={filterClient}
              onChange={(e) => setFilterClient(e.target.value)}
              options={[{ value: '', label: 'All Clients' }, ...clients.map((c) => ({ value: c.id, label: c.name }))]}
            />
          ) : (
            <Input
              label="Client"
              placeholder="Filter by Client ID"
              value={filterClient}
              onChange={(e) => setFilterClient(e.target.value)}
            />
          )}

          {projects.length > 0 ? (
            <Select
              label="Project"
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
              options={[{ value: '', label: 'All Projects' }, ...projects.map((p) => ({ value: p.id, label: p.name }))]}
            />
          ) : (
            <Input
              label="Project"
              placeholder="Filter by Project ID"
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
            />
          )}

          {sites.length > 0 ? (
            <Select
              label="Site"
              value={filterSite}
              onChange={(e) => setFilterSite(e.target.value)}
              options={[{ value: '', label: 'All Sites' }, ...sites.map((s) => ({ value: s.id, label: s.name }))]}
            />
          ) : (
            <Input
              label="Site"
              placeholder="Filter by Site ID"
              value={filterSite}
              onChange={(e) => setFilterSite(e.target.value)}
            />
          )}
          <Select
            label="Status"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            options={[
              { value: '', label: 'All Statuses' },
              { value: 'draft', label: 'Draft' },
              { value: 'issued', label: 'Issued' },
              { value: 'partially_paid', label: 'Partially Paid' },
              { value: 'paid', label: 'Paid' },
              { value: 'cancelled', label: 'Cancelled' },
            ]}
          />
          <Input
            label="From Date"
            type="date"
            value={filterStartDate}
            onChange={(e) => setFilterStartDate(e.target.value)}
          />
          <Input
            label="To Date"
            type="date"
            value={filterEndDate}
            onChange={(e) => setFilterEndDate(e.target.value)}
          />
          <div className={styles.filterActions}>
            <Button variant="secondary" onClick={handleApplyFilters}>
              Filter
            </Button>
            <Button variant="outline" onClick={handleResetFilters}>
              Reset
            </Button>
          </div>
        </div>
      </Card>

      {/* Main Table */}
      {error && <ErrorMessage message={error} />}

      {loading ? (
        <LoadingSpinner label="Loading invoices..." />
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Client</th>
                <th>Project / Site</th>
                <th>Period</th>
                <th>Work Subtotal</th>
                <th>Mat. Subtotal</th>
                <th>Tax</th>
                <th>Total Amount</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan={10} className={styles.emptyState}>
                    No invoices found matching your filters.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <span className={styles.invNumberLink} onClick={() => navigate(`/invoices/${inv.id}`)}>
                        {inv.invoice_number}
                      </span>
                    </td>
                    <td>{inv.client_name || '-'}</td>
                    <td>
                      <div>{inv.project_name || '-'}</div>
                      <small style={{ color: 'var(--color-neutral-500)' }}>{inv.site_name || '-'}</small>
                    </td>
                    <td>
                      {inv.period_start} to {inv.period_end}
                    </td>
                    <td>{formatCurrency(inv.subtotal_work)}</td>
                    <td>{formatCurrency(inv.subtotal_material)}</td>
                    <td>{formatCurrency(inv.tax_amount)}</td>
                    <td>
                      <strong>{formatCurrency(inv.total_amount)}</strong>
                    </td>
                    <td>
                      <StatusBadge status={inv.status} />
                    </td>
                    <td>
                      <Button variant="secondary" size="sm" onClick={() => navigate(`/invoices/${inv.id}`)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Generate & Preview Modal */}
      {showGenerateModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>Preview & Generate Invoice</h3>
              <button className={styles.closeBtn} onClick={() => setShowGenerateModal(false)}>
                &times;
              </button>
            </div>

            {previewError && <ErrorMessage message={previewError} />}
            {generateError && <ErrorMessage message={generateError} />}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {clients.length > 0 ? (
                <Select
                  label="Client *"
                  value={genClientId}
                  onChange={(e) => {
                    setGenClientId(e.target.value);
                    setGenProjectId('');
                    setGenSiteId('');
                    setPreviewData(null);
                  }}
                  options={[
                    { value: '', label: 'Select Client' },
                    ...clients.map((c) => ({ value: c.id, label: c.name })),
                  ]}
                />
              ) : (
                <Input
                  label="Client *"
                  placeholder="Enter Client ID (UUID)"
                  value={genClientId}
                  onChange={(e) => {
                    setGenClientId(e.target.value);
                    setPreviewData(null);
                  }}
                />
              )}

              {modalProjects.length > 0 ? (
                <Select
                  label="Project *"
                  value={genProjectId}
                  onChange={(e) => {
                    setGenProjectId(e.target.value);
                    setGenSiteId('');
                    setPreviewData(null);
                  }}
                  options={[
                    { value: '', label: 'Select Project' },
                    ...modalProjects.map((p) => ({ value: p.id, label: p.name })),
                  ]}
                />
              ) : (
                <Input
                  label="Project *"
                  placeholder="Enter Project ID (UUID)"
                  value={genProjectId}
                  onChange={(e) => {
                    setGenProjectId(e.target.value);
                    setPreviewData(null);
                  }}
                />
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
              {modalSites.length > 0 ? (
                <Select
                  label="Site *"
                  value={genSiteId}
                  onChange={(e) => {
                    setGenSiteId(e.target.value);
                    setPreviewData(null);
                  }}
                  options={[
                    { value: '', label: 'Select Site' },
                    ...modalSites.map((s) => ({ value: s.id, label: s.name })),
                  ]}
                />
              ) : (
                <Input
                  label="Site *"
                  placeholder="Enter Site ID (UUID)"
                  value={genSiteId}
                  onChange={(e) => {
                    setGenSiteId(e.target.value);
                    setPreviewData(null);
                  }}
                />
              )}

              <Input
                label="Period Start *"
                type="date"
                value={genPeriodStart}
                onChange={(e) => {
                  setGenPeriodStart(e.target.value);
                  setPreviewData(null);
                }}
              />

              <Input
                label="Period End *"
                type="date"
                value={genPeriodEnd}
                onChange={(e) => {
                  setGenPeriodEnd(e.target.value);
                  setPreviewData(null);
                }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <Input
                label="Client PO Number (Optional)"
                placeholder="e.g. PO-2026-001"
                value={genClientPo}
                onChange={(e) => setGenClientPo(e.target.value)}
              />
              <Input
                label="Notes (Optional)"
                placeholder="Billing notes"
                value={genNotes}
                onChange={(e) => setGenNotes(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-start', gap: '8px' }}>
              <Button
                variant="secondary"
                onClick={handlePreview}
                disabled={previewLoading || !genClientId || !genProjectId || !genSiteId}
              >
                {previewLoading ? 'Inspecting Records...' : '1. Preview Billable Records'}
              </Button>
            </div>

            {/* Preview Results */}
            {previewData && (
              <div className={styles.previewSummaryCard}>
                <div className={styles.previewMetrics}>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Billable Work Entries</span>
                    <span className={styles.metricVal}>{previewData.billable_work_count}</span>
                  </div>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Billable Material Tx</span>
                    <span className={styles.metricVal}>{previewData.billable_material_count}</span>
                  </div>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Work Subtotal</span>
                    <span className={styles.metricVal}>{formatCurrency(previewData.subtotal_work)}</span>
                  </div>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Material Subtotal</span>
                    <span className={styles.metricVal}>{formatCurrency(previewData.subtotal_material)}</span>
                  </div>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Estimated Total</span>
                    <span className={styles.metricVal} style={{ color: 'var(--color-primary-700)' }}>
                      {formatCurrency(previewData.estimated_total)}
                    </span>
                  </div>
                </div>

                {previewData.items.length === 0 ? (
                  <p style={{ margin: 0, color: 'var(--color-neutral-600)' }}>
                    No unbilled approved records exist for this site and date range.
                  </p>
                ) : (
                  <>
                    <div className={styles.previewTableWrapper}>
                      <table className={styles.dataTable}>
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Date</th>
                            <th>Description</th>
                            <th>Qty</th>
                            <th>Rate</th>
                            <th>Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewData.items.map((item, idx) => (
                            <tr key={idx}>
                              <td>
                                <StatusBadge
                                  status={item.source_type === 'work' ? 'verified' : 'submitted'}
                                  label={item.source_type.toUpperCase()}
                                />
                              </td>
                              <td>{item.source_date}</td>
                              <td>{item.item_description}</td>
                              <td>
                                {item.quantity} {item.uom}
                              </td>
                              <td>{formatCurrency(item.unit_rate)}</td>
                              <td>{formatCurrency(item.line_amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
                      <Button variant="outline" onClick={() => setShowGenerateModal(false)}>
                        Cancel
                      </Button>
                      <Button variant="primary" onClick={handleGenerate} disabled={generating}>
                        {generating ? 'Generating Draft...' : '2. Generate Draft Invoice'}
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

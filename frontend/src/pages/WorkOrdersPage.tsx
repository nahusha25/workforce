import React, { useEffect, useState } from 'react';
import {
  getWorkOrdersApi,
  getWorkOrderByIdApi,
  createWorkOrderApi,
  updateWorkOrderApi,
  getProjectsApi,
  getSitesApi,
  type WorkOrderResponseData,
  type ProjectResponseData,
  type SiteResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import styles from './MasterDataPage.module.css';

export const WorkOrdersPage: React.FC = () => {
  const [workOrders, setWorkOrders] = useState<WorkOrderResponseData[]>([]);
  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Fields
  const [orderNumber, setOrderNumber] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [siteId, setSiteId] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [billingBasis, setBillingBasis] = useState<string>('lump_sum');
  const [statusVal, setStatusVal] = useState<string>('open');

  const fetchData = async () => {
    setError(null);
    try {
      const [woData, projData, siteData] = await Promise.all([
        getWorkOrdersApi(),
        getProjectsApi(),
        getSitesApi(),
      ]);
      setWorkOrders(woData);
      setProjects(projData);
      setSites(siteData);
      if (projData.length > 0 && !projectId) {
        setProjectId(projData[0].id);
      }
      if (siteData.length > 0 && !siteId) {
        setSiteId(siteData[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load work orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const resetForm = () => {
    setOrderNumber('');
    setDescription('');
    setStartDate('');
    setEndDate('');
    setBillingBasis('lump_sum');
    setStatusVal('open');
    setEditingId(null);
    setFormError(null);
    setShowForm(false);
  };

  const handleStartCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleStartEdit = async (id: string) => {
    setFormError(null);
    setSuccessMsg(null);
    try {
      const existing = await getWorkOrderByIdApi(id);
      setEditingId(existing.id);
      setOrderNumber(existing.order_number);
      setProjectId(existing.project_id);
      setSiteId(existing.site_id);
      setDescription(existing.description || '');
      setStartDate(existing.start_date || '');
      setEndDate(existing.end_date || '');
      setBillingBasis(existing.billing_basis || 'lump_sum');
      setStatusVal(existing.status || 'open');
      setShowForm(true);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch work order details');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!orderNumber.trim()) {
      setFormError('Order number is required');
      return;
    }
    if (!projectId) {
      setFormError('Please select a project');
      return;
    }
    if (!siteId) {
      setFormError('Please select a site');
      return;
    }

    setSubmitting(true);
    try {
      if (editingId) {
        await updateWorkOrderApi(editingId, {
          order_number: orderNumber.trim(),
          project_id: projectId,
          site_id: siteId,
          description: description.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          billing_basis: billingBasis || null,
          status: statusVal,
        });
        setSuccessMsg(`Work Order "${orderNumber.trim()}" updated successfully!`);
      } else {
        await createWorkOrderApi({
          order_number: orderNumber.trim(),
          project_id: projectId,
          site_id: siteId,
          description: description.trim() || undefined,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
          billing_basis: billingBasis || undefined,
          status: statusVal,
          is_active: true,
        });
        setSuccessMsg(`Work Order "${orderNumber.trim()}" created successfully!`);
      }
      resetForm();
      await fetchData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save work order');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeactivate = async (id: string, currentNumber: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateWorkOrderApi(id, { is_active: false });
      setSuccessMsg(`Work Order "${currentNumber}" deactivated successfully.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to deactivate work order');
    }
  };

  const handleActivate = async (id: string, currentNumber: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateWorkOrderApi(id, { is_active: true });
      setSuccessMsg(`Work Order "${currentNumber}" reactivated successfully.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to activate work order');
    }
  };

  const projectOptions: SelectOption[] = projects.map((p) => ({
    value: p.id,
    label: p.name,
  }));

  const siteOptions: SelectOption[] = sites.map((s) => ({
    value: s.id,
    label: s.name,
  }));

  const statusOptions: SelectOption[] = [
    { value: 'draft', label: 'Draft' },
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
    { value: 'closed', label: 'Closed' },
  ];

  const billingBasisOptions: SelectOption[] = [
    { value: 'per_metre', label: 'Per Metre' },
    { value: 'per_device', label: 'Per Device' },
    { value: 'lump_sum', label: 'Lump Sum' },
  ];

  const getProjectName = (pid: string) => projects.find((p) => p.id === pid)?.name || pid;
  const getSiteName = (sid: string) => sites.find((s) => s.id === sid)?.name || sid;

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Work Order Management</h2>
          <p>Create and manage site work orders, scope, and target milestones</p>
        </div>
        <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-work-order-btn">
          {showForm ? 'Cancel' : '+ Add Work Order'}
        </Button>
      </div>

      {successMsg && (
        <div className={styles.alertSuccess} role="status">
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Error" message={error} onRetry={fetchData} />}

      {showForm && (
        <Card
          title={editingId ? 'Edit Work Order' : 'Create New Work Order'}
          subtitle="Configure work order metadata and project linkages"
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSubmit} className={styles.formGrid}>
            <div className={styles.formRow}>
              <Input
                label="Order Number *"
                placeholder="e.g. WO-2026-001"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                required
                data-testid="order-number-input"
              />
              <Select
                label="Project *"
                options={projectOptions}
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                required
                data-testid="project-select"
              />
              <Select
                label="Site *"
                options={siteOptions}
                value={siteId}
                onChange={(e) => setSiteId(e.target.value)}
                required
                data-testid="site-select"
              />
            </div>

            <div className={styles.formRow}>
              <Select
                label="Status"
                options={statusOptions}
                value={statusVal}
                onChange={(e) => setStatusVal(e.target.value)}
                data-testid="status-select"
              />
              <Select
                label="Billing Basis"
                options={billingBasisOptions}
                value={billingBasis}
                onChange={(e) => setBillingBasis(e.target.value)}
                data-testid="billing-basis-select"
              />
              <Input
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                data-testid="start-date-input"
              />
              <Input
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                data-testid="end-date-input"
              />
            </div>

            <Input
              label="Description"
              placeholder="e.g. Fiber optical cabling and terminal equipment mounting"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              data-testid="description-input"
            />

            <div className={styles.formActions}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-work-order-btn">
                {editingId ? 'Update Work Order' : 'Save Work Order'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading work orders..." />
      ) : workOrders.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No work orders found. Click <strong>+ Add Work Order</strong> to create one.</p>
          </div>
        </Card>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable} data-testid="work-orders-table">
            <thead>
              <tr>
                <th>Order #</th>
                <th>Project</th>
                <th>Site</th>
                <th>Status</th>
                <th>Billing Basis</th>
                <th>Timeline</th>
                <th>Active Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {workOrders.map((wo) => (
                <tr key={wo.id} className={!wo.is_active ? styles.inactiveRow : undefined}>
                  <td><strong>{wo.order_number}</strong></td>
                  <td>{getProjectName(wo.project_id)}</td>
                  <td>{getSiteName(wo.site_id)}</td>
                  <td><StatusBadge status={wo.status as any} /></td>
                  <td>{wo.billing_basis?.replace('_', ' ') || '—'}</td>
                  <td>
                    {wo.start_date || wo.end_date
                      ? `${wo.start_date || '—'} to ${wo.end_date || '—'}`
                      : '—'}
                  </td>
                  <td>
                    <StatusBadge status={wo.is_active ? 'active' : 'inactive'} />
                  </td>
                  <td>
                    <div className={styles.actionBtns}>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStartEdit(wo.id)}
                        data-testid={`edit-btn-${wo.id}`}
                      >
                        Edit
                      </Button>
                      {wo.is_active ? (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => handleDeactivate(wo.id, wo.order_number)}
                          data-testid={`deactivate-btn-${wo.id}`}
                        >
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleActivate(wo.id, wo.order_number)}
                          data-testid={`activate-btn-${wo.id}`}
                        >
                          Activate
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

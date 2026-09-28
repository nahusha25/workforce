import React, { useEffect, useState } from 'react';
import {
  getActivitiesApi,
  getActivityByIdApi,
  createActivityApi,
  updateActivityApi,
  type ActivityResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import styles from './MasterDataPage.module.css';

export const ActivitiesPage: React.FC = () => {
  const [activities, setActivities] = useState<ActivityResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Fields
  const [name, setName] = useState<string>('');
  const [category, setCategory] = useState<string>('cable');
  const [unitOfMeasure, setUnitOfMeasure] = useState<string>('');
  const [approvedRate, setApprovedRate] = useState<string>('0.00');

  const fetchActivities = async () => {
    setError(null);
    try {
      const data = await getActivitiesApi();
      setActivities(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load activities');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, []);

  const resetForm = () => {
    setName('');
    setCategory('cable');
    setUnitOfMeasure('');
    setApprovedRate('0.00');
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
      const existing = await getActivityByIdApi(id);
      setEditingId(existing.id);
      setName(existing.name);
      setCategory(existing.category);
      setUnitOfMeasure(existing.unit_of_measure);
      setApprovedRate(String(existing.approved_rate));
      setShowForm(true);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch activity details');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim()) {
      setFormError('Activity name is required');
      return;
    }
    if (!unitOfMeasure.trim()) {
      setFormError('Unit of measure is required');
      return;
    }
    const rateNum = parseFloat(approvedRate);
    if (isNaN(rateNum) || rateNum < 0) {
      setFormError('Approved rate must be a non-negative number');
      return;
    }

    setSubmitting(true);
    try {
      if (editingId) {
        await updateActivityApi(editingId, {
          name: name.trim(),
          category,
          unit_of_measure: unitOfMeasure.trim(),
          approved_rate: rateNum,
        });
        setSuccessMsg(`Activity "${name.trim()}" updated successfully!`);
      } else {
        await createActivityApi({
          name: name.trim(),
          category,
          unit_of_measure: unitOfMeasure.trim(),
          approved_rate: rateNum,
          is_active: true,
        });
        setSuccessMsg(`Activity "${name.trim()}" created successfully!`);
      }
      resetForm();
      await fetchActivities();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save activity');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeactivate = async (id: string, currentName: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateActivityApi(id, { is_active: false });
      setSuccessMsg(`Activity "${currentName}" deactivated successfully.`);
      await fetchActivities();
    } catch (err: any) {
      setError(err.message || 'Failed to deactivate activity');
    }
  };

  const handleActivate = async (id: string, currentName: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateActivityApi(id, { is_active: true });
      setSuccessMsg(`Activity "${currentName}" reactivated successfully.`);
      await fetchActivities();
    } catch (err: any) {
      setError(err.message || 'Failed to activate activity');
    }
  };

  const categoryOptions: SelectOption[] = [
    { value: 'cable', label: 'Cable Laying' },
    { value: 'device', label: 'Device Installation' },
    { value: 'drilling', label: 'Drilling & Chipping' },
    { value: 'mounting', label: 'Mounting & Brackets' },
    { value: 'testing', label: 'Testing' },
    { value: 'commissioning', label: 'Commissioning' },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Activity Catalog Management</h2>
          <p>Define standard trade tasks, measurement units, and billing rates</p>
        </div>
        <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-activity-btn">
          {showForm ? 'Cancel' : '+ Add Activity'}
        </Button>
      </div>

      {successMsg && (
        <div className={styles.alertSuccess} role="status">
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Error" message={error} onRetry={fetchActivities} />}

      {showForm && (
        <Card
          title={editingId ? 'Edit Activity' : 'Create New Activity'}
          subtitle="Configure trade activity specifications and approved rates"
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSubmit} className={styles.formGrid}>
            <div className={styles.formRow}>
              <Input
                label="Activity Name *"
                placeholder="e.g. Cat6 Cable Laying & Termination"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                data-testid="activity-name-input"
              />
              <Select
                label="Category *"
                options={categoryOptions}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
                data-testid="category-select"
              />
            </div>

            <div className={styles.formRow}>
              <Input
                label="Unit of Measure *"
                placeholder="e.g. metre, device, hole, point"
                value={unitOfMeasure}
                onChange={(e) => setUnitOfMeasure(e.target.value)}
                required
                data-testid="uom-input"
              />
              <Input
                label="Approved Rate (₹) *"
                type="number"
                step="0.01"
                min="0"
                value={approvedRate}
                onChange={(e) => setApprovedRate(e.target.value)}
                required
                data-testid="rate-input"
              />
            </div>

            <div className={styles.formActions}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-activity-btn">
                {editingId ? 'Update Activity' : 'Save Activity'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading activities..." />
      ) : activities.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No activities found. Click <strong>+ Add Activity</strong> to add trade activities.</p>
          </div>
        </Card>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable} data-testid="activities-table">
            <thead>
              <tr>
                <th>Activity Name</th>
                <th>Category</th>
                <th>Unit of Measure</th>
                <th>Approved Rate</th>
                <th>Active Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((act) => (
                <tr key={act.id} className={!act.is_active ? styles.inactiveRow : undefined}>
                  <td><strong>{act.name}</strong></td>
                  <td><span style={{ textTransform: 'capitalize' }}>{act.category}</span></td>
                  <td>{act.unit_of_measure}</td>
                  <td>₹{Number(act.approved_rate).toFixed(2)}</td>
                  <td>
                    <StatusBadge status={act.is_active ? 'active' : 'inactive'} />
                  </td>
                  <td>
                    <div className={styles.actionBtns}>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStartEdit(act.id)}
                        data-testid={`edit-btn-${act.id}`}
                      >
                        Edit
                      </Button>
                      {act.is_active ? (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => handleDeactivate(act.id, act.name)}
                          data-testid={`deactivate-btn-${act.id}`}
                        >
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleActivate(act.id, act.name)}
                          data-testid={`activate-btn-${act.id}`}
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

import React, { useEffect, useState } from 'react';
import {
  getMaterialsApi,
  getMaterialByIdApi,
  createMaterialApi,
  updateMaterialApi,
  type MaterialResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import styles from './MasterDataPage.module.css';

export const MaterialsPage: React.FC = () => {
  const [materials, setMaterials] = useState<MaterialResponseData[]>([]);
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
  const [materialCode, setMaterialCode] = useState<string>('');
  const [category, setCategory] = useState<string>('consumable');
  const [unitOfMeasure, setUnitOfMeasure] = useState<string>('');
  const [approvalLimit, setApprovalLimit] = useState<string>('1000.00');
  const [description, setDescription] = useState<string>('');

  const fetchMaterials = async () => {
    setError(null);
    try {
      const data = await getMaterialsApi();
      setMaterials(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load materials');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterials();
  }, []);

  const resetForm = () => {
    setName('');
    setMaterialCode('');
    setCategory('consumable');
    setUnitOfMeasure('');
    setApprovalLimit('1000.00');
    setDescription('');
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
      const existing = await getMaterialByIdApi(id);
      setEditingId(existing.id);
      setName(existing.name);
      setMaterialCode(existing.material_code || '');
      setCategory(existing.category);
      setUnitOfMeasure(existing.unit_of_measure);
      setApprovalLimit(String(existing.purchase_approval_limit));
      setDescription(existing.description || '');
      setShowForm(true);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch material details');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim()) {
      setFormError('Material name is required');
      return;
    }
    if (!unitOfMeasure.trim()) {
      setFormError('Unit of measure is required');
      return;
    }
    const limitNum = parseFloat(approvalLimit);
    if (isNaN(limitNum) || limitNum < 0) {
      setFormError('Purchase approval limit must be a non-negative number');
      return;
    }

    setSubmitting(true);
    try {
      if (editingId) {
        await updateMaterialApi(editingId, {
          name: name.trim(),
          material_code: materialCode.trim() || null,
          category,
          unit_of_measure: unitOfMeasure.trim(),
          purchase_approval_limit: limitNum,
          description: description.trim() || null,
        });
        setSuccessMsg(`Material "${name.trim()}" updated successfully!`);
      } else {
        await createMaterialApi({
          name: name.trim(),
          material_code: materialCode.trim() || undefined,
          category,
          unit_of_measure: unitOfMeasure.trim(),
          purchase_approval_limit: limitNum,
          description: description.trim() || undefined,
          is_active: true,
        });
        setSuccessMsg(`Material "${name.trim()}" created successfully!`);
      }
      resetForm();
      await fetchMaterials();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save material');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeactivate = async (id: string, currentName: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateMaterialApi(id, { is_active: false });
      setSuccessMsg(`Material "${currentName}" deactivated successfully.`);
      await fetchMaterials();
    } catch (err: any) {
      setError(err.message || 'Failed to deactivate material');
    }
  };

  const handleActivate = async (id: string, currentName: string) => {
    setSuccessMsg(null);
    setError(null);
    try {
      await updateMaterialApi(id, { is_active: true });
      setSuccessMsg(`Material "${currentName}" reactivated successfully.`);
      await fetchMaterials();
    } catch (err: any) {
      setError(err.message || 'Failed to activate material');
    }
  };

  const categoryOptions: SelectOption[] = [
    { value: 'cable', label: 'Cables & Wiring' },
    { value: 'device', label: 'Devices & Equipment' },
    { value: 'tool', label: 'Tools & Hardware' },
    { value: 'consumable', label: 'Consumables & Fasteners' },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h2>Material Master Management</h2>
          <p>Register standard site materials, classifications, and purchase approval thresholds</p>
        </div>
        <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-material-btn">
          {showForm ? 'Cancel' : '+ Add Material'}
        </Button>
      </div>

      {successMsg && (
        <div className={styles.alertSuccess} role="status">
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Error" message={error} onRetry={fetchMaterials} />}

      {showForm && (
        <Card
          title={editingId ? 'Edit Material' : 'Register New Material'}
          subtitle="Define material item properties and purchase expenditure limit"
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSubmit} className={styles.formGrid}>
            <div className={styles.formRow}>
              <Input
                label="Material Name *"
                placeholder="e.g. RJ45 Connectors (Pack of 100)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                data-testid="material-name-input"
              />
              <Input
                label="Material Code"
                placeholder="e.g. MAT-RJ45-100"
                value={materialCode}
                onChange={(e) => setMaterialCode(e.target.value)}
                data-testid="material-code-input"
              />
            </div>

            <div className={styles.formRow}>
              <Select
                label="Category *"
                options={categoryOptions}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
                data-testid="category-select"
              />
              <Input
                label="Unit of Measure *"
                placeholder="e.g. piece, box, coil, metre"
                value={unitOfMeasure}
                onChange={(e) => setUnitOfMeasure(e.target.value)}
                required
                data-testid="uom-input"
              />
              <Input
                label="Purchase Approval Limit (₹) *"
                type="number"
                step="0.01"
                min="0"
                value={approvalLimit}
                onChange={(e) => setApprovalLimit(e.target.value)}
                required
                data-testid="limit-input"
                helperText="Purchases above this threshold trigger supervisor high-value approval"
              />
            </div>

            <Input
              label="Description"
              placeholder="e.g. Cat6 unshielded modular plugs for patch cables"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              data-testid="description-input"
            />

            <div className={styles.formActions}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-material-btn">
                {editingId ? 'Update Material' : 'Save Material'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading materials..." />
      ) : materials.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No materials found. Click <strong>+ Add Material</strong> to register site materials.</p>
          </div>
        </Card>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable} data-testid="materials-table">
            <thead>
              <tr>
                <th>Material Name</th>
                <th>Code</th>
                <th>Category</th>
                <th>Unit</th>
                <th>Approval Limit</th>
                <th>Active Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {materials.map((mat) => (
                <tr key={mat.id} className={!mat.is_active ? styles.inactiveRow : undefined}>
                  <td><strong>{mat.name}</strong></td>
                  <td>{mat.material_code || '—'}</td>
                  <td><span style={{ textTransform: 'capitalize' }}>{mat.category}</span></td>
                  <td>{mat.unit_of_measure}</td>
                  <td>₹{Number(mat.purchase_approval_limit).toFixed(2)}</td>
                  <td>
                    <StatusBadge status={mat.is_active ? 'active' : 'inactive'} />
                  </td>
                  <td>
                    <div className={styles.actionBtns}>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStartEdit(mat.id)}
                        data-testid={`edit-btn-${mat.id}`}
                      >
                        Edit
                      </Button>
                      {mat.is_active ? (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => handleDeactivate(mat.id, mat.name)}
                          data-testid={`deactivate-btn-${mat.id}`}
                        >
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleActivate(mat.id, mat.name)}
                          data-testid={`activate-btn-${mat.id}`}
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

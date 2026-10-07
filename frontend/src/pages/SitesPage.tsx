import React, { useEffect, useState } from 'react';
import {
  createSiteApi,
  deleteSiteApi,
  getProjectsApi,
  getSitesApi,
  updateSiteApi,
  type ProjectResponseData,
  type SiteResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDeleteModal } from '../components/ui/ConfirmDeleteModal';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const SitesPage: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';

  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Deletion state
  const [deleteTarget, setDeleteTarget] = useState<SiteResponseData | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [address, setAddress] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [permittedRadiusM, setPermittedRadiusM] = useState<string>('100');
  const [isActive, setIsActive] = useState<boolean>(true);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchData = async () => {
    setError(null);
    try {
      const [siteData, projData] = await Promise.all([getSitesApi(), getProjectsApi()]);
      setSites(siteData);
      setProjects(projData);
      if (projData.length > 0 && !projectId) {
        setProjectId(projData[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load site data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const resetForm = () => {
    setName('');
    setAddress('');
    setLocation('');
    setPermittedRadiusM('100');
    setIsActive(true);
    if (projects.length > 0) {
      setProjectId(projects[0].id);
    }
    setEditingId(null);
    setFormError(null);
    setShowForm(false);
  };

  const handleStartCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleStartEdit = (site: SiteResponseData) => {
    setFormError(null);
    setSuccessMsg(null);
    setEditingId(site.id);
    setName(site.name);
    setProjectId(site.project_id);
    setAddress(site.address || '');
    setLocation(site.location || '');
    setPermittedRadiusM(site.permitted_radius_m !== null && site.permitted_radius_m !== undefined ? String(site.permitted_radius_m) : '100');
    setIsActive(site.is_active);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaveSite = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim() || name.trim().length < 2) {
      setFormError('Site name must be at least 2 characters');
      return;
    }

    if (!projectId) {
      setFormError('Please select a valid project');
      return;
    }

    const radiusVal = permittedRadiusM ? parseFloat(permittedRadiusM) : undefined;
    if (radiusVal !== undefined && (isNaN(radiusVal) || radiusVal < 0)) {
      setFormError('Permitted radius must be a positive number');
      return;
    }

    setSubmitting(true);
    try {
      if (editingId) {
        await updateSiteApi(editingId, {
          name: name.trim(),
          project_id: projectId,
          address: address.trim() || null,
          location: location.trim() || null,
          permitted_radius_m: radiusVal,
          is_active: isActive,
        });
        setSuccessMsg(`Site "${name.trim()}" updated successfully!`);
      } else {
        await createSiteApi({
          name: name.trim(),
          project_id: projectId,
          address: address.trim() || undefined,
          location: location.trim() || undefined,
          permitted_radius_m: radiusVal,
          is_active: true,
        });
        setSuccessMsg(`Site "${name.trim()}" created successfully!`);
      }

      resetForm();
      await fetchData();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message || (editingId ? 'Failed to update site' : 'Failed to create site'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    setDeleteError(null);
    setSuccessMsg(null);
    try {
      await deleteSiteApi(deleteTarget.id);
      setSuccessMsg(`Site "${deleteTarget.name}" deleted successfully.`);
      setDeleteTarget(null);
      await fetchData();
    } catch (err: any) {
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete site.');
    } finally {
      setIsDeleting(false);
    }
  };

  const getProjectName = (pid: string): string => {
    const p = projects.find((item) => item.id === pid);
    return p ? p.name : pid;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold' }}>Site Management</h2>
          <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)' }}>
            Manage construction sites and geofence radii under projects
          </p>
        </div>
        {isAdmin && (
          <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-site-btn">
            {showForm ? 'Cancel' : '+ Add Site'}
          </Button>
        )}
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--color-primary-50)', color: 'var(--color-primary-800)', borderRadius: 'var(--radius-md)', fontWeight: 500 }} data-testid="success-banner">
          {successMsg}
        </div>
      )}

      {deleteError && <ErrorMessage title="Deletion Error" message={deleteError} />}

      {error && <ErrorMessage title="Failed to Load Data" message={error} onRetry={fetchData} />}

      {showForm && (
        <Card
          title={editingId ? 'Edit Construction Site' : 'Register New Construction Site'}
          subtitle={editingId ? 'Update existing site details' : 'Fill in site details according to master schema'}
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSaveSite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Select
              label="Select Project *"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              options={projects.map((p) => ({ value: p.id, label: p.name }))}
              required
              data-testid="site-project-select"
            />
            <Input
              label="Site Name *"
              placeholder="e.g. Tower A Construction Site"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              data-testid="site-name-input"
            />
            <Input
              label="Site Address"
              placeholder="e.g. Sector 62, MG Road, Bengaluru"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              data-testid="site-address-input"
            />
            <Input
              label="Location (GPS / Address)"
              placeholder="e.g. 12.9716, 77.5946"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              data-testid="site-location-input"
            />
            <Input
              label="Permitted Radius (meters)"
              type="number"
              min="0"
              placeholder="100"
              value={permittedRadiusM}
              onChange={(e) => setPermittedRadiusM(e.target.value)}
              inputMode="numeric"
              data-testid="site-radius-input"
            />
            {editingId && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                <input
                  type="checkbox"
                  id="site-active-toggle"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  data-testid="site-active-checkbox"
                />
                <label htmlFor="site-active-toggle" style={{ fontWeight: 500, cursor: 'pointer' }}>
                  Active Site
                </label>
              </div>
            )}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-site-btn">
                {editingId ? 'Update Site' : 'Save Site'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading sites..." />
      ) : sites.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-neutral-700)' }}>
            <p>No sites found. Click <strong>+ Add Site</strong> to create the first site.</p>
          </div>
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {sites.map((site) => (
            <Card key={site.id} title={site.name}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                <div>
                  <strong>Project:</strong> {getProjectName(site.project_id)}
                </div>
                <div>
                  <strong>Status:</strong>{' '}
                  <StatusBadge status={site.is_active ? 'active' : 'inactive'} />
                </div>
                {site.address && (
                  <div>
                    <strong>Address:</strong> {site.address}
                  </div>
                )}
                {site.permitted_radius_m !== null && site.permitted_radius_m !== undefined && (
                  <div>
                    <strong>Geofence Radius:</strong> {site.permitted_radius_m} m
                  </div>
                )}
                {isAdmin && (
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--color-neutral-200)' }}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleStartEdit(site)}
                      data-testid={`edit-site-${site.id}`}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        setDeleteError(null);
                        setDeleteTarget(site);
                      }}
                      data-testid={`delete-site-${site.id}`}
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmDeleteModal
        isOpen={!!deleteTarget}
        title="Delete Site"
        message={
          deleteTarget && (
            <div>
              <p>
                Are you sure you want to permanently delete site <strong>{deleteTarget.name}</strong>?
              </p>
              <p style={{ marginTop: '8px', color: 'var(--color-neutral-600)' }}>
                Project: {getProjectName(deleteTarget.project_id)}
              </p>
              <p style={{ marginTop: '8px', color: 'var(--color-neutral-600)' }}>
                This will also permanently delete all attendance records, daily work entries, work orders, and worker assignments at this site.
              </p>
            </div>
          )
        }
        confirmLabel="Delete Site"
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setDeleteTarget(null);
        }}
      />
    </div>
  );
};

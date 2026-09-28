import React, { useEffect, useState } from 'react';
import {
  createSiteApi,
  getProjectsApi,
  getSitesApi,
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

export const SitesPage: React.FC = () => {
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [address, setAddress] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [permittedRadiusM, setPermittedRadiusM] = useState<string>('100');
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

  const handleCreateSite = async (e: React.FormEvent) => {
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
      await createSiteApi({
        name: name.trim(),
        project_id: projectId,
        address: address.trim() || undefined,
        location: location.trim() || undefined,
        permitted_radius_m: radiusVal,
        is_active: true,
      });

      setSuccessMsg(`Site "${name.trim()}" created successfully!`);
      setName('');
      setAddress('');
      setLocation('');
      setPermittedRadiusM('100');
      setShowForm(false);
      await fetchData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create site');
    } finally {
      setSubmitting(false);
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
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Site'}
        </Button>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--color-primary-50)', color: 'var(--color-primary-800)', borderRadius: 'var(--radius-md)', fontWeight: 500 }}>
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Failed to Load Data" message={error} onRetry={fetchData} />}

      {showForm && (
        <Card title="Register New Construction Site" subtitle="Fill in site details according to master schema">
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleCreateSite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Select
              label="Select Project *"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              options={projects.map((p) => ({ value: p.id, label: p.name }))}
              required
            />
            <Input
              label="Site Name *"
              placeholder="e.g. Tower A Construction Site"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              label="Site Address"
              placeholder="e.g. Sector 62, MG Road, Bengaluru"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
            <Input
              label="Location (GPS / Address)"
              placeholder="e.g. 12.9716, 77.5946"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            <Input
              label="Permitted Radius (meters)"
              type="number"
              min="0"
              placeholder="100"
              value={permittedRadiusM}
              onChange={(e) => setPermittedRadiusM(e.target.value)}
              inputMode="numeric"
            />
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting}>
                Save Site
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
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

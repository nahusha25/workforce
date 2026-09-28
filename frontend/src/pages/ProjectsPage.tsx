import React, { useEffect, useState } from 'react';
import {
  createProjectApi,
  getClientsApi,
  getProjectsApi,
  type ClientResponseData,
  type ProjectResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [clientId, setClientId] = useState<string>('');
  const [status, setStatus] = useState<string>('Active');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);

  const fetchData = async () => {
    setError(null);
    try {
      const [projData, clientData] = await Promise.all([getProjectsApi(), getClientsApi()]);
      setProjects(projData);
      setClients(clientData);
      if (clientData.length > 0 && !clientId) {
        setClientId(clientData[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim() || name.trim().length < 2) {
      setFormError('Project name must be at least 2 characters');
      return;
    }

    if (!clientId) {
      setFormError('Please select a valid client');
      return;
    }

    setSubmitting(true);
    try {
      await createProjectApi({
        name: name.trim(),
        client_id: clientId,
        status: status.trim() || 'Active',
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      setSuccessMsg(`Project "${name.trim()}" created successfully!`);
      setName('');
      setStartDate('');
      setEndDate('');
      setShowForm(false);
      await fetchData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  const getClientName = (cid: string): string => {
    const c = clients.find((item) => item.id === cid);
    return c ? c.name : cid;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold' }}>Project Management</h2>
          <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)' }}>
            Manage construction projects linked to clients
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Project'}
        </Button>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--color-primary-50)', color: 'var(--color-primary-800)', borderRadius: 'var(--radius-md)', fontWeight: 500 }}>
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Failed to Load Data" message={error} onRetry={fetchData} />}

      {showForm && (
        <Card title="Register New Project" subtitle="Fill in project details according to master schema">
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Select
              label="Select Client *"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              options={clients.map((c) => ({ value: c.id, label: c.name }))}
              required
            />
            <Input
              label="Project Name *"
              placeholder="e.g. Sunrise Heights Phase 1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Select
              label="Status *"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[
                { value: 'Active', label: 'Active' },
                { value: 'Planned', label: 'Planned' },
                { value: 'Completed', label: 'Completed' },
                { value: 'On Hold', label: 'On Hold' },
              ]}
              required
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <Input
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <Input
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting}>
                Save Project
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading projects..." />
      ) : projects.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-neutral-700)' }}>
            <p>No projects found. Click <strong>+ Add Project</strong> to create the first project.</p>
          </div>
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {projects.map((project) => (
            <Card key={project.id} title={project.name}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                <div>
                  <strong>Client:</strong> {getClientName(project.client_id)}
                </div>
                <div>
                  <strong>Status:</strong>{' '}
                  <StatusBadge
                    status={project.status === 'Active' ? 'active' : 'draft'}
                    label={project.status}
                  />
                </div>
                {project.start_date && (
                  <div>
                    <strong>Start Date:</strong> {project.start_date}
                  </div>
                )}
                {project.end_date && (
                  <div>
                    <strong>End Date:</strong> {project.end_date}
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

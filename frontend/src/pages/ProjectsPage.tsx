import React, { useEffect, useState } from 'react';
import {
  createProjectApi,
  deleteProjectApi,
  getClientsApi,
  getProjectsApi,
  updateProjectApi,
  type ClientResponseData,
  type ProjectResponseData,
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

export const ProjectsPage: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';

  const [projects, setProjects] = useState<ProjectResponseData[]>([]);
  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Deletion state
  const [deleteTarget, setDeleteTarget] = useState<ProjectResponseData | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
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

  const resetForm = () => {
    setName('');
    setStartDate('');
    setEndDate('');
    setStatus('Active');
    if (clients.length > 0) {
      setClientId(clients[0].id);
    }
    setEditingId(null);
    setFormError(null);
    setShowForm(false);
  };

  const handleStartCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleStartEdit = (project: ProjectResponseData) => {
    setFormError(null);
    setSuccessMsg(null);
    setEditingId(project.id);
    setName(project.name);
    setClientId(project.client_id);
    setStatus(project.status);
    setStartDate(project.start_date || '');
    setEndDate(project.end_date || '');
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaveProject = async (e: React.FormEvent) => {
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
      if (editingId) {
        await updateProjectApi(editingId, {
          name: name.trim(),
          client_id: clientId,
          status: status.trim() || 'Active',
          start_date: startDate || null,
          end_date: endDate || null,
        });
        setSuccessMsg(`Project "${name.trim()}" updated successfully!`);
      } else {
        await createProjectApi({
          name: name.trim(),
          client_id: clientId,
          status: status.trim() || 'Active',
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        });
        setSuccessMsg(`Project "${name.trim()}" created successfully!`);
      }

      resetForm();
      await fetchData();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message || (editingId ? 'Failed to update project' : 'Failed to create project'));
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
      await deleteProjectApi(deleteTarget.id);
      setSuccessMsg(`Project "${deleteTarget.name}" deleted successfully.`);
      setDeleteTarget(null);
      await fetchData();
    } catch (err: any) {
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete project.');
    } finally {
      setIsDeleting(false);
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
        {isAdmin && (
          <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-project-btn">
            {showForm ? 'Cancel' : '+ Add Project'}
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
          title={editingId ? 'Edit Project' : 'Register New Project'}
          subtitle={editingId ? 'Update existing project details' : 'Fill in project details according to master schema'}
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSaveProject} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Select
              label="Select Client *"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              options={clients.map((c) => ({ value: c.id, label: c.name }))}
              required
              data-testid="project-client-select"
            />
            <Input
              label="Project Name *"
              placeholder="e.g. Sunrise Heights Phase 1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              data-testid="project-name-input"
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
              data-testid="project-status-select"
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <Input
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                data-testid="project-start-date-input"
              />
              <Input
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                data-testid="project-end-date-input"
              />
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-project-btn">
                {editingId ? 'Update Project' : 'Save Project'}
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
                {isAdmin && (
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--color-neutral-200)' }}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleStartEdit(project)}
                      data-testid={`edit-project-${project.id}`}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        setDeleteError(null);
                        setDeleteTarget(project);
                      }}
                      data-testid={`delete-project-${project.id}`}
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
        title="Delete Project"
        message={
          deleteTarget && (
            <div>
              <p>
                Are you sure you want to permanently delete project <strong>{deleteTarget.name}</strong>?
              </p>
              <p style={{ marginTop: '8px', color: 'var(--color-neutral-600)' }}>
                Client: {getClientName(deleteTarget.client_id)} &bull; Status: {deleteTarget.status}
              </p>
              <p style={{ marginTop: '8px', color: 'var(--color-neutral-600)' }}>
                This will also permanently delete all sites, work orders, and work entries under this project.
              </p>
            </div>
          )
        }
        confirmLabel="Delete Project"
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setDeleteTarget(null);
        }}
      />
    </div>
  );
};

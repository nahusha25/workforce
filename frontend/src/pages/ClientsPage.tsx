import React, { useEffect, useState } from 'react';
import {
  createClientApi,
  deleteClientApi,
  getClientsApi,
  updateClientApi,
  type ClientResponseData,
} from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDeleteModal } from '../components/ui/ConfirmDeleteModal';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const ClientsPage: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';

  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Deletion state
  const [deleteTarget, setDeleteTarget] = useState<ClientResponseData | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [contactPerson, setContactPerson] = useState<string>('');
  const [contactMobile, setContactMobile] = useState<string>('');
  const [isActive, setIsActive] = useState<boolean>(true);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchClients = async () => {
    setError(null);
    try {
      const data = await getClientsApi();
      setClients(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const resetForm = () => {
    setName('');
    setContactPerson('');
    setContactMobile('');
    setIsActive(true);
    setEditingId(null);
    setFormError(null);
    setShowForm(false);
  };

  const handleStartCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleStartEdit = (client: ClientResponseData) => {
    setFormError(null);
    setSuccessMsg(null);
    setEditingId(client.id);
    setName(client.name);
    setContactPerson(client.contact_person || '');
    setContactMobile(client.contact_mobile || '');
    setIsActive(client.is_active);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaveClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim() || name.trim().length < 2) {
      setFormError('Client name must be at least 2 characters');
      return;
    }

    setSubmitting(true);
    try {
      if (editingId) {
        await updateClientApi(editingId, {
          name: name.trim(),
          contact_person: contactPerson.trim() || null,
          contact_mobile: contactMobile.trim() || null,
          is_active: isActive,
        });
        setSuccessMsg(`Client "${name.trim()}" updated successfully!`);
      } else {
        await createClientApi({
          name: name.trim(),
          contact_person: contactPerson.trim() || undefined,
          contact_mobile: contactMobile.trim() || undefined,
          is_active: true,
        });
        setSuccessMsg(`Client "${name.trim()}" created successfully!`);
      }

      resetForm();
      await fetchClients();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message || (editingId ? 'Failed to update client' : 'Failed to create client'));
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
      await deleteClientApi(deleteTarget.id);
      setSuccessMsg(`Client "${deleteTarget.name}" deleted successfully.`);
      setDeleteTarget(null);
      await fetchClients();
    } catch (err: any) {
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete client.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold' }}>Client Management</h2>
          <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)' }}>
            Manage client records for construction projects
          </p>
        </div>
        {isAdmin && (
          <Button onClick={showForm ? resetForm : handleStartCreate} data-testid="add-client-btn">
            {showForm ? 'Cancel' : '+ Add Client'}
          </Button>
        )}
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--color-primary-50)', color: 'var(--color-primary-800)', borderRadius: 'var(--radius-md)', fontWeight: 500 }} data-testid="success-banner">
          {successMsg}
        </div>
      )}

      {deleteError && <ErrorMessage title="Deletion Error" message={deleteError} />}

      {error && <ErrorMessage title="Failed to Load Data" message={error} onRetry={fetchClients} />}

      {showForm && (
        <Card
          title={editingId ? 'Edit Client' : 'Register New Client'}
          subtitle={editingId ? 'Update existing client details' : 'Fill in client details according to master schema'}
        >
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleSaveClient} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Input
              label="Client Name *"
              placeholder="e.g. Acme Construction Corp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              data-testid="client-name-input"
            />
            <Input
              label="Contact Person"
              placeholder="e.g. Jane Doe"
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
              data-testid="client-contact-person-input"
            />
            <Input
              label="Contact Mobile"
              placeholder="e.g. +919876543210"
              value={contactMobile}
              onChange={(e) => setContactMobile(e.target.value)}
              inputMode="tel"
              data-testid="client-contact-mobile-input"
            />
            {editingId && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                <input
                  type="checkbox"
                  id="client-active-toggle"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  data-testid="client-active-checkbox"
                />
                <label htmlFor="client-active-toggle" style={{ fontWeight: 500, cursor: 'pointer' }}>
                  Active Client
                </label>
              </div>
            )}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting} data-testid="save-client-btn">
                {editingId ? 'Update Client' : 'Save Client'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingSpinner label="Loading clients..." />
      ) : clients.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-neutral-700)' }}>
            <p>No clients found. Click <strong>+ Add Client</strong> to create the first client.</p>
          </div>
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {clients.map((client) => (
            <Card key={client.id} title={client.name}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: 'var(--font-size-sm)' }}>
                <div>
                  <strong>Status:</strong>{' '}
                  <StatusBadge status={client.is_active ? 'active' : 'inactive'} />
                </div>
                {client.contact_person && (
                  <div>
                    <strong>Contact Person:</strong> {client.contact_person}
                  </div>
                )}
                {client.contact_mobile && (
                  <div>
                    <strong>Mobile:</strong> {client.contact_mobile}
                  </div>
                )}
                <div style={{ color: 'var(--color-neutral-500)', fontSize: 'var(--font-size-xs)', marginTop: '8px' }}>
                  Registered on: {new Date(client.created_at).toLocaleDateString()}
                </div>
                {isAdmin && (
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--color-neutral-200)' }}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleStartEdit(client)}
                      data-testid={`edit-client-${client.id}`}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        setDeleteError(null);
                        setDeleteTarget(client);
                      }}
                      data-testid={`delete-client-${client.id}`}
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
        title="Delete Client"
        message={
          deleteTarget && (
            <div>
              <p>
                Are you sure you want to permanently delete client <strong>{deleteTarget.name}</strong>?
              </p>
              <p style={{ marginTop: '8px', color: 'var(--color-neutral-600)' }}>
                This will also permanently delete all associated projects, sites, and work records under this client.
              </p>
            </div>
          )
        }
        confirmLabel="Delete Client"
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setDeleteTarget(null);
        }}
      />
    </div>
  );
};

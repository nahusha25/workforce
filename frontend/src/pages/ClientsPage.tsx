import React, { useEffect, useState } from 'react';
import { createClientApi, getClientsApi, type ClientResponseData } from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { StatusBadge } from '../components/ui/StatusBadge';

export const ClientsPage: React.FC = () => {
  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [contactPerson, setContactPerson] = useState<string>('');
  const [contactMobile, setContactMobile] = useState<string>('');
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

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!name.trim() || name.trim().length < 2) {
      setFormError('Client name must be at least 2 characters');
      return;
    }

    setSubmitting(true);
    try {
      await createClientApi({
        name: name.trim(),
        contact_person: contactPerson.trim() || undefined,
        contact_mobile: contactMobile.trim() || undefined,
        is_active: true,
      });

      setSuccessMsg(`Client "${name.trim()}" created successfully!`);
      setName('');
      setContactPerson('');
      setContactMobile('');
      setShowForm(false);
      await fetchClients();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create client');
    } finally {
      setSubmitting(false);
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
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Client'}
        </Button>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--color-primary-50)', color: 'var(--color-primary-800)', borderRadius: 'var(--radius-md)', fontWeight: 500 }}>
          {successMsg}
        </div>
      )}

      {error && <ErrorMessage title="Failed to Load Data" message={error} onRetry={fetchClients} />}

      {showForm && (
        <Card title="Register New Client" subtitle="Fill in client details according to master schema">
          {formError && <ErrorMessage message={formError} />}
          <form onSubmit={handleCreateClient} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Input
              label="Client Name *"
              placeholder="e.g. Acme Construction Corp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              label="Contact Person"
              placeholder="e.g. Jane Doe"
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
            />
            <Input
              label="Contact Mobile"
              placeholder="e.g. +919876543210"
              value={contactMobile}
              onChange={(e) => setContactMobile(e.target.value)}
              inputMode="tel"
            />
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={submitting}>
                Save Client
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
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

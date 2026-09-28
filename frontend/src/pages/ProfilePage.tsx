import React from 'react';
import { Card } from '../components/ui/Card';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';

export const ProfilePage: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <Card title="User Profile" subtitle="Authenticated Employee Details">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div>
            <strong>Name:</strong>
            <p>{user.name}</p>
          </div>
          <div>
            <strong>Employee Code:</strong>
            <p>{user.employee_code}</p>
          </div>
          <div>
            <strong>Mobile Number:</strong>
            <p>{user.mobile_id}</p>
          </div>
          <div>
            <strong>System Role:</strong>
            <p>
              <StatusBadge status="active" label={user.system_role} />
            </p>
          </div>
        </div>
      </Card>

      {user.trade_roles && user.trade_roles.length > 0 && (
        <Card title="Assigned Trade Roles">
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {user.trade_roles.map((r) => (
              <StatusBadge key={r.id} status="submitted" label={r.name} />
            ))}
          </div>
        </Card>
      )}

      {user.current_rate && (
        <Card title="Active Rate">
          <p>
            <strong>{user.current_rate.rate_type.toUpperCase()} Rate:</strong> ₹
            {user.current_rate.rate_amount} (Effective from {user.current_rate.effective_from})
          </p>
        </Card>
      )}

      {user.active_sites && user.active_sites.length > 0 && (
        <Card title="Assigned Sites">
          <ul style={{ paddingLeft: '20px' }}>
            {user.active_sites.map((s) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
};

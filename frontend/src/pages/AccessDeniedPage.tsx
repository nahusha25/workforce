import React from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

export const AccessDeniedPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: '500px', margin: '60px auto' }}>
      <Card title="403 — Access Denied" subtitle="Insufficient Permissions">
        <p style={{ color: 'var(--color-neutral-700)', marginBottom: '16px' }}>
          You do not have the required system role to access this resource. Please contact your administrator if you believe this is an error.
        </p>
        <Button onClick={() => navigate('/profile')}>Return to Profile</Button>
      </Card>
    </div>
  );
};

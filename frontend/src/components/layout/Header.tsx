import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { StatusBadge } from '../ui/StatusBadge';
import { Button } from '../ui/Button';
import styles from './Header.module.css';

export const Header: React.FC = () => {
  const { user, role, logout } = useAuth();

  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.logoText}>Workforce</span>
        {role && (
          <StatusBadge
            status={role === 'administrator' ? 'approved' : role === 'supervisor' ? 'submitted' : 'draft'}
            label={role}
          />
        )}
      </div>

      {user && (
        <div className={styles.userSection}>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{user.name}</span>
            <span className={styles.userCode}>{user.employee_code}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            Logout
          </Button>
        </div>
      )}
    </header>
  );
};

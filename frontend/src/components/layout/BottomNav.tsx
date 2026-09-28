import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './BottomNav.module.css';

export const BottomNav: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';
  const isSupervisor = role === 'supervisor' || role === 'administrator' || role === 'director';

  return (
    <nav className={styles.bottomNav}>
      <NavLink
        to="/profile"
        className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
      >
        <span>Profile</span>
      </NavLink>
      <NavLink
        to="/attendance"
        className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
      >
        <span>Attendance</span>
      </NavLink>
      {role === 'employee' && (
        <NavLink
          to="/daily-work"
          className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
        >
          <span>Daily Work</span>
        </NavLink>
      )}
      {isSupervisor && (
        <NavLink
          to="/supervisor/attendance"
          className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
        >
          <span>Team</span>
        </NavLink>
      )}

      {isAdmin && (
        <>
          <NavLink
            to="/onboarding"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <span>Onboard</span>
          </NavLink>
          <NavLink
            to="/admin/clients"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <span>Clients</span>
          </NavLink>
          <NavLink
            to="/admin/sites"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            <span>Sites</span>
          </NavLink>
        </>
      )}
    </nav>
  );
};

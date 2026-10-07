import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './Sidebar.module.css';

export const Sidebar: React.FC = () => {
  const { role } = useAuth();
  const isAdmin = role === 'administrator';
  const isSupervisor = role === 'supervisor' || role === 'administrator' || role === 'director';
  const isAdminOrDirector = role === 'administrator' || role === 'director';

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        <div className={styles.sectionTitle}>Main</div>
        <NavLink
          to="/profile"
          className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
        >
          My Profile
        </NavLink>
        {role === 'employee' && (
          <NavLink
            to="/attendance"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            My Attendance
          </NavLink>
        )}
        {role === 'employee' && (
          <NavLink
            to="/daily-work"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            Daily Work
          </NavLink>
        )}
        {isSupervisor && (
          <>
            <NavLink
              to="/supervisor/attendance"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Team Attendance
            </NavLink>
            <NavLink
              to="/verification"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Verification
            </NavLink>
          </>
        )}

        {isAdminOrDirector && (
          <>
            <div className={styles.sectionTitle}>Administration</div>
            {isAdmin && (
              <NavLink
                to="/onboarding"
                className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
              >
                Employee Onboarding
              </NavLink>
            )}
            <NavLink
              to="/admin/employees"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Employees
            </NavLink>
            {isAdmin && (
              <>
                <NavLink
                  to="/admin/clients"
                  className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
                >
                  Clients
                </NavLink>
                <NavLink
                  to="/admin/projects"
                  className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
                >
                  Projects
                </NavLink>
                <NavLink
                  to="/admin/sites"
                  className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
                >
                  Sites
                </NavLink>
              </>
            )}
          </>
        )}

        {isAdminOrDirector && (
          <>
            <div className={styles.sectionTitle}>Master Data</div>
            <NavLink
              to="/admin/work-orders"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Work Orders
            </NavLink>
            <NavLink
              to="/admin/activities"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Activities
            </NavLink>
            <NavLink
              to="/admin/materials"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Materials
            </NavLink>
            <div className={styles.sectionTitle}>Analytics & Reports</div>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/reports/attendance"
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              Reports
            </NavLink>
          </>
        )}
      </nav>
    </aside>
  );
};

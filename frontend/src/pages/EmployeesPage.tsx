import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllEmployeesApi, type EmployeeResponseData } from '../api/employee';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select, type SelectOption } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import styles from './EmployeesPage.module.css';

export const EmployeesPage: React.FC = () => {
  const navigate = useNavigate();
  const { role } = useAuth();
  const isAdmin = role === 'administrator';

  const [employees, setEmployees] = useState<EmployeeResponseData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      // Aggregates all pages client-side until response < 100 for true total count
      const allData = await getAllEmployeesApi(100);
      setEmployees(allData);
    } catch (err: any) {
      setError(err.message || 'Failed to load employees');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const roleOptions: SelectOption[] = [
    { value: 'all', label: 'All Roles' },
    { value: 'employee', label: 'Field Worker' },
    { value: 'supervisor', label: 'Supervisor' },
    { value: 'director', label: 'Director' },
    { value: 'administrator', label: 'Administrator' },
  ];

  const statusOptions: SelectOption[] = [
    { value: 'all', label: 'All Statuses' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' },
  ];

  const filteredEmployees = useMemo(() => {
    return employees.filter((emp) => {
      // Search matching code, name, or phone number
      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        !term ||
        emp.name.toLowerCase().includes(term) ||
        emp.employee_code.toLowerCase().includes(term) ||
        emp.mobile_id.toLowerCase().includes(term);

      // Role filter
      const matchesRole = roleFilter === 'all' || emp.system_role === roleFilter;

      // Status filter
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && emp.is_active) ||
        (statusFilter === 'inactive' && !emp.is_active);

      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [employees, searchTerm, roleFilter, statusFilter]);

  const getRoleBadgeClass = (systemRole: string) => {
    switch (systemRole) {
      case 'administrator':
        return styles.roleAdministrator;
      case 'director':
        return styles.roleDirector;
      case 'supervisor':
        return styles.roleSupervisor;
      default:
        return styles.roleEmployee;
    }
  };

  return (
    <div className={styles.container}>
      {/* Header with Title, True Total Count Badge, and Action */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <div className={styles.titleWithCount}>
            <h2>Employee Directory</h2>
            <span className={styles.countBadge} data-testid="total-employees-count">
              Total: {employees.length}
            </span>
          </div>
          <p>View and manage all registered employees and workforce assignments</p>
        </div>

        <div className={styles.headerActions}>
          {isAdmin && (
            <Button onClick={() => navigate('/onboarding')} data-testid="onboard-employee-btn">
              + Onboard Employee
            </Button>
          )}
        </div>
      </div>

      {error && (
        <ErrorMessage
          title="Failed to Load Employees"
          message={error}
          onRetry={fetchEmployees}
        />
      )}

      {/* Filter and Search Bar */}
      {!error && (
        <div className={styles.toolbar} role="search">
          <div className={styles.searchInput}>
            <Input
              placeholder="Search by name, code, or mobile..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Search employees"
            />
          </div>
          <div className={styles.filterSelect}>
            <Select
              options={roleOptions}
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              aria-label="Filter by role"
            />
          </div>
          <div className={styles.filterSelect}>
            <Select
              options={statusOptions}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
            />
          </div>
          {(searchTerm || roleFilter !== 'all' || statusFilter !== 'all') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchTerm('');
                setRoleFilter('all');
                setStatusFilter('all');
              }}
            >
              Reset Filters
            </Button>
          )}
        </div>
      )}

      {/* Main Content: Loading, Empty, or Table */}
      {loading ? (
        <LoadingSpinner label="Loading employees..." />
      ) : employees.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No employees registered yet.</p>
            {isAdmin && (
              <Button onClick={() => navigate('/onboarding')}>
                + Onboard First Employee
              </Button>
            )}
          </div>
        </Card>
      ) : filteredEmployees.length === 0 ? (
        <Card>
          <div className={styles.emptyState}>
            <p>No employees match the selected search or filter criteria.</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchTerm('');
                setRoleFilter('all');
                setStatusFilter('all');
              }}
            >
              Clear Filters
            </Button>
          </div>
        </Card>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable} aria-label="Employees Table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Mobile Number</th>
                <th>System Role</th>
                <th>Trade Roles</th>
                <th>Site Assignment</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmployees.map((emp) => (
                <tr
                  key={emp.id}
                  className={!emp.is_active ? styles.inactiveRow : undefined}
                  data-testid={`employee-row-${emp.id}`}
                >
                  <td>
                    <strong>{emp.employee_code}</strong>
                  </td>
                  <td>{emp.name}</td>
                  <td>{emp.mobile_id}</td>
                  <td>
                    <span
                      className={`${styles.roleBadge} ${getRoleBadgeClass(emp.system_role)}`}
                      data-testid={`role-badge-${emp.id}`}
                    >
                      {emp.system_role}
                    </span>
                  </td>
                  <td>
                    {emp.trade_roles && emp.trade_roles.length > 0
                      ? emp.trade_roles.map((r) => r.name).join(', ')
                      : '—'}
                  </td>
                  <td>
                    {emp.active_sites && emp.active_sites.length > 0 ? (
                      <div className={styles.tagList}>
                        {emp.active_sites.map((site) => (
                          <span key={site.id} className={styles.siteTag}>
                            {site.name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: 'var(--color-neutral-500)' }}>Unassigned</span>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={emp.is_active ? 'active' : 'inactive'} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

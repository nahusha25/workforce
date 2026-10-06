import React, { useEffect, useState, useMemo } from 'react';
import { RotateCcw } from 'lucide-react';
import { getClientsApi, getSitesApi, type ClientResponseData, type SiteResponseData } from '../../api/masterData';
import { getEmployeesApi, type EmployeeResponseData } from '../../api/employee';
import type { DashboardFilters } from '../../api/dashboard';
import { getLocalISODate } from '../../utils/date';
import styles from './FilterBar.module.css';

export interface FilterBarProps {
  filters: DashboardFilters;
  onFilterChange: (newFilters: Partial<DashboardFilters>) => void;
  onReset?: () => void;
  isLoading?: boolean;
  showEntityFilters?: boolean;
  children?: React.ReactNode;
}

export function getDefaultFilterDates(): { date_from: string; date_to: string } {
  const today = new Date();
  const past30 = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  return {
    date_to: getLocalISODate(today),
    date_from: getLocalISODate(past30),
  };
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  onReset,
  isLoading = false,
  showEntityFilters = true,
  children,
}) => {
  const [clients, setClients] = useState<ClientResponseData[]>([]);
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [employees, setEmployees] = useState<EmployeeResponseData[]>([]);
  const [dateError, setDateError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    Promise.allSettled([
      getClientsApi(),
      getSitesApi(),
      getEmployeesApi(0, 200),
    ]).then(([clientsRes, sitesRes, empsRes]) => {
      if (!isMounted) return;
      if (clientsRes.status === 'fulfilled') setClients(clientsRes.value);
      if (sitesRes.status === 'fulfilled') setSites(sitesRes.value);
      if (empsRes.status === 'fulfilled') setEmployees(empsRes.value);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  // Validate dates
  useEffect(() => {
    if (filters.date_from && filters.date_to) {
      if (filters.date_from > filters.date_to) {
        setDateError('From date must be earlier than or equal to To date');
        return;
      }
      const fromTime = new Date(filters.date_from).getTime();
      const toTime = new Date(filters.date_to).getTime();
      const daysDiff = Math.round((toTime - fromTime) / (1000 * 60 * 60 * 24));
      if (daysDiff > 365) {
        setDateError('Date range cannot exceed 365 days');
        return;
      }
    }
    setDateError(null);
  }, [filters.date_from, filters.date_to]);

  const supervisors = useMemo(() => {
    return employees.filter(
      (e) => e.system_role === 'supervisor' || e.system_role === 'administrator'
    );
  }, [employees]);

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ date_from: e.target.value });
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ date_to: e.target.value });
  };

  const handleClientChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    onFilterChange({ client_id: val });
  };

  const handleSiteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    onFilterChange({ site_id: val });
  };

  const handleEmployeeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    onFilterChange({ employee_id: val });
  };

  const handleSupervisorChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    onFilterChange({ supervisor_id: val });
  };

  const handleReset = () => {
    const defaults = getDefaultFilterDates();
    if (onReset) {
      onReset();
    } else {
      onFilterChange({
        ...defaults,
        client_id: null,
        site_id: null,
        employee_id: null,
        supervisor_id: null,
      });
    }
  };

  return (
    <div className={styles.filterBar} data-testid="dashboard-filter-bar">
      <div className={styles.formGrid}>
        {/* Date From */}
        <div className={styles.filterGroup}>
          <label htmlFor="filter-date-from" className={styles.label}>
            From Date
          </label>
          <input
            id="filter-date-from"
            type="date"
            className={`${styles.input} ${dateError ? styles.inputError : ''}`}
            value={filters.date_from || ''}
            onChange={handleDateFromChange}
            disabled={isLoading}
            data-testid="filter-date-from"
          />
        </div>

        {/* Date To */}
        <div className={styles.filterGroup}>
          <label htmlFor="filter-date-to" className={styles.label}>
            To Date
          </label>
          <input
            id="filter-date-to"
            type="date"
            className={`${styles.input} ${dateError ? styles.inputError : ''}`}
            value={filters.date_to || ''}
            onChange={handleDateToChange}
            disabled={isLoading}
            data-testid="filter-date-to"
          />
        </div>

        {showEntityFilters && (
          <>
            {/* Client Dropdown */}
            <div className={styles.filterGroup}>
              <label htmlFor="filter-client" className={styles.label}>
                Client
              </label>
              <select
                id="filter-client"
                className={styles.select}
                value={filters.client_id || ''}
                onChange={handleClientChange}
                disabled={isLoading}
                data-testid="filter-client"
              >
                <option value="">All Clients</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Site Dropdown */}
            <div className={styles.filterGroup}>
              <label htmlFor="filter-site" className={styles.label}>
                Site
              </label>
              <select
                id="filter-site"
                className={styles.select}
                value={filters.site_id || ''}
                onChange={handleSiteChange}
                disabled={isLoading}
                data-testid="filter-site"
              >
                <option value="">All Sites</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Supervisor Dropdown */}
            <div className={styles.filterGroup}>
              <label htmlFor="filter-supervisor" className={styles.label}>
                Supervisor
              </label>
              <select
                id="filter-supervisor"
                className={styles.select}
                value={filters.supervisor_id || ''}
                onChange={handleSupervisorChange}
                disabled={isLoading}
                data-testid="filter-supervisor"
              >
                <option value="">All Supervisors</option>
                {supervisors.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.employee_code})
                  </option>
                ))}
              </select>
            </div>

            {/* Employee Dropdown */}
            <div className={styles.filterGroup}>
              <label htmlFor="filter-employee" className={styles.label}>
                Employee
              </label>
              <select
                id="filter-employee"
                className={styles.select}
                value={filters.employee_id || ''}
                onChange={handleEmployeeChange}
                disabled={isLoading}
                data-testid="filter-employee"
              >
                <option value="">All Employees</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.employee_code})
                  </option>
                ))}
              </select>
            </div>
          </>
        )}

        {/* Reset Action */}
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.resetBtn}
            onClick={handleReset}
            disabled={isLoading}
            data-testid="filter-reset-btn"
          >
            <RotateCcw size={16} />
            Reset
          </button>
        </div>
      </div>

      {dateError && (
        <div className={styles.errorText} role="alert" data-testid="filter-date-error">
          {dateError}
        </div>
      )}

      {children && <div className={styles.extraFilters}>{children}</div>}
    </div>
  );
};

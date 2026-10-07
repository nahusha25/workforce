import React, { useEffect, useState } from 'react';
import {
  getEmployeesApi,
  updateEmployeeApi,
  type EmployeeResponseData,
  type EmployeeUpdateData,
} from '../../api/employee';
import {
  getRolesApi,
  getSitesApi,
  type RoleResponseData,
  type SiteResponseData,
} from '../../api/masterData';
import { Button } from '../ui/Button';
import { ErrorMessage } from '../ui/ErrorMessage';
import { Input } from '../ui/Input';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { Select, type SelectOption } from '../ui/Select';
import type { SystemRole } from '../../types/auth';
import styles from './EditEmployeeModal.module.css';

export interface EditEmployeeModalProps {
  isOpen: boolean;
  employee: EmployeeResponseData | null;
  onClose: () => void;
  onSaved: (updatedEmployee: EmployeeResponseData) => void;
}

export const EditEmployeeModal: React.FC<EditEmployeeModalProps> = ({
  isOpen,
  employee,
  onClose,
  onSaved,
}) => {
  const [prereqLoading, setPrereqLoading] = useState<boolean>(false);
  const [tradeRoles, setTradeRoles] = useState<RoleResponseData[]>([]);
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [supervisors, setSupervisors] = useState<EmployeeResponseData[]>([]);

  // Form states
  const [name, setName] = useState<string>('');
  const [mobileNumber, setMobileNumber] = useState<string>('');
  const [systemRole, setSystemRole] = useState<SystemRole>('employee');
  const [selectedTradeRoleIds, setSelectedTradeRoleIds] = useState<string[]>([]);
  const [rateType, setRateType] = useState<string>('daily');
  const [rateAmount, setRateAmount] = useState<string>('500');
  const [supervisorId, setSupervisorId] = useState<string>('');
  const [selectedSiteIds, setSelectedSiteIds] = useState<string[]>([]);
  const [isActive, setIsActive] = useState<boolean>(true);

  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch prerequisite master data when modal opens
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchPrereqs = async () => {
      setPrereqLoading(true);
      setError(null);
      try {
        const [rolesData, sitesData, empData] = await Promise.all([
          getRolesApi(),
          getSitesApi(),
          getEmployeesApi(0, 100),
        ]);
        if (!isMounted) return;
        setTradeRoles(rolesData);
        setSites(sitesData);
        // Exclude current employee from supervisor list
        const eligibleSupervisors = empData.filter(
          (e) => e.is_active && (!employee || e.id !== employee.id)
        );
        setSupervisors(eligibleSupervisors);
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load trade roles or sites');
        }
      } finally {
        if (isMounted) setPrereqLoading(false);
      }
    };

    fetchPrereqs();
    return () => {
      isMounted = false;
    };
  }, [isOpen, employee]);

  // Populate form fields from target employee
  useEffect(() => {
    if (employee && isOpen) {
      setName(employee.name || '');
      setMobileNumber(employee.mobile_id || '');
      setSystemRole(employee.system_role || 'employee');
      setSelectedTradeRoleIds(employee.trade_roles ? employee.trade_roles.map((r) => r.id) : []);
      setRateType(employee.current_rate?.rate_type || 'daily');
      setRateAmount(
        employee.current_rate?.rate_amount !== undefined && employee.current_rate?.rate_amount !== null
          ? String(employee.current_rate.rate_amount)
          : '500'
      );
      setSupervisorId(employee.supervisor_id || '');
      setSelectedSiteIds(employee.active_sites ? employee.active_sites.map((s) => s.id) : []);
      setIsActive(employee.is_active);
      setError(null);
    }
  }, [employee, isOpen]);

  // Keyboard accessibility: Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !saving) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, saving, onClose]);

  if (!isOpen || !employee) return null;

  const handleTradeRoleToggle = (roleId: string) => {
    setSelectedTradeRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
    );
  };

  const handleSiteToggle = (siteId: string) => {
    setSelectedSiteIds((prev) =>
      prev.includes(siteId) ? prev.filter((id) => id !== siteId) : [...prev, siteId]
    );
  };

  const formatMobileForApi = (val: string): string => {
    let clean = val.trim();
    if (clean.length === 10 && /^\d{10}$/.test(clean)) {
      return `+91${clean}`;
    }
    return clean;
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim() || name.trim().length < 2) {
      setError('Full Name must be at least 2 characters.');
      return;
    }

    const formattedMobile = formatMobileForApi(mobileNumber);
    if (!/^\+?[1-9]\d{7,14}$/.test(formattedMobile)) {
      setError('Enter a valid mobile number (10 digits).');
      return;
    }

    if (selectedTradeRoleIds.length === 0) {
      setError('At least one Trade Role must be selected.');
      return;
    }

    const numericRate = parseFloat(rateAmount);
    if (isNaN(numericRate) || numericRate < 0) {
      setError('Rate Amount must be a non-negative number.');
      return;
    }

    if (selectedSiteIds.length === 0) {
      setError('At least one Client Site must be assigned.');
      return;
    }

    setSaving(true);
    try {
      const payload: EmployeeUpdateData = {
        name: name.trim(),
        mobile_number: formattedMobile,
        system_role: systemRole,
        trade_role_ids: selectedTradeRoleIds,
        rate_type: rateType,
        rate_amount: numericRate,
        supervisor_id: supervisorId ? supervisorId : null,
        site_ids: selectedSiteIds,
        is_active: isActive,
      };

      const updated = await updateEmployeeApi(employee.id, payload);
      onSaved(updated);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to update employee details');
    } finally {
      setSaving(false);
    }
  };

  const systemRoleOptions: SelectOption[] = [
    { value: 'employee', label: 'Field Worker' },
    { value: 'supervisor', label: 'Supervisor' },
    { value: 'director', label: 'Director' },
    { value: 'administrator', label: 'Administrator' },
  ];

  const rateTypeOptions: SelectOption[] = [
    { value: 'daily', label: 'Daily Rate (INR / Day)' },
    { value: 'piece_rate', label: 'Piece Rate (Per Unit)' },
    { value: 'hourly', label: 'Hourly Rate (INR / Hr)' },
    { value: 'monthly', label: 'Monthly Fixed Rate' },
  ];

  const supervisorOptions: SelectOption[] = [
    { value: '', label: 'None (Direct Report / Management)' },
    ...supervisors.map((s) => ({
      value: s.id,
      label: `${s.name} (${s.employee_code}) - ${s.system_role}`,
    })),
  ];

  return (
    <div
      className={styles.modalOverlay}
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
      data-testid="edit-employee-modal-overlay"
    >
      <div
        className={styles.modalContent}
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-employee-modal-title"
      >
        <div className={styles.modalHeader}>
          <div className={styles.titleArea}>
            <h3 id="edit-employee-modal-title" className={styles.modalTitle}>
              Edit Employee: {employee.name} ({employee.employee_code})
            </h3>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            disabled={saving}
            aria-label="Close modal"
            data-testid="close-edit-employee-modal-btn"
          >
            &times;
          </button>
        </div>

        {prereqLoading ? (
          <div style={{ padding: '32px' }}>
            <LoadingSpinner label="Loading employee master configuration..." />
          </div>
        ) : (
          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <div className={styles.modalBody}>
              {error && <ErrorMessage message={error} />}

              <div className={styles.gridTwoCol}>
                <Input
                  label="Full Name *"
                  placeholder="e.g. Ramesh Kumar"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  data-testid="edit-emp-name-input"
                />
                <Input
                  label="Mobile Number *"
                  placeholder="e.g. 9876543210"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  required
                  inputMode="tel"
                  data-testid="edit-emp-mobile-input"
                />
              </div>

              <div className={styles.gridTwoCol}>
                <Select
                  label="System Role *"
                  value={systemRole}
                  onChange={(e) => setSystemRole(e.target.value as SystemRole)}
                  options={systemRoleOptions}
                  required
                  data-testid="edit-emp-system-role-select"
                />
                <Select
                  label="Reporting Supervisor"
                  value={supervisorId}
                  onChange={(e) => setSupervisorId(e.target.value)}
                  options={supervisorOptions}
                  data-testid="edit-emp-supervisor-select"
                />
              </div>

              <div className={styles.gridTwoCol}>
                <Select
                  label="Rate Type *"
                  value={rateType}
                  onChange={(e) => setRateType(e.target.value)}
                  options={rateTypeOptions}
                  required
                  data-testid="edit-emp-rate-type-select"
                />
                <Input
                  label="Rate Amount (INR) *"
                  type="number"
                  min="0"
                  step="0.01"
                  value={rateAmount}
                  onChange={(e) => setRateAmount(e.target.value)}
                  required
                  data-testid="edit-emp-rate-amount-input"
                />
              </div>

              {/* Trade Roles Checklist */}
              <div className={styles.formSection}>
                <label className={styles.sectionTitle}>Trade Roles * (Select all applicable)</label>
                <div className={styles.checkboxGrid} data-testid="edit-emp-trade-roles-container">
                  {tradeRoles.map((role) => (
                    <label key={role.id} className={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        checked={selectedTradeRoleIds.includes(role.id)}
                        onChange={() => handleTradeRoleToggle(role.id)}
                        data-testid={`trade-role-${role.id}`}
                      />
                      {role.name}
                    </label>
                  ))}
                </div>
              </div>

              {/* Sites Checklist */}
              <div className={styles.formSection}>
                <label className={styles.sectionTitle}>Assigned Client Sites * (Select at least one)</label>
                <div className={styles.checkboxGrid} data-testid="edit-emp-sites-container">
                  {sites.map((site) => (
                    <label key={site.id} className={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        checked={selectedSiteIds.includes(site.id)}
                        onChange={() => handleSiteToggle(site.id)}
                        data-testid={`site-assign-${site.id}`}
                      />
                      {site.name}
                    </label>
                  ))}
                </div>
              </div>

              {/* Active Status Toggle */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                <input
                  type="checkbox"
                  id="edit-emp-active-toggle"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  data-testid="edit-emp-active-checkbox"
                />
                <label htmlFor="edit-emp-active-toggle" style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)', cursor: 'pointer' }}>
                  Active Employee Account
                </label>
              </div>
            </div>

            <div className={styles.modalFooter}>
              <Button type="button" variant="outline" onClick={onClose} disabled={saving} data-testid="cancel-edit-emp-btn">
                Cancel
              </Button>
              <Button type="submit" isLoading={saving} data-testid="save-edit-emp-btn">
                Save Changes
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

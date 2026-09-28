import React, { useEffect, useState } from 'react';
import { createEmployeeApi, getEmployeesApi, type EmployeeResponseData } from '../api/employee';
import { getRolesApi, getSitesApi, type RoleResponseData, type SiteResponseData } from '../api/masterData';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import type { SystemRole } from '../types/auth';
import styles from './OnboardingPage.module.css';

export const OnboardingPage: React.FC = () => {
  // Prerequisite Master Data
  const [tradeRoles, setTradeRoles] = useState<RoleResponseData[]>([]);
  const [sites, setSites] = useState<SiteResponseData[]>([]);
  const [supervisors, setSupervisors] = useState<EmployeeResponseData[]>([]);
  const [recentEmployees, setRecentEmployees] = useState<EmployeeResponseData[]>([]);

  // Page State
  const [dataLoading, setDataLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Form Fields
  const [name, setName] = useState<string>('');
  const [mobileNumber, setMobileNumber] = useState<string>('');
  const [employeeCode, setEmployeeCode] = useState<string>('');
  const [systemRole, setSystemRole] = useState<SystemRole>('employee');
  const [selectedTradeRoleIds, setSelectedTradeRoleIds] = useState<string[]>([]);
  const [rateType, setRateType] = useState<string>('daily');
  const [rateAmount, setRateAmount] = useState<string>('500');
  const [supervisorId, setSupervisorId] = useState<string>('');
  const [selectedSiteIds, setSelectedSiteIds] = useState<string[]>([]);

  const fetchPrerequisites = async () => {
    setError(null);
    try {
      const [rolesData, sitesData, empData] = await Promise.all([
        getRolesApi(),
        getSitesApi(),
        getEmployeesApi(0, 100),
      ]);
      setTradeRoles(rolesData);
      setSites(sitesData);
      setRecentEmployees(empData);

      // Filter active employees eligible for supervisor role
      const validSupervisors = empData.filter(
        (e) => e.is_active && (e.system_role === 'supervisor' || e.system_role === 'administrator')
      );
      setSupervisors(validSupervisors.length > 0 ? validSupervisors : empData.filter((e) => e.is_active));
    } catch (err: any) {
      setError(err.message || 'Failed to load prerequisite data for onboarding');
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    fetchPrerequisites();
  }, []);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    // Client-side validations matching backend Pydantic rules
    if (!name.trim() || name.trim().length < 2) {
      setFormError('Full Name must be at least 2 characters.');
      return;
    }

    const formattedMobile = formatMobileForApi(mobileNumber);
    if (!/^\+?[1-9]\d{7,14}$/.test(formattedMobile)) {
      setFormError('Enter a valid 10-digit mobile number.');
      return;
    }

    if (!employeeCode.trim()) {
      setFormError('Employee Code is required.');
      return;
    }

    if (selectedTradeRoleIds.length === 0) {
      setFormError('At least one Trade Role must be selected.');
      return;
    }

    const numericRate = parseFloat(rateAmount);
    if (isNaN(numericRate) || numericRate < 0) {
      setFormError('Rate Amount must be a non-negative number.');
      return;
    }

    if (selectedSiteIds.length === 0) {
      setFormError('At least one Client Site must be assigned.');
      return;
    }

    setSubmitting(true);
    try {
      const createdEmp = await createEmployeeApi({
        name: name.trim(),
        mobile_number: formatMobileForApi(mobileNumber),
        employee_code: employeeCode.trim(),
        system_role: systemRole,
        trade_role_ids: selectedTradeRoleIds,
        rate_type: rateType,
        rate_amount: numericRate,
        supervisor_id: supervisorId || undefined,
        site_ids: selectedSiteIds,
      });

      setSuccessMsg(`Employee "${createdEmp.name}" (${createdEmp.employee_code}) onboarded successfully!`);

      // Reset form
      setName('');
      setMobileNumber('');
      setEmployeeCode('');
      setSystemRole('employee');
      setSelectedTradeRoleIds([]);
      setRateType('daily');
      setRateAmount('500');
      setSupervisorId('');
      setSelectedSiteIds([]);

      // Refresh recent employees list
      await fetchPrerequisites();
    } catch (err: any) {
      setFormError(err.message || 'Failed to onboard employee');
    } finally {
      setSubmitting(false);
    }
  };

  if (dataLoading) {
    return <LoadingSpinner label="Loading onboarding configuration..." />;
  }

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Employee Onboarding</h2>
          <p className={styles.subtitle}>Register new employees, assign system & trade roles, rates, and site assignments</p>
        </div>
      </div>

      {successMsg && <div className={styles.successBanner}>{successMsg}</div>}

      {error && <ErrorMessage title="Prerequisite Load Error" message={error} onRetry={fetchPrerequisites} />}

      <Card title="New Employee Registration Form" subtitle="Fill in details matching backend EmployeeCreate contract">
        {formError && <ErrorMessage message={formError} />}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className={styles.formGrid}>
            <Input
              label="Full Name *"
              placeholder="e.g. John Builder"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              label="Mobile Number (Login ID) *"
              placeholder="e.g. 9876543210"
              value={mobileNumber}
              onChange={(e) => setMobileNumber(e.target.value)}
              inputMode="tel"
              required
            />
            <Input
              label="Employee Code *"
              placeholder="e.g. EMP-1001"
              value={employeeCode}
              onChange={(e) => setEmployeeCode(e.target.value)}
              required
            />
            <Select
              label="System Role (RBAC Security) *"
              value={systemRole}
              onChange={(e) => setSystemRole(e.target.value as SystemRole)}
              options={[
                { value: 'employee', label: 'Employee (Field Worker)' },
                { value: 'supervisor', label: 'Supervisor' },
                { value: 'director', label: 'Director' },
                { value: 'administrator', label: 'Administrator' },
              ]}
              required
            />
          </div>

          {/* Trade Roles Multi-Select */}
          <div className={styles.sectionGroup}>
            <label className={styles.sectionLabel}>Trade / Job Role(s) * (Select at least 1)</label>
            {tradeRoles.length === 0 ? (
              <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)' }}>
                No trade roles found. Please add roles in Admin Master Data.
              </p>
            ) : (
              <div className={styles.checkboxGrid}>
                {tradeRoles.map((role) => (
                  <label key={role.id} className={styles.checkboxItem}>
                    <input
                      type="checkbox"
                      checked={selectedTradeRoleIds.includes(role.id)}
                      onChange={() => handleTradeRoleToggle(role.id)}
                    />
                    <span>{role.name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Rate Configuration */}
          <div className={styles.formGrid}>
            <Select
              label="Rate Type *"
              value={rateType}
              onChange={(e) => setRateType(e.target.value)}
              options={[
                { value: 'daily', label: 'Daily Rate' },
                { value: 'weekly', label: 'Weekly Rate' },
                { value: 'piece', label: 'Piece Rate' },
              ]}
              required
            />
            <Input
              label="Rate Amount (₹) *"
              type="number"
              min="0"
              placeholder="500"
              value={rateAmount}
              onChange={(e) => setRateAmount(e.target.value)}
              inputMode="numeric"
              required
            />
          </div>

          {/* Supervisor Selection */}
          <div className={styles.formGrid}>
            <Select
              label="Assigned Supervisor (Optional)"
              value={supervisorId}
              onChange={(e) => setSupervisorId(e.target.value)}
              options={[
                { value: '', label: '-- None (Unassigned) --' },
                ...supervisors.map((s) => ({ value: s.id, label: `${s.name} (${s.employee_code})` })),
              ]}
            />
          </div>

          {/* Site Assignments Multi-Select */}
          <div className={styles.sectionGroup}>
            <label className={styles.sectionLabel}>Assigned Client Site(s) * (Select at least 1)</label>
            {sites.length === 0 ? (
              <p style={{ color: 'var(--color-neutral-700)', fontSize: 'var(--font-size-sm)' }}>
                No construction sites found. Please add sites in Admin Master Data first.
              </p>
            ) : (
              <div className={styles.checkboxGrid}>
                {sites.map((site) => (
                  <label key={site.id} className={styles.checkboxItem}>
                    <input
                      type="checkbox"
                      checked={selectedSiteIds.includes(site.id)}
                      onChange={() => handleSiteToggle(site.id)}
                    />
                    <span>{site.name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
            <Button type="submit" size="lg" isLoading={submitting}>
              Onboard Employee
            </Button>
          </div>
        </form>
      </Card>

      {/* Recent Onboarded Employees Section */}
      {recentEmployees.length > 0 && (
        <Card title="Recently Onboarded Employees" subtitle="Total registered employees">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {recentEmployees.slice(0, 6).map((emp) => (
              <div
                key={emp.id}
                style={{
                  padding: '12px',
                  border: '1px solid var(--color-neutral-200)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  fontSize: 'var(--font-size-sm)',
                }}
              >
                <div style={{ fontWeight: 'bold' }}>{emp.name} ({emp.employee_code})</div>
                <div>System Role: <StatusBadge status="active" label={emp.system_role} /></div>
                <div>
                  Trade Roles:{' '}
                  {emp.trade_roles.map((r) => r.name).join(', ') || 'None'}
                </div>
                {emp.current_rate && (
                  <div>Rate: ₹{emp.current_rate.rate_amount} / {emp.current_rate.rate_type}</div>
                )}
                <div>Assigned Sites: {emp.active_sites.map((s) => s.name).join(', ') || 'None'}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

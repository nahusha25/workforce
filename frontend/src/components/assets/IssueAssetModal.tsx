import React, { useEffect, useState } from 'react';
import { issueAssetApi, type AssetResponse } from '../../api/assets';
import { getAllEmployeesApi, type EmployeeResponseData } from '../../api/employee';
import { Button } from '../ui/Button';
import styles from './AssetModals.module.css';

interface IssueAssetModalProps {
  isOpen: boolean;
  asset: AssetResponse | null;
  onClose: () => void;
  onSuccess: (updatedAsset: AssetResponse) => void;
}

export const IssueAssetModal: React.FC<IssueAssetModalProps> = ({
  isOpen,
  asset,
  onClose,
  onSuccess,
}) => {
  const [employeeId, setEmployeeId] = useState('');
  const [remarks, setRemarks] = useState('');
  const [employees, setEmployees] = useState<EmployeeResponseData[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && asset?.current_site_id) {
      setLoadingEmployees(true);
      setEmployeeId('');
      setRemarks('');
      setErrorMessage(null);

      getAllEmployeesApi()
        .then((res) => {
          // Filter to active employees
          const activeEmps = res.filter((e) => e.is_active);
          setEmployees(activeEmps);

          // Find first employee actively assigned to this site
          const siteEmps = activeEmps.filter((e) =>
            e.active_sites?.some((s) => s.id === asset.current_site_id)
          );
          if (siteEmps.length > 0) {
            setEmployeeId(siteEmps[0].id);
          }
        })
        .catch((err) => {
          console.error('Failed to load employees for asset issue', err);
        })
        .finally(() => {
          setLoadingEmployees(false);
        });
    }
  }, [isOpen, asset]);

  if (!isOpen || !asset) return null;

  // Separate employees who are assigned to this site vs others
  const assignedToSite = employees.filter((e) =>
    e.active_sites?.some((s) => s.id === asset.current_site_id)
  );
  const otherEmployees = employees.filter(
    (e) => !e.active_sites?.some((s) => s.id === asset.current_site_id)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId) {
      setErrorMessage('Please select an employee to issue the asset to.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await issueAssetApi(asset.id, {
        employee_id: employeeId,
        remarks: remarks.trim() ? remarks.trim() : null,
        idempotency_key: `issue-${asset.id}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      });
      onSuccess(res);
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to issue asset';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="issue-title">
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h3 id="issue-title">Issue Asset to Employee</h3>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {errorMessage && <div className={styles.alertError}>{errorMessage}</div>}

        <div className={styles.assetSummaryBadge}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Asset Tag</span>
            <span className={styles.summaryValue}>{asset.asset_tag}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Asset Name</span>
            <span className={styles.summaryValue}>{asset.name}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Current Site</span>
            <span className={styles.summaryValue}>{asset.current_site_name || 'Assigned Site'}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Condition</span>
            <span className={styles.summaryValue} style={{ textTransform: 'capitalize' }}>
              {asset.condition}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.formGrid}>
          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="issue-employee">
              Select Recipient Employee <span className={styles.required}>*</span>
            </label>
            <select
              id="issue-employee"
              className={styles.select}
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              disabled={loadingEmployees || isSubmitting}
              required
            >
              <option value="">-- Choose recipient employee --</option>
              {assignedToSite.length > 0 && (
                <optgroup label={`Assigned to ${asset.current_site_name || 'this site'} (Eligible)`}>
                  {assignedToSite.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.name} ({emp.employee_code})
                    </option>
                  ))}
                </optgroup>
              )}
              {otherEmployees.length > 0 && (
                <optgroup label="Other Active Employees (Assignment Required)">
                  {otherEmployees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.name} ({emp.employee_code}) — Unassigned to site
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            <span className={styles.helpText}>
              Per policy, an employee must have an active assignment to {asset.current_site_name || 'the current site'} to be issued this asset.
            </span>
          </div>

          <div className={`${styles.formGroup} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="issue-remarks">
              Issue Remarks
            </label>
            <textarea
              id="issue-remarks"
              className={styles.textarea}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Issued for column shuttering alignment work on Block B..."
            />
          </div>

          <div className={`${styles.modalFooter} ${styles.fullWidth}`}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting || loadingEmployees || !employeeId}>
              {isSubmitting ? 'Issuing...' : 'Confirm Issue'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

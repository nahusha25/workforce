import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  approveEmployeePaymentApi,
  cancelEmployeePaymentApi,
  getEmployeePaymentApi,
  payEmployeePaymentApi,
  type EmployeePaymentDetailResponse,
} from '../api/employeePayments';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { getLocalISODate } from '../utils/date';
import styles from './EmployeePaymentDetailPage.module.css';

export const formatCurrency = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || isNaN(Number(amount))) return '₹0.00';
  return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const PAYMENT_METHOD_OPTIONS = [
  { value: 'bank_transfer', label: 'Bank Transfer (NEFT / RTGS / IMPS)' },
  { value: 'upi', label: 'UPI' },
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'other', label: 'Other' },
];

export const EmployeePaymentDetailPage: React.FC = () => {
  const { paymentId } = useParams<{ paymentId: string }>();
  const navigate = useNavigate();
  const { role } = useAuth();
  const isDirectorOrAdmin = role === 'director' || role === 'administrator';

  const [payment, setPayment] = useState<EmployeePaymentDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Approve modal
  const [showApproveModal, setShowApproveModal] = useState<boolean>(false);
  const [approving, setApproving] = useState<boolean>(false);
  const [approveError, setApproveError] = useState<string | null>(null);

  // Pay modal
  const [showPayModal, setShowPayModal] = useState<boolean>(false);
  const [payDate, setPayDate] = useState<string>(() => getLocalISODate(new Date()));
  const [payMethod, setPayMethod] = useState<string>('bank_transfer');
  const [payRef, setPayRef] = useState<string>('');
  const [payRemarks, setPayRemarks] = useState<string>('');
  const [paying, setPaying] = useState<boolean>(false);
  const [payError, setPayError] = useState<string | null>(null);

  // Cancel modal
  const [showCancelModal, setShowCancelModal] = useState<boolean>(false);
  const [cancelReason, setCancelReason] = useState<string>('');
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const fetchPayment = async () => {
    if (!paymentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getEmployeePaymentApi(paymentId);
      setPayment(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load employee payment details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayment();
  }, [paymentId]);

  // Handle Approve
  const handleApprove = async () => {
    if (!paymentId) return;
    setApproving(true);
    setApproveError(null);
    try {
      const updated = await approveEmployeePaymentApi(paymentId);
      setPayment(updated);
      setShowApproveModal(false);
      setSuccessMsg(`Payment ${updated.payment_number} approved successfully.`);
    } catch (err: any) {
      setApproveError(err?.response?.data?.detail || err?.message || 'Failed to approve payment');
    } finally {
      setApproving(false);
    }
  };

  // Handle Mark as Paid
  const handlePay = async () => {
    if (!paymentId) return;
    if (!payMethod) {
      setPayError('Payment method is required.');
      return;
    }
    setPaying(true);
    setPayError(null);
    try {
      const updated = await payEmployeePaymentApi(paymentId, {
        payment_date: payDate || undefined,
        payment_method: payMethod,
        reference_number: payRef.trim() || undefined,
        remarks: payRemarks.trim() || undefined,
      });
      setPayment(updated);
      setShowPayModal(false);
      setSuccessMsg(`Payment ${updated.payment_number} marked as paid successfully.`);
    } catch (err: any) {
      setPayError(err?.response?.data?.detail || err?.message || 'Failed to mark payment as paid');
    } finally {
      setPaying(false);
    }
  };

  // Handle Cancel
  const handleCancel = async () => {
    if (!paymentId) return;
    const trimmedReason = cancelReason.trim();
    if (trimmedReason.length < 3) {
      setCancelError('Cancellation reason must be at least 3 characters.');
      return;
    }
    setCancelling(true);
    setCancelError(null);
    try {
      const updated = await cancelEmployeePaymentApi(paymentId, {
        cancellation_reason: trimmedReason,
      });
      setPayment(updated);
      setShowCancelModal(false);
      setSuccessMsg(`Payment ${updated.payment_number} cancelled and source records unlocked.`);
    } catch (err: any) {
      setCancelError(err?.response?.data?.detail || err?.message || 'Failed to cancel payment');
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !payment) {
    return (
      <div className={styles.container}>
        <button className={styles.backBtn} onClick={() => navigate('/employee-payments')}>
          &larr; Back to Employee Payments
        </button>
        <ErrorMessage message={error || 'Payment record not found.'} />
      </div>
    );
  }

  const isDraft = payment.status === 'draft';
  const isApproved = payment.status === 'approved';
  const isPaid = payment.status === 'paid';
  const isCancelled = payment.status === 'cancelled';

  return (
    <div className={styles.container}>
      <button className={styles.backBtn} onClick={() => navigate('/employee-payments')}>
        &larr; Back to Employee Payments
      </button>

      {/* Header Row */}
      <div className={styles.headerRow}>
        <div className={styles.headerLeft}>
          <h2>{payment.payment_number}</h2>
          <StatusBadge status={payment.status} label={payment.status.toUpperCase()} />
        </div>

        {isDirectorOrAdmin && (
          <div className={styles.headerActions}>
            {isDraft && (
              <>
                <Button
                  variant="primary"
                  onClick={() => {
                    setApproveError(null);
                    setShowApproveModal(true);
                  }}
                >
                  Approve Payment
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setCancelReason('');
                    setCancelError(null);
                    setShowCancelModal(true);
                  }}
                >
                  Cancel Payment
                </Button>
              </>
            )}

            {isApproved && (
              <>
                <Button
                  variant="primary"
                  onClick={() => {
                    let defaultPayDate: string;
                    if (payment?.period_end) {
                      const [y, m] = payment.period_end.split('-').map(Number);
                      const nextMonth = m === 12 ? 1 : m + 1;
                      const nextYear = m === 12 ? y + 1 : y;
                      defaultPayDate = `${nextYear}-${String(nextMonth).padStart(2, '0')}-01`;
                    } else {
                      const now = new Date();
                      defaultPayDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
                    }
                    setPayDate(defaultPayDate);
                    setPayMethod('bank_transfer');
                    setPayRef('');
                    setPayRemarks('');
                    setPayError(null);
                    setShowPayModal(true);
                  }}
                >
                  Mark Paid
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setCancelReason('');
                    setCancelError(null);
                    setShowCancelModal(true);
                  }}
                >
                  Cancel Payment
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className={styles.successMessage} role="status">
          {successMsg}
        </div>
      )}

      {/* Cancellation Notice Banner */}
      {isCancelled && (
        <div className={styles.bannerCancelled} data-testid="cancellation-banner">
          <strong>Payment Cancelled</strong>
          <div>
            Reason: <span>{payment.cancellation_reason || '—'}</span>
          </div>
          {payment.cancelled_at && (
            <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>
              Cancelled on: {new Date(payment.cancelled_at).toLocaleString()}
            </div>
          )}
        </div>
      )}

      {/* Paid Settlement Details Banner */}
      {isPaid && (
        <div className={styles.bannerPaid} data-testid="paid-banner">
          <strong>Settlement Completed</strong>
          <div>
            Payment Method: <span style={{ textTransform: 'capitalize' }}>{payment.payment_method?.replace('_', ' ')}</span> | Date:{' '}
            <span>{payment.payment_date || '—'}</span>
            {payment.reference_number && <span> | Ref: {payment.reference_number}</span>}
          </div>
          {payment.remarks && <div>Remarks: {payment.remarks}</div>}
          {payment.paid_at && (
            <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>
              Recorded on: {new Date(payment.paid_at).toLocaleString()}
            </div>
          )}
        </div>
      )}

      {/* Overview Metadata Card */}
      <Card>
        <h3 className={styles.cardTitle}>Payment Overview</h3>
        <div className={styles.metaGrid}>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Employee</span>
            <span className={styles.metaValue}>{payment.employee_name || '—'}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Pay Period</span>
            <span className={styles.metaValue}>
              {payment.period_start} to {payment.period_end}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Approved Days</span>
            <span className={styles.metaValue}>{payment.total_days}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Approved Qty</span>
            <span className={styles.metaValue}>{payment.total_quantity}</span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Regular Amount</span>
            <span className={styles.metaValue} data-testid="total-regular-amount">
              {formatCurrency(payment.total_regular_amount ?? 0)}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Overtime Hours</span>
            <span className={styles.metaValue} data-testid="total-overtime-hours">
              {Number(payment.total_overtime_hours ?? 0).toFixed(2)} hrs
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Overtime Amount</span>
            <span className={styles.metaValue} data-testid="total-overtime-amount">
              {formatCurrency(payment.total_overtime_amount ?? 0)}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Total Payment Amount</span>
            <span className={styles.metaValue} data-testid="total-payment-amount" style={{ color: 'var(--color-primary-700, #1d4ed8)', fontSize: '1.125rem' }}>
              {formatCurrency(payment.total_amount)}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Idempotency Key</span>
            <span className={styles.metaValue} style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
              {payment.idempotency_key}
            </span>
          </div>

          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Created Date</span>
            <span className={styles.metaValue}>
              {payment.created_at ? new Date(payment.created_at).toLocaleString() : '—'}
            </span>
          </div>

          {payment.approved_at && (
            <div className={styles.metaField}>
              <span className={styles.metaLabel}>Approved Date</span>
              <span className={styles.metaValue}>{new Date(payment.approved_at).toLocaleString()}</span>
            </div>
          )}
        </div>
      </Card>

      {/* Rate Band Summaries Card */}
      <Card>
        <h3 className={styles.cardTitle}>Rate Band Summaries</h3>
        {payment.rate_band_summaries.length === 0 ? (
          <div className={styles.emptyState}>No rate band summaries available for this payment.</div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Rate Type</th>
                  <th>Unit Rate</th>
                  <th>Effective Range</th>
                  <th>Approved Days</th>
                  <th>Approved Quantity</th>
                  <th>Gross Amount</th>
                </tr>
              </thead>
              <tbody>
                {payment.rate_band_summaries.map((rbs, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{rbs.rate_type}</td>
                    <td>{formatCurrency(rbs.rate_amount)}</td>
                    <td>
                      {rbs.rate_effective_from} to {rbs.rate_effective_to || 'Present'}
                    </td>
                    <td>{rbs.approved_days}</td>
                    <td>{rbs.approved_quantity}</td>
                    <td style={{ fontWeight: 700 }}>{formatCurrency(rbs.gross_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Itemized Lines Card */}
      <Card>
        <h3 className={styles.cardTitle}>Itemized Payment Lines</h3>
        {payment.lines.length === 0 ? (
          <div className={styles.emptyState}>No itemized payment lines found.</div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable} data-testid="itemized-lines-table">
              <thead>
                <tr>
                  <th>Source Date</th>
                  <th>Source</th>
                  <th>Rate Type & Unit Rate</th>
                  <th>Regular Breakdown</th>
                  <th>Overtime Breakdown</th>
                  <th>Line Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {payment.lines.map((line) => {
                  const isAttendance = Boolean(line.source_attendance_id);
                  const isPiece = line.rate_type === 'piece';
                  const hasOvertime = Number(line.overtime_hours ?? 0) > 0;

                  return (
                    <tr key={line.id} data-testid={`payment-line-${line.id}`}>
                      <td>{line.source_date}</td>
                      <td>
                        <span
                          className={`${styles.typeBadge} ${
                            isAttendance ? styles.badgeAttendance : styles.badgeWork
                          }`}
                        >
                          {isAttendance ? 'Attendance' : 'Work Entry'}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {line.rate_type}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)' }}>
                          {formatCurrency(line.rate_amount)} / {line.rate_type === 'piece' ? 'unit' : line.rate_type === 'weekly' ? 'wk' : line.rate_type === 'monthly' ? 'mo' : 'day'}
                        </div>
                      </td>
                      <td>
                        {isPiece ? (
                          <div>
                            <div>{line.quantity} units</div>
                            <div style={{ fontWeight: 600 }}>{formatCurrency(line.regular_amount ?? line.amount)}</div>
                          </div>
                        ) : (
                          <div>
                            <div>
                              {Number(line.regular_hours ?? 0).toFixed(2)} hrs
                              {line.standard_day_hours != null && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)', marginLeft: '4px' }}>
                                  {' '}({Number(line.standard_day_hours).toFixed(2)}h std)
                                </span>
                              )}
                            </div>
                            <div style={{ fontWeight: 600 }}>
                              {formatCurrency(line.regular_amount ?? 0)} ({line.days}d)
                            </div>
                          </div>
                        )}
                      </td>
                      <td>
                        {isPiece ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>
                            — (Piece-rate excluded)
                          </span>
                        ) : hasOvertime ? (
                          <div>
                            <div>
                              <strong style={{ color: '#b45309' }}>{Number(line.overtime_hours).toFixed(2)} hrs</strong>
                              {line.overtime_multiplier != null && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)', marginLeft: '4px' }}>
                                  {' '}@ {Number(line.overtime_multiplier).toFixed(2)}x
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--color-neutral-600)' }}>
                              Equiv: {formatCurrency(line.hourly_equivalent_rate)}/hr
                            </div>
                            <div style={{ fontWeight: 600, color: '#b45309' }}>
                              + {formatCurrency(line.overtime_amount ?? 0)}
                            </div>
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>
                            0.00 hrs (₹0.00)
                          </span>
                        )}
                      </td>
                      <td style={{ fontWeight: 700 }}>{formatCurrency(line.amount)}</td>
                      <td>
                        <StatusBadge
                          status={line.is_active ? 'active' : 'inactive'}
                          label={line.is_active ? 'ACTIVE' : 'LOCKED'}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className={styles.totalsRow} data-testid="lines-totals-row">
              <div>
                Total Days: <strong>{payment.total_days}</strong>
              </div>
              <div>
                Total Qty: <strong>{payment.total_quantity}</strong>
              </div>
              <div>
                Total Regular: <strong>{formatCurrency(payment.total_regular_amount ?? 0)}</strong>
              </div>
              <div>
                Total Overtime:{' '}
                <strong>
                  {Number(payment.total_overtime_hours ?? 0).toFixed(2)} hrs (
                  {formatCurrency(payment.total_overtime_amount ?? 0)})
                </strong>
              </div>
              <div className={styles.totalHighlight}>
                Grand Total: {formatCurrency(payment.total_amount)}
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Approve Confirmation Modal */}
      {showApproveModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="approve-modal-title">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3 id="approve-modal-title">Approve Employee Payment</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowApproveModal(false)}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            {approveError && <ErrorMessage message={approveError} />}

            <p style={{ margin: 0 }}>
              Are you sure you want to approve payment <strong>{payment.payment_number}</strong> for{' '}
              <strong>{payment.employee_name}</strong> totaling{' '}
              <strong>{formatCurrency(payment.total_amount)}</strong>?
            </p>

            <div className={styles.warningBox}>
              Once approved, this payment record can be marked as paid.
            </div>

            <div className={styles.modalActions}>
              <Button variant="outline" onClick={() => setShowApproveModal(false)} disabled={approving}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleApprove} disabled={approving}>
                {approving ? 'Approving...' : 'Confirm Approval'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Mark Paid Modal */}
      {showPayModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="pay-modal-title">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3 id="pay-modal-title">Record Payment Settlement</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowPayModal(false)}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            {payError && <ErrorMessage message={payError} />}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <Input
                label="Payment Date *"
                type="date"
                value={payDate}
                onChange={(e) => setPayDate(e.target.value)}
              />

              <Select
                label="Payment Method *"
                value={payMethod}
                onChange={(e) => setPayMethod(e.target.value)}
                options={PAYMENT_METHOD_OPTIONS}
              />

              <Input
                label="Reference Number (Optional)"
                placeholder="e.g. UTR / Cheque / Txn Number"
                value={payRef}
                onChange={(e) => setPayRef(e.target.value)}
              />

              <Input
                label="Remarks (Optional)"
                placeholder="e.g. Cleared through bank transfer"
                value={payRemarks}
                onChange={(e) => setPayRemarks(e.target.value)}
              />
            </div>

            <div className={styles.warningBox}>
              Marking this payment as paid records settlement. This financial action cannot be undone.
            </div>

            <div className={styles.modalActions}>
              <Button variant="outline" onClick={() => setShowPayModal(false)} disabled={paying}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handlePay} disabled={paying}>
                {paying ? 'Recording...' : 'Confirm & Mark Paid'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Payment Modal */}
      {showCancelModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="cancel-modal-title">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3 id="cancel-modal-title">Cancel Employee Payment</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowCancelModal(false)}
                aria-label="Close dialog"
              >
                &times;
              </button>
            </div>

            {cancelError && <ErrorMessage message={cancelError} />}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-neutral-800)' }}>
                Cancellation Reason *
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Provide a mandatory reason for cancelling this payment (min 3 chars)..."
                rows={4}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--color-neutral-300)',
                  fontSize: '0.875rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div className={styles.warningBox}>
              Cancelling this payment will release source-locks on all associated attendance and daily work entries,
              making them eligible for future payment generation.
            </div>

            <div className={styles.modalActions}>
              <Button variant="outline" onClick={() => setShowCancelModal(false)} disabled={cancelling}>
                Back
              </Button>
              <Button
                variant="primary"
                onClick={handleCancel}
                disabled={cancelling || cancelReason.trim().length < 3}
                style={{ backgroundColor: '#dc2626', borderColor: '#dc2626' }}
              >
                {cancelling ? 'Cancelling...' : 'Confirm Cancellation'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

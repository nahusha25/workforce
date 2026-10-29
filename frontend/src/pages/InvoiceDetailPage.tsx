import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  cancelInvoiceApi,
  getInvoiceApi,
  issueInvoiceApi,
  updateDraftInvoiceApi,
  type InvoiceDetailResponse,
  type RateOverrideItem,
} from '../api/invoices';
import {
  listPaymentsForInvoiceApi,
  recordPaymentApi,
  voidPaymentApi,
  uploadPaymentReceiptApi,
  viewPaymentReceipt,
  type ClientPaymentResponse,
  type PaymentMethod,
} from '../api/clientPayments';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { getLocalISODate } from '../utils/date';
import styles from './InvoiceDetailPage.module.css';
import { formatCurrency } from './InvoicesPage';

const PAYMENT_METHOD_OPTIONS = [
  { value: 'neft', label: 'NEFT' },
  { value: 'rtgs', label: 'RTGS' },
  { value: 'imps', label: 'IMPS' },
  { value: 'upi', label: 'UPI' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
];

export const InvoiceDetailPage: React.FC = () => {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const navigate = useNavigate();
  const { role } = useAuth();
  const isDirectorOrAdmin = role === 'director' || role === 'administrator';

  const [invoice, setInvoice] = useState<InvoiceDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Draft editable fields
  const [clientPo, setClientPo] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [remarks, setRemarks] = useState<string>('');
  const [taxAmount, setTaxAmount] = useState<number>(0);
  const [rateEdits, setRateEdits] = useState<Record<string, { unitRate: number; reason: string }>>({});
  const [saving, setSaving] = useState<boolean>(false);

  // Issue modal
  const [showIssueModal, setShowIssueModal] = useState<boolean>(false);
  const [issueDate, setIssueDate] = useState<string>(() => getLocalISODate(new Date()));
  const [dueDate, setDueDate] = useState<string>('');
  const [issuing, setIssuing] = useState<boolean>(false);
  const [issueError, setIssueError] = useState<string | null>(null);

  // Cancel modal
  const [showCancelModal, setShowCancelModal] = useState<boolean>(false);
  const [cancellationReason, setCancellationReason] = useState<string>('');
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // Payment states
  const [payments, setPayments] = useState<ClientPaymentResponse[]>([]);
  const [, setPaymentsLoading] = useState<boolean>(false);

  // Record payment modal
  const [showRecordPaymentModal, setShowRecordPaymentModal] = useState<boolean>(false);
  const [paymentAmount, setPaymentAmount] = useState<string>('');
  const [paymentDate, setPaymentDate] = useState<string>(() => getLocalISODate(new Date()));
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('neft');
  const [paymentRef, setPaymentRef] = useState<string>('');
  const [paymentNotes, setPaymentNotes] = useState<string>('');
  const [recordReceiptFile, setRecordReceiptFile] = useState<File | null>(null);
  const [recordingPayment, setRecordingPayment] = useState<boolean>(false);
  const [recordPaymentError, setRecordPaymentError] = useState<string | null>(null);

  // Void payment modal
  const [showVoidPaymentModal, setShowVoidPaymentModal] = useState<boolean>(false);
  const [selectedPaymentToVoid, setSelectedPaymentToVoid] = useState<ClientPaymentResponse | null>(null);
  const [voidReason, setVoidReason] = useState<string>('');
  const [voidingPayment, setVoidingPayment] = useState<boolean>(false);
  const [voidPaymentError, setVoidPaymentError] = useState<string | null>(null);

  // Attach / replace receipt modal
  const [showAttachReceiptModal, setShowAttachReceiptModal] = useState<boolean>(false);
  const [selectedPaymentForReceipt, setSelectedPaymentForReceipt] = useState<ClientPaymentResponse | null>(null);
  const [attachReceiptFile, setAttachReceiptFile] = useState<File | null>(null);
  const [attachingReceipt, setAttachingReceipt] = useState<boolean>(false);
  const [attachReceiptError, setAttachReceiptError] = useState<string | null>(null);

  const fetchPayments = async () => {
    if (!invoiceId) return;
    setPaymentsLoading(true);
    try {
      const data = await listPaymentsForInvoiceApi(invoiceId);
      setPayments(data);
    } catch (err: any) {
      console.error('Failed to load payments:', err);
    } finally {
      setPaymentsLoading(false);
    }
  };

  const fetchInvoice = async () => {
    if (!invoiceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getInvoiceApi(invoiceId);
      setInvoice(data);
      setClientPo(data.client_po_number || '');
      setNotes(data.notes || '');
      setRemarks(data.remarks || '');
      setTaxAmount(Number(data.tax_amount || 0));

      // Populate existing line rate overrides
      const edits: Record<string, { unitRate: number; reason: string }> = {};
      (data.lines || []).forEach((l) => {
        if (l.line_type === 'work' && l.source_daily_work_entry_id) {
          edits[l.source_daily_work_entry_id] = {
            unitRate: Number(l.unit_rate),
            reason: l.rate_override_reason || '',
          };
        }
      });
      setRateEdits(edits);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load invoice');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoice();
    fetchPayments();
  }, [invoiceId]);

  if (loading) {
    return <LoadingSpinner fullScreen label="Loading invoice details..." />;
  }

  if (!invoice) {
    return (
      <div className={styles.container}>
        <button className={styles.backBtn} onClick={() => navigate('/invoices')}>
          &larr; Back to Invoices
        </button>
        <ErrorMessage message={error || 'Invoice not found'} />
      </div>
    );
  }

  const isDraft = invoice.status === 'draft';
  const isIssued = invoice.status === 'issued';
  const isCancelled = invoice.status === 'cancelled';
  const isPartiallyPaid = invoice.status === 'partially_paid';
  const balanceDue = Number(invoice.total_amount) - Number(invoice.paid_amount);
  const canRecordPayment = (isIssued || isPartiallyPaid) && balanceDue > 0 && isDirectorOrAdmin;

  // Handle rate change on a work line item
  const handleRateChange = (sourceId: string, newRate: number) => {
    setRateEdits((prev) => ({
      ...prev,
      [sourceId]: {
        unitRate: newRate,
        reason: prev[sourceId]?.reason || '',
      },
    }));
  };

  // Handle override reason change on a work line item
  const handleReasonChange = (sourceId: string, newReason: string) => {
    setRateEdits((prev) => ({
      ...prev,
      [sourceId]: {
        unitRate: prev[sourceId]?.unitRate ?? 0,
        reason: newReason,
      },
    }));
  };

  // Save draft changes
  const handleSaveDraft = async () => {
    if (!invoiceId) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    // Validate override reasons
    const overrides: RateOverrideItem[] = [];
    for (const line of invoice.lines || []) {
      if (line.line_type === 'work' && line.source_daily_work_entry_id) {
        const edit = rateEdits[line.source_daily_work_entry_id];
        if (edit && Number(edit.unitRate) !== Number(line.standard_rate)) {
          if (!edit.reason || !edit.reason.trim()) {
            setError(`Rate override reason is mandatory for line "${line.item_description}"`);
            setSaving(false);
            return;
          }
          overrides.push({
            source_id: line.source_daily_work_entry_id,
            unit_rate: Number(edit.unitRate),
            rate_override_reason: edit.reason.trim(),
          });
        }
      }
    }

    try {
      const updated = await updateDraftInvoiceApi(invoiceId, {
        client_po_number: clientPo.trim() || null,
        notes: notes.trim() || null,
        remarks: remarks.trim() || null,
        tax_amount: Number(taxAmount || 0),
        rate_overrides: overrides.length > 0 ? overrides : undefined,
      });
      setInvoice(updated);
      setSuccessMsg('Invoice draft updated successfully.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to update invoice');
    } finally {
      setSaving(false);
    }
  };

  // Issue invoice
  const handleIssue = async () => {
    if (!invoiceId) return;
    setIssuing(true);
    setIssueError(null);
    try {
      const updated = await issueInvoiceApi(invoiceId, {
        issue_date: issueDate || undefined,
        due_date: dueDate || undefined,
      });
      setInvoice(updated);
      setShowIssueModal(false);
      setSuccessMsg('Invoice issued successfully. Financial amounts are now permanently frozen.');
    } catch (err: any) {
      setIssueError(err?.response?.data?.detail || err.message || 'Failed to issue invoice');
    } finally {
      setIssuing(false);
    }
  };

  // Cancel invoice
  const handleCancel = async () => {
    if (!invoiceId || !cancellationReason.trim()) {
      setCancelError('Cancellation reason is strictly mandatory.');
      return;
    }
    setCancelling(true);
    setCancelError(null);
    try {
      const updated = await cancelInvoiceApi(invoiceId, {
        cancellation_reason: cancellationReason.trim(),
      });
      setInvoice(updated);
      setShowCancelModal(false);
      setSuccessMsg('Invoice cancelled. All associated work and material records have been unlocked.');
    } catch (err: any) {
      setCancelError(err?.response?.data?.detail || err.message || 'Failed to cancel invoice');
    } finally {
      setCancelling(false);
    }
  };

  const handleOpenRecordPaymentModal = () => {
    setPaymentAmount(balanceDue > 0 ? balanceDue.toFixed(2) : '');
    setPaymentDate(getLocalISODate(new Date()));
    setPaymentMethod('neft');
    setPaymentRef('');
    setPaymentNotes('');
    setRecordReceiptFile(null);
    setRecordPaymentError(null);
    setShowRecordPaymentModal(true);
  };

  const handleRecordPayment = async () => {
    if (!invoiceId) return;
    const amountNum = parseFloat(paymentAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setRecordPaymentError('Payment amount must be greater than ₹0.00');
      return;
    }
    if (amountNum > balanceDue) {
      setRecordPaymentError(`Payment amount cannot exceed outstanding balance of ${formatCurrency(balanceDue)}`);
      return;
    }
    if (!paymentDate) {
      setRecordPaymentError('Payment date is mandatory.');
      return;
    }

    setRecordingPayment(true);
    setRecordPaymentError(null);
    try {
      const idempotencyKey =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `pay-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      const res = await recordPaymentApi({
        invoice_id: invoiceId,
        amount: amountNum,
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference_number: paymentRef.trim() || undefined,
        notes: paymentNotes.trim() || undefined,
        idempotency_key: idempotencyKey,
      });

      setShowRecordPaymentModal(false);
      await Promise.all([fetchInvoice(), fetchPayments()]);

      if (recordReceiptFile) {
        try {
          await uploadPaymentReceiptApi(res.id, recordReceiptFile);
          setSuccessMsg(`Payment ${res.payment_number} of ${formatCurrency(res.amount)} recorded and receipt attached successfully.`);
          await fetchPayments();
        } catch (uploadErr: any) {
          setSuccessMsg(null);
          const uploadMsg = uploadErr?.response?.data?.detail || uploadErr?.message || 'Upload failed';
          setError(`Payment ${res.payment_number} recorded successfully, but receipt upload failed: ${uploadMsg}. You can attach the receipt from the payments table.`);
        }
      } else {
        setSuccessMsg(`Payment ${res.payment_number} of ${formatCurrency(res.amount)} recorded successfully.`);
      }

      setRecordReceiptFile(null);
    } catch (err: any) {
      setRecordPaymentError(err?.response?.data?.detail || err?.message || 'Failed to record payment');
    } finally {
      setRecordingPayment(false);
    }
  };

  const handleViewReceipt = async (paymentId: string) => {
    try {
      await viewPaymentReceipt(paymentId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to access receipt document');
    }
  };

  const handleOpenAttachReceiptModal = (payment: ClientPaymentResponse) => {
    setSelectedPaymentForReceipt(payment);
    setAttachReceiptFile(null);
    setAttachReceiptError(null);
    setShowAttachReceiptModal(true);
  };

  const handleAttachReceiptSubmit = async () => {
    if (!selectedPaymentForReceipt) return;
    if (!attachReceiptFile) {
      setAttachReceiptError('Please select a receipt document/image to upload.');
      return;
    }
    if (attachReceiptFile.size > 10 * 1024 * 1024) {
      setAttachReceiptError('Receipt file size exceeds maximum limit of 10MB.');
      return;
    }

    setAttachingReceipt(true);
    setAttachReceiptError(null);
    try {
      await uploadPaymentReceiptApi(selectedPaymentForReceipt.id, attachReceiptFile);
      setShowAttachReceiptModal(false);
      setSelectedPaymentForReceipt(null);
      setAttachReceiptFile(null);
      setSuccessMsg(`Receipt attached successfully for payment ${selectedPaymentForReceipt.payment_number}.`);
      await fetchPayments();
    } catch (err: any) {
      setAttachReceiptError(err?.response?.data?.detail || err?.message || 'Failed to upload receipt');
    } finally {
      setAttachingReceipt(false);
    }
  };

  const handleOpenVoidModal = (payment: ClientPaymentResponse) => {
    setSelectedPaymentToVoid(payment);
    setVoidReason('');
    setVoidPaymentError(null);
    setShowVoidPaymentModal(true);
  };

  const handleVoidPayment = async () => {
    if (!selectedPaymentToVoid) return;
    const trimmedReason = voidReason.trim();
    if (trimmedReason.length < 10) {
      setVoidPaymentError('Void audit reason must contain at least 10 characters.');
      return;
    }

    setVoidingPayment(true);
    setVoidPaymentError(null);
    try {
      const voidIdempotencyKey =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `void-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      const res = await voidPaymentApi(selectedPaymentToVoid.id, {
        void_idempotency_key: voidIdempotencyKey,
        void_reason: trimmedReason,
      });

      setShowVoidPaymentModal(false);
      setSelectedPaymentToVoid(null);
      setSuccessMsg(`Payment ${res.payment_number} voided successfully.`);
      await Promise.all([fetchInvoice(), fetchPayments()]);
    } catch (err: any) {
      setVoidPaymentError(err?.response?.data?.detail || err?.message || 'Failed to void payment');
    } finally {
      setVoidingPayment(false);
    }
  };

  return (
    <div className={styles.container}>
      <button className={styles.backBtn} onClick={() => navigate('/invoices')}>
        &larr; Back to Invoices
      </button>

      {/* Header Row */}
      <div className={styles.headerRow}>
        <div className={styles.headerLeft}>
          <h2>{invoice.invoice_number}</h2>
          <StatusBadge status={invoice.status} />
        </div>

        <div className={styles.headerActions}>
          {isDraft && isDirectorOrAdmin && (
            <>
              <Button variant="secondary" onClick={handleSaveDraft} disabled={saving}>
                {saving ? 'Saving...' : 'Save Draft'}
              </Button>
              <Button variant="primary" onClick={() => setShowIssueModal(true)}>
                Issue Invoice
              </Button>
              <Button variant="outline" onClick={() => setShowCancelModal(true)}>
                Cancel Invoice
              </Button>
            </>
          )}

          {canRecordPayment && (
            <Button variant="primary" onClick={handleOpenRecordPaymentModal}>
              Record Payment
            </Button>
          )}

          {isIssued && Number(invoice.paid_amount) === 0 && isDirectorOrAdmin && (
            <Button variant="outline" onClick={() => setShowCancelModal(true)}>
              Cancel Invoice
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      {error && <ErrorMessage message={error} />}
      {successMsg && (
        <div style={{ color: '#166534', background: '#dcfce7', padding: '12px', borderRadius: '6px' }}>
          {successMsg}
        </div>
      )}

      {/* Cancellation Banner */}
      {isCancelled && (
        <div className={styles.bannerCancelled}>
          <strong>Invoice Cancelled:</strong> {invoice.cancellation_reason || 'No reason provided.'}
          {invoice.cancelled_at && <span> (on {new Date(invoice.cancelled_at).toLocaleString()})</span>}
        </div>
      )}

      {/* Metadata Card */}
      <Card>
        <div className={styles.metaGrid}>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Client</span>
            <span className={styles.metaValue}>{invoice.client_name || '-'}</span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Project</span>
            <span className={styles.metaValue}>{invoice.project_name || '-'}</span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Site</span>
            <span className={styles.metaValue}>{invoice.site_name || '-'}</span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Billing Period</span>
            <span className={styles.metaValue}>
              {invoice.period_start} to {invoice.period_end}
            </span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Issue Date</span>
            <span className={styles.metaValue}>{invoice.issue_date || 'Not Issued'}</span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Due Date</span>
            <span className={styles.metaValue}>{invoice.due_date || '-'}</span>
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Client PO #</span>
            {isDraft ? (
              <Input
                value={clientPo}
                onChange={(e) => setClientPo(e.target.value)}
                placeholder="PO number"
                style={{ marginTop: '4px' }}
              />
            ) : (
              <span className={styles.metaValue}>{invoice.client_po_number || '-'}</span>
            )}
          </div>
          <div className={styles.metaField}>
            <span className={styles.metaLabel}>Notes</span>
            {isDraft ? (
              <Input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notes for client"
                style={{ marginTop: '4px' }}
              />
            ) : (
              <span className={styles.metaValue}>{invoice.notes || '-'}</span>
            )}
          </div>
        </div>
      </Card>

      {/* Line Items Card */}
      <Card>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', color: 'var(--color-neutral-900)' }}>
          Invoice Line Items ({(invoice.lines || []).length})
        </h3>
        <div className={styles.tableWrapper}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Type</th>
                <th>Source Date</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Standard Rate</th>
                <th>Unit Rate</th>
                <th>Line Amount</th>
                <th>Rate Override & Mandatory Reason</th>
              </tr>
            </thead>
            <tbody>
              {(invoice.lines || []).map((line) => {
                const isWork = line.line_type === 'work';
                const sourceId = line.source_daily_work_entry_id;
                const edit = sourceId ? rateEdits[sourceId] : undefined;
                const currentUnitRate = edit ? edit.unitRate : Number(line.unit_rate);
                const isOverridden = isWork && currentUnitRate !== Number(line.standard_rate);
                const overrideReason = edit ? edit.reason : line.rate_override_reason || '';
                const hasMissingReason = isOverridden && !overrideReason.trim();

                return (
                  <tr key={line.id}>
                    <td>
                      <StatusBadge
                        status={isWork ? 'verified' : 'submitted'}
                        label={line.line_type.toUpperCase()}
                      />
                    </td>
                    <td>{line.source_date}</td>
                    <td>
                      <strong>{line.item_description}</strong>
                    </td>
                    <td>
                      {line.quantity} {line.uom}
                    </td>
                    <td>{formatCurrency(line.standard_rate)}</td>
                    <td>
                      {isDraft && isWork && isDirectorOrAdmin ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className={styles.inputRate}
                          value={currentUnitRate}
                          onChange={(e) => sourceId && handleRateChange(sourceId, parseFloat(e.target.value) || 0)}
                        />
                      ) : (
                        formatCurrency(line.unit_rate)
                      )}
                    </td>
                    <td>
                      <strong>{formatCurrency(line.line_amount)}</strong>
                    </td>
                    <td>
                      {isOverridden ? (
                        <div>
                          <small style={{ color: '#d97706', fontWeight: 600 }}>Rate Overridden</small>
                          {isDraft && isDirectorOrAdmin ? (
                            <input
                              type="text"
                              className={`${styles.inputReason} ${hasMissingReason ? styles.inputReasonRequired : ''}`}
                              placeholder="* Mandatory reason for override"
                              value={overrideReason}
                              onChange={(e) => sourceId && handleReasonChange(sourceId, e.target.value)}
                            />
                          ) : (
                            <div style={{ fontSize: '0.75rem', color: 'var(--color-neutral-700)' }}>
                              Reason: {overrideReason}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--color-neutral-400)', fontSize: '0.75rem' }}>Standard Rate</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Payments & Receipts Card */}
      {(!isDraft || payments.length > 0) && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '1.125rem', color: 'var(--color-neutral-900)' }}>
              Payments & Receipts ({payments.length})
            </h3>
            {canRecordPayment && (
              <Button variant="primary" size="sm" onClick={handleOpenRecordPaymentModal}>
                + Record Payment
              </Button>
            )}
          </div>

          {payments.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-neutral-500)', fontSize: '0.875rem' }}>
              No payments recorded yet for this invoice.
            </div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Payment #</th>
                    <th>Date</th>
                    <th>Method</th>
                    <th>Amount</th>
                    <th>Reference / UTR</th>
                    <th>Status</th>
                    {isDirectorOrAdmin && <th>Receipt</th>}
                    <th>Notes & Audit</th>
                    {isDirectorOrAdmin && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {payments.map((p) => {
                    const isRecorded = p.status === 'recorded';
                    return (
                      <tr key={p.id}>
                        <td>
                          <strong>{p.payment_number}</strong>
                        </td>
                        <td>{p.payment_date}</td>
                        <td>
                          <span style={{ textTransform: 'uppercase', fontWeight: 600, fontSize: '0.75rem', color: 'var(--color-neutral-700)' }}>
                            {p.payment_method}
                          </span>
                        </td>
                        <td>
                          <strong style={{ color: isRecorded ? '#16a34a' : 'var(--color-neutral-500)', textDecoration: isRecorded ? 'none' : 'line-through' }}>
                            {formatCurrency(p.amount)}
                          </strong>
                        </td>
                        <td>{p.reference_number || '-'}</td>
                        <td>
                          <StatusBadge status={p.status} />
                        </td>
                        {isDirectorOrAdmin && (
                          <td>
                            {p.receipt_url ? (
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleViewReceipt(p.id)}
                                >
                                  View Receipt
                                </Button>
                                {isRecorded && (
                                  <button
                                    type="button"
                                    onClick={() => handleOpenAttachReceiptModal(p)}
                                    style={{
                                      fontSize: '0.75rem',
                                      color: 'var(--color-primary-600)',
                                      background: 'none',
                                      border: 'none',
                                      cursor: 'pointer',
                                      textDecoration: 'underline',
                                    }}
                                  >
                                    Replace
                                  </button>
                                )}
                              </div>
                            ) : isRecorded ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOpenAttachReceiptModal(p)}
                              >
                                Attach Receipt
                              </Button>
                            ) : (
                              <span style={{ color: 'var(--color-neutral-400)', fontSize: '0.75rem' }}>No receipt</span>
                            )}
                          </td>
                        )}
                        <td>
                          {p.status === 'voided' ? (
                            <div>
                              <small style={{ color: '#b91c1c', fontWeight: 600 }}>Voided</small>
                              <div style={{ fontSize: '0.75rem', color: 'var(--color-neutral-700)' }}>
                                Reason: {p.void_reason}
                              </div>
                              {p.voided_at && (
                                <div style={{ fontSize: '0.7rem', color: 'var(--color-neutral-500)' }}>
                                  {new Date(p.voided_at).toLocaleString()}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: 'var(--color-neutral-600)' }}>
                              {p.notes || '-'}
                            </span>
                          )}
                        </td>
                        {isDirectorOrAdmin && (
                          <td>
                            {isRecorded ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOpenVoidModal(p)}
                              >
                                Void
                              </Button>
                            ) : (
                              <span style={{ color: 'var(--color-neutral-400)', fontSize: '0.75rem' }}>Voided</span>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Financial Summary Card */}
      <div className={styles.totalsCard}>
        <div className={styles.totalsRow}>
          <span>Subtotal Work (Approved):</span>
          <span>{formatCurrency(invoice.subtotal_work)}</span>
        </div>
        <div className={styles.totalsRow}>
          <span>Subtotal Material (Approved Cost):</span>
          <span>{formatCurrency(invoice.subtotal_material)}</span>
        </div>
        <div className={styles.totalsRow}>
          <span>Tax Amount:</span>
          {isDraft && isDirectorOrAdmin ? (
            <input
              type="number"
              step="0.01"
              min="0"
              style={{ width: '120px', padding: '4px 8px', textAlign: 'right' }}
              value={taxAmount}
              onChange={(e) => setTaxAmount(parseFloat(e.target.value) || 0)}
            />
          ) : (
            <span>{formatCurrency(invoice.tax_amount)}</span>
          )}
        </div>
        <div className={styles.totalsTotal}>
          <span>Total Billed Amount:</span>
          <span>{formatCurrency(invoice.total_amount)}</span>
        </div>
        <div className={styles.totalsRow}>
          <span>Paid Amount:</span>
          <span style={{ color: '#16a34a', fontWeight: 600 }}>{formatCurrency(invoice.paid_amount)}</span>
        </div>
        <div className={styles.totalsRow}>
          <span>Balance Due:</span>
          <span style={{ fontWeight: 700, color: balanceDue > 0 ? '#b91c1c' : '#15803d' }}>
            {formatCurrency(balanceDue)}
          </span>
        </div>
      </div>

      {/* Issue Confirmation Modal */}
      {showIssueModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <h3>Issue Invoice</h3>
            {issueError && <ErrorMessage message={issueError} />}
            <p style={{ color: 'var(--color-neutral-700)', fontSize: '0.875rem' }}>
              Are you sure you want to issue <strong>{invoice.invoice_number}</strong>? Once issued, this invoice
              and all rates, quantities, descriptions, and amounts become permanently frozen and immutable.
            </p>
            <Input
              label="Issue Date"
              type="date"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
            />
            <Input
              label="Due Date (Optional)"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
            <div className={styles.modalActions}>
              <Button variant="outline" onClick={() => setShowIssueModal(false)} disabled={issuing}>
                Back
              </Button>
              <Button variant="primary" onClick={handleIssue} disabled={issuing}>
                {issuing ? 'Issuing...' : 'Confirm & Issue Invoice'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Confirmation Modal */}
      {showCancelModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <h3>Cancel Invoice</h3>
            {cancelError && <ErrorMessage message={cancelError} />}
            <p style={{ color: '#991b1b', fontSize: '0.875rem' }}>
              Cancelling invoice <strong>{invoice.invoice_number}</strong> will atomically release its source locks,
              allowing the underlying daily work and material entries to be re-invoiced.
            </p>
            <Input
              label="Cancellation Reason *"
              placeholder="State mandatory reason for cancellation"
              value={cancellationReason}
              onChange={(e) => setCancellationReason(e.target.value)}
            />
            <div className={styles.modalActions}>
              <Button variant="outline" onClick={() => setShowCancelModal(false)} disabled={cancelling}>
                Back
              </Button>
              <Button variant="danger" onClick={handleCancel} disabled={cancelling || !cancellationReason.trim()}>
                {cancelling ? 'Cancelling...' : 'Confirm Cancellation'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Record Payment Modal */}
      {showRecordPaymentModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="record-payment-title">
          <div className={styles.modalContent}>
            <h3 id="record-payment-title">Record Client Payment</h3>
            {recordPaymentError && <ErrorMessage message={recordPaymentError} />}
            <p style={{ color: 'var(--color-neutral-700)', fontSize: '0.875rem', margin: 0 }}>
              Record a payment received for invoice <strong>{invoice.invoice_number}</strong>. Outstanding balance:{' '}
              <strong style={{ color: '#b91c1c' }}>{formatCurrency(balanceDue)}</strong>.
            </p>

            <Input
              label="Payment Amount (₹) *"
              type="number"
              step="0.01"
              min="0.01"
              max={balanceDue > 0 ? balanceDue : undefined}
              value={paymentAmount}
              onChange={(e) => setPaymentAmount(e.target.value)}
              placeholder="0.00"
              required
            />

            <Input
              label="Payment Date *"
              type="date"
              min={invoice.issue_date || undefined}
              max={getLocalISODate(new Date())}
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              required
            />

            <Select
              label="Payment Method *"
              options={PAYMENT_METHOD_OPTIONS}
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
              required
            />

            <Input
              label="Reference / UTR / Cheque Number"
              type="text"
              placeholder="e.g. UTR12345678 or CHQ987654"
              value={paymentRef}
              onChange={(e) => setPaymentRef(e.target.value)}
            />

            <Input
              label="Notes / Remarks"
              type="text"
              placeholder="Optional payment notes"
              value={paymentNotes}
              onChange={(e) => setPaymentNotes(e.target.value)}
            />

            <div>
              <label htmlFor="record-receipt-file-input" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '6px' }}>
                Receipt / Bank Slip (Optional)
              </label>
              <input
                id="record-receipt-file-input"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                aria-label="Receipt / Bank Slip (Optional)"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    if (f.size > 10 * 1024 * 1024) {
                      setRecordPaymentError('Receipt file size exceeds 10MB limit.');
                      setRecordReceiptFile(null);
                    } else {
                      setRecordPaymentError(null);
                      setRecordReceiptFile(f);
                    }
                  }
                }}
                style={{ fontSize: '0.875rem' }}
              />
              <small style={{ display: 'block', color: 'var(--color-neutral-500)', marginTop: '4px' }}>
                Supported formats: PDF, JPG, PNG, WebP (Max 10MB).
              </small>
              {recordReceiptFile && (
                <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#166534' }}>
                  Selected: {recordReceiptFile.name} ({(recordReceiptFile.size / 1024).toFixed(1)} KB)
                  <button
                    type="button"
                    onClick={() => setRecordReceiptFile(null)}
                    style={{
                      marginLeft: '8px',
                      color: '#b91c1c',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>

            <div className={styles.modalActions}>
              <Button
                variant="outline"
                onClick={() => setShowRecordPaymentModal(false)}
                disabled={recordingPayment}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleRecordPayment}
                disabled={recordingPayment || !paymentAmount || parseFloat(paymentAmount) <= 0}
              >
                {recordingPayment ? 'Recording...' : 'Confirm & Record Payment'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Void Payment Modal */}
      {showVoidPaymentModal && selectedPaymentToVoid && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="void-payment-title">
          <div className={styles.modalContent}>
            <h3 id="void-payment-title">Void Payment</h3>
            {voidPaymentError && <ErrorMessage message={voidPaymentError} />}
            <p style={{ color: '#991b1b', fontSize: '0.875rem', margin: 0 }}>
              Are you sure you want to void payment <strong>{selectedPaymentToVoid.payment_number}</strong> for{' '}
              <strong>{formatCurrency(selectedPaymentToVoid.amount)}</strong>? This will atomically reverse the payment
              from invoice <strong>{invoice.invoice_number}</strong> and recalculate outstanding balance.
            </p>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '6px' }}>
                Void Audit Reason *
              </label>
              <textarea
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--color-neutral-300)',
                  fontSize: '0.875rem',
                  minHeight: '80px',
                  boxSizing: 'border-box',
                }}
                placeholder="State mandatory audit reason (at least 10 characters)"
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
              />
              <small style={{ color: voidReason.trim().length < 10 ? '#b91c1c' : 'var(--color-neutral-500)' }}>
                {voidReason.trim().length} / 10 characters minimum
              </small>
            </div>

            <div className={styles.modalActions}>
              <Button
                variant="outline"
                onClick={() => {
                  setShowVoidPaymentModal(false);
                  setSelectedPaymentToVoid(null);
                }}
                disabled={voidingPayment}
              >
                Back
              </Button>
              <Button
                variant="danger"
                onClick={handleVoidPayment}
                disabled={voidingPayment || voidReason.trim().length < 10}
              >
                {voidingPayment ? 'Voiding...' : 'Confirm & Void Payment'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Attach / Replace Receipt Modal */}
      {showAttachReceiptModal && selectedPaymentForReceipt && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="attach-receipt-title">
          <div className={styles.modalContent}>
            <h3 id="attach-receipt-title">
              {selectedPaymentForReceipt.receipt_url ? 'Replace Receipt' : 'Attach Receipt'}
            </h3>
            {attachReceiptError && <ErrorMessage message={attachReceiptError} />}
            <p style={{ color: 'var(--color-neutral-700)', fontSize: '0.875rem', margin: 0 }}>
              Upload receipt for payment <strong>{selectedPaymentForReceipt.payment_number}</strong> ({formatCurrency(selectedPaymentForReceipt.amount)}).
            </p>

            <div>
              <label htmlFor="attach-receipt-file-input" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '6px' }}>
                Select File (PDF, JPG, PNG, WebP — Max 10MB) *
              </label>
              <input
                id="attach-receipt-file-input"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                aria-label="Select Receipt File"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    if (f.size > 10 * 1024 * 1024) {
                      setAttachReceiptError('File size exceeds the 10MB limit.');
                      setAttachReceiptFile(null);
                    } else {
                      setAttachReceiptError(null);
                      setAttachReceiptFile(f);
                    }
                  }
                }}
                style={{ fontSize: '0.875rem' }}
              />
              {attachReceiptFile && (
                <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#166534' }}>
                  Selected: {attachReceiptFile.name} ({(attachReceiptFile.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>

            <div className={styles.modalActions}>
              <Button
                variant="outline"
                onClick={() => {
                  setShowAttachReceiptModal(false);
                  setSelectedPaymentForReceipt(null);
                  setAttachReceiptFile(null);
                }}
                disabled={attachingReceipt}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleAttachReceiptSubmit}
                disabled={attachingReceipt || !attachReceiptFile}
              >
                {attachingReceipt ? 'Uploading...' : 'Upload Receipt'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

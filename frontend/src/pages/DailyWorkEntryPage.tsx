import React, { useEffect, useState, useMemo, useContext, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Select, type SelectOption } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import {
  getActivities,
  getWorkOrders,
  getDailyWorkEntries,
  createDailyWorkEntry,
  updateDailyWorkEntry,
  submitDailyWorkEntry,
  type Activity,
  type WorkOrder,
  type DailyWorkEntry,
  type WorkPhoto,
  type MaterialTransaction,
} from '../api/dailyWork';
import { WorkPhotoCapture } from '../components/WorkPhotoCapture';
import { MaterialTransactionEntry } from '../components/MaterialTransactionEntry';
import { getAttendanceRecords, type AttendanceRecord } from '../api/attendance';
import { AuthContext } from '../context/AuthContext';
import { normalizeError } from '../api/client';
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Loader2,
  Save,
  Send,
  MapPin,
  Clock,
  RotateCcw,
  X,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  Paperclip,
} from 'lucide-react';
import styles from './DailyWorkEntryPage.module.css';
import { AxiosError } from 'axios';

export const getDraftStorageKey = (empId: string, dateStr: string) =>
  `daily_work_draft_${empId}_${dateStr}`;

export const generateClientUuid = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export interface LocalDailyWorkLineDraft {
  id?: string;
  idempotencyKey: string;
  activityId: string;
  workOrderId?: string;
  quantity: number;
  remarks?: string;
}

export interface LocalDailyWorkDraft {
  employeeId: string;
  date: string;
  items: LocalDailyWorkLineDraft[];
  savedAt: number;
}

export interface ActivityLineItem {
  id?: string;
  tempId: string;
  idempotencyKey: string;
  activityId: string;
  workOrderId: string;
  quantity: number | '';
  uom: string;
  remarks: string;
  status: string;
  photos: WorkPhoto[];
  materials: MaterialTransaction[];
  saveError?: string | null;
  expandedAttachments?: boolean;
}

export interface DailyWorkEntryPageProps {
  employeeId?: string;
  debounceMs?: number;
}

export const DailyWorkEntryPage: React.FC<DailyWorkEntryPageProps> = ({
  employeeId,
  debounceMs = 1000,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Reference data
  const [activities, setActivities] = useState<Activity[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord | null>(null);

  // Multi-Activity Line Items State
  const [lineItems, setLineItems] = useState<ActivityLineItem[]>([]);
  const [pendingRestoreDraft, setPendingRestoreDraft] = useState<LocalDailyWorkDraft | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState<boolean>(false);

  const today = useMemo(() => new Date().toISOString().split('T')[0], []);
  const auth = useContext(AuthContext);

  const effectiveEmployeeId =
    employeeId ||
    auth?.user?.id ||
    auth?.user?.user_id ||
    attendance?.employee_id ||
    'default_employee';

  const storageKey = useMemo(() => {
    return getDraftStorageKey(effectiveEmployeeId, today);
  }, [effectiveEmployeeId, today]);

  const activityOptions: SelectOption[] = useMemo(() => {
    const list = activities.map((a) => ({
      value: a.id,
      label: `${a.name} (${a.category.toUpperCase()}) - ${a.unit_of_measure}`,
    }));
    return [{ value: '', label: '-- Select Activity --' }, ...list];
  }, [activities]);

  const workOrderOptions: SelectOption[] = useMemo(() => {
    const list = workOrders.map((w) => ({
      value: w.id,
      label: `${w.order_number}${w.description ? ` - ${w.description}` : ''}`,
    }));
    return [{ value: '', label: '-- None / Not Applicable --' }, ...list];
  }, [workOrders]);

  const createEmptyLine = useCallback(
    (acts: Activity[]): ActivityLineItem => {
      const defaultAct = acts.length > 0 ? acts[0] : null;
      return {
        tempId: generateClientUuid(),
        idempotencyKey: generateClientUuid(),
        activityId: defaultAct ? defaultAct.id : '',
        workOrderId: '',
        quantity: 0,
        uom: defaultAct ? defaultAct.unit_of_measure : '',
        remarks: '',
        status: 'draft',
        photos: [],
        materials: [],
        saveError: null,
        expandedAttachments: false,
      };
    },
    []
  );

  const allLinesValidQuantity = useMemo(() => {
    if (lineItems.length === 0) return false;
    return lineItems.every((it) => Boolean(it.activityId) && Number(it.quantity) > 0);
  }, [lineItems]);

  const isReadOnly = useMemo(() => {
    if (lineItems.length === 0) return false;
    return lineItems.every((it) => it.status === 'submitted' || it.status === 'approved');
  }, [lineItems]);

  const overallStatus = useMemo(() => {
    if (lineItems.length === 0) return 'draft';
    if (lineItems.every((it) => it.status === 'approved')) return 'approved';
    if (lineItems.every((it) => it.status === 'submitted' || it.status === 'approved')) return 'submitted';
    if (lineItems.some((it) => it.status === 'correction_required')) return 'correction_required';
    if (lineItems.some((it) => it.status === 'rejected')) return 'rejected';
    return 'draft';
  }, [lineItems]);

  const isCheckedIn = attendance ? attendance.check_out_time === null : false;

  const loadData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [acts, wos, attList, entries] = await Promise.all([
        getActivities().catch(() => [] as Activity[]),
        getWorkOrders().catch(() => [] as WorkOrder[]),
        getAttendanceRecords(today).catch(() => [] as AttendanceRecord[]),
        getDailyWorkEntries(today).catch(() => [] as DailyWorkEntry[]),
      ]);

      setActivities(acts);
      setWorkOrders(wos);

      if (attList.length > 0) {
        const sorted = [...attList].sort(
          (a, b) => new Date(b.check_in_time).getTime() - new Date(a.check_in_time).getTime()
        );
        setAttendance(sorted[0]);
      } else {
        setAttendance(null);
      }

      // Check for existing work entries from server
      if (entries.length > 0) {
        const mappedLines: ActivityLineItem[] = entries.map((entry) => {
          const matchedAct = acts.find((a) => a.id === entry.activity_id);
          return {
            id: entry.id,
            tempId: entry.id,
            idempotencyKey: entry.idempotency_key || entry.id,
            activityId: entry.activity_id,
            workOrderId: entry.work_order_id || '',
            quantity: Number(entry.quantity) || 0,
            uom: entry.uom || (matchedAct ? matchedAct.unit_of_measure : ''),
            remarks: entry.remarks || '',
            status: entry.status,
            photos: entry.photos || [],
            materials: entry.materials || [],
            saveError: null,
            expandedAttachments: false,
          };
        });
        setLineItems(mappedLines);
      } else {
        setLineItems([createEmptyLine(acts)]);
      }

      // Check for unsaved local draft with Refinement 3 Migration Guard
      const currentEmpId =
        employeeId ||
        auth?.user?.id ||
        auth?.user?.user_id ||
        (attList.length > 0 ? attList[0].employee_id : undefined) ||
        'default_employee';

      const key = getDraftStorageKey(currentEmpId, today);
      const localDraftRaw = localStorage.getItem(key);
      if (localDraftRaw) {
        try {
          const parsed = JSON.parse(localDraftRaw);
          // Refinement 3: Migration Guard for old scalar shape
          // If items is not an array, or if old legacy scalar properties are present, safely discard
          if (!parsed || !Array.isArray(parsed.items) || 'cableRuns' in parsed) {
            localStorage.removeItem(key);
          } else if (
            parsed.employeeId === currentEmpId &&
            parsed.date === today &&
            parsed.items.length > 0
          ) {
            const latestServerTime = entries.reduce((maxT, e) => {
              const t = new Date(e.updated_at || e.created_at || 0).getTime();
              return t > maxT ? t : maxT;
            }, 0);

            if (entries.length === 0 || (parsed.savedAt && parsed.savedAt > latestServerTime)) {
              setPendingRestoreDraft(parsed as LocalDailyWorkDraft);
            }
          }
        } catch {
          localStorage.removeItem(key);
        }
      }
    } catch (err) {
      const normalized = normalizeError(err as AxiosError<any>);
      setErrorMsg(`Failed to load work entry data: ${normalized.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [today, employeeId]);

  // Debounced LocalStorage Auto-Save (FE-013)
  useEffect(() => {
    if (loading || isReadOnly || Boolean(pendingRestoreDraft)) return;

    const isDirty = lineItems.some(
      (it) => Boolean(it.activityId) || Number(it.quantity) > 0 || Boolean(it.remarks.trim())
    );

    if (!isDirty) return;

    const timer = setTimeout(() => {
      try {
        const draftObj: LocalDailyWorkDraft = {
          employeeId: effectiveEmployeeId,
          date: today,
          items: lineItems.map((it) => ({
            id: it.id,
            idempotencyKey: it.idempotencyKey,
            activityId: it.activityId,
            workOrderId: it.workOrderId || undefined,
            quantity: Number(it.quantity) || 0,
            remarks: it.remarks || undefined,
          })),
          savedAt: Date.now(),
        };
        localStorage.setItem(storageKey, JSON.stringify(draftObj));
      } catch {
        // ignore quota errors
      }
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [
    loading,
    isReadOnly,
    pendingRestoreDraft,
    storageKey,
    effectiveEmployeeId,
    today,
    lineItems,
    debounceMs,
  ]);

  const handleRestoreDraft = () => {
    if (!pendingRestoreDraft) return;

    const restoredLines: ActivityLineItem[] = pendingRestoreDraft.items.map((item) => {
      const matchedAct = activities.find((a) => a.id === item.activityId);
      return {
        id: item.id,
        tempId: item.id || item.idempotencyKey || generateClientUuid(),
        idempotencyKey: item.idempotencyKey || generateClientUuid(),
        activityId: item.activityId,
        workOrderId: item.workOrderId || '',
        quantity: item.quantity ?? 0,
        uom: matchedAct ? matchedAct.unit_of_measure : '',
        remarks: item.remarks || '',
        status: 'draft',
        photos: [],
        materials: [],
        saveError: null,
        expandedAttachments: false,
      };
    });

    setLineItems(restoredLines);
    setPendingRestoreDraft(null);
    setSuccessMsg('Local draft restored.');
  };

  const handleDiscardDraft = () => {
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
    setPendingRestoreDraft(null);
  };

  const updateLineField = (index: number, field: keyof ActivityLineItem, value: any) => {
    setLineItems((prev) => {
      const next = [...prev];
      const line = { ...next[index], [field]: value };
      if (field !== 'saveError') {
        line.saveError = null;
      }
      if (field === 'activityId') {
        const act = activities.find((a) => a.id === value);
        line.uom = act ? act.unit_of_measure : '';
      }
      next[index] = line;
      return next;
    });
  };

  const handleAddLine = () => {
    setLineItems((prev) => [...prev, createEmptyLine(activities)]);
  };

  const handleRemoveLine = (index: number) => {
    setLineItems((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((_, i) => i !== index);
    });
  };

  const toggleExpandAttachments = (index: number) => {
    setLineItems((prev) => {
      const next = [...prev];
      next[index] = {
        ...next[index],
        expandedAttachments: !next[index].expandedAttachments,
      };
      return next;
    });
  };

  // Refinement 1 & 2: Save a single line item with error tracking and retry capability
  const saveSingleLineItem = async (index: number): Promise<boolean> => {
    const line = lineItems[index];
    if (!line.activityId) {
      updateLineField(index, 'saveError', 'Please select an activity.');
      return false;
    }

    const qty = Number(line.quantity) || 0;
    if (qty < 0) {
      updateLineField(index, 'saveError', 'Quantity must be non-negative.');
      return false;
    }

    try {
      if (line.id) {
        const updated = await updateDailyWorkEntry(line.id, {
          activity_id: line.activityId,
          work_order_id: line.workOrderId || null,
          quantity: qty,
          remarks: line.remarks.trim() || null,
        });

        setLineItems((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            status: updated.status,
            photos: updated.photos || next[index].photos,
            materials: updated.materials || next[index].materials,
            saveError: null,
          };
          return next;
        });
      } else {
        const created = await createDailyWorkEntry({
          idempotency_key: line.idempotencyKey,
          activity_id: line.activityId,
          work_order_id: line.workOrderId || null,
          quantity: qty,
          work_date: today,
          remarks: line.remarks.trim() || null,
        });

        setLineItems((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            id: created.id,
            status: created.status,
            photos: created.photos || [],
            materials: created.materials || [],
            saveError: null,
          };
          return next;
        });
      }
      return true;
    } catch (err: any) {
      const norm = normalizeError(err as AxiosError<any>);
      const msg = norm.message || 'Failed to save activity line.';
      updateLineField(index, 'saveError', msg);
      return false;
    }
  };

  // Refinement 1: Auto-save on first attachment
  const handleAutoSaveForAttachments = async (index: number) => {
    setSaving(true);
    setErrorMsg(null);
    const success = await saveSingleLineItem(index);
    setSaving(false);
    if (success) {
      setSuccessMsg('Activity line saved. You can now add photos and materials.');
      setLineItems((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], expandedAttachments: true };
        return next;
      });
    }
  };

  // Refinement 2: Save All Drafts with partial-failure reporting
  const handleSaveAllDrafts = async () => {
    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    let anyFailed = false;
    for (let i = 0; i < lineItems.length; i++) {
      const ok = await saveSingleLineItem(i);
      if (!ok) {
        anyFailed = true;
      }
    }

    setSaving(false);
    if (anyFailed) {
      setErrorMsg('Some activity lines could not be saved. Please review and retry the highlighted lines.');
    } else {
      setSuccessMsg('All activity lines saved successfully!');
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // ignore
      }
      setPendingRestoreDraft(null);
    }
  };

  const handleOpenSubmitModal = () => {
    setErrorMsg(null);
    if (lineItems.length === 0) {
      setErrorMsg('No activity lines to submit.');
      return;
    }

    const missingActivity = lineItems.some((it) => !it.activityId);
    if (missingActivity) {
      setErrorMsg('Please select an activity for every line before submitting.');
      return;
    }

    const hasZeroQuantity = lineItems.some((it) => (Number(it.quantity) || 0) <= 0);
    if (hasZeroQuantity) {
      setErrorMsg('Cannot submit: All activity lines must have a quantity greater than zero.');
      return;
    }

    setShowSubmitModal(true);
  };

  const handleConfirmSubmit = async () => {
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      // Step 1: Ensure all line items are saved first
      let saveFailed = false;
      for (let i = 0; i < lineItems.length; i++) {
        const ok = await saveSingleLineItem(i);
        if (!ok) {
          saveFailed = true;
        }
      }

      if (saveFailed) {
        setErrorMsg('Failed to save all activity lines before submission. Please review errors.');
        setShowSubmitModal(false);
        setSubmitting(false);
        return;
      }

      // Step 2: Submit all line items
      for (let i = 0; i < lineItems.length; i++) {
        const item = lineItems[i];
        if (item.id && (item.status === 'draft' || item.status === 'correction_required')) {
          await submitDailyWorkEntry(item.id);
        }
      }

      // Step 3: Transition status to submitted
      setLineItems((prev) =>
        prev.map((it) => ({
          ...it,
          status: 'submitted',
        }))
      );

      setShowSubmitModal(false);
      setSuccessMsg('Work entry submitted successfully! Submitted for supervisor review.');

      try {
        localStorage.removeItem(storageKey);
      } catch {
        // ignore
      }
      setPendingRestoreDraft(null);
    } catch (err: any) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to submit work entries.');
      setShowSubmitModal(false);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <Card title="Daily Work Entry" subtitle="Record daily progress and work quantities">
          <div className={styles.loadingSpinner}>
            <Loader2 className={styles.spinIcon} size={28} />
            <span>Loading work entry form...</span>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Attendance Context Banner */}
      {isCheckedIn ? (
        <div className={`${styles.attendanceBanner} ${styles.checkedIn}`}>
          <MapPin size={18} />
          <div>
            <strong>Checked in</strong> at {attendance?.site_name || 'Assigned Site'}{' '}
            <span>({attendance?.check_in_time ? new Date(attendance.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''})</span>
          </div>
        </div>
      ) : (
        <div className={`${styles.attendanceBanner} ${styles.notCheckedIn}`} data-testid="attendance-banner-not-checked-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            <span>You are not checked in today. Attendance is required for submission.</span>
          </div>
          <Link to="/attendance">
            <Button size="sm" variant="outline">Go to Attendance</Button>
          </Link>
        </div>
      )}

      {/* Local Draft Restore Prompt (FE-013) */}
      {pendingRestoreDraft && !isReadOnly && (
        <div className={styles.restorePromptBanner} data-testid="draft-restore-prompt">
          <div className={styles.restorePromptText}>
            <Clock size={16} />
            <span>You have an unsaved local draft available from earlier today.</span>
          </div>
          <div className={styles.restorePromptActions}>
            <Button size="sm" variant="primary" data-testid="restore-draft-btn" onClick={handleRestoreDraft}>
              <RotateCcw size={14} style={{ marginRight: 4 }} />
              Restore Draft
            </Button>
            <Button size="sm" variant="outline" data-testid="discard-draft-btn" onClick={handleDiscardDraft}>
              <X size={14} style={{ marginRight: 4 }} />
              Discard
            </Button>
          </div>
        </div>
      )}

      {/* Global Alerts */}
      {errorMsg && (
        <div className={styles.alertError} role="alert">
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>{errorMsg}</div>
        </div>
      )}
      {successMsg && (
        <div className={styles.alertSuccess} role="status">
          <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>{successMsg}</div>
        </div>
      )}

      {/* Locked Notice if Read Only */}
      {isReadOnly && (
        <div className={styles.alertSuccess} data-testid="locked-notice">
          <CheckCircle2 size={18} />
          <span>Daily work entry is {overallStatus}. Submitted for supervisor review (read-only).</span>
        </div>
      )}

      <Card
        title="Daily Work Entry"
        subtitle={`Session for ${today} • Grouped line items per visit`}
      >
        <div className={styles.statusHeader}>
          <h3>Work Activities</h3>
          <StatusBadge status={overallStatus} />
        </div>

        {/* Activity Line Items List */}
        <div className={styles.lineItemsList}>
          {lineItems.map((line, index) => {
            const matchedAct = activities.find((a) => a.id === line.activityId);
            const lineReadOnly = line.status === 'submitted' || line.status === 'approved';

            return (
              <div
                key={line.tempId}
                className={`${styles.lineItemCard} ${line.saveError ? styles.hasError : ''}`}
                data-testid={`activity-line-card-${index}`}
              >
                {/* Line Item Header */}
                <div className={styles.lineItemHeader}>
                  <div className={styles.lineItemTitle}>
                    <span>Activity #{index + 1}</span>
                    <StatusBadge status={line.status || 'draft'} />
                  </div>
                  <div className={styles.lineItemHeaderActions}>
                    {!isReadOnly && !lineReadOnly && lineItems.length > 1 && (
                      <button
                        type="button"
                        className={styles.removeLineBtn}
                        onClick={() => handleRemoveLine(index)}
                        title="Remove activity line"
                      >
                        <Trash2 size={14} />
                        Remove Line
                      </button>
                    )}
                  </div>
                </div>

                {/* Line Form Grid */}
                <div className={styles.lineItemGrid}>
                  {/* Activity Selector */}
                  <div>
                    <Select
                      label={`Activity #${index + 1} *`}
                      options={activityOptions}
                      value={line.activityId}
                      onChange={(e) => updateLineField(index, 'activityId', e.target.value)}
                      disabled={isReadOnly || lineReadOnly}
                    />
                  </div>

                  {/* Quantity and Auto-derived UOM */}
                  <div className={styles.quantityGroup}>
                    <label htmlFor={`quantity-input-${index}`}>
                      Quantity *
                    </label>
                    <div className={styles.quantityInputRow}>
                      <input
                        id={`quantity-input-${index}`}
                        type="number"
                        min="0"
                        step="any"
                        className={styles.quantityInput}
                        value={line.quantity}
                        onChange={(e) => {
                          const val = e.target.value;
                          updateLineField(index, 'quantity', val === '' ? '' : parseFloat(val));
                        }}
                        placeholder="0.0"
                        disabled={isReadOnly || lineReadOnly}
                      />
                      <span className={styles.uomBadge} title="Auto-derived Unit of Measure">
                        {line.uom || (matchedAct ? matchedAct.unit_of_measure : '—')}
                      </span>
                    </div>
                  </div>

                  {/* Work Order Selector */}
                  <div>
                    <Select
                      label="Work Order"
                      options={workOrderOptions}
                      value={line.workOrderId}
                      onChange={(e) => updateLineField(index, 'workOrderId', e.target.value)}
                      disabled={isReadOnly || lineReadOnly}
                    />
                  </div>
                </div>

                {/* Remarks Row */}
                <div className={styles.remarksRow}>
                  <label htmlFor={`remarks-input-${index}`}>Remarks &amp; Notes</label>
                  <textarea
                    id={`remarks-input-${index}`}
                    className={styles.remarksInput}
                    value={line.remarks}
                    onChange={(e) => updateLineField(index, 'remarks', e.target.value)}
                    placeholder="Optional notes regarding this activity..."
                    disabled={isReadOnly || lineReadOnly}
                  />
                </div>

                {/* Line-Specific Partial Failure Banner & Retry (Refinement 2) */}
                {line.saveError && (
                  <div className={styles.lineItemError} role="alert" data-testid={`line-error-${index}`}>
                    <span>
                      <strong>Error saving line #{index + 1}:</strong> {line.saveError}
                    </span>
                    <button
                      type="button"
                      className={styles.lineItemRetryBtn}
                      onClick={() => saveSingleLineItem(index)}
                      disabled={saving}
                    >
                      Retry Line #{index + 1}
                    </button>
                  </div>
                )}

                {/* Expandable Attachments: Photos & Materials (Decision #4 & Refinement 1) */}
                <div className={styles.attachmentsContainer}>
                  <button
                    type="button"
                    className={styles.attachmentsToggle}
                    onClick={() => toggleExpandAttachments(index)}
                  >
                    <Paperclip size={14} />
                    <span>
                      Attachments &amp; Materials ({line.photos.length} photos, {line.materials.length} items)
                    </span>
                    {line.expandedAttachments ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {line.expandedAttachments && (
                    <div className={styles.attachmentsBody}>
                      {line.id ? (
                        <>
                          <WorkPhotoCapture
                            dailyWorkEntryId={line.id}
                            status={line.status || 'draft'}
                            initialPhotos={line.photos}
                            onPhotosLoaded={(loadedPhotos) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                if (next[index]) {
                                  next[index] = {
                                    ...next[index],
                                    photos: loadedPhotos,
                                  };
                                }
                                return next;
                              });
                            }}
                            onPhotoUploaded={(photo) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                next[index] = {
                                  ...next[index],
                                  photos: [photo, ...next[index].photos],
                                };
                                return next;
                              });
                            }}
                            onPhotoDeleted={(photoId) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                next[index] = {
                                  ...next[index],
                                  photos: next[index].photos.filter((p) => p.id !== photoId),
                                };
                                return next;
                              });
                            }}
                          />

                          <MaterialTransactionEntry
                            dailyWorkEntryId={line.id}
                            status={line.status || 'draft'}
                            initialMaterials={line.materials}
                            onMaterialsLoaded={(loadedMaterials) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                if (next[index]) {
                                  next[index] = {
                                    ...next[index],
                                    materials: loadedMaterials,
                                  };
                                }
                                return next;
                              });
                            }}
                            onMaterialAdded={(tx) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                next[index] = {
                                  ...next[index],
                                  materials: [tx, ...next[index].materials],
                                };
                                return next;
                              });
                            }}
                            onMaterialDeleted={(txId) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                next[index] = {
                                  ...next[index],
                                  materials: next[index].materials.filter((m) => m.id !== txId),
                                };
                                return next;
                              });
                            }}
                          />
                        </>
                      ) : (
                        <div className={styles.unpersistedAttachmentNotice}>
                          <span>
                            Save this activity line draft first to attach photos and materials.
                          </span>
                          <button
                            type="button"
                            className={styles.autoSaveBtn}
                            onClick={() => handleAutoSaveForAttachments(index)}
                            disabled={saving}
                          >
                            Auto-save &amp; Attach
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Add Another Activity Button */}
        {!isReadOnly && (
          <div style={{ marginTop: 16 }}>
            <button
              type="button"
              className={styles.addLineButton}
              onClick={handleAddLine}
              style={{ width: '100%' }}
            >
              <Plus size={18} />
              Add Another Activity Line
            </button>
          </div>
        )}

        {/* Action Bar */}
        <div className={styles.actionsBar}>
          {!allLinesValidQuantity && !isReadOnly && (
            <div className={styles.zeroQuantitiesNotice}>
              * Enter at least one quantity to enable submission.
            </div>
          )}

          {!isReadOnly && (
            <Button
              variant="outline"
              onClick={handleSaveAllDrafts}
              disabled={saving || submitting}
            >
              {saving ? (
                <>
                  <Loader2 size={16} className={styles.spinIcon} style={{ marginRight: 6 }} />
                  Saving Drafts...
                </>
              ) : (
                <>
                  <Save size={16} style={{ marginRight: 6 }} />
                  Save Draft
                </>
              )}
            </Button>
          )}

          {!isReadOnly && (
            <Button
              variant="primary"
              onClick={handleOpenSubmitModal}
              disabled={saving || submitting || !allLinesValidQuantity}
            >
              <Send size={16} style={{ marginRight: 6 }} />
              Submit Work ({lineItems.length} {lineItems.length === 1 ? 'Line' : 'Lines'})
            </Button>
          )}
        </div>
      </Card>

      {/* Unified Submit Modal */}
      {showSubmitModal && (
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="submit-modal-title"
          data-testid="submit-confirmation-modal"
        >
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h2 id="submit-modal-title">Review &amp; Submit Daily Work</h2>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
              >
                <X size={20} />
              </button>
            </div>

            <div className={styles.modalBody}>
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#475569' }}>
                Please review the {lineItems.length} activity line items recorded for today:
              </p>

              <table className={styles.modalTable}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Activity</th>
                    <th>Qty &amp; UOM</th>
                    <th>Attachments</th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((line, idx) => {
                    const act = activities.find((a) => a.id === line.activityId);
                    return (
                      <tr key={line.tempId}>
                        <td>{idx + 1}</td>
                        <td>
                          <strong>{act?.name || 'Selected Activity'}</strong>
                          {line.workOrderId && (
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                              WO: {workOrders.find((w) => w.id === line.workOrderId)?.order_number || line.workOrderId}
                            </div>
                          )}
                        </td>
                        <td>
                          {line.quantity} {line.uom || act?.unit_of_measure}
                        </td>
                        <td>
                          {line.photos.length} photo(s), {line.materials.length} transaction(s)
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <div className={styles.warningBox}>
                <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <strong>Locking Notice:</strong> Once submitted, all activity lines will be locked for editing until supervisor verification.
                </div>
              </div>
            </div>

            <div className={styles.modalFooter}>
              <Button
                variant="outline"
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirmSubmit}
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className={styles.spinIcon} style={{ marginRight: 6 }} />
                    Submitting All Lines...
                  </>
                ) : (
                  'Confirm & Submit'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

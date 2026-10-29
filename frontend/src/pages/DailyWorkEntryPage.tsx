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
  getMaterialsCatalogue,
  type Activity,
  type WorkOrder,
  type DailyWorkEntry,
  type WorkPhoto,
  type MaterialTransaction,
  type CatalogueMaterial,
} from '../api/dailyWork';
import { WorkPhotoCapture } from '../components/WorkPhotoCapture';
import { MaterialTransactionEntry } from '../components/MaterialTransactionEntry';
import {
  isMatchingConsumedMaterial,
  isDistanceUom,
  getActivityUnitDisplay,
} from '../utils/materialMapping';
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

export interface MeasurementRow {
  tempId: string;
  startPoint: string;
  endPoint: string;
  distance: number | '';
}

export const createEmptyMeasurementRow = (
  startPoint = '',
  endPoint = '',
  distance: number | '' = ''
): MeasurementRow => ({
  tempId: generateClientUuid(),
  startPoint,
  endPoint,
  distance,
});

export const formatTotalDistance = (val: number | string | '' | null | undefined): string => {
  if (val === null || val === undefined || val === '') return '0.00';
  const num = Number(val);
  return isNaN(num) ? '0.00' : num.toFixed(2);
};

export const syncLineMaterialsWithMeasurement = (
  currentMaterials: MaterialTransaction[],
  activityId: string,
  newTotal: number,
  allActivities: Activity[],
  allCatalogueMaterials: CatalogueMaterial[],
  _ownerId?: string
): MaterialTransaction[] => {
  const activity = allActivities.find((a) => a.id === activityId);
  if (!activity) return currentMaterials;

  // Check if there is already a matching consumed material transaction
  const hasMatching = currentMaterials.some((tx) =>
    isMatchingConsumedMaterial(tx, activity, allCatalogueMaterials)
  );

  if (hasMatching) {
    return currentMaterials.map((tx) => {
      if (isMatchingConsumedMaterial(tx, activity, allCatalogueMaterials)) {
        return {
          ...tx,
          quantity: newTotal,
        };
      }
      return tx;
    });
  }

  return currentMaterials;
};

export interface LocalDailyWorkLineDraft {
  id?: string;
  idempotencyKey: string;
  activityId: string;
  workOrderId?: string;
  measurements?: { startPoint: string; endPoint: string; distance: number | '' }[];
  quantity?: number;
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
  measurements: MeasurementRow[];
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

export const dedupePhotos = (photos?: WorkPhoto[] | null): WorkPhoto[] => {
  if (!photos || !Array.isArray(photos)) return [];
  const seen = new Set<string>();
  const result: WorkPhoto[] = [];
  for (const p of photos) {
    if (p && p.id && !seen.has(p.id)) {
      seen.add(p.id);
      result.push(p);
    }
  }
  return result;
};

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
  const [catalogueMaterials, setCatalogueMaterials] = useState<CatalogueMaterial[]>([]);

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
        measurements: [createEmptyMeasurementRow('P1', 'P2')],
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
    return lineItems.every(
      (it) =>
        Boolean(it.activityId) &&
        it.measurements &&
        it.measurements.length > 0 &&
        it.measurements.every(
          (m) =>
            Boolean(String(m.startPoint || '').trim()) &&
            Boolean(String(m.endPoint || '').trim()) &&
            Number(m.distance) > 0
        ) &&
        Number(it.quantity) > 0
    );
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
      const [acts, wos, attList, entries, cats] = await Promise.all([
        getActivities().catch(() => [] as Activity[]),
        getWorkOrders().catch(() => [] as WorkOrder[]),
        getAttendanceRecords(today).catch(() => [] as AttendanceRecord[]),
        getDailyWorkEntries(today).catch(() => [] as DailyWorkEntry[]),
        getMaterialsCatalogue().catch(() => [] as CatalogueMaterial[]),
      ]);

      setActivities(acts);
      setWorkOrders(wos);
      setCatalogueMaterials(cats);

      let currentSession: AttendanceRecord | null = null;
      if (attList.length > 0) {
        const sorted = [...attList].sort(
          (a, b) => new Date(b.check_in_time).getTime() - new Date(a.check_in_time).getTime()
        );
        // Identify active attendance session (check_out_time === null); fallback to latest
        const active = sorted.find((a) => a.check_out_time === null);
        currentSession = active || sorted[0];
        setAttendance(currentSession);
      } else {
        setAttendance(null);
      }

      // Filter entries by matching attendance session ID
      const sessionEntries = currentSession
        ? entries.filter(
            (entry) =>
              entry.attendance_record_id === currentSession.id ||
              (!entry.attendance_record_id && attList.length <= 1)
          )
        : entries;

      // Check for existing work entries from server for this session
      if (sessionEntries.length > 0) {
        const mappedLines: ActivityLineItem[] = sessionEntries.map((entry) => {
          const matchedAct = acts.find((a) => a.id === entry.activity_id);
          const rawMeasurements = (entry as any).measurements;
          const measurements: MeasurementRow[] =
            Array.isArray(rawMeasurements) && rawMeasurements.length > 0
              ? rawMeasurements.map((m: any) => ({
                  tempId: generateClientUuid(),
                  startPoint: m.start_point || '',
                  endPoint: m.end_point || '',
                  distance: m.distance !== undefined && m.distance !== null ? m.distance : '',
                }))
              : [
                  createEmptyMeasurementRow(
                    'P1',
                    'P2',
                    Number(entry.quantity) > 0 ? Number(entry.quantity) : ''
                  ),
                ];

          const totalDistance = measurements.reduce(
            (acc, m) => acc + (Number(m.distance) || 0),
            0
          );
          const totalQty = totalDistance || Number(entry.quantity) || 0;
          const syncedMaterials = syncLineMaterialsWithMeasurement(
            entry.materials || [],
            entry.activity_id,
            totalQty,
            acts,
            cats,
            entry.id
          );

          return {
            id: entry.id,
            tempId: entry.id,
            idempotencyKey: entry.idempotency_key || entry.id,
            activityId: entry.activity_id,
            workOrderId: entry.work_order_id || '',
            measurements,
            quantity: totalQty,
            uom: entry.uom || (matchedAct ? matchedAct.unit_of_measure : ''),
            remarks: entry.remarks || '',
            status: entry.status,
            photos: dedupePhotos(entry.photos),
            materials: syncedMaterials,
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
            const latestServerTime = sessionEntries.reduce((maxT, e) => {
              const t = new Date(e.updated_at || e.created_at || 0).getTime();
              return t > maxT ? t : maxT;
            }, 0);

            if (sessionEntries.length === 0 || (parsed.savedAt && parsed.savedAt > latestServerTime)) {
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
            measurements: it.measurements.map((m) => ({
              startPoint: m.startPoint,
              endPoint: m.endPoint,
              distance: m.distance,
            })),
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
      const measurements: MeasurementRow[] =
        Array.isArray(item.measurements) && item.measurements.length > 0
          ? item.measurements.map((m) => ({
              tempId: generateClientUuid(),
              startPoint: m.startPoint || '',
              endPoint: m.endPoint || '',
              distance: m.distance !== undefined && m.distance !== null ? m.distance : '',
            }))
          : [
              createEmptyMeasurementRow(
                'P1',
                'P2',
                Number(item.quantity) > 0 ? Number(item.quantity) : ''
              ),
            ];

      const totalDistance = measurements.reduce(
        (acc, m) => acc + (Number(m.distance) || 0),
        0
      );

      return {
        id: item.id,
        tempId: item.id || item.idempotencyKey || generateClientUuid(),
        idempotencyKey: item.idempotencyKey || generateClientUuid(),
        activityId: item.activityId,
        workOrderId: item.workOrderId || '',
        measurements,
        quantity: totalDistance || Number(item.quantity) || 0,
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
        const currentTotal = (line.measurements || []).reduce((sum, r) => sum + (Number(r.distance) || 0), 0);
        line.materials = syncLineMaterialsWithMeasurement(
          line.materials || [],
          value,
          currentTotal,
          activities,
          catalogueMaterials,
          line.id || line.tempId
        );
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

  const addMeasurementRow = (lineIndex: number) => {
    setLineItems((prev) => {
      const next = [...prev];
      if (!next[lineIndex]) return prev;
      const line = { ...next[lineIndex] };
      const currentRows = [...line.measurements];
      const lastRow = currentRows[currentRows.length - 1];
      const nextStart = lastRow && lastRow.endPoint.trim() ? lastRow.endPoint.trim() : '';
      let nextEnd = '';
      if (nextStart.match(/^P(\d+)$/i)) {
        const num = parseInt(nextStart.slice(1), 10);
        nextEnd = `P${num + 1}`;
      }
      currentRows.push(createEmptyMeasurementRow(nextStart, nextEnd));
      line.measurements = currentRows;
      const newTotal = currentRows.reduce((sum, r) => sum + (Number(r.distance) || 0), 0);
      line.quantity = newTotal;
      line.materials = syncLineMaterialsWithMeasurement(
        line.materials || [],
        line.activityId,
        newTotal,
        activities,
        catalogueMaterials,
        line.id || line.tempId
      );
      line.saveError = null;
      next[lineIndex] = line;
      return next;
    });
  };

  const removeMeasurementRow = (lineIndex: number, rowIndex: number) => {
    setLineItems((prev) => {
      const next = [...prev];
      if (!next[lineIndex]) return prev;
      const line = { ...next[lineIndex] };
      if (line.measurements.length <= 1) return prev;
      const currentRows = line.measurements.filter((_, idx) => idx !== rowIndex);
      line.measurements = currentRows;
      const newTotal = currentRows.reduce((sum, r) => sum + (Number(r.distance) || 0), 0);
      line.quantity = newTotal;
      line.materials = syncLineMaterialsWithMeasurement(
        line.materials || [],
        line.activityId,
        newTotal,
        activities,
        catalogueMaterials,
        line.id || line.tempId
      );
      line.saveError = null;
      next[lineIndex] = line;
      return next;
    });
  };

  const updateMeasurementField = (
    lineIndex: number,
    rowIndex: number,
    field: 'startPoint' | 'endPoint' | 'distance',
    value: any
  ) => {
    setLineItems((prev) => {
      const next = [...prev];
      if (!next[lineIndex]) return prev;
      const line = { ...next[lineIndex] };
      const currentRows = [...line.measurements];
      currentRows[rowIndex] = { ...currentRows[rowIndex], [field]: value };
      line.measurements = currentRows;
      const newTotal = currentRows.reduce((sum, r) => sum + (Number(r.distance) || 0), 0);
      line.quantity = newTotal;
      line.materials = syncLineMaterialsWithMeasurement(
        line.materials || [],
        line.activityId,
        newTotal,
        activities,
        catalogueMaterials,
        line.id || line.tempId
      );
      line.saveError = null;
      next[lineIndex] = line;
      return next;
    });
  };

  // Save a single line item with point-to-point measurements and total quantity
  const saveSingleLineItem = async (index: number): Promise<{ id: string; status: string } | null> => {
    const line = lineItems[index];
    if (!line.activityId) {
      updateLineField(index, 'saveError', 'Please select an activity.');
      return null;
    }

    if (!line.measurements || line.measurements.length === 0) {
      updateLineField(index, 'saveError', 'At least one measurement row is required.');
      return null;
    }

    for (let r = 0; r < line.measurements.length; r++) {
      const row = line.measurements[r];
      const startP = String(row.startPoint || '').trim();
      const endP = String(row.endPoint || '').trim();
      const dist = Number(row.distance);

      if (!startP) {
        updateLineField(index, 'saveError', `Measurement row #${r + 1}: Start Point is required.`);
        return null;
      }
      if (!endP) {
        updateLineField(index, 'saveError', `Measurement row #${r + 1}: End Point is required.`);
        return null;
      }
      if (isNaN(dist) || dist <= 0) {
        updateLineField(index, 'saveError', `Measurement row #${r + 1}: Distance must be a positive number greater than 0.`);
        return null;
      }
    }

    const totalQty = line.measurements.reduce((acc, m) => acc + Number(m.distance), 0);
    if (totalQty <= 0) {
      updateLineField(index, 'saveError', 'Total distance must be greater than zero.');
      return null;
    }

    const payloadMeasurements = line.measurements.map((m) => ({
      start_point: m.startPoint.trim(),
      end_point: m.endPoint.trim(),
      distance: Number(m.distance),
    }));

    const matchedAct = activities.find((a) => a.id === line.activityId);
    const matchingTx = (line.materials || []).find((tx) =>
      isMatchingConsumedMaterial(tx, matchedAct, catalogueMaterials)
    );
    const mappedMaterialId = matchingTx ? (matchingTx.material_id || undefined) : undefined;
    const mappedMaterialQuantity = matchingTx ? totalQty : undefined;

    try {
      let savedId = line.id;
      let savedStatus = line.status;

      if (line.id) {
        const updated = await updateDailyWorkEntry(line.id, {
          activity_id: line.activityId,
          work_order_id: line.workOrderId || null,
          quantity: totalQty,
          measurements: payloadMeasurements,
          material_id: mappedMaterialId,
          material_quantity: mappedMaterialQuantity,
          remarks: line.remarks.trim() || null,
        });

        savedId = updated.id;
        savedStatus = updated.status;

        setLineItems((prev) => {
          const next = [...prev];
          if (!next[index]) return prev;
          const currentPhotos = next[index].photos || [];
          const incomingPhotos = updated.photos && updated.photos.length > 0 ? updated.photos : currentPhotos;
          next[index] = {
            ...next[index],
            status: updated.status,
            quantity: Number(updated.quantity) || totalQty,
            photos: dedupePhotos([...incomingPhotos, ...currentPhotos]),
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
          quantity: totalQty,
          measurements: payloadMeasurements,
          material_id: mappedMaterialId,
          material_quantity: mappedMaterialQuantity,
          work_date: today,
          remarks: line.remarks.trim() || null,
        });

        savedId = created.id;
        savedStatus = created.status;

        setLineItems((prev) => {
          const next = [...prev];
          if (!next[index]) return prev;
          const currentPhotos = next[index].photos || [];
          const incomingPhotos = created.photos && created.photos.length > 0 ? created.photos : currentPhotos;
          next[index] = {
            ...next[index],
            id: created.id,
            status: created.status,
            quantity: Number(created.quantity) || totalQty,
            photos: dedupePhotos([...incomingPhotos, ...currentPhotos]),
            materials: created.materials && created.materials.length > 0 ? created.materials : next[index].materials,
            saveError: null,
          };
          return next;
        });
      }
      return { id: savedId, status: savedStatus };
    } catch (err: any) {
      const norm = normalizeError(err as AxiosError<any>);
      const msg = norm.message || 'Failed to save activity line.';
      updateLineField(index, 'saveError', msg);
      return null;
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

    const hasInvalidMeasurement = lineItems.some((line) => {
      if (!line.measurements || line.measurements.length === 0) return true;
      return line.measurements.some(
        (m) =>
          !String(m.startPoint || '').trim() ||
          !String(m.endPoint || '').trim() ||
          Number(m.distance) <= 0 ||
          isNaN(Number(m.distance))
      );
    });
    if (hasInvalidMeasurement) {
      setErrorMsg('Cannot submit: All measurement rows must have valid start points, end points, and positive distances.');
      return;
    }

    const hasZeroQuantity = lineItems.some((it) => (Number(it.quantity) || 0) <= 0);
    if (hasZeroQuantity) {
      setErrorMsg('Cannot submit: All activity lines must have a total distance greater than zero.');
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
      const savedLines: { id: string; status: string }[] = [];
      let saveFailed = false;
      for (let i = 0; i < lineItems.length; i++) {
        const saved = await saveSingleLineItem(i);
        if (!saved) {
          saveFailed = true;
        } else {
          savedLines.push(saved);
        }
      }

      if (saveFailed) {
        setErrorMsg('Failed to save all activity lines before submission. Please review errors.');
        setShowSubmitModal(false);
        setSubmitting(false);
        return;
      }

      // Step 2: Submit all line items
      for (let i = 0; i < savedLines.length; i++) {
        const item = savedLines[i];
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
            const rawUom = line.uom || (matchedAct ? matchedAct.unit_of_measure : 'metres');
            const unitDisplay = getActivityUnitDisplay(rawUom);
            const isDistance = isDistanceUom(unitDisplay);

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

                {/* Point-to-Point Measurement Table */}
                <div className={styles.measurementsSection}>
                  <div className={styles.measurementsHeader}>
                    <h4 className={styles.measurementsTitle}>Work Measurements (Point-to-Point)</h4>
                    <span className={styles.measurementsSubtitle} data-testid={`measurements-help-${index}`}>
                      Record start/end points and {isDistance ? 'distance' : 'quantity'} in {unitDisplay}. The total {isDistance ? 'distance' : 'quantity'} automatically derives the activity quantity.
                    </span>
                  </div>

                  <div className={styles.tableResponsive}>
                    <table className={styles.measurementsTable}>
                      <thead>
                        <tr>
                          <th style={{ width: '40px' }}>#</th>
                          <th style={{ minWidth: '130px' }}>Start Point *</th>
                          <th style={{ minWidth: '130px' }}>End Point *</th>
                          <th style={{ minWidth: '130px', textAlign: 'right' }} data-testid={`measurement-header-unit-${index}`}>
                            {isDistance ? `Distance (${unitDisplay})` : `Quantity (${unitDisplay})`} *
                          </th>
                          {!isReadOnly && !lineReadOnly && <th style={{ width: '50px' }}></th>}
                        </tr>
                      </thead>
                      <tbody>
                        {line.measurements.map((row, rIdx) => (
                          <tr key={rIdx}>
                            <td>{rIdx + 1}</td>
                            <td>
                              <input
                                type="text"
                                className={styles.pointInput}
                                placeholder="e.g. P1"
                                aria-label={`Start Point #${rIdx + 1} for Activity #${index + 1}`}
                                value={row.startPoint}
                                onChange={(e) => updateMeasurementField(index, rIdx, 'startPoint', e.target.value)}
                                disabled={isReadOnly || lineReadOnly}
                                data-testid={`measurement-start-${index}-${rIdx}`}
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                className={styles.pointInput}
                                placeholder="e.g. P2"
                                aria-label={`End Point #${rIdx + 1} for Activity #${index + 1}`}
                                value={row.endPoint}
                                onChange={(e) => updateMeasurementField(index, rIdx, 'endPoint', e.target.value)}
                                disabled={isReadOnly || lineReadOnly}
                                data-testid={`measurement-end-${index}-${rIdx}`}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                min="0"
                                step="any"
                                className={styles.distanceInput}
                                placeholder="0.0"
                                aria-label={`${isDistance ? 'Distance' : 'Quantity'} #${rIdx + 1} for Activity #${index + 1}`}
                                value={row.distance}
                                onChange={(e) => updateMeasurementField(index, rIdx, 'distance', e.target.value)}
                                disabled={isReadOnly || lineReadOnly}
                                data-testid={`measurement-dist-${index}-${rIdx}`}
                              />
                            </td>
                            {!isReadOnly && !lineReadOnly && (
                              <td style={{ textAlign: 'center' }}>
                                {line.measurements.length > 1 && (
                                  <button
                                    type="button"
                                    className={styles.removeRowBtn}
                                    onClick={() => removeMeasurementRow(index, rIdx)}
                                    title="Remove measurement row"
                                    aria-label={`Remove measurement row #${rIdx + 1}`}
                                    data-testid={`measurement-remove-${index}-${rIdx}`}
                                  >
                                    <Trash2 size={15} />
                                  </button>
                                )}
                              </td>
                            )}
                          </tr>
                        ))}
                        <tr className={styles.totalRow}>
                          <td colSpan={3} className={styles.totalLabel}>
                            <strong data-testid={`measurement-total-label-${index}`}>
                              {isDistance ? 'Total Distance' : 'Total Quantity'}
                            </strong>
                          </td>
                          <td style={{ textAlign: 'right' }} className={styles.totalValue}>
                            <strong data-testid={`measurement-total-${index}`}>
                              {formatTotalDistance(line.quantity)} {unitDisplay}
                            </strong>
                            <span
                              className={styles.uomBadge}
                              style={{ marginLeft: 6, display: 'inline-block' }}
                              data-testid={`activity-uom-badge-${index}`}
                            >
                              {unitDisplay}
                            </span>
                          </td>
                          {!isReadOnly && !lineReadOnly && <td></td>}
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {!isReadOnly && !lineReadOnly && (
                    <div className={styles.addRowContainer}>
                      <button
                        type="button"
                        className={styles.addRowBtn}
                        onClick={() => addMeasurementRow(index)}
                        data-testid={`measurement-add-row-${index}`}
                      >
                        <Plus size={14} />
                        Add Measurement Row
                      </button>
                    </div>
                  )}
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
                    data-testid={`attachments-toggle-${index}`}
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
                                if (!next[index]) return prev;
                                const currentPhotos = next[index].photos || [];
                                const merged = dedupePhotos([...loadedPhotos, ...currentPhotos]);
                                const currentIds = currentPhotos.map((p) => p.id).join(',');
                                const nextIds = merged.map((p) => p.id).join(',');
                                if (currentIds === nextIds) {
                                  return prev;
                                }
                                next[index] = {
                                  ...next[index],
                                  photos: merged,
                                };
                                return next;
                              });
                            }}
                            onPhotoUploaded={(photo) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                if (!next[index]) return prev;
                                const currentPhotos = next[index].photos || [];
                                if (currentPhotos.some((p) => p.id === photo.id)) {
                                  return prev;
                                }
                                next[index] = {
                                  ...next[index],
                                  photos: dedupePhotos([photo, ...currentPhotos]),
                                };
                                return next;
                              });
                            }}
                            onPhotoDeleted={(photoId) => {
                              setLineItems((prev) => {
                                const next = [...prev];
                                if (!next[index]) return prev;
                                next[index] = {
                                  ...next[index],
                                  photos: (next[index].photos || []).filter((p) => p.id !== photoId),
                                };
                                return next;
                              });
                            }}
                          />

                          <MaterialTransactionEntry
                            dailyWorkEntryId={line.id}
                            status={line.status || 'draft'}
                            siteId={attendance?.site_id || auth?.user?.active_sites?.[0]?.id}
                            activity={matchedAct}
                            measurementTotal={Number(line.quantity) || 0}
                            catalogueMaterialsList={catalogueMaterials}
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
                                if (!next[index]) return prev;
                                const existing = next[index].materials || [];
                                const updated = existing.some((m) => m.id === tx.id)
                                  ? existing.map((m) => (m.id === tx.id ? tx : m))
                                  : [tx, ...existing];
                                next[index] = {
                                  ...next[index],
                                  materials: updated,
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
                    <th>Measurements</th>
                    <th>Total Qty</th>
                    <th>Attachments</th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((line, idx) => {
                    const act = activities.find((a) => a.id === line.activityId);
                    const actUom = getActivityUnitDisplay(line.uom || act?.unit_of_measure);
                    const measurementSpans = line.measurements
                      .filter((m) => m.startPoint && m.endPoint)
                      .map((m) => `${m.startPoint}->${m.endPoint} (${m.distance || 0} ${actUom})`)
                      .join(', ');
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
                        <td style={{ fontSize: '0.8rem', color: '#475569' }}>
                          {measurementSpans || '—'}
                        </td>
                        <td>
                          {line.quantity} {actUom}
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

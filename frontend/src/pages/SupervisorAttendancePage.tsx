import React, { useEffect, useState, useMemo } from 'react';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { getAttendanceRecords, overrideAttendance, type AttendanceRecord } from '../api/attendance';
import { formatWorkingHours } from '../utils/workingHours';
import { normalizeError } from '../api/client';
import {
  Users,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Calendar,
  RefreshCw,
  X,
  ShieldCheck,
  Loader2,
  MapPin,
  ExternalLink,
  Navigation,
} from 'lucide-react';
import styles from './SupervisorAttendancePage.module.css';
import { AxiosError } from 'axios';

const formatCoordinates = (lat?: number | null, lng?: number | null): string => {
  if (lat == null || lng == null) return '—';
  const latDir = lat >= 0 ? 'N' : 'S';
  const lngDir = lng >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(6)}° ${latDir}, ${Math.abs(lng).toFixed(6)}° ${lngDir}`;
};

const formatDistanceM = (metres?: number | null): string => {
  if (metres == null) return '—';
  if (metres >= 1000) {
    return `${(metres / 1000).toFixed(2)} km (${Math.round(metres).toLocaleString()} m)`;
  }
  return `${Math.round(metres).toLocaleString()} m`;
};

export const SupervisorAttendancePage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [filterMode, setFilterMode] = useState<'all' | 'flagged'>('all');
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal State
  const [modalRecord, setModalRecord] = useState<AttendanceRecord | null>(null);
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [submittingOverride, setSubmittingOverride] = useState<boolean>(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  const fetchRecords = async () => {
    setLoading(true);
    setError(null);
    try {
      // Backend list_attendance returns team records for supervisor
      const data = await getAttendanceRecords(selectedDate);
      setRecords(data);
    } catch (err) {
      const normalized = normalizeError(err as AxiosError<any>);
      setError(`Failed to load team attendance records: ${normalized.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [selectedDate]);

  // Filter records by selected date (if records span multiple dates) and status
  const displayedRecords = useMemo(() => {
    return records.filter((rec) => {
      // Date matching (string prefix or exact match)
      const matchesDate = !selectedDate || rec.date === selectedDate || rec.date.startsWith(selectedDate);
      if (!matchesDate) return false;
      if (filterMode === 'flagged') {
        return rec.status === 'flagged';
      }
      return true;
    });
  }, [records, selectedDate, filterMode]);

  const flaggedCount = useMemo(() => {
    return records.filter((r) => {
      const matchesDate = !selectedDate || r.date === selectedDate || r.date.startsWith(selectedDate);
      return matchesDate && r.status === 'flagged';
    }).length;
  }, [records, selectedDate]);

  const totalDateCount = useMemo(() => {
    return records.filter((r) => {
      return !selectedDate || r.date === selectedDate || r.date.startsWith(selectedDate);
    }).length;
  }, [records, selectedDate]);

  const handleOpenOverride = (record: AttendanceRecord) => {
    setModalRecord(record);
    setOverrideReason('');
    setOverrideError(null);
  };

  const handleCloseModal = () => {
    if (submittingOverride) return;
    setModalRecord(null);
    setOverrideReason('');
    setOverrideError(null);
  };

  const handleSubmitOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalRecord) return;

    const trimmedReason = overrideReason.trim();
    if (trimmedReason.length <= 10) {
      setOverrideError('Override reason must be more than 10 characters.');
      return;
    }

    setSubmittingOverride(true);
    setOverrideError(null);

    try {
      await overrideAttendance(modalRecord.id, { override_reason: trimmedReason });
      const empDisplay = modalRecord.employee_name || modalRecord.employee_id;
      setSuccessMsg(`Successfully overridden attendance record for ${empDisplay}`);
      setModalRecord(null);
      await fetchRecords();
    } catch (err) {
      const normalized = normalizeError(err as AxiosError<any>);
      setOverrideError(normalized.message || 'Failed to submit override.');
    } finally {
      setSubmittingOverride(false);
    }
  };

  const isReasonValid = overrideReason.trim().length > 10;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div className={styles.headerTitles}>
          <h1>Team Attendance Review</h1>
          <p>Inspect team attendance check-ins and approve out-of-geofence exceptions</p>
        </div>
      </div>

      {/* Success Banner */}
      {successMsg && (
        <div className={styles.alertSuccess} role="alert">
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSuccessMsg(null)}
            style={{ marginLeft: 'auto', padding: '0 4px' }}
          >
            <X size={16} />
          </Button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className={styles.alertError} role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={fetchRecords} style={{ marginLeft: 'auto' }}>
            Retry
          </Button>
        </div>
      )}

      {/* Controls Bar */}
      <div className={styles.controlsBar}>
        <div className={styles.datePickerGroup}>
          <Calendar size={18} color="var(--color-neutral-700)" />
          <label htmlFor="attendance-date">Review Date:</label>
          <input
            id="attendance-date"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className={styles.dateInput}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
          >
            Today
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedDate('')}
          >
            All Dates
          </Button>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchRecords}
          isLoading={loading}
          title="Refresh attendance records"
        >
          <RefreshCw size={14} /> Refresh
        </Button>

        {/* Filter Pills */}
        <div className={styles.filterGroup}>
          <button
            type="button"
            className={`${styles.filterBtn} ${filterMode === 'all' ? styles.active : ''}`}
            onClick={() => setFilterMode('all')}
          >
            All ({totalDateCount})
          </button>
          <button
            type="button"
            className={`${styles.filterBtn} ${styles.hasFlagged} ${
              filterMode === 'flagged' ? styles.active : ''
            }`}
            onClick={() => setFilterMode('flagged')}
          >
            Flagged Only ({flaggedCount})
          </button>
        </div>
      </div>

      {/* Attendance Table */}
      {loading ? (
        <div className={styles.loadingContainer}>
          <Loader2 className={styles.spinIcon} size={32} />
          <p>Loading team attendance records...</p>
        </div>
      ) : displayedRecords.length === 0 ? (
        <div className={styles.emptyState}>
          <Users size={48} className={styles.emptyIcon} />
          <h3>No attendance records found</h3>
          <p>
            {filterMode === 'flagged'
              ? 'There are no flagged out-of-geofence records for this date.'
              : `No team members have recorded attendance for ${selectedDate || 'the selected filter'}.`}
          </p>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.recordsTable}>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Date</th>
                <th>Check-In</th>
                <th>Check-Out</th>
                <th>Working Hours</th>
                <th>Geofence</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedRecords.map((rec) => {
                const isFlagged = rec.status === 'flagged';
                const checkInDate = rec.check_in_time ? new Date(rec.check_in_time) : null;
                const checkOutDate = rec.check_out_time ? new Date(rec.check_out_time) : null;

                return (
                  <tr key={rec.id} className={isFlagged ? styles.flaggedRow : undefined}>
                    <td>
                      <span className={rec.employee_name ? undefined : styles.empIdCode} title={rec.employee_id}>
                        {rec.employee_name || rec.employee_id}
                      </span>
                    </td>
                    <td>{rec.date}</td>
                    <td>
                      {checkInDate ? checkInDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                    <td>
                      {checkOutDate ? (
                        checkOutDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      ) : (
                        <span style={{ color: 'var(--color-neutral-500)' }}>Active</span>
                      )}
                    </td>
                    <td>{formatWorkingHours(rec.working_hours)}</td>
                    <td>
                      {rec.is_within_geofence === true ? (
                        <div className={styles.geofenceCell}>
                          <span className={styles.geofenceValid}>
                            <CheckCircle2 size={12} /> Within
                          </span>
                          {rec.check_in_distance_m != null && (
                            <span className={styles.geofenceDistValid}>
                              {Math.round(rec.check_in_distance_m)}m from site
                            </span>
                          )}
                        </div>
                      ) : rec.is_within_geofence === false ? (
                        <div className={styles.geofenceCell}>
                          <span className={styles.geofenceInvalid}>
                            <AlertTriangle size={12} /> Outside
                          </span>
                          {rec.check_in_distance_m != null && (
                            <span className={styles.geofenceDistFlagged}>
                              {formatDistanceM(rec.check_in_distance_m)} from site
                            </span>
                          )}
                          {rec.check_in_latitude != null && rec.check_in_longitude != null ? (
                            <span
                              className={styles.geofenceCoords}
                              title={`${rec.check_in_latitude}, ${rec.check_in_longitude}`}
                            >
                              {rec.check_in_latitude.toFixed(4)}°, {rec.check_in_longitude.toFixed(4)}°
                            </span>
                          ) : (
                            <span className={styles.geofenceCoordsFallback}>No GPS coords</span>
                          )}
                        </div>
                      ) : (
                        <span className={styles.geofenceUnknown}>—</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={rec.status} />
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {isFlagged ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenOverride(rec)}
                          style={{ borderColor: '#d97706', color: '#b45309' }}
                        >
                          <ShieldCheck size={14} style={{ marginRight: 4 }} />
                          Override
                        </Button>
                      ) : (
                        <span style={{ color: 'var(--color-neutral-500)', fontSize: 'var(--font-size-xs)' }}>
                          {rec.status === 'approved' ? 'Overridden' : '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Override Modal */}
      {modalRecord && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="override-modal-title">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h2 id="override-modal-title">Authorize Geofence Override</h2>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={handleCloseModal}
                disabled={submittingOverride}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmitOverride}>
              <div className={styles.modalBody}>
                {/* Record Context Card */}
                <div className={styles.recordSummary}>
                  <div className={styles.recordSummaryRow}>
                    <span className={styles.recordSummaryLabel}>Employee:</span>
                    <span className={styles.recordSummaryValue}>
                      {modalRecord.employee_name || modalRecord.employee_id}
                    </span>
                  </div>
                  {modalRecord.site_name && (
                    <div className={styles.recordSummaryRow}>
                      <span className={styles.recordSummaryLabel}>Site:</span>
                      <span className={styles.recordSummaryValue}>{modalRecord.site_name}</span>
                    </div>
                  )}
                  <div className={styles.recordSummaryRow}>
                    <span className={styles.recordSummaryLabel}>Date & Time:</span>
                    <span className={styles.recordSummaryValue}>
                      {modalRecord.date} {modalRecord.check_in_time ? new Date(modalRecord.check_in_time).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <div className={styles.recordSummaryRow}>
                    <span className={styles.recordSummaryLabel}>Current Status:</span>
                    <span className={styles.recordSummaryValue}>Flagged (Outside Geofence)</span>
                  </div>
                </div>

                {/* GPS Location & Distance Inspection */}
                <div className={styles.locationComparison}>
                  <div className={styles.locationGrid}>
                    {/* Reported Check-In Location */}
                    <div className={`${styles.locationCard} ${styles.locationCardFlagged}`}>
                      <div className={styles.locationCardHeader}>
                        <Navigation size={14} className={styles.iconFlagged} />
                        <span className={styles.headerTextFlagged}>Reported Check-In Location</span>
                      </div>

                      {modalRecord.check_in_latitude != null && modalRecord.check_in_longitude != null ? (
                        <>
                          <div className={styles.coordBox}>
                            <span className={styles.coordLabel}>Actual Coordinates:</span>
                            <span className={styles.coordValue}>
                              {formatCoordinates(modalRecord.check_in_latitude, modalRecord.check_in_longitude)}
                            </span>
                            <span className={styles.rawCoordValue}>
                              ({modalRecord.check_in_latitude.toFixed(6)}, {modalRecord.check_in_longitude.toFixed(6)})
                            </span>
                          </div>

                          {modalRecord.check_in_distance_m != null && (
                            <div className={styles.distanceBadge}>
                              <div>
                                <strong>Distance:</strong> {formatDistanceM(modalRecord.check_in_distance_m)} from site
                              </div>
                              {modalRecord.site_permitted_radius_m != null &&
                                modalRecord.check_in_distance_m > modalRecord.site_permitted_radius_m && (
                                  <span className={styles.distanceExcess}>
                                    {Math.round(modalRecord.check_in_distance_m - modalRecord.site_permitted_radius_m).toLocaleString()}m outside permitted {modalRecord.site_permitted_radius_m}m radius
                                  </span>
                                )}
                            </div>
                          )}

                          <a
                            href={`https://www.openstreetmap.org/?mlat=${modalRecord.check_in_latitude}&mlon=${modalRecord.check_in_longitude}#map=17/${modalRecord.check_in_latitude}/${modalRecord.check_in_longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.osmLink}
                            title="View reported check-in location on OpenStreetMap"
                          >
                            <MapPin size={14} />
                            <span>View on OpenStreetMap</span>
                            <ExternalLink size={12} />
                          </a>
                        </>
                      ) : (
                        <div className={styles.missingGpsNotice}>
                          <AlertCircle size={14} />
                          <span>Actual check-in coordinates are unavailable for this record.</span>
                        </div>
                      )}
                    </div>

                    {/* Registered Site Location */}
                    <div className={`${styles.locationCard} ${styles.locationCardSite}`}>
                      <div className={styles.locationCardHeader}>
                        <MapPin size={14} className={styles.iconSite} />
                        <span className={styles.headerTextSite}>Registered Site Location</span>
                      </div>

                      {modalRecord.site_latitude != null && modalRecord.site_longitude != null ? (
                        <>
                          <div className={styles.coordBox}>
                            <span className={styles.coordLabel}>Site Coordinates:</span>
                            <span className={styles.coordValue}>
                              {formatCoordinates(modalRecord.site_latitude, modalRecord.site_longitude)}
                            </span>
                          </div>

                          <div className={styles.radiusBadge}>
                            <strong>Permitted Radius:</strong> {modalRecord.site_permitted_radius_m != null ? `${modalRecord.site_permitted_radius_m} m` : '100 m'}
                          </div>

                          <a
                            href={`https://www.openstreetmap.org/?mlat=${modalRecord.site_latitude}&mlon=${modalRecord.site_longitude}#map=17/${modalRecord.site_latitude}/${modalRecord.site_longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.osmLinkSite}
                            title="View registered site location on OpenStreetMap"
                          >
                            <MapPin size={14} />
                            <span>View Site on OpenStreetMap</span>
                            <ExternalLink size={12} />
                          </a>
                        </>
                      ) : (
                        <div className={styles.missingGpsNotice}>
                          <AlertCircle size={14} />
                          <span>Site coordinates are not configured for this location.</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className={styles.warningBox}>
                  <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <strong>Geofence Exception Detected:</strong> This employee checked in outside the site's permitted
                    radius. An override requires supervisor justification and will be permanently recorded in the audit log.
                  </div>
                </div>

                {overrideError && (
                  <div className={styles.alertError} role="alert">
                    <AlertCircle size={16} />
                    <span>{overrideError}</span>
                  </div>
                )}

                <div className={styles.formGroup}>
                  <label htmlFor="override-reason-input" className={styles.formLabel}>
                    Mandatory Reason for Override <span>*</span>
                  </label>
                  <textarea
                    id="override-reason-input"
                    className={styles.textarea}
                    rows={4}
                    placeholder="Provide a specific explanation (>10 characters, e.g. Temporary GPS drift at site perimeter, authorized adjacent sub-station work)..."
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    disabled={submittingOverride}
                    required
                  />
                  <div className={styles.charCount}>
                    <span className={!isReasonValid && overrideReason.length > 0 ? styles.charCountInvalid : undefined}>
                      {overrideReason.trim().length} / 11 characters minimum
                    </span>
                    {!isReasonValid && overrideReason.length > 0 && (
                      <span className={styles.charCountInvalid}>
                        Need {Math.max(0, 11 - overrideReason.trim().length)} more characters
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className={styles.modalFooter}>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleCloseModal}
                  disabled={submittingOverride}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={submittingOverride}
                  disabled={submittingOverride || !isReasonValid}
                >
                  Submit Override
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

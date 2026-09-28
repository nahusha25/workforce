import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useGeolocation } from '../hooks/useGeolocation';
import { getAttendanceRecords, checkIn, checkOut, type AttendanceRecord } from '../api/attendance';
import { normalizeError } from '../api/client';
import { MapPin, LogIn, LogOut, Loader2, AlertCircle, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import styles from './AttendancePage.module.css';
import { AxiosError } from 'axios';

export const AttendancePage: React.FC = () => {
  const { location, error: geoError, loading: geoLoading, getLocation } = useGeolocation();
  
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loadingData, setLoadingData] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [checkoutWarning, setCheckoutWarning] = useState<string | null>(null);
  const [showWarningModal, setShowWarningModal] = useState<boolean>(false);

  const fetchRecords = async () => {
    setLoadingData(true);
    setActionError(null);
    try {
      // Get today's date in YYYY-MM-DD
      const today = new Date().toISOString().split('T')[0];
      const data = await getAttendanceRecords(today);
      setRecords(data);
    } catch (err) {
      const normalized = normalizeError(err as AxiosError<any>);
      setActionError(`Failed to load attendance records: ${normalized.message}`);
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    fetchRecords();
    getLocation(); // Request initial GPS lock immediately
  }, [getLocation]);

  const sortedRecords = [...records].sort(
    (a, b) => new Date(b.check_in_time).getTime() - new Date(a.check_in_time).getTime()
  );
  
  const latestRecord = sortedRecords.length > 0 ? sortedRecords[0] : null;
  const isCheckedIn = latestRecord ? latestRecord.check_out_time === null : false;

  const handleAction = async (type: 'check-in' | 'check-out') => {
    if (submitting) return;

    // We must have a location
    if (!location) {
      if (geoError) {
        setActionError(`Cannot proceed: ${geoError}. Please enable GPS and try again.`);
      } else {
        setActionError('Acquiring GPS location... Please wait and try again.');
        getLocation();
      }
      return;
    }

    setSubmitting(true);
    setActionError(null);
    setSuccessMsg(null);

    try {
      if (type === 'check-in') {
        await checkIn({ latitude: location.latitude, longitude: location.longitude });
        setSuccessMsg('Successfully checked in!');
        await fetchRecords();
      } else {
        const res = await checkOut({ latitude: location.latitude, longitude: location.longitude });
        if (res.requires_confirmation) {
          setCheckoutWarning(
            res.warning || 'No daily work entries submitted for this session. Please confirm check-out.'
          );
          setShowWarningModal(true);
        } else {
          setSuccessMsg('Successfully checked out!');
          await fetchRecords();
        }
      }
    } catch (err) {
      const normalized = normalizeError(err as AxiosError<any>);
      setActionError(normalized.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDismissWarning = async () => {
    setShowWarningModal(false);
    setSuccessMsg('Successfully checked out!');
    await fetchRecords();
  };

  return (
    <div className={styles.container}>
      <Card title="Daily Attendance" subtitle="Check in and out of your assigned site">
        
        {/* GPS Status Indicator */}
        <div className={styles.gpsStatus}>
          {geoLoading ? (
            <div className={styles.gpsLoading}>
              <Loader2 className={styles.spinIcon} size={16} /> Acquiring GPS signal...
            </div>
          ) : geoError ? (
            <div className={styles.gpsError}>
              <AlertCircle size={16} /> {geoError}
              <Button variant="ghost" size="sm" onClick={getLocation} className={styles.retryBtn}>Retry</Button>
            </div>
          ) : location ? (
            <div className={styles.gpsSuccess}>
              <MapPin size={16} /> GPS Ready
            </div>
          ) : (
            <div className={styles.gpsWarning}>
              <AlertCircle size={16} /> Waiting for location permission...
            </div>
          )}
        </div>

        {/* Loading / Content */}
        {loadingData ? (
          <div className={styles.loadingContainer}>
            <Loader2 className={styles.spinIcon} size={32} />
            <p>Loading attendance status...</p>
          </div>
        ) : (
          <div className={styles.actionsContainer}>
            <div className={styles.statusPanel}>
              <h3>Current Status: <span className={isCheckedIn ? styles.statusIn : styles.statusOut}>{isCheckedIn ? 'Checked In' : 'Checked Out'}</span></h3>
              {latestRecord && isCheckedIn && (
                <p className={styles.timeLabel}>Since: {new Date(latestRecord.check_in_time).toLocaleTimeString()}</p>
              )}
            </div>

            {/* Error / Success Messages */}
            {actionError && (
              <div className={styles.alertError}>
                <AlertCircle size={18} /> {actionError}
              </div>
            )}
            {successMsg && (
              <div className={styles.alertSuccess}>
                <CheckCircle2 size={18} /> {successMsg}
              </div>
            )}

            {/* Action Buttons */}
            <div className={styles.buttonsGroup}>
              {!isCheckedIn ? (
                <Button 
                  variant="primary" 
                  size="lg" 
                  fullWidth 
                  onClick={() => handleAction('check-in')}
                  isLoading={submitting || geoLoading}
                  disabled={submitting || !!geoError || !location}
                  className={styles.checkInBtn}
                >
                  <LogIn className={styles.btnIcon} /> CHECK IN
                </Button>
              ) : (
                <Button 
                  variant="danger" 
                  size="lg" 
                  fullWidth 
                  onClick={() => handleAction('check-out')}
                  isLoading={submitting || geoLoading}
                  disabled={submitting || !!geoError || !location}
                  className={styles.checkOutBtn}
                >
                  <LogOut className={styles.btnIcon} /> CHECK OUT
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Pre-checkout Daily Work Warning Modal (BE-022 / FE-014) */}
      {showWarningModal && (
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="checkout-warning-modal-title"
          data-testid="checkout-warning-modal"
        >
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h2 id="checkout-warning-modal-title">Check-Out Warning</h2>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={handleDismissWarning}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <div className={styles.modalBody}>
              <div className={styles.warningBox}>
                <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <strong>Work Submission Alert:</strong>
                  <p style={{ margin: '4px 0 0 0' }}>{checkoutWarning}</p>
                </div>
              </div>

              <p className={styles.modalDescription}>
                You are checking out without submitting completed daily work for this attendance session. You can complete your daily work entry now, or proceed with checkout.
              </p>
            </div>

            <div className={styles.modalFooter}>
              <Link to="/daily-work">
                <Button type="button" variant="primary">
                  Complete Daily Work
                </Button>
              </Link>
              <Button
                type="button"
                variant="ghost"
                onClick={handleDismissWarning}
              >
                Check out anyway
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

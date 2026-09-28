import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ErrorMessage } from '../components/ui/ErrorMessage';
import { Input } from '../components/ui/Input';
import { useAuth } from '../context/AuthContext';
import { useCountdown } from '../hooks/useCountdown';
import styles from './LoginPage.module.css';

export const LoginPage: React.FC = () => {
  const { role, requestOtp, verifyOtp, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [mobile, setMobile] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'mobile' | 'otp'>('mobile');
  const [submitting, setSubmitting] = useState(false);
  const [mobileValidationError, setMobileValidationError] = useState<string | null>(null);
  const [otpValidationError, setOtpValidationError] = useState<string | null>(null);

  const { isExpired, formattedTime, startTimer, resetTimer } = useCountdown(300);

  // Redirect authenticated user based on verified backend system role
  useEffect(() => {
    if (isAuthenticated && role) {
      if (role === 'administrator') {
        navigate('/onboarding', { replace: true });
      } else {
        navigate('/profile', { replace: true });
      }
    }
  }, [isAuthenticated, role, navigate]);

  const formatMobileForApi = (val: string): string => {
    let clean = val.trim();
    if (clean.length === 10 && /^\d{10}$/.test(clean)) {
      return `+91${clean}`;
    }
    return clean;
  };

  const validateMobile = (val: string): boolean => {
    const cleanMobile = val.trim();
    if (!cleanMobile) {
      setMobileValidationError('Mobile number is required');
      return false;
    }
    const formatted = formatMobileForApi(val);
    if (!/^\+?[1-9]\d{7,14}$/.test(formatted)) {
      setMobileValidationError('Enter a valid 10-digit mobile number');
      return false;
    }
    setMobileValidationError(null);
    return true;
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!validateMobile(mobile)) return;

    setSubmitting(true);
    try {
      await requestOtp(formatMobileForApi(mobile));
      setStep('otp');
      startTimer(300);
    } catch {
      // Backend error populated in AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendOtp = async () => {
    clearError();
    setSubmitting(true);
    try {
      await requestOtp(formatMobileForApi(mobile));
      resetTimer();
    } catch {
      // Backend error populated in AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    const cleanOtp = otp.trim();
    if (cleanOtp.length !== 6 || !/^\d{6}$/.test(cleanOtp)) {
      setOtpValidationError('OTP must be a 6-digit number');
      return;
    }
    setOtpValidationError(null);

    setSubmitting(true);
    try {
      await verifyOtp(formatMobileForApi(mobile), cleanOtp);
      // Navigation handled by useEffect on role change
    } catch {
      // Backend error populated in AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const handleChangeMobile = () => {
    clearError();
    setStep('mobile');
    setOtp('');
    setOtpValidationError(null);
  };

  return (
    <div className={styles.pageWrapper}>
      <Card
        title="Workforce Management"
        subtitle="OTP Authentication System"
        className={styles.loginCard}
      >
        {error && <ErrorMessage title="Authentication Error" message={error} onRetry={clearError} />}

        {step === 'mobile' ? (
          <form onSubmit={handleSendOtp} className={styles.form} noValidate>
            <Input
              label="Mobile Number"
              placeholder="9876543210"
              value={mobile}
              onChange={(e) => {
                setMobile(e.target.value);
                if (mobileValidationError) setMobileValidationError(null);
              }}
              inputMode="tel"
              autoComplete="tel"
              error={mobileValidationError || undefined}
              helperText="Enter your registered mobile number for SMS OTP"
              required
            />
            <Button type="submit" fullWidth isLoading={submitting}>
              Send OTP
            </Button>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} className={styles.form} noValidate>
            <div className={styles.targetMobile}>
              <span>Sending OTP to: <strong>{formatMobileForApi(mobile)}</strong></span>
              <button type="button" onClick={handleChangeMobile} className={styles.editLink}>
                Edit
              </button>
            </div>

            <Input
              label="6-Digit OTP"
              placeholder="123456"
              value={otp}
              onChange={(e) => {
                setOtp(e.target.value);
                if (otpValidationError) setOtpValidationError(null);
              }}
              inputMode="numeric"
              maxLength={6}
              autoFocus
              error={otpValidationError || undefined}
              required
            />

            <div className={styles.timerSection}>
              <span>OTP Expiry:</span>
              <span className={`${styles.timerBadge} ${isExpired ? styles.timerExpired : ''}`}>
                {isExpired ? 'Expired' : formattedTime}
              </span>
            </div>

            <div className={styles.actionRow}>
              <Button type="submit" fullWidth isLoading={submitting}>
                Verify & Login
              </Button>
              <Button
                type="button"
                variant="outline"
                fullWidth
                disabled={!isExpired || submitting}
                onClick={handleResendOtp}
              >
                Resend OTP
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
};

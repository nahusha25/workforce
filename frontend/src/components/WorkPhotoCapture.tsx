import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { AxiosError } from 'axios';
import { Camera, Image as ImageIcon, Trash2, Loader2, AlertCircle, X, RefreshCw } from 'lucide-react';
import {
  getWorkPhotos,
  uploadWorkPhoto,
  deleteWorkPhoto,
  type WorkPhoto,
} from '../api/dailyWork';
import { normalizeError } from '../api/client';
import { compressImage } from '../utils/imageCompression';
import styles from './WorkPhotoCapture.module.css';

export interface WorkPhotoCaptureProps {
  dailyWorkEntryId: string | null;
  status: string; // 'draft' | 'correction_required' | 'submitted' | 'approved'
  initialPhotos?: WorkPhoto[];
  onPhotoUploaded?: (photo: WorkPhoto) => void;
  onPhotoDeleted?: (photoId: string) => void;
  onPhotosLoaded?: (photos: WorkPhoto[]) => void;
}

const deduplicatePhotos = (list: WorkPhoto[]): WorkPhoto[] => {
  return list.filter((p, idx, arr) => arr.findIndex((x) => x.id === p.id) === idx);
};

export const WorkPhotoCapture: React.FC<WorkPhotoCaptureProps> = ({
  dailyWorkEntryId,
  status,
  initialPhotos,
  onPhotoUploaded,
  onPhotoDeleted,
  onPhotosLoaded,
}) => {
  const [photos, setPhotos] = useState<WorkPhoto[]>(() =>
    initialPhotos ? deduplicatePhotos(initialPhotos) : []
  );
  const [loadingPhotos, setLoadingPhotos] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activePhotoType, setActivePhotoType] = useState<string | undefined>(undefined);

  // Camera states
  const [isCameraOpen, setIsCameraOpen] = useState<boolean>(false);
  const [cameraLoading, setCameraLoading] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fetchedEntryIdRef = useRef<string | null>(null);

  const isEditable =
    Boolean(dailyWorkEntryId) && (status === 'draft' || status === 'correction_required');

  const stopCameraTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const handleCloseCamera = useCallback(() => {
    stopCameraTracks();
    setIsCameraOpen(false);
    setCameraError(null);
    setCameraLoading(false);
  }, [stopCameraTracks]);

  // Clean up stream tracks on unmount
  useEffect(() => {
    return () => {
      stopCameraTracks();
    };
  }, [stopCameraTracks]);

  // Ensure video element receives stream whenever camera modal opens or stream changes
  useEffect(() => {
    if (isCameraOpen && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [isCameraOpen]);

  // Load photos whenever dailyWorkEntryId changes or initialPhotos updates
  useEffect(() => {
    if (!dailyWorkEntryId) {
      setPhotos([]);
      fetchedEntryIdRef.current = null;
      return;
    }

    // If initialPhotos is explicitly provided (including empty array []), sync it without re-fetching
    if (initialPhotos !== undefined) {
      setPhotos(deduplicatePhotos(initialPhotos));
      setLoadingPhotos(false);
      return;
    }

    // Only fetch if initialPhotos is undefined and we haven't fetched for this entry yet
    if (fetchedEntryIdRef.current === dailyWorkEntryId) {
      return;
    }

    let isMounted = true;
    fetchedEntryIdRef.current = dailyWorkEntryId;

    const fetchPhotos = async () => {
      setLoadingPhotos(true);
      setErrorMsg(null);
      try {
        const data = await getWorkPhotos(dailyWorkEntryId);
        if (isMounted) {
          const unique = deduplicatePhotos(data);
          setPhotos(unique);
          onPhotosLoaded?.(unique);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const norm = normalizeError(err as AxiosError<any>);
          setErrorMsg(norm.message);
        }
      } finally {
        if (isMounted) {
          setLoadingPhotos(false);
        }
      }
    };

    fetchPhotos();

    return () => {
      isMounted = false;
    };
  }, [dailyWorkEntryId, initialPhotos, onPhotosLoaded]);

  const processAndUploadFile = async (file: File, typeToUpload?: string) => {
    if (!dailyWorkEntryId) return;

    setUploading(true);
    setUploadProgress(10);
    setErrorMsg(null);

    const targetType = typeToUpload !== undefined ? typeToUpload : activePhotoType;

    try {
      // 1. Client-side Canvas Image Compression
      const compressed = await compressImage(file, {
        maxWidth: 1920,
        maxHeight: 1080,
        quality: 0.8,
      });
      setUploadProgress(30);

      // 2. Upload via API multipart endpoint
      const onProgress = (percent: number) => {
        setUploadProgress(30 + Math.round((percent * 70) / 100));
      };
      const newPhoto = targetType
        ? await uploadWorkPhoto(dailyWorkEntryId, compressed, targetType, onProgress)
        : await uploadWorkPhoto(dailyWorkEntryId, compressed, onProgress);

      setPhotos((prev) => {
        if (newPhoto.photo_type === 'start_point' || newPhoto.photo_type === 'end_point') {
          const withoutSameType = prev.filter((p) => p.photo_type !== newPhoto.photo_type);
          return [...withoutSameType, newPhoto];
        }
        return prev.some((p) => p.id === newPhoto.id) ? prev : [...prev, newPhoto];
      });
      onPhotoUploaded?.(newPhoto);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to upload photo');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      setActivePhotoType(undefined);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !dailyWorkEntryId) return;

    // Reset input value so selecting the same file triggers onChange again
    e.target.value = '';
    await processAndUploadFile(file, activePhotoType);
  };

  const triggerBrowse = (photoType?: string) => {
    setActivePhotoType(photoType);
    fileInputRef.current?.click();
  };

  const handleStartCamera = async (
    requestedFacingMode: 'environment' | 'user' = 'environment',
    photoType?: string
  ) => {
    setErrorMsg(null);
    setCameraError(null);
    setActivePhotoType(photoType);

    // Verify browser support for getUserMedia
    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraError(
        'Camera access is not supported by your browser or is blocked in insecure contexts (HTTPS required).'
      );
      setIsCameraOpen(true);
      return;
    }

    setIsCameraOpen(true);
    setCameraLoading(true);

    stopCameraTracks();

    try {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: requestedFacingMode },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
      } catch {
        // Fallback for desktop or cameras that reject facingMode constraints
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      streamRef.current = stream;
      setFacingMode(requestedFacingMode);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        try {
          await videoRef.current.play();
        } catch {
          // inline playback
        }
      }
    } catch (err: any) {
      stopCameraTracks();
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setCameraError(
          'Camera permission denied. Please allow camera access in your browser settings to take photos.'
        );
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setCameraError('No camera device found on this device.');
      } else if (name === 'NotReadableError' || name === 'TrackStartError') {
        setCameraError(
          'Camera is currently in use by another application or cannot be started.'
        );
      } else {
        setCameraError(err?.message || 'Unable to access camera.');
      }
    } finally {
      setCameraLoading(false);
    }
  };

  const handleSwitchCamera = () => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment';
    handleStartCamera(nextMode);
  };

  const handleCaptureFrame = () => {
    if (!videoRef.current || !streamRef.current || cameraLoading) return;

    const video = videoRef.current;
    const videoWidth = video.videoWidth || 1280;
    const videoHeight = video.videoHeight || 720;

    const canvas = document.createElement('canvas');
    canvas.width = videoWidth;
    canvas.height = videoHeight;
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      setCameraError('Failed to capture frame from video canvas.');
      return;
    }

    ctx.drawImage(video, 0, 0, videoWidth, videoHeight);

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setCameraError('Failed to generate image from camera capture.');
          return;
        }

        const capturedFile = new File(
          [blob],
          `site_photo_${Date.now()}.jpg`,
          { type: 'image/jpeg' }
        );

        handleCloseCamera();
        await processAndUploadFile(capturedFile, activePhotoType);
      },
      'image/jpeg',
      0.85
    );
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (!isEditable || deletingId) return;

    setDeletingId(photoId);
    setErrorMsg(null);

    try {
      await deleteWorkPhoto(photoId);
      setPhotos((prev) => prev.filter((p) => p.id !== photoId));
      onPhotoDeleted?.(photoId);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to delete photo');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className={styles.photoSection}>
      <div className={styles.headerRow}>
        <h4 className={styles.sectionTitle}>
          <Camera size={18} />
          Site Progress Photos
          <span className={styles.photoCountBadge}>{photos.length}</span>
        </h4>

        {isEditable && (
          <div className={styles.buttonsGroup}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              aria-label="Select photo from files"
              className={styles.hiddenInput}
              onChange={handleFileSelect}
              disabled={uploading}
            />

            <button
              type="button"
              className={styles.captureBtn}
              onClick={() => handleStartCamera('environment')}
              disabled={uploading}
              aria-label="Take Photo"
            >
              <Camera size={16} />
              Take Photo
            </button>

            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={() => triggerBrowse('general')}
              disabled={uploading}
              aria-label="Upload Photo"
            >
              <ImageIcon size={16} />
              Browse
            </button>
          </div>
        )}
      </div>

      {/* Camera Modal Viewfinder */}
      {isCameraOpen && (
        <div
          className={styles.cameraOverlay}
          role="dialog"
          aria-modal="true"
          aria-label="Camera viewfinder"
        >
          <div className={styles.cameraModal}>
            <div className={styles.cameraHeader}>
              <h5 className={styles.cameraTitle}>
                <Camera size={18} />
                Capture Site Photo
              </h5>
              <button
                type="button"
                className={styles.closeCameraBtn}
                onClick={handleCloseCamera}
                aria-label="Close camera"
              >
                <X size={20} />
              </button>
            </div>

            {cameraError ? (
              <div className={styles.cameraErrorContainer}>
                <AlertCircle size={32} />
                <p className={styles.cameraErrorText} role="alert">
                  {cameraError}
                </p>
                <div className={styles.cameraErrorActions}>
                  <button
                    type="button"
                    className={styles.retryCameraBtn}
                    onClick={() => handleStartCamera(facingMode)}
                  >
                    Try Again
                  </button>
                  <button
                    type="button"
                    className={styles.cameraActionBtn}
                    onClick={handleCloseCamera}
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className={styles.cameraViewfinder}>
                  <video
                    ref={videoRef}
                    playsInline
                    autoPlay
                    muted
                    className={styles.cameraVideo}
                    aria-label="Live camera preview"
                  />
                  {cameraLoading && (
                    <div className={styles.cameraLoadingOverlay}>
                      <Loader2 size={24} className="animate-spin" />
                      <span>Starting camera...</span>
                    </div>
                  )}
                </div>

                <div className={styles.cameraFooter}>
                  <button
                    type="button"
                    className={styles.cameraActionBtn}
                    onClick={handleSwitchCamera}
                    disabled={cameraLoading}
                    aria-label="Flip camera"
                    title="Switch camera"
                  >
                    <RefreshCw size={16} />
                    Switch
                  </button>

                  <button
                    type="button"
                    className={styles.shutterBtn}
                    onClick={handleCaptureFrame}
                    disabled={cameraLoading}
                    aria-label="Capture photo"
                    title="Capture photo"
                  >
                    <Camera size={26} />
                  </button>

                  <button
                    type="button"
                    className={styles.cameraActionBtn}
                    onClick={handleCloseCamera}
                    aria-label="Cancel camera"
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Uploading progress indicator */}
      {uploading && (
        <div className={styles.uploadingBanner} role="status">
          <Loader2 size={16} className="animate-spin" />
          <span>Compressing & uploading photo...</span>
          <div className={styles.progressBarContainer}>
            <div
              className={styles.progressBarFill}
              style={{ width: `${Math.max(uploadProgress, 15)}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Banner */}
      {errorMsg && (
        <div className={styles.errorBanner} role="alert">
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* When no entry draft exists yet */}
      {!dailyWorkEntryId && (
        <div className={styles.hintBanner}>
          Save a work entry draft before attaching site progress photos.
        </div>
      )}

      {/* Loading state for existing photos */}
      {loadingPhotos && (
        <div className={styles.hintBanner} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <Loader2 size={16} className="animate-spin" />
          Loading photos...
        </div>
      )}

      {/* Grid of uploaded photos */}
      {!loadingPhotos && photos.length > 0 && (
        <div className={styles.photoGrid}>
          {photos.map((photo) => (
            <div key={photo.id} className={styles.photoCard}>
              {photo.photo_type === 'start_point' && (
                <span className={`${styles.photoTypeBadge} ${styles.badgeStart}`}>Start Point</span>
              )}
              {photo.photo_type === 'end_point' && (
                <span className={`${styles.photoTypeBadge} ${styles.badgeEnd}`}>End Point</span>
              )}
              {photo.photo_type === 'progress' && (
                <span className={`${styles.photoTypeBadge} ${styles.badgeProgress}`}>Progress</span>
              )}
              <img
                src={photo.thumbnail_url || photo.image_url}
                alt="Work site progress"
                className={styles.thumbnailImg}
                loading="lazy"
              />

              {isEditable && (
                <button
                  type="button"
                  className={styles.deleteBtn}
                  onClick={() => handleDeletePhoto(photo.id)}
                  disabled={deletingId === photo.id}
                  aria-label="Delete photo"
                  title="Delete photo"
                >
                  {deletingId === photo.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              )}

              <div className={styles.photoFooter}>
                {new Date(photo.uploaded_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state when entry exists but has 0 photos */}
      {!loadingPhotos && dailyWorkEntryId && photos.length === 0 && (
        <div className={styles.hintBanner}>
          No site photos attached yet. Tap &ldquo;Take Photo&rdquo; or browse files to document work.
        </div>
      )}
    </div>
  );
};


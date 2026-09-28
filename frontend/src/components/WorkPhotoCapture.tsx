import React, { useState, useEffect, useRef } from 'react';
import type { AxiosError } from 'axios';
import { Camera, Image as ImageIcon, Trash2, Loader2, AlertCircle, X } from 'lucide-react';
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

export const WorkPhotoCapture: React.FC<WorkPhotoCaptureProps> = ({
  dailyWorkEntryId,
  status,
  initialPhotos,
  onPhotoUploaded,
  onPhotoDeleted,
  onPhotosLoaded,
}) => {
  const [photos, setPhotos] = useState<WorkPhoto[]>(initialPhotos || []);
  const [loadingPhotos, setLoadingPhotos] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const isEditable =
    Boolean(dailyWorkEntryId) && (status === 'draft' || status === 'correction_required');

  // Load photos whenever dailyWorkEntryId changes and initialPhotos wasn't provided or empty
  useEffect(() => {
    if (!dailyWorkEntryId) {
      setPhotos([]);
      return;
    }

    if (initialPhotos && initialPhotos.length > 0) {
      setPhotos(initialPhotos);
      setLoadingPhotos(false);
      return;
    }

    let isMounted = true;
    const fetchPhotos = async () => {
      setLoadingPhotos(true);
      setErrorMsg(null);
      try {
        const data = await getWorkPhotos(dailyWorkEntryId);
        if (isMounted) {
          setPhotos(data);
          onPhotosLoaded?.(data);
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
  }, [dailyWorkEntryId, initialPhotos]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !dailyWorkEntryId) return;

    // Reset input value so selecting the same file triggers onChange again
    e.target.value = '';

    setUploading(true);
    setUploadProgress(10);
    setErrorMsg(null);

    try {
      // 1. Client-side Canvas Image Compression
      const compressed = await compressImage(file, {
        maxWidth: 1920,
        maxHeight: 1080,
        quality: 0.8,
      });
      setUploadProgress(30);

      // 2. Upload via API multipart endpoint
      const newPhoto = await uploadWorkPhoto(dailyWorkEntryId, compressed, (percent) => {
        setUploadProgress(30 + Math.round((percent * 70) / 100));
      });

      setPhotos((prev) => [...prev, newPhoto]);
      onPhotoUploaded?.(newPhoto);
    } catch (err: unknown) {
      const norm = normalizeError(err as AxiosError<any>);
      setErrorMsg(norm.message || 'Failed to upload photo');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
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
              ref={cameraInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              aria-label="Capture photo with camera"
              className={styles.hiddenInput}
              onChange={handleFileSelect}
              disabled={uploading}
            />
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
              onClick={() => cameraInputRef.current?.click()}
              disabled={uploading}
              aria-label="Take Photo"
            >
              <Camera size={16} />
              Take Photo
            </button>

            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              aria-label="Upload Photo"
            >
              <ImageIcon size={16} />
              Browse
            </button>
          </div>
        )}
      </div>

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

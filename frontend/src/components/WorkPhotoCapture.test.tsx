import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { WorkPhotoCapture } from './WorkPhotoCapture';
import {
  getWorkPhotos,
  uploadWorkPhoto,
  deleteWorkPhoto,
  type WorkPhoto,
} from '../api/dailyWork';

vi.mock('../api/dailyWork', () => ({
  getWorkPhotos: vi.fn(),
  uploadWorkPhoto: vi.fn(),
  deleteWorkPhoto: vi.fn(),
}));

vi.mock('../utils/imageCompression', () => ({
  compressImage: vi.fn(async (file: File) => file),
}));

const mockPhotos: WorkPhoto[] = [
  {
    id: 'photo-101',
    daily_work_entry_id: 'entry-1',
    image_url: 'http://localhost:8000/storage/photos/sample1.jpg',
    thumbnail_url: 'http://localhost:8000/storage/photos/thumb_sample1.jpg',
    file_size_bytes: 102400,
    uploaded_at: '2026-09-25T10:30:00Z',
  },
];

describe('WorkPhotoCapture Component', () => {
  let mockTrack: { stop: ReturnType<typeof vi.fn>; kind: string; enabled: boolean };
  let mockStream: { getTracks: ReturnType<typeof vi.fn>; getVideoTracks: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    vi.clearAllMocks();
    (getWorkPhotos as any).mockResolvedValue([]);

    mockTrack = {
      stop: vi.fn(),
      kind: 'video',
      enabled: true,
    };

    mockStream = {
      getTracks: vi.fn(() => [mockTrack]),
      getVideoTracks: vi.fn(() => [mockTrack]),
    };

    vi.spyOn(HTMLVideoElement.prototype, 'play').mockImplementation(async () => {});

    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation((contextId: string) => {
      if (contextId === '2d') {
        return {
          drawImage: vi.fn(),
        } as any;
      }
      return null;
    });

    HTMLCanvasElement.prototype.toBlob = function (callback: BlobCallback, type?: string) {
      const blob = new Blob(['mock-captured-bytes'], { type: type || 'image/jpeg' });
      callback(blob);
    };

    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream),
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders photo capture controls and header with 0 count badge', () => {
    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    expect(screen.getByText('Site Progress Photos')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Take Photo/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload Photo/i })).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('opens camera interface via getUserMedia and captures photo with canvas frame', async () => {
    const uploadedPhoto: WorkPhoto = {
      id: 'photo-camera-1',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/camera1.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_camera1.jpg',
      file_size_bytes: 204800,
      uploaded_at: '2026-09-25T11:00:00Z',
    };
    (uploadWorkPhoto as any).mockResolvedValue(uploadedPhoto);

    const onPhotoUploaded = vi.fn();

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
        onPhotoUploaded={onPhotoUploaded}
      />
    );

    // Click Take Photo
    const takePhotoButton = screen.getByRole('button', { name: /Take Photo/i });
    fireEvent.click(takePhotoButton);

    // Verify getUserMedia was requested with environment facingMode
    await waitFor(() => {
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(
        expect.objectContaining({
          video: expect.objectContaining({
            facingMode: { ideal: 'environment' },
          }),
          audio: false,
        })
      );
    });

    // Camera viewfinder modal is open
    expect(screen.getByRole('dialog', { name: /Camera viewfinder/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Live camera preview')).toBeInTheDocument();

    // Click shutter button to capture frame
    const shutterBtn = screen.getByRole('button', { name: /Capture photo/i });
    fireEvent.click(shutterBtn);

    // Verify photo was uploaded through uploadWorkPhoto
    await waitFor(() => {
      expect(uploadWorkPhoto).toHaveBeenCalledWith(
        'entry-1',
        expect.any(File),
        expect.any(Function)
      );
    });

    // Verify camera track was stopped and modal closed
    expect(mockTrack.stop).toHaveBeenCalled();
    expect(screen.queryByRole('dialog', { name: /Camera viewfinder/i })).not.toBeInTheDocument();

    // Verify photo is displayed in DOM and callback triggered
    await waitFor(() => {
      const img = screen.getByAltText('Work site progress');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', uploadedPhoto.thumbnail_url);
    });

    expect(onPhotoUploaded).toHaveBeenCalledWith(uploadedPhoto);
  });

  it('keeps Browse working separately for selecting existing images via file picker', async () => {
    const uploadedPhoto: WorkPhoto = {
      id: 'photo-file-1',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/file1.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_file1.jpg',
      file_size_bytes: 150000,
      uploaded_at: '2026-09-25T11:15:00Z',
    };
    (uploadWorkPhoto as any).mockResolvedValue(uploadedPhoto);

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    const fileInput = screen.getByLabelText('Select photo from files') as HTMLInputElement;
    const testFile = new File(['image-bytes'], 'progress.jpg', { type: 'image/jpeg' });

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(uploadWorkPhoto).toHaveBeenCalledWith('entry-1', expect.any(File), expect.any(Function));
    });

    // Camera API must NOT have been called for file selection
    expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled();

    await waitFor(() => {
      expect(screen.getByAltText('Work site progress')).toBeInTheDocument();
    });
  });

  it('handles camera permission denial (NotAllowedError) clearly without opening file picker', async () => {
    const permError = new DOMException('Permission denied', 'NotAllowedError');
    (navigator.mediaDevices.getUserMedia as any).mockRejectedValue(permError);

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Take Photo/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          'Camera permission denied. Please allow camera access in your browser settings to take photos.'
        )
      ).toBeInTheDocument();
    });

    // Displays retry action and close button
    expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();

    // Closing camera clears modal and stops tracks
    fireEvent.click(screen.getByRole('button', { name: /^Close$/i }));
    expect(screen.queryByRole('dialog', { name: /Camera viewfinder/i })).not.toBeInTheDocument();
  });

  it('handles unavailable camera (NotFoundError) clearly', async () => {
    const notFoundError = new DOMException('Requested device not found', 'NotFoundError');
    (navigator.mediaDevices.getUserMedia as any).mockRejectedValue(notFoundError);

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Take Photo/i }));

    await waitFor(() => {
      expect(screen.getByText('No camera device found on this device.')).toBeInTheDocument();
    });
  });

  it('handles unsupported camera browser environment gracefully', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      configurable: true,
      value: undefined,
    });

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Take Photo/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          'Camera access is not supported by your browser or is blocked in insecure contexts (HTTPS required).'
        )
      ).toBeInTheDocument();
    });
  });

  it('stops camera tracks when user cancels or closes the camera modal', async () => {
    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Take Photo/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Camera viewfinder/i })).toBeInTheDocument();
    });

    // Click Cancel in modal footer
    const cancelBtn = screen.getByRole('button', { name: /Cancel camera/i });
    fireEvent.click(cancelBtn);

    expect(mockTrack.stop).toHaveBeenCalled();
    expect(screen.queryByRole('dialog', { name: /Camera viewfinder/i })).not.toBeInTheDocument();
  });

  it('stops camera tracks when component unmounts with active stream', async () => {
    const { unmount } = render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Take Photo/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Camera viewfinder/i })).toBeInTheDocument();
    });

    unmount();

    expect(mockTrack.stop).toHaveBeenCalled();
  });

  it('prevents duplicate photo entries in state and DOM when uploading same photo', async () => {
    const singlePhoto: WorkPhoto = {
      id: 'photo-single-1',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/single.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_single.jpg',
      uploaded_at: '2026-09-25T10:00:00Z',
    };
    (uploadWorkPhoto as any).mockResolvedValue(singlePhoto);

    const { rerender } = render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[singlePhoto]}
      />
    );

    // Initial render has 1 photo
    expect(screen.getAllByAltText('Work site progress')).toHaveLength(1);
    expect(screen.getByText('1')).toBeInTheDocument();

    // Rerender with duplicate photos in initialPhotos (simulating race condition / double props)
    rerender(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[singlePhoto, singlePhoto]}
      />
    );

    // Deduplication must ensure only 1 image and count 1
    expect(screen.getAllByAltText('Work site progress')).toHaveLength(1);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('supports multiple distinct legitimate photo uploads', async () => {
    const photo1: WorkPhoto = {
      id: 'photo-m1',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/m1.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_m1.jpg',
      uploaded_at: '2026-09-25T10:00:00Z',
    };
    const photo2: WorkPhoto = {
      id: 'photo-m2',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/m2.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_m2.jpg',
      uploaded_at: '2026-09-25T10:05:00Z',
    };

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[photo1, photo2]}
      />
    );

    // Both legitimate distinct photos must be displayed
    const images = screen.getAllByAltText('Work site progress');
    expect(images).toHaveLength(2);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('allows deleting a photo while entry is in draft status', async () => {
    (deleteWorkPhoto as any).mockResolvedValue({
      status: 'success',
      message: 'Photo deleted',
    });

    const onPhotoDeleted = vi.fn();

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={mockPhotos}
        onPhotoDeleted={onPhotoDeleted}
      />
    );

    expect(screen.getByAltText('Work site progress')).toBeInTheDocument();
    const deleteBtn = screen.getByLabelText('Delete photo');
    expect(deleteBtn).toBeInTheDocument();

    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(deleteWorkPhoto).toHaveBeenCalledWith('photo-101');
    });

    await waitFor(() => {
      expect(screen.queryByAltText('Work site progress')).not.toBeInTheDocument();
    });

    expect(onPhotoDeleted).toHaveBeenCalledWith('photo-101');
  });

  it('hides delete controls and capture buttons when entry is submitted', () => {
    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="submitted"
        initialPhotos={mockPhotos}
      />
    );

    expect(screen.getByAltText('Work site progress')).toBeInTheDocument();
    expect(screen.queryByLabelText('Delete photo')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Take Photo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Upload Photo/i })).not.toBeInTheDocument();
  });

  it('displays backend validation error when upload is rejected for invalid type or size', async () => {
    const backendError = {
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: 'Invalid file type. Only JPEG/PNG/WEBP allowed.',
        },
      },
    };
    (uploadWorkPhoto as any).mockRejectedValue(backendError);

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    const fileInput = screen.getByLabelText('Select photo from files');
    const invalidFile = new File(['text-content'], 'notes.txt', { type: 'text/plain' });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(
        screen.getByText('Invalid file type. Only JPEG/PNG/WEBP allowed.')
      ).toBeInTheDocument();
    });
  });

  it('shows oversized file validation error from backend', async () => {
    const oversizedError = {
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: 'File size exceeds 10MB limit',
        },
      },
    };
    (uploadWorkPhoto as any).mockRejectedValue(oversizedError);

    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    const fileInput = screen.getByLabelText('Select photo from files');
    const hugeFile = new File(['a'.repeat(100)], 'huge.jpg', { type: 'image/jpeg' });

    fireEvent.change(fileInput, { target: { files: [hugeFile] } });

    await waitFor(() => {
      expect(screen.getByText('File size exceeds 10MB limit')).toBeInTheDocument();
    });
  });

  it('prompts user to save draft first when dailyWorkEntryId is null', () => {
    render(
      <WorkPhotoCapture
        dailyWorkEntryId={null}
        status="draft"
      />
    );

    expect(
      screen.getByText(/Save a work entry draft before attaching site progress photos/i)
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Take Photo/i })).not.toBeInTheDocument();
  });

  it('does not render mandatory start-point and end-point evidence cards', () => {
    render(
      <WorkPhotoCapture
        dailyWorkEntryId="entry-1"
        status="draft"
        initialPhotos={[]}
      />
    );

    expect(screen.queryByTestId('evidence-section')).not.toBeInTheDocument();
    expect(screen.queryByTestId('start-point-slot')).not.toBeInTheDocument();
    expect(screen.queryByTestId('end-point-slot')).not.toBeInTheDocument();
  });
});

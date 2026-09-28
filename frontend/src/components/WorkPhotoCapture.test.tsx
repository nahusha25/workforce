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
  beforeEach(() => {
    vi.clearAllMocks();
    (getWorkPhotos as any).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders photo capture controls and uploads photo successfully', async () => {
    const uploadedPhoto: WorkPhoto = {
      id: 'photo-102',
      daily_work_entry_id: 'entry-1',
      image_url: 'http://localhost:8000/storage/photos/cables.jpg',
      thumbnail_url: 'http://localhost:8000/storage/photos/thumb_cables.jpg',
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

    // Verify header and buttons
    expect(screen.getByText('Site Progress Photos')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Take Photo/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload Photo/i })).toBeInTheDocument();

    // Select file via camera input
    const cameraInput = screen.getByLabelText('Capture photo with camera') as HTMLInputElement;
    const testFile = new File(['dummy-image-bytes'], 'cables.jpg', { type: 'image/jpeg' });

    fireEvent.change(cameraInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(uploadWorkPhoto).toHaveBeenCalledWith(
        'entry-1',
        expect.any(File),
        expect.any(Function)
      );
    });

    // Wait for the new photo to appear in the DOM
    await waitFor(() => {
      const img = screen.getByAltText('Work site progress');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', uploadedPhoto.thumbnail_url);
    });

    expect(onPhotoUploaded).toHaveBeenCalledWith(uploadedPhoto);
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

    // Photo should be displayed with delete button
    expect(screen.getByAltText('Work site progress')).toBeInTheDocument();
    const deleteBtn = screen.getByLabelText('Delete photo');
    expect(deleteBtn).toBeInTheDocument();

    // Click delete
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(deleteWorkPhoto).toHaveBeenCalledWith('photo-101');
    });

    // After deletion, photo should be removed
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

    // Photo is still displayed
    expect(screen.getByAltText('Work site progress')).toBeInTheDocument();

    // Capture and delete controls must be hidden
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
});

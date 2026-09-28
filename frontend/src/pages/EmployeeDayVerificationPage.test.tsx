import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { RoleGuard } from '../components/guards/RoleGuard';
import {
  EmployeeDayVerificationPage,
  formatLocalTime,
  formatDateTime,
  isNextDay,
} from './EmployeeDayVerificationPage';
import {
  getEmployeeDayDetail,
  approveEntity,
  rejectEntity,
  returnEntity,
  type EmployeeDayDetailResponse,
} from '../api/verification';
import { getLocalISODate } from '../utils/date';
import type { SystemRole } from '../types/auth';

let idempCounter = 0;
vi.mock('../api/verification', () => ({
  getEmployeeDayDetail: vi.fn(),
  approveEntity: vi.fn(),
  rejectEntity: vi.fn(),
  returnEntity: vi.fn(),
  generateIdempotencyKey: vi.fn(() => `test-idemp-${++idempCounter}`),
}));

const mockDetail: EmployeeDayDetailResponse = {
  employee_id: 'emp-101',
  employee_name: 'Rajesh Worker',
  employee_code: 'EMP-101',
  date: '2026-09-28',
  site_id: 'site-1',
  site_name: 'Central Metro Station',
  all_verified: true,
  exception_flags: ['out_of_location'],
  attendance: {
    id: 'att-101',
    date: '2026-09-28',
    session_number: 1,
    check_in_time: '2026-09-28T09:00:00Z',
    check_in_distance_m: 125.4,
    check_out_time: '2026-09-28T17:30:00Z',
    check_out_distance_m: 45.2,
    is_within_geofence: false,
    working_hours: 8.5,
    overtime_hours: 0.5,
    status: 'flagged',
    override_by: 'sup-user-id',
    verification_record_id: 'vr-1',
    verification_action: null,
    verification_remarks: null,
    history: [
      {
        id: 'h-1',
        action: 'flagged',
        remarks: 'Out of location check-in',
        verified_by: 'u-1',
        verified_by_name: 'System Engine',
        verified_at: '2026-09-28T09:01:00Z',
      },
      {
        id: 'h-2',
        action: 'correction_required',
        remarks: 'Please explain the distance from site boundary',
        verified_by: 'u-2',
        verified_by_name: 'Amit Supervisor',
        verified_at: '2026-09-28T12:00:00Z',
      },
      {
        id: 'h-3',
        action: 'approved',
        remarks: 'Valid reason verified on site survey',
        verified_by: 'u-2',
        verified_by_name: 'Amit Supervisor',
        verified_at: '2026-09-28T18:00:00Z',
      },
    ],
  },
  work_entries: [
    {
      id: 'dwe-101',
      idempotency_key: 'idemp-1',
      activity_id: 'act-1',
      activity_name: 'Fiber Cable Laying',
      activity_category: 'Cabling',
      work_order_id: 'wo-1',
      work_order_number: 'WO-2026-001',
      work_date: '2026-09-28',
      quantity: '45.5',
      uom: 'meters',
      status: 'approved',
      remarks: 'North corridor installation completed',
      verification_record_id: 'vr-2',
      verification_action: 'approved',
      verification_remarks: null,
      history: [],
      photos: [
        {
          id: 'photo-1',
          daily_work_entry_id: 'dwe-101',
          image_url: 'http://example.com/photo1.jpg',
          thumbnail_url: 'http://example.com/photo1_thumb.jpg',
          file_size_bytes: 102400,
          uploaded_at: '2026-09-28T10:00:00Z',
        },
      ],
      materials: [
        {
          id: 'mat-1',
          daily_work_entry_id: 'dwe-101',
          material_id: 'm-1',
          site_id: 'site-1',
          transaction_type: 'consumed',
          item_name: 'Cat6 Ethernet Cable',
          quantity: '50.00',
          amount: '1250.75',
          bill_image_url: 'http://example.com/bill1.jpg',
          is_high_value: true,
          status: 'approved',
          verification_record_id: 'vr-3',
          verification_action: 'approved',
          verification_remarks: null,
          history: [],
        },
      ],
    },
  ],
};

const renderWithRouter = (
  role: SystemRole = 'supervisor',
  initialRoute = '/verification/emp-101?date=2026-09-28'
) => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'user-1',
          user_id: 'u-1',
          employee_code: 'SUP-001',
          mobile_id: '+919876543210',
          name: 'Test Supervisor',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
        },
        role,
        accessToken: 'fake-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={['supervisor', 'administrator', 'director']} />}>
            <Route path="/verification" element={<div data-testid="queue-page">Queue Page</div>} />
            <Route path="/verification/:employeeId" element={<EmployeeDayVerificationPage />} />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('EmployeeDayVerificationPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (getEmployeeDayDetail as any).mockResolvedValue(mockDetail);
    (approveEntity as any).mockResolvedValue({
      id: 'vr-mock-1',
      action: 'approved',
      is_replay: false,
    });
    (rejectEntity as any).mockResolvedValue({
      id: 'vr-mock-2',
      action: 'rejected',
      is_replay: false,
    });
    (returnEntity as any).mockResolvedValue({
      id: 'vr-mock-3',
      action: 'correction_required',
      is_replay: false,
    });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  // 1. Loading state
  it('renders loading indicator while fetching employee day detail', () => {
    (getEmployeeDayDetail as any).mockImplementation(() => new Promise(() => {}));
    renderWithRouter();
    expect(screen.getByTestId('detail-loading')).toBeTruthy();
    expect(screen.getByText(/Loading verification details…/i)).toBeTruthy();
  });

  // 2. Error state & retry
  it('renders error banner when API fails and retries upon clicking Retry', async () => {
    (getEmployeeDayDetail as any).mockRejectedValueOnce(new Error('Network failure'));
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('detail-error')).toBeTruthy();
      expect(screen.getByText(/Network failure/i)).toBeTruthy();
    });

    (getEmployeeDayDetail as any).mockResolvedValueOnce(mockDetail);
    fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Rajesh Worker')).toBeTruthy();
    });
  });

  // 3. 403 / 404 friendly error states
  it('renders friendly 404 message when employee day detail is not found', async () => {
    const error404: any = new Error('Not found');
    error404.response = { status: 404, data: { detail: 'Record not found' } };
    (getEmployeeDayDetail as any).mockRejectedValueOnce(error404);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Employee Record Not Found')).toBeTruthy();
      expect(screen.getByRole('link', { name: /Return to Queue/i })).toBeTruthy();
    });
  });

  it('renders friendly 403 message when user is unauthorized', async () => {
    const error403: any = new Error('Forbidden');
    error403.response = { status: 403, data: { detail: 'Unauthorized supervisor' } };
    (getEmployeeDayDetail as any).mockRejectedValueOnce(error403);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Access Denied')).toBeTruthy();
      expect(screen.getByRole('link', { name: /Return to Queue/i })).toBeTruthy();
    });
  });

  // 4. Empty day state
  it('renders "No records for this date" when employee has neither attendance nor work entries', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      attendance: null,
      work_entries: [],
    });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('detail-empty-day')).toBeTruthy();
      expect(screen.getByText(/No records for this date/i)).toBeTruthy();
    });
  });

  // 5. Attendance outside geofence rendering & override
  it('renders outside-geofence indicator and supervisor override banner', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('attendance-section')).toBeTruthy();
    });

    expect(screen.getByTestId('geofence-outside')).toBeTruthy();
    expect(screen.getByText(/Outside Geofence/i)).toBeTruthy();
    expect(screen.getByTestId('override-banner')).toBeTruthy();
    expect(screen.getByText(/Supervisor override applied/i)).toBeTruthy();
    expect(screen.getByText('125m from site')).toBeTruthy();
    expect(screen.getByText('45m from site')).toBeTruthy();
  });

  // 6. Work entry with uom and work order
  it('renders work entries with activity name, category, quantity with uom, and work order number', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('work-entries-section')).toBeTruthy();
    });

    expect(screen.getByText('Fiber Cable Laying')).toBeTruthy();
    expect(screen.getByText('Cabling')).toBeTruthy();
    expect(screen.getByTestId('entry-quantity').textContent).toBe('45.5 meters');
    expect(screen.getByText('WO-2026-001')).toBeTruthy();
    expect(screen.getByText('North corridor installation completed')).toBeTruthy();
  });

  // 7. Photo lightbox open and Esc close
  it('opens photo in lightbox on click and closes when Escape is pressed or backdrop is clicked', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('photo-thumbnail')).toBeTruthy();
    });

    // Lightbox closed initially
    expect(screen.queryByTestId('lightbox-backdrop')).toBeNull();

    // Click thumbnail to open lightbox
    fireEvent.click(screen.getByTestId('photo-thumbnail'));
    expect(screen.getByTestId('lightbox-backdrop')).toBeTruthy();
    expect(screen.getByTestId('lightbox-image')).toBeTruthy();

    // Press Escape to close
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('lightbox-backdrop')).toBeNull();

    // Reopen and close via close button
    fireEvent.click(screen.getByTestId('photo-thumbnail'));
    expect(screen.getByTestId('lightbox-backdrop')).toBeTruthy();
    fireEvent.click(screen.getByTestId('lightbox-close-btn'));
    expect(screen.queryByTestId('lightbox-backdrop')).toBeNull();
  });

  // 8. Broken image fallback with "Open original" link
  it('displays broken-image fallback with "Open original" link when image fails to load', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('photo-thumbnail')).toBeTruthy();
    });

    // Trigger image error
    fireEvent.error(screen.getByTestId('photo-thumbnail'));

    expect(screen.getByTestId('broken-image-fallback')).toBeTruthy();
    expect(screen.getByText(/Image failed/i)).toBeTruthy();
    const link = screen.getByTestId('open-original-link') as HTMLAnchorElement;
    expect(link.href).toBe('http://example.com/photo1.jpg');
  });

  // 9. High-value material badge and 2-decimal amount formatting
  it('displays high-value material badge and formats amount with formatDecimal (2 decimal places)', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('material-row')).toBeTruthy();
    });

    expect(screen.getByText('Cat6 Ethernet Cable')).toBeTruthy();
    expect(screen.getByTestId('high-value-badge')).toBeTruthy();
    expect(screen.getByText('High Value')).toBeTruthy();
    expect(screen.getByTestId('material-amount').textContent).toContain('₹1250.75');
  });

  // 10. Three-event history renders in chronological order
  it('renders three verification audit history events in chronological order', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Attendance Audit History')).toBeTruthy();
    });

    expect(screen.getByText('Out of location check-in')).toBeTruthy();
    expect(screen.getByText('Please explain the distance from site boundary')).toBeTruthy();
    expect(screen.getByText('Valid reason verified on site survey')).toBeTruthy();
    expect(screen.getByText(/System Engine/i)).toBeTruthy();
    expect(screen.getAllByText(/Amit Supervisor/i).length).toBe(2);
  });

  // 11. ?date= parameter passed to API (and defaults to local today when absent)
  it('passes ?date= query parameter to the getEmployeeDayDetail API', async () => {
    renderWithRouter('supervisor', '/verification/emp-101?date=2026-09-25');

    await waitFor(() => {
      expect(getEmployeeDayDetail).toHaveBeenCalledWith('emp-101', '2026-09-25');
    });
  });

  it('defaults to local today when ?date= query parameter is omitted', async () => {
    renderWithRouter('supervisor', '/verification/emp-101');

    await waitFor(() => {
      expect(getEmployeeDayDetail).toHaveBeenCalledWith('emp-101', getLocalISODate());
    });
  });

  // 12. Back link keeps the date
  it('renders back link to /verification?date=<date>', async () => {
    renderWithRouter('supervisor', '/verification/emp-101?date=2026-09-25');

    await waitFor(() => {
      expect(screen.getByTestId('back-link')).toBeTruthy();
    });

    const link = screen.getByTestId('back-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/verification?date=2026-09-25');
  });

  // 13. Role guard blocks employee
  it('blocks worker/employee role and redirects to /403', async () => {
    renderWithRouter('employee');

    await waitFor(() => {
      expect(screen.getByTestId('forbidden-page')).toBeTruthy();
      expect(screen.queryByTestId('detail-header')).toBeNull();
    });
  });

  // 14. Lightbox image load failure handling
  it('displays lightbox failure fallback with "Open original" link when full-size image fails to load', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('photo-thumbnail')).toBeTruthy();
    });

    // Open lightbox
    fireEvent.click(screen.getByTestId('photo-thumbnail'));
    expect(screen.getByTestId('lightbox-backdrop')).toBeTruthy();
    const fullImg = screen.getByTestId('lightbox-image');
    expect(fullImg).toBeTruthy();

    // Trigger full-size image error in lightbox
    fireEvent.error(fullImg);

    expect(screen.getByTestId('lightbox-error-fallback')).toBeTruthy();
    expect(screen.getByText('Failed to load full-size image')).toBeTruthy();
    const openOrig = screen.getByTestId('lightbox-open-original') as HTMLAnchorElement;
    expect(openOrig.href).toBe('http://example.com/photo1.jpg');
    expect(screen.queryByTestId('lightbox-image')).toBeNull();
  });

  // 15. Broken bill image visibly flagged
  it('visibly flags broken bill image with fallback and "Open original" link instead of staying silently empty', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('bill-thumbnail')).toBeTruthy();
    });

    // Trigger error on bill thumbnail
    fireEvent.error(screen.getByTestId('bill-thumbnail'));

    expect(screen.getByTestId('broken-bill-fallback')).toBeTruthy();
    expect(screen.getByText('Bill image failed')).toBeTruthy();
    const billLink = screen.getByTestId('open-original-bill') as HTMLAnchorElement;
    expect(billLink.href).toBe('http://example.com/bill1.jpg');
    expect(screen.queryByTestId('bill-thumbnail')).toBeNull();
  });

  // 16. Attendance same-day session under TZ=Asia/Kolkata
  it('renders check-in and check-out with dates and times for same-day session without next-day marker under TZ=Asia/Kolkata', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      attendance: {
        ...mockDetail.attendance!,
        check_in_time: '2026-09-26T03:30:00Z', // 09:00 AM IST on 26 Sep
        check_out_time: '2026-09-26T12:00:00Z', // 05:30 PM IST on 26 Sep
      },
    });

    renderWithRouter('supervisor', '/verification/emp-101?date=2026-09-26');

    await waitFor(() => {
      expect(screen.getByTestId('attendance-section')).toBeTruthy();
    });

    expect(screen.getByTestId('check-in-time').textContent).toBe('26 Sep, 9:00 AM');
    expect(screen.getByTestId('check-out-time').textContent).toBe('26 Sep, 5:30 PM');
    expect(screen.queryByTestId('next-day-tag')).toBeNull();
  });

  // 17. Attendance cross-midnight session under TZ=Asia/Kolkata
  it('renders check-in and check-out with dates and times and marks next day clearly for cross-midnight session under TZ=Asia/Kolkata', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      attendance: {
        ...mockDetail.attendance!,
        check_in_time: '2026-09-26T12:45:00Z', // 6:15 PM IST on 26 Sep
        check_out_time: '2026-09-26T21:30:00Z', // 3:00 AM IST on 27 Sep
      },
    });

    renderWithRouter('supervisor', '/verification/emp-101?date=2026-09-26');

    await waitFor(() => {
      expect(screen.getByTestId('attendance-section')).toBeTruthy();
    });

    expect(screen.getByTestId('check-in-time').textContent).toBe('26 Sep, 6:15 PM');
    expect(screen.getByTestId('check-out-time').textContent).toContain('27 Sep, 3:00 AM');
    expect(screen.getByTestId('next-day-tag')).toBeTruthy();
    expect(screen.getByTestId('next-day-tag').textContent).toBe('next day');
  });

  // 18. Per-item action buttons appear only for submitted items; draft shows the note
  it('displays action buttons only for submitted items and shows "Not submitted yet" for draft items', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      attendance: {
        ...mockDetail.attendance!,
        status: 'flagged',
      },
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-sub',
          status: 'submitted',
          materials: [
            {
              ...mockDetail.work_entries[0].materials[0],
              id: 'mat-draft',
              status: 'draft',
            },
            {
              ...mockDetail.work_entries[0].materials[0],
              id: 'mat-sub',
              status: 'submitted',
            },
          ],
        },
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-draft',
          status: 'draft',
          materials: [],
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-sub')).toBeTruthy();
      expect(screen.getByTestId('reject-work-entry-dwe-sub')).toBeTruthy();
      expect(screen.getByTestId('return-work-entry-dwe-sub')).toBeTruthy();
    });

    // Draft work entry shows note, no action buttons
    expect(screen.getByTestId('draft-note-dwe-draft')).toBeTruthy();
    expect(screen.getByTestId('draft-note-dwe-draft').textContent).toBe('Not submitted yet');
    expect(screen.queryByTestId('approve-work-entry-dwe-draft')).toBeNull();

    // Draft material shows note, no action buttons
    expect(screen.getByTestId('draft-note-mat-draft')).toBeTruthy();
    expect(screen.getByTestId('draft-note-mat-draft').textContent).toBe('Not submitted yet');
    expect(screen.queryByTestId('approve-material-mat-draft')).toBeNull();

    // Submitted material shows buttons
    expect(screen.getByTestId('approve-material-mat-sub')).toBeTruthy();

    // Flagged attendance shows buttons
    expect(screen.getByTestId('approve-attendance-btn')).toBeTruthy();
  });

  // 19. Supervisor does not see Reopen and admin does
  it('hides Reopen button for supervisor and shows Reopen button for administrator on approved/verified items', async () => {
    const approvedDetail = {
      ...mockDetail,
      attendance: {
        ...mockDetail.attendance!,
        status: 'verified',
      },
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-app',
          status: 'approved',
          materials: [
            {
              ...mockDetail.work_entries[0].materials[0],
              id: 'mat-app',
              status: 'approved',
            },
          ],
        },
      ],
    };

    // Supervisor: Reopen buttons NOT shown
    (getEmployeeDayDetail as any).mockResolvedValueOnce(approvedDetail);
    const { unmount } = renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('work-entries-section')).toBeTruthy();
    });
    expect(screen.queryByTestId('reopen-work-entry-dwe-app')).toBeNull();
    expect(screen.queryByTestId('reopen-material-mat-app')).toBeNull();
    expect(screen.queryByTestId('reopen-attendance-btn')).toBeNull();

    unmount();

    // Administrator: Reopen buttons ARE shown
    (getEmployeeDayDetail as any).mockResolvedValueOnce(approvedDetail);
    renderWithRouter('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('reopen-work-entry-dwe-app')).toBeTruthy();
      expect(screen.getByTestId('reopen-material-mat-app')).toBeTruthy();
      expect(screen.getByTestId('reopen-attendance-btn')).toBeTruthy();
    });
  });

  // 20. Reject requires 10+ trimmed chars in modal
  it('requires at least 10 trimmed characters for rejection remarks in modal', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('reject-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('reject-work-entry-dwe-1'));

    const confirmBtn = screen.getByRole('button', { name: /confirm rejection/i });
    expect(confirmBtn).toBeDisabled();

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: '   short   ' } });
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(textarea, { target: { value: 'Work entry rejected due to missing site measurement' } });
    expect(confirmBtn).not.toBeDisabled();
  });

  // 21. Cancel sends nothing
  it('does not send any request when cancelling or closing the verification modal', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('reject-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('reject-work-entry-dwe-1'));
    expect(screen.getByRole('dialog')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /close modal/i }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(rejectEntity).not.toHaveBeenCalled();
    expect(approveEntity).not.toHaveBeenCalled();
    expect(returnEntity).not.toHaveBeenCalled();
  });

  // 22. Approve success refreshes and shows a notice
  it('refreshes day detail and shows success notice upon successful approval', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    expect(screen.getByTestId('approve-confirm-modal')).toBeTruthy();

    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(approveEntity).toHaveBeenCalledWith('dwe-1', {
        entity_type: 'daily_work',
        idempotency_key: expect.any(String),
        remarks: null,
      });
      expect(screen.getByTestId('success-notice')).toBeTruthy();
      expect(screen.getByTestId('success-notice').textContent).toContain('approved successfully');
    });

    await waitFor(() => {
      expect(getEmployeeDayDetail).toHaveBeenCalledTimes(2);
    });
  });

  // 23. Double-click sends one request
  it('disables action buttons while submission is in flight preventing double-click duplicate requests', async () => {
    let resolveApprove: any;
    (approveEntity as any).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveApprove = resolve;
        })
    );

    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    const confirmBtn = screen.getByTestId('confirm-approve-btn');

    // First click
    fireEvent.click(confirmBtn);
    expect(approveEntity).toHaveBeenCalledTimes(1);
    expect(confirmBtn).toBeDisabled();

    // Second click during in-flight submission
    fireEvent.click(confirmBtn);
    expect(approveEntity).toHaveBeenCalledTimes(1);

    // Resolve in flight
    resolveApprove({
      id: 'vr-1',
      action: 'approved',
      is_replay: false,
    });

    await waitFor(() => {
      expect(screen.queryByTestId('approve-confirm-modal')).toBeNull();
    });
  });

  // 24. Retry after failure reuses the exact same idempotency key
  it('reuses the same idempotency key when retrying after a failed action', async () => {
    (approveEntity as any).mockRejectedValueOnce(new Error('Network connectivity issue'));
    (approveEntity as any).mockResolvedValueOnce({
      id: 'vr-1',
      action: 'approved',
      is_replay: false,
    });

    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('page-action-error')).toBeTruthy();
      expect(screen.getByTestId('action-retry-btn')).toBeTruthy();
    });

    const firstKey = vi.mocked(approveEntity).mock.calls[0][1].idempotency_key;
    expect(firstKey).toBeTruthy();

    // Click retry from page notice
    fireEvent.click(screen.getByTestId('action-retry-btn'));

    await waitFor(() => {
      expect(approveEntity).toHaveBeenCalledTimes(2);
    });

    const secondKey = vi.mocked(approveEntity).mock.calls[1][1].idempotency_key;
    expect(secondKey).toBe(firstKey);
    expect(approveEntity).toHaveBeenNthCalledWith(
      1,
      'dwe-1',
      expect.objectContaining({ idempotency_key: firstKey })
    );
    expect(approveEntity).toHaveBeenNthCalledWith(
      2,
      'dwe-1',
      expect.objectContaining({ idempotency_key: firstKey })
    );
  });

  // 25. Replay response is treated as success
  it('treats is_replay=true response as success, closes modal, and refreshes day detail', async () => {
    (approveEntity as any).mockResolvedValueOnce({
      id: 'vr-replay-1',
      action: 'approved',
      is_replay: true,
    });

    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('approve-confirm-modal')).toBeNull();
      expect(screen.getByTestId('success-notice')).toBeTruthy();
      expect(screen.getByTestId('success-notice').textContent).toContain('approved successfully');
    });

    expect(getEmployeeDayDetail).toHaveBeenCalledTimes(2);
  });

  // 26. State conflict response (409 and specific 400) reloads with message
  it('handles state-conflict response (409 and specific 400) by displaying record changed message and reloading detail', async () => {
    const conflictErr409: any = new Error('State conflict');
    conflictErr409.response = { status: 409, data: { detail: 'Record already verified by another supervisor' } };
    (approveEntity as any).mockRejectedValueOnce(conflictErr409);

    const submittedDetail = {
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    };
    (getEmployeeDayDetail as any).mockResolvedValue(submittedDetail);

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('approve-confirm-modal')).toBeNull();
      expect(screen.getByTestId('conflict-notice')).toBeTruthy();
      expect(screen.getByTestId('conflict-notice').textContent).toContain('This record changed; refreshed');
    });

    expect(getEmployeeDayDetail).toHaveBeenCalledTimes(2);

    // Also verify specific 400 InvalidVerificationStateError detail triggers conflict reload
    const conflictErr400: any = new Error('Bad request');
    conflictErr400.response = {
      status: 400,
      data: { detail: "Cannot approve record with status 'approved'. Target must be submitted." },
    };
    (approveEntity as any).mockRejectedValueOnce(conflictErr400);

    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('approve-confirm-modal')).toBeNull();
      expect(screen.getByTestId('conflict-notice')).toBeTruthy();
      expect(screen.getByTestId('conflict-notice').textContent).toContain('This record changed; refreshed');
    });

    expect(getEmployeeDayDetail).toHaveBeenCalledTimes(3);
  });

  // 27. High-value approval requires confirm
  it('prompts with visible warning and requires explicit confirmation for high-value material approval', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'approved',
          materials: [
            {
              ...mockDetail.work_entries[0].materials[0],
              id: 'mat-hv',
              item_name: 'High End Switch',
              is_high_value: true,
              status: 'submitted',
            },
          ],
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-material-mat-hv')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-material-mat-hv'));

    expect(screen.getByTestId('approve-confirm-modal')).toBeTruthy();
    expect(screen.getByTestId('high-value-warning')).toBeTruthy();
    expect(screen.getByText(/This purchase exceeds the approval limit/i)).toBeTruthy();

    expect(approveEntity).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(approveEntity).toHaveBeenCalledWith('mat-hv', {
        entity_type: 'material',
        idempotency_key: expect.any(String),
        remarks: null,
      });
    });
  });

  // 28. Failed action shows error with retry
  it('displays page-level error message with a retry button when an action fails outside modal', async () => {
    const error500: any = new Error('Server error');
    error500.response = { status: 500, data: { detail: 'Internal server fault' } };
    (returnEntity as any).mockRejectedValueOnce(error500);
    (returnEntity as any).mockResolvedValueOnce({ id: 'vr-1', action: 'correction_required', is_replay: false });

    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('return-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('return-work-entry-dwe-1'));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Detailed explanation for returning work entry' },
    });
    fireEvent.click(screen.getByRole('button', { name: /send for correction/i }));

    await waitFor(() => {
      expect(returnEntity).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('page-action-error')).toBeTruthy();
      expect(screen.getByText('Internal server fault')).toBeTruthy();
      expect(screen.getByTestId('action-retry-btn')).toBeTruthy();
    });

    // Click retry from page notice
    fireEvent.click(screen.getByTestId('action-retry-btn'));

    await waitFor(() => {
      expect(returnEntity).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId('success-notice')).toBeTruthy();
    });
  });

  // 29. 422 shows error in modal and keeps typed remarks
  it('keeps modal open with typed remarks when backend returns 422 validation error', async () => {
    const err422: any = new Error('Validation error');
    err422.response = {
      status: 422,
      data: { detail: "Remarks are mandatory with at least 10 characters when action is 'rejected'" },
    };
    (rejectEntity as any).mockRejectedValueOnce(err422);

    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('reject-work-entry-dwe-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('reject-work-entry-dwe-1'));

    const typedRemarks = 'Measurement mismatch on site survey';
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: typedRemarks },
    });
    fireEvent.click(screen.getByRole('button', { name: /confirm rejection/i }));

    await waitFor(() => {
      expect(rejectEntity).toHaveBeenCalledTimes(1);
    });

    // Modal must REMAIN open
    expect(screen.getByRole('dialog')).toBeTruthy();
    // Error banner is rendered inside modal
    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText("Remarks are mandatory with at least 10 characters when action is 'rejected'")).toBeTruthy();
    // Remarks textarea preserves typed remarks
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toBe(typedRemarks);
  });

  // 30. Open attendance session (check_out_time null) shows "Session still open" and no buttons
  it('handles open attendance session by showing "Session still open" and hiding action buttons', async () => {
    const openAttendanceDetail = {
      ...mockDetail,
      attendance: {
        ...mockDetail.attendance!,
        check_out_time: null,
        status: 'draft',
      },
    };

    (getEmployeeDayDetail as any).mockResolvedValueOnce(openAttendanceDetail);
    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('attendance-section')).toBeTruthy();
    });

    expect(screen.getByTestId('attendance-open-session-note')).toBeTruthy();
    expect(screen.getByTestId('attendance-open-session-note').textContent).toBe('Session still open');
    expect(screen.queryByTestId('approve-attendance-btn')).toBeNull();
    expect(screen.queryByTestId('reject-attendance-btn')).toBeNull();
    expect(screen.queryByTestId('return-attendance-btn')).toBeNull();
  });

  // 31. Reopen modal displays Reopen title and Confirm Reopen button
  it('opens reopen modal with Reopen title and Confirm Reopen button for administrator', async () => {
    const approvedDetail = {
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-app-1',
          status: 'approved',
        },
      ],
    };

    (getEmployeeDayDetail as any).mockResolvedValueOnce(approvedDetail);
    renderWithRouter('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('reopen-work-entry-dwe-app-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('reopen-work-entry-dwe-app-1'));

    // Modal title must say Reopen
    expect(screen.getByText(/Reopen — Mandatory Remarks/i)).toBeTruthy();
    // Submit button must say Confirm Reopen
    expect(screen.getByRole('button', { name: /Confirm Reopen/i })).toBeTruthy();
    // Textarea placeholder mentions reopening
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.placeholder).toContain('reason for reopening');
  });

  // 32. Material item_name shown in modal
  it('displays item_name in the modal title when approving a material transaction', async () => {
    (getEmployeeDayDetail as any).mockResolvedValueOnce({
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'approved',
          materials: [
            {
              ...mockDetail.work_entries[0].materials[0],
              id: 'mat-item-1',
              item_name: 'Cement 50kg Bags',
              is_high_value: false,
              status: 'submitted',
            },
          ],
        },
      ],
    });

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-material-mat-item-1')).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId('approve-material-mat-item-1'));

    expect(screen.getByTestId('approve-confirm-modal')).toBeTruthy();
    expect(screen.getByText(/Material: Cement 50kg Bags/i)).toBeTruthy();
  });

  // 33. Opening a new action clears any previously visible success notice
  it('clears success notice when a new action is opened', async () => {
    const twoEntriesDetail = {
      ...mockDetail,
      work_entries: [
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-1',
          status: 'submitted',
        },
        {
          ...mockDetail.work_entries[0],
          id: 'dwe-2',
          status: 'submitted',
        },
      ],
    };
    (getEmployeeDayDetail as any).mockResolvedValue(twoEntriesDetail);

    renderWithRouter('supervisor');

    await waitFor(() => {
      expect(screen.getByTestId('approve-work-entry-dwe-1')).toBeTruthy();
    });

    // Approve first entry
    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-1'));
    fireEvent.click(screen.getByTestId('confirm-approve-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('success-notice')).toBeTruthy();
    });

    // Opening second action must immediately clear the success notice
    fireEvent.click(screen.getByTestId('approve-work-entry-dwe-2'));
    expect(screen.queryByTestId('success-notice')).toBeNull();
  });
});

// 18. formatLocalTime helper tests
describe('formatLocalTime', () => {
  it('returns "—" for null, undefined, or invalid ISO strings', () => {
    expect(formatLocalTime(null)).toBe('—');
    expect(formatLocalTime(undefined)).toBe('—');
    expect(formatLocalTime('invalid-datetime')).toBe('—');
  });

  it('formats valid ISO datetime into local time format', () => {
    const formatted = formatLocalTime('2026-09-28T09:30:00Z');
    expect(formatted).not.toBe('—');
    expect(typeof formatted).toBe('string');
  });
});

// 19. formatDateTime helper tests
describe('formatDateTime', () => {
  it('returns "—" for null, undefined, or invalid ISO strings', () => {
    expect(formatDateTime(null)).toBe('—');
    expect(formatDateTime(undefined)).toBe('—');
    expect(formatDateTime('invalid-datetime')).toBe('—');
  });

  it('formats valid ISO datetime into "day month, time" format under TZ=Asia/Kolkata', () => {
    const formatted = formatDateTime('2026-09-26T12:45:00Z');
    expect(formatted).toBe('26 Sep, 6:15 PM');
  });
});

// 20. isNextDay helper tests
describe('isNextDay', () => {
  it('returns false when check-in or check-out is missing or invalid', () => {
    expect(isNextDay(null, null)).toBe(false);
    expect(isNextDay('2026-09-26T12:45:00Z', null)).toBe(false);
    expect(isNextDay(null, '2026-09-26T12:45:00Z')).toBe(false);
    expect(isNextDay('invalid', '2026-09-26T12:45:00Z')).toBe(false);
  });

  it('returns false when check-in and check-out occur on the same local calendar day', () => {
    expect(isNextDay('2026-09-26T03:30:00Z', '2026-09-26T12:00:00Z')).toBe(false);
  });

  it('returns true when check-out crosses midnight into next local calendar day under TZ=Asia/Kolkata', () => {
    // In UTC, both are 2026-09-26; but in Asia/Kolkata (+05:30), check-in is 26 Sep 18:15 and check-out is 27 Sep 03:00
    expect(isNextDay('2026-09-26T12:45:00Z', '2026-09-26T21:30:00Z')).toBe(true);
  });
});


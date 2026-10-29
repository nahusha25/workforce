import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { DailyWorkEntryPage, getDraftStorageKey, type LocalDailyWorkDraft } from './DailyWorkEntryPage';
import {
  getActivities,
  getWorkOrders,
  getDailyWorkEntries,
  createDailyWorkEntry,
  updateDailyWorkEntry,
  submitDailyWorkEntry,
  uploadWorkPhoto,
  type Activity,
  type WorkOrder,
  type DailyWorkEntry,
  type WorkPhoto,
} from '../api/dailyWork';
import { getAttendanceRecords, type AttendanceRecord } from '../api/attendance';

vi.mock('../utils/imageCompression', () => ({
  compressImage: vi.fn(async (file: File) => file),
}));

// Mock API modules
vi.mock('../api/dailyWork', () => ({
  getActivities: vi.fn(),
  getWorkOrders: vi.fn(),
  getDailyWorkEntries: vi.fn(),
  createDailyWorkEntry: vi.fn(),
  updateDailyWorkEntry: vi.fn(),
  submitDailyWorkEntry: vi.fn(),
  getWorkPhotos: vi.fn().mockResolvedValue([]),
  uploadWorkPhoto: vi.fn(),
  deleteWorkPhoto: vi.fn(),
  getMaterialTransactions: vi.fn().mockResolvedValue([]),
  createMaterialTransaction: vi.fn(),
  deleteMaterialTransaction: vi.fn(),
  getMaterialsCatalogue: vi.fn().mockResolvedValue([
    {
      id: 'mat-1',
      name: 'Cat6 Cable 30m',
      unit_of_measure: 'mtr',
      category: 'cable',
      purchase_approval_limit: 1000,
      is_active: true,
    },
    {
      id: 'mat-2',
      name: 'RJ45 Connectors',
      unit_of_measure: 'pcs',
      category: 'accessories',
      purchase_approval_limit: 500,
      is_active: true,
    },
  ]),
}));

vi.mock('../api/attendance', () => ({
  getAttendanceRecords: vi.fn(),
}));

const today = new Date().toISOString().split('T')[0];

const mockActivities: Activity[] = [
  {
    id: 'act-1',
    name: 'Cable Pulling',
    category: 'cable',
    unit_of_measure: 'metres',
    approved_rate: 15.5,
    is_active: true,
  },
  {
    id: 'act-2',
    name: 'Camera Mounting',
    category: 'device',
    unit_of_measure: 'pcs',
    approved_rate: 45.0,
    is_active: true,
  },
];

const mockWorkOrders: WorkOrder[] = [
  {
    id: 'wo-1',
    order_number: 'WO-2026-001',
    project_id: 'proj-1',
    site_id: 'site-1',
    description: 'Main Building Cabling',
    status: 'active',
    is_active: true,
  },
];

const mockAttendanceCheckedIn: AttendanceRecord[] = [
  {
    id: 'att-1',
    employee_id: 'emp-1',
    employee_name: 'Worker Bob',
    site_id: 'site-1',
    site_name: 'Metro Station Gate 1',
    date: today,
    check_in_time: `${today}T08:00:00Z`,
    check_out_time: null,
    status: 'draft',
    working_hours: null,
    is_within_geofence: true,
  },
];

const renderComponent = (props: any = {}) =>
  render(
    <MemoryRouter>
      <DailyWorkEntryPage {...props} />
    </MemoryRouter>
  );

describe('DailyWorkEntryPage (Multi-Activity Line-Item UX)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    (getActivities as any).mockResolvedValue(mockActivities);
    (getWorkOrders as any).mockResolvedValue(mockWorkOrders);
    (getAttendanceRecords as any).mockResolvedValue(mockAttendanceCheckedIn);
    (getDailyWorkEntries as any).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders loading indicator initially then loads form', async () => {
    renderComponent();
    expect(screen.getByText('Loading work entry form...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Loading work entry form...')).not.toBeInTheDocument();
      expect(screen.getByText('Daily Work Entry')).toBeInTheDocument();
      expect(screen.getByText(/Metro Station Gate 1/i)).toBeInTheDocument();
    });
  });

  it('populates activity and work order dropdowns on initial line', async () => {
    renderComponent();

    await waitFor(() => {
      const activitySelect = screen.getByLabelText(/Activity #1 \*/i) as HTMLSelectElement;
      expect(activitySelect).toBeInTheDocument();
      expect(activitySelect.options.length).toBe(3); // placeholder + 2 activities
      expect(screen.getByText(/Cable Pulling \(CABLE\) - metres/i)).toBeInTheDocument();

      const woSelect = screen.getByLabelText(/Work Order/i) as HTMLSelectElement;
      expect(woSelect).toBeInTheDocument();
      expect(woSelect.options.length).toBe(2); // placeholder + 1 WO
      expect(screen.getByText(/WO-2026-001 - Main Building Cabling/i)).toBeInTheDocument();
    });
  });

  it('disables submit button when quantity is zero and enables when quantity > 0', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Daily Work Entry')).toBeInTheDocument();
    });

    // Zero quantities notice is shown
    expect(
      screen.getByText('* Enter at least one quantity to enable submission.')
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Submit Work/i });
    expect(submitBtn).toBeDisabled();

    // Now enter a measurement distance > 0
    const distInput = screen.getByTestId('measurement-dist-0-0');
    fireEvent.change(distInput, { target: { value: '25.5' } });

    expect(
      screen.queryByText('* Enter at least one quantity to enable submission.')
    ).not.toBeInTheDocument();
    expect(submitBtn).not.toBeDisabled();
  });

  it('saves a new work entry draft successfully with client-side idempotency_key', async () => {
    const mockCreatedEntry: DailyWorkEntry = {
      id: 'entry-uuid-999',
      idempotency_key: 'test-idemp-key',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_date: today,
      quantity: 50.5,
      uom: 'metres',
      status: 'draft',
      remarks: 'First phase completed',
    };
    (createDailyWorkEntry as any).mockResolvedValue(mockCreatedEntry);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('measurement-dist-0-0')).toBeInTheDocument();
    });

    // Enter values
    fireEvent.change(screen.getByTestId('measurement-dist-0-0'), { target: { value: '50.5' } });
    fireEvent.change(screen.getByLabelText(/Remarks & Notes/i), {
      target: { value: 'First phase completed' },
    });

    const saveDraftBtn = screen.getByRole('button', { name: /Save Draft/i });
    fireEvent.click(saveDraftBtn);

    await waitFor(() => {
      expect(createDailyWorkEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          activity_id: 'act-1',
          work_order_id: null,
          quantity: 50.5,
          work_date: today,
          remarks: 'First phase completed',
          idempotency_key: expect.any(String),
        })
      );
      expect(screen.getByText('All activity lines saved successfully!')).toBeInTheDocument();
    });
  });

  it('updates an existing draft when one already exists on server for today', async () => {
    const existingEntry: DailyWorkEntry = {
      id: 'existing-entry-1',
      idempotency_key: 'existing-idemp-1',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-2',
      work_order_id: 'wo-1',
      work_date: today,
      quantity: 4,
      uom: 'pcs',
      status: 'draft',
      remarks: 'Mounting cameras',
    };
    (getDailyWorkEntries as any).mockResolvedValue([existingEntry]);
    (updateDailyWorkEntry as any).mockResolvedValue({
      ...existingEntry,
      quantity: 6,
    });

    renderComponent();

    await waitFor(() => {
      const distInput = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
      expect(distInput.value).toBe('4');
      const remarksInput = screen.getByLabelText(/Remarks & Notes/i) as HTMLTextAreaElement;
      expect(remarksInput.value).toBe('Mounting cameras');
    });

    // Update quantity via measurement distance
    fireEvent.change(screen.getByTestId('measurement-dist-0-0'), { target: { value: '6' } });

    const saveDraftBtn = screen.getByRole('button', { name: /Save Draft/i });
    fireEvent.click(saveDraftBtn);

    await waitFor(() => {
      expect(updateDailyWorkEntry).toHaveBeenCalledWith(
        'existing-entry-1',
        expect.objectContaining({
          activity_id: 'act-2',
          quantity: 6,
          remarks: 'Mounting cameras',
        })
      );
      expect(screen.getByText('All activity lines saved successfully!')).toBeInTheDocument();
    });
  });

  it('adds multiple activity lines and updates auto-derived UOM badges dynamically', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
      expect(screen.getByText('metres')).toBeInTheDocument(); // auto-derived for act-1
    });

    // Click "Add Another Activity Line"
    const addLineBtn = screen.getByRole('button', { name: /Add Another Activity Line/i });
    fireEvent.click(addLineBtn);

    await waitFor(() => {
      expect(screen.getByText('Activity #2')).toBeInTheDocument();
    });

    // Change Activity #2 to Camera Mounting (act-2)
    const activity2Select = screen.getByLabelText(/Activity #2 \*/i);
    fireEvent.change(activity2Select, { target: { value: 'act-2' } });

    await waitFor(() => {
      expect(screen.getByText('pcs')).toBeInTheDocument(); // auto-derived for act-2
    });

    // Enter measurement distances on both lines
    const distInput0 = screen.getByTestId('measurement-dist-0-0');
    const distInput1 = screen.getByTestId('measurement-dist-1-0');
    fireEvent.change(distInput0, { target: { value: '100' } });
    fireEvent.change(distInput1, { target: { value: '8' } });

    expect(screen.getByRole('button', { name: /Submit Work \(2 Lines\)/i })).not.toBeDisabled();
  });

  it('deletes an activity line item when Remove Line is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
    });

    // Add second line
    fireEvent.click(screen.getByRole('button', { name: /Add Another Activity Line/i }));

    await waitFor(() => {
      expect(screen.getByText('Activity #2')).toBeInTheDocument();
    });

    // "Remove Line" button is now visible because line count > 1
    const removeBtns = screen.getAllByRole('button', { name: /Remove Line/i });
    expect(removeBtns.length).toBe(2);

    // Remove the second line
    fireEvent.click(removeBtns[1]);

    await waitFor(() => {
      expect(screen.queryByText('Activity #2')).not.toBeInTheDocument();
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
      // Remove button disappears when only 1 line remains
      expect(screen.queryByRole('button', { name: /Remove Line/i })).not.toBeInTheDocument();
    });
  });

  it('auto-saves draft on attachment attempt and mounts photo & material capture', async () => {
    (createDailyWorkEntry as any).mockResolvedValue({
      id: 'auto-saved-entry-id',
      idempotency_key: 'auto-key',
      activity_id: 'act-1',
      work_date: today,
      quantity: 12,
      uom: 'metres',
      status: 'draft',
      photos: [],
      materials: [],
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('measurement-dist-0-0'), { target: { value: '12' } });

    // Expand attachments
    const toggleBtn = screen.getByRole('button', { name: /Attachments & Materials/i });
    fireEvent.click(toggleBtn);

    // Prompt to auto-save and attach appears
    await waitFor(() => {
      expect(
        screen.getByText('Save this activity line draft first to attach photos and materials.')
      ).toBeInTheDocument();
    });

    const autoSaveBtn = screen.getByRole('button', { name: /Auto-save & Attach/i });
    fireEvent.click(autoSaveBtn);

    await waitFor(() => {
      expect(createDailyWorkEntry).toHaveBeenCalled();
      expect(
        screen.getByText('Activity line saved. You can now add photos and materials.')
      ).toBeInTheDocument();
      // WorkPhotoCapture and MaterialTransactionEntry are now rendered with entry id
      expect(screen.getByRole('button', { name: /Take Photo/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Add Material/i })).toBeInTheDocument();
    });
  });

  it('handles partial save failure per-line with retry capability (Refinement 2)', async () => {
    // Line 1 will succeed, Line 2 will fail
    (createDailyWorkEntry as any)
      .mockResolvedValueOnce({
        id: 'line-1-saved',
        status: 'draft',
      })
      .mockRejectedValueOnce(new Error('Site capacity exceeded for activity 2'));

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
    });

    // Add second line
    fireEvent.click(screen.getByRole('button', { name: /Add Another Activity Line/i }));

    await waitFor(() => {
      expect(screen.getByText('Activity #2')).toBeInTheDocument();
    });

    const distInput0 = screen.getByTestId('measurement-dist-0-0');
    const distInput1 = screen.getByTestId('measurement-dist-1-0');
    fireEvent.change(distInput0, { target: { value: '50' } });
    fireEvent.change(distInput1, { target: { value: '10' } });

    // Click Save Draft
    fireEvent.click(screen.getByRole('button', { name: /Save Draft/i }));

    await waitFor(() => {
      // Global error banner informs user
      expect(
        screen.getByText(
          'Some activity lines could not be saved. Please review and retry the highlighted lines.'
        )
      ).toBeInTheDocument();
      // Specific line error rendered on line #2
      expect(screen.getByTestId('line-error-1')).toBeInTheDocument();
      expect(screen.getByText(/Site capacity exceeded for activity 2/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry Line #2/i })).toBeInTheDocument();
    });

    // Now mock Line 2 success and click retry
    (createDailyWorkEntry as any).mockResolvedValueOnce({
      id: 'line-2-saved',
      status: 'draft',
    });

    fireEvent.click(screen.getByRole('button', { name: /Retry Line #2/i }));

    await waitFor(() => {
      expect(screen.queryByTestId('line-error-1')).not.toBeInTheDocument();
    });
  });

  it('submits multiple activity lines in unified submit flow and displays summary modal', async () => {
    const existingLines: DailyWorkEntry[] = [
      {
        id: 'entry-1',
        idempotency_key: 'k-1',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 50,
        uom: 'metres',
        status: 'draft',
        remarks: 'Cabling done',
        photos: [{ id: 'p-1', daily_work_entry_id: 'entry-1', image_url: '/p1.jpg', uploaded_at: today }],
        materials: [{ id: 'm-1', daily_work_entry_id: 'entry-1', item_name: 'Clamps', quantity: 10, amount: 20, is_high_value: false, status: 'draft', transaction_type: 'consumed', created_at: today }],
      },
      {
        id: 'entry-2',
        idempotency_key: 'k-2',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-2',
        work_order_id: null,
        work_date: today,
        quantity: 5,
        uom: 'pcs',
        status: 'draft',
        remarks: '',
        photos: [],
        materials: [],
      },
    ];

    (getDailyWorkEntries as any).mockResolvedValue(existingLines);
    (updateDailyWorkEntry as any).mockImplementation((id: string, data: any) =>
      Promise.resolve({ id, status: 'draft', ...data })
    );
    (submitDailyWorkEntry as any).mockResolvedValue({
      id: 'entry-1',
      status: 'submitted',
      submitted_at: `${today}T17:00:00Z`,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
      expect(screen.getByText('Activity #2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Submit Work \(2 Lines\)/i })).not.toBeDisabled();
    });

    // Open submit modal
    fireEvent.click(screen.getByRole('button', { name: /Submit Work \(2 Lines\)/i }));

    await waitFor(() => {
      const modal = screen.getByTestId('submit-confirmation-modal');
      expect(modal).toBeInTheDocument();
      expect(within(modal).getByText('Review & Submit Daily Work')).toBeInTheDocument();
      expect(within(modal).getByText('Cable Pulling')).toBeInTheDocument();
      expect(within(modal).getByText('Camera Mounting')).toBeInTheDocument();
      expect(within(modal).getByText('50 metres')).toBeInTheDocument();
      expect(within(modal).getByText('5 pcs')).toBeInTheDocument();
      expect(within(modal).getByText(/1 photo\(s\), 1 transaction\(s\)/i)).toBeInTheDocument();
      expect(within(modal).getByText(/Locking Notice/i)).toBeInTheDocument();
    });

    // Confirm submit
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Submit/i }));

    await waitFor(() => {
      expect(submitDailyWorkEntry).toHaveBeenCalledWith('entry-1');
      expect(submitDailyWorkEntry).toHaveBeenCalledWith('entry-2');
      expect(
        screen.getByText('Work entry submitted successfully! Submitted for supervisor review.')
      ).toBeInTheDocument();
      expect(screen.getByTestId('locked-notice')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Submit Work/i })).not.toBeInTheDocument();
    });
  });

  it('submission confirmation modal shows correct summary and can be cancelled', async () => {
    const existingLines: DailyWorkEntry[] = [
      {
        id: 'entry-cancel-1',
        idempotency_key: 'k-c1',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 35,
        uom: 'metres',
        status: 'draft',
        remarks: 'Morning cabling',
        photos: [{ id: 'p-c1', daily_work_entry_id: 'entry-cancel-1', image_url: '/p1.jpg', uploaded_at: today }],
        materials: [{ id: 'm-c1', daily_work_entry_id: 'entry-cancel-1', item_name: 'Clamps', quantity: 10, amount: 20, is_high_value: false, status: 'draft', transaction_type: 'consumed', created_at: today }],
      },
    ];

    (getDailyWorkEntries as any).mockResolvedValue(existingLines);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Submit Work \(1 Line\)/i })).not.toBeDisabled();
    });

    // Open submit confirmation modal
    fireEvent.click(screen.getByRole('button', { name: /Submit Work \(1 Line\)/i }));

    await waitFor(() => {
      const modal = screen.getByTestId('submit-confirmation-modal');
      expect(modal).toBeInTheDocument();
      expect(within(modal).getByText('Review & Submit Daily Work')).toBeInTheDocument();
      expect(within(modal).getByText('Cable Pulling')).toBeInTheDocument();
      expect(within(modal).getByText('35 metres')).toBeInTheDocument();
      expect(within(modal).getByText(/1 photo\(s\), 1 transaction\(s\)/i)).toBeInTheDocument();
      expect(within(modal).getByText(/Locking Notice/i)).toBeInTheDocument();
    });

    // Click Cancel in modal
    const modal = screen.getByTestId('submit-confirmation-modal');
    const cancelBtn = within(modal).getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    // Modal is dismissed and no submit call is made
    await waitFor(() => {
      expect(screen.queryByTestId('submit-confirmation-modal')).not.toBeInTheDocument();
    });
    expect(submitDailyWorkEntry).not.toHaveBeenCalled();
    // Form remains in editable draft mode
    expect(screen.getByRole('button', { name: /Submit Work \(1 Line\)/i })).toBeInTheDocument();
  });

  it('safely discards old scalar draft shape without crashing or corrupting state (Refinement 3)', async () => {
    // Seed legacy scalar draft shape (with cableRuns, devicesInstalled, etc.)
    const legacyDraft = {
      employeeId: 'emp-1',
      date: today,
      activityId: 'act-1',
      workOrderId: 'wo-1',
      cableRuns: 42,
      cableLengthMetres: 200,
      devicesInstalled: 5,
      drillingQty: 10,
      remarks: 'Old legacy format draft',
      savedAt: Date.now(),
    };
    const key = getDraftStorageKey('emp-1', today);
    localStorage.setItem(key, JSON.stringify(legacyDraft));

    renderComponent({ employeeId: 'emp-1' });

    await waitFor(() => {
      expect(screen.getByText('Daily Work Entry')).toBeInTheDocument();
    });

    // Old draft must be safely discarded from localStorage and NO restore prompt shown
    expect(localStorage.getItem(key)).toBeNull();
    expect(screen.queryByTestId('draft-restore-prompt')).not.toBeInTheDocument();

    // Form initializes normally with 1 blank line
    expect(screen.getByText('Activity #1')).toBeInTheDocument();
    const distInput = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
    expect(distInput.value).toBe('');
    expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('0.00 m');
  });

  it('prompts to restore when valid multi-line draft is available in localStorage', async () => {
    const validDraft: LocalDailyWorkDraft = {
      employeeId: 'emp-1',
      date: today,
      items: [
        {
          idempotencyKey: 'draft-key-1',
          activityId: 'act-1',
          workOrderId: 'wo-1',
          quantity: 75,
          remarks: 'Restored line 1',
        },
        {
          idempotencyKey: 'draft-key-2',
          activityId: 'act-2',
          quantity: 12,
          remarks: 'Restored line 2',
        },
      ],
      savedAt: Date.now(),
    };
    const key = getDraftStorageKey('emp-1', today);
    localStorage.setItem(key, JSON.stringify(validDraft));

    renderComponent({ employeeId: 'emp-1' });

    await waitFor(() => {
      expect(screen.getByTestId('draft-restore-prompt')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('restore-draft-btn'));

    await waitFor(() => {
      expect(screen.getByText('Activity #1')).toBeInTheDocument();
      expect(screen.getByText('Activity #2')).toBeInTheDocument();
      const distInput0 = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
      const distInput1 = screen.getByTestId('measurement-dist-1-0') as HTMLInputElement;
      expect(distInput0.value).toBe('75');
      expect(distInput1.value).toBe('12');
      expect(screen.getByText('Local draft restored.')).toBeInTheDocument();
    });
  });

  it('discards valid draft when user clicks discard button', async () => {
    const validDraft: LocalDailyWorkDraft = {
      employeeId: 'emp-1',
      date: today,
      items: [
        {
          idempotencyKey: 'draft-key-1',
          activityId: 'act-1',
          quantity: 10,
        },
      ],
      savedAt: Date.now(),
    };
    const key = getDraftStorageKey('emp-1', today);
    localStorage.setItem(key, JSON.stringify(validDraft));

    renderComponent({ employeeId: 'emp-1' });

    await waitFor(() => {
      expect(screen.getByTestId('draft-restore-prompt')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('discard-draft-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('draft-restore-prompt')).not.toBeInTheDocument();
      expect(localStorage.getItem(key)).toBeNull();
    });
  });

  it('shows not-checked-in banner when employee has no active check-in', async () => {
    (getAttendanceRecords as any).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('attendance-banner-not-checked-in')).toBeInTheDocument();
      expect(screen.getByText(/You are not checked in today/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Go to Attendance/i })).toBeInTheDocument();
    });
  });

  it('displays accurate photo and material counts in attachments accordion header for submitted entry', async () => {
    const submittedEntry: DailyWorkEntry = {
      id: 'sub-entry-1',
      idempotency_key: 'sub-key-1',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_order_id: 'wo-1',
      work_date: today,
      quantity: 25,
      uom: 'metres',
      status: 'submitted',
      remarks: 'Submitted work',
      photos: [
        {
          id: 'photo-1',
          daily_work_entry_id: 'sub-entry-1',
          image_url: 'http://example.com/p1.jpg',
          uploaded_at: `${today}T10:00:00Z`,
        },
      ],
      materials: [],
    };

    (getDailyWorkEntries as any).mockResolvedValue([submittedEntry]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Attachments & Materials \(1 photos, 0 items\)/i)).toBeInTheDocument();
    });
  });

  it('ensures single photo upload produces exactly one visible photo and correct attachment count', async () => {
    const existingEntry: DailyWorkEntry = {
      id: 'entry-photo-test',
      idempotency_key: 'key-photo-test',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_order_id: 'wo-1',
      work_date: today,
      quantity: 10,
      uom: 'metres',
      status: 'draft',
      remarks: 'Test photo',
      photos: [],
      materials: [],
    };
    (getDailyWorkEntries as any).mockResolvedValue([existingEntry]);

    const uploadedPhoto: WorkPhoto = {
      id: 'photo-unique-1',
      daily_work_entry_id: 'entry-photo-test',
      image_url: 'http://example.com/single.jpg',
      thumbnail_url: 'http://example.com/single_thumb.jpg',
      uploaded_at: `${today}T10:00:00Z`,
    };
    (uploadWorkPhoto as any).mockResolvedValue(uploadedPhoto);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Attachments & Materials \(0 photos, 0 items\)/i)).toBeInTheDocument();
    });

    // Expand attachments
    fireEvent.click(screen.getByRole('button', { name: /Attachments & Materials/i }));

    await waitFor(() => {
      expect(screen.getByLabelText('Select photo from files')).toBeInTheDocument();
    });

    // Select file via browse
    const fileInput = screen.getByLabelText('Select photo from files');
    const testFile = new File(['dummy-bytes'], 'single.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(uploadWorkPhoto).toHaveBeenCalled();
    });

    // Verify attachment count updated to exactly 1
    await waitFor(() => {
      expect(screen.getByText(/Attachments & Materials \(1 photos, 0 items\)/i)).toBeInTheDocument();
    });

    // Verify exactly one photo element is rendered
    const photoThumbs = screen.getAllByAltText('Work site progress');
    expect(photoThumbs).toHaveLength(1);
    expect(photoThumbs[0]).toHaveAttribute('src', uploadedPhoto.thumbnail_url);
  });

  it('deduplicates photos and preserves valid multiple distinct uploads', async () => {
    const duplicatePhoto: WorkPhoto = {
      id: 'photo-dup-1',
      daily_work_entry_id: 'entry-dup-test',
      image_url: 'http://example.com/p1.jpg',
      thumbnail_url: 'http://example.com/p1.jpg',
      uploaded_at: `${today}T10:00:00Z`,
    };
    const distinctPhoto: WorkPhoto = {
      id: 'photo-distinct-2',
      daily_work_entry_id: 'entry-dup-test',
      image_url: 'http://example.com/p2.jpg',
      thumbnail_url: 'http://example.com/p2.jpg',
      uploaded_at: `${today}T10:05:00Z`,
    };

    // Entry with duplicate photo entries from server or state sync
    const entryWithDupes: DailyWorkEntry = {
      id: 'entry-dup-test',
      idempotency_key: 'key-dup-test',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_order_id: 'wo-1',
      work_date: today,
      quantity: 15,
      uom: 'metres',
      status: 'draft',
      remarks: 'Duplicate test',
      photos: [duplicatePhoto, duplicatePhoto, distinctPhoto],
      materials: [],
    };
    (getDailyWorkEntries as any).mockResolvedValue([entryWithDupes]);

    renderComponent();

    // Verify deduplication: 3 raw items with 1 duplicate -> 2 unique photos
    await waitFor(() => {
      expect(screen.getByText(/Attachments & Materials \(2 photos, 0 items\)/i)).toBeInTheDocument();
    });

    // Expand attachments
    fireEvent.click(screen.getByRole('button', { name: /Attachments & Materials/i }));

    await waitFor(() => {
      const photos = screen.getAllByAltText('Work site progress');
      expect(photos).toHaveLength(2);
    });
  });

  it('preserves independent units between work activity quantity and linked material transactions', async () => {
    const entryWithMaterial: DailyWorkEntry = {
      id: 'entry-with-mat',
      idempotency_key: 'idemp-mat-1',
      attendance_record_id: 'att-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_date: today,
      quantity: 50,
      uom: 'metres',
      status: 'draft',
      remarks: 'Cabling work with connectors',
      photos: [],
      materials: [
        {
          id: 'tx-mat-1',
          daily_work_entry_id: 'entry-with-mat',
          material_id: 'mat-2',
          transaction_type: 'consumed',
          item_name: 'RJ45 Connectors',
          quantity: 4,
          amount: 0,
          is_high_value: false,
          status: 'draft',
          created_at: `${today}T10:00:00Z`,
        },
      ],
    };
    (getDailyWorkEntries as any).mockResolvedValue([entryWithMaterial]);

    renderComponent();

    // 1. Verify activity quantity uses its configured unit (metres)
    await waitFor(() => {
      expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('metres');
    });

    // 2. Expand Attachments & Materials
    const attachmentsToggle = screen.getByRole('button', {
      name: /Attachments & Materials \(0 photos, 1 items\)/i,
    });
    fireEvent.click(attachmentsToggle);

    // 3. Verify material transaction displays its catalogue unit (pcs), not the activity unit (metres)
    await waitFor(() => {
      expect(screen.getByText('RJ45 Connectors')).toBeInTheDocument();
      expect(screen.getByTestId('material-tx-uom')).toHaveTextContent('pcs');
    });

    // 4. Change activity to Camera Mounting (pcs)
    const actSelect = screen.getByLabelText(/Activity #1 \*/i);
    fireEvent.change(actSelect, { target: { value: 'act-2' } });

    // Activity UOM badge updates dynamically to pcs
    await waitFor(() => {
      expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('pcs');
    });

    // Material transaction remains independent with pcs
    expect(screen.getByTestId('material-tx-uom')).toHaveTextContent('pcs');
  });

  describe('Multi-Session Daily Work Filtering', () => {
    const session1Attendance: AttendanceRecord = {
      id: 'session-1',
      employee_id: 'emp-1',
      employee_name: 'John',
      site_id: 'site-1',
      site_name: 'Metro Station Gate 1',
      date: today,
      check_in_time: `${today}T07:26:00Z`,
      check_out_time: `${today}T08:18:00Z`,
      status: 'verified',
      working_hours: 0.86,
      is_within_geofence: true,
    };

    const session2Attendance: AttendanceRecord = {
      id: 'session-2',
      employee_id: 'emp-1',
      employee_name: 'John',
      site_id: 'site-1',
      site_name: 'Metro Station Gate 1',
      date: today,
      check_in_time: `${today}T08:37:00Z`,
      check_out_time: `${today}T08:39:00Z`,
      status: 'verified',
      working_hours: 0.03,
      is_within_geofence: true,
    };

    const session3AttendanceActive: AttendanceRecord = {
      id: 'session-3',
      employee_id: 'emp-1',
      employee_name: 'John',
      site_id: 'site-1',
      site_name: 'Metro Station Gate 1',
      date: today,
      check_in_time: `${today}T08:41:00Z`,
      check_out_time: null,
      status: 'draft',
      working_hours: null,
      is_within_geofence: true,
    };

    const approvedSession1Entry: DailyWorkEntry = {
      id: 'dwe-session-1',
      idempotency_key: 'idemp-session-1',
      attendance_record_id: 'session-1',
      employee_id: 'emp-1',
      site_id: 'site-1',
      activity_id: 'act-1',
      work_date: today,
      quantity: 2,
      uom: 'pcs',
      status: 'approved',
      remarks: 'Completed work in morning shift',
      photos: [],
      materials: [],
    };

    it('ensures an approved entry from Session 1 does not lock Session 3 empty form', async () => {
      (getAttendanceRecords as any).mockResolvedValue([
        session1Attendance,
        session2Attendance,
        session3AttendanceActive,
      ]);
      (getDailyWorkEntries as any).mockResolvedValue([approvedSession1Entry]);

      renderComponent();

      // Form should be rendered for Session 3, NOT locked read-only by Session 1
      await waitFor(() => {
        expect(screen.queryByTestId('locked-notice')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Submit Work/i })).toBeInTheDocument();
      });

      // Measurement distance input should be editable and defaulted to empty line
      const distInput = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
      expect(distInput).not.toBeDisabled();
      expect(distInput.value).toBe('');

      // The status badge for the fresh line should be draft, not approved
      expect(screen.getAllByText('draft').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText('approved')).not.toBeInTheDocument();
    });

    it('loads entries belonging to the active session correctly while ignoring other sessions', async () => {
      const draftSession3Entry: DailyWorkEntry = {
        id: 'dwe-session-3',
        idempotency_key: 'idemp-session-3',
        attendance_record_id: 'session-3',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-2',
        work_date: today,
        quantity: 8,
        uom: 'pcs',
        status: 'draft',
        remarks: 'Afternoon work session 3',
        photos: [],
        materials: [],
      };

      (getAttendanceRecords as any).mockResolvedValue([
        session1Attendance,
        session2Attendance,
        session3AttendanceActive,
      ]);
      (getDailyWorkEntries as any).mockResolvedValue([
        approvedSession1Entry,
        draftSession3Entry,
      ]);

      renderComponent();

      // Should load Session 3 entry and NOT Session 1 entry
      await waitFor(() => {
        const remarksInput = screen.getByLabelText(/Remarks & Notes/i) as HTMLTextAreaElement;
        expect(remarksInput.value).toBe('Afternoon work session 3');
      });

      const distInput = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
      expect(distInput.value).toBe('8');
      expect(screen.queryByText('Completed work in morning shift')).not.toBeInTheDocument();
    });

    it('preserves the earlier approved entry unchanged when working in active session', async () => {
      (createDailyWorkEntry as any).mockResolvedValue({
        id: 'new-s3-line',
        attendance_record_id: 'session-3',
        status: 'draft',
      });

      (getAttendanceRecords as any).mockResolvedValue([
        session1Attendance,
        session2Attendance,
        session3AttendanceActive,
      ]);
      (getDailyWorkEntries as any).mockResolvedValue([approvedSession1Entry]);

      renderComponent();

      await waitFor(() => {
        expect(screen.queryByTestId('locked-notice')).not.toBeInTheDocument();
      });

      // Fill in fresh quantity for Session 3 and trigger save
      const distInput = screen.getByTestId('measurement-dist-0-0');
      fireEvent.change(distInput, { target: { value: '15' } });

      const saveDraftBtn = screen.getByRole('button', { name: /Save Draft/i });
      fireEvent.click(saveDraftBtn);

      await waitFor(() => {
        expect(createDailyWorkEntry).toHaveBeenCalled();
      });

      // Verify createDailyWorkEntry was called with the fresh quantity for today
      expect(createDailyWorkEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          quantity: 15,
          work_date: today,
        })
      );

      // Verify updateDailyWorkEntry was NEVER called with the approved entry ID 'dwe-session-1'
      expect(updateDailyWorkEntry).not.toHaveBeenCalledWith(
        'dwe-session-1',
        expect.anything()
      );
    });

    it('associates new daily work submission with the active session without touching past approved entry', async () => {
      const createdSession3Entry: DailyWorkEntry = {
        id: 'new-created-s3',
        idempotency_key: 'idemp-new-s3',
        attendance_record_id: 'session-3',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_date: today,
        quantity: 12,
        uom: 'metres',
        status: 'draft',
        remarks: 'New entry for active session',
        photos: [],
        materials: [],
      };
      (createDailyWorkEntry as any).mockResolvedValue(createdSession3Entry);
      (submitDailyWorkEntry as any).mockResolvedValue({
        id: 'new-created-s3',
        status: 'submitted',
        submitted_at: `${today}T12:00:00Z`,
      });

      (getAttendanceRecords as any).mockResolvedValue([
        session1Attendance,
        session2Attendance,
        session3AttendanceActive,
      ]);
      (getDailyWorkEntries as any).mockResolvedValue([approvedSession1Entry]);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Submit Work/i })).toBeInTheDocument();
      });

      // Enter quantity on the fresh line
      const distInput = screen.getByTestId('measurement-dist-0-0');
      fireEvent.change(distInput, { target: { value: '12' } });

      // Click Submit Work
      const submitBtn = screen.getByRole('button', { name: /Submit Work/i });
      fireEvent.click(submitBtn);

      // Confirm in modal
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Review & Submit Daily Work/i })).toBeInTheDocument();
      });
      const confirmBtn = screen.getByRole('button', { name: /Confirm & Submit/i });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        // createDailyWorkEntry should be called for creating fresh entry
        expect(createDailyWorkEntry).toHaveBeenCalledWith(
          expect.objectContaining({
            work_date: today,
            quantity: 12,
          })
        );
        // submitDailyWorkEntry called for the new entry belonging to session 3, NOT the approved session 1 entry
        expect(submitDailyWorkEntry).toHaveBeenCalledWith('new-created-s3');
        expect(submitDailyWorkEntry).not.toHaveBeenCalledWith('dwe-session-1');
      });
    });
  });

  describe('Point-to-Point Work Measurements Table', () => {
    it('renders initial measurement row with P1, P2 and auto-derived total distance', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Work Measurements (Point-to-Point)')).toBeInTheDocument();
      });

      const startInput = screen.getByTestId('measurement-start-0-0') as HTMLInputElement;
      const endInput = screen.getByTestId('measurement-end-0-0') as HTMLInputElement;
      const distInput = screen.getByTestId('measurement-dist-0-0') as HTMLInputElement;
      const totalSpan = screen.getByTestId('measurement-total-0');

      expect(startInput.value).toBe('P1');
      expect(endInput.value).toBe('P2');
      expect(distInput.value).toBe('');
      expect(totalSpan).toHaveTextContent('0.00 m');
    });

    it('adds and removes measurement rows dynamically and updates total distance', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Work Measurements (Point-to-Point)')).toBeInTheDocument();
      });

      // Fill in row 0: P1 -> P2, 50 m
      fireEvent.change(screen.getByTestId('measurement-dist-0-0'), { target: { value: '50' } });
      expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('50.00 m');

      // Click Add Measurement Row
      fireEvent.click(screen.getByTestId('measurement-add-row-0'));

      await waitFor(() => {
        expect(screen.getByTestId('measurement-dist-0-1')).toBeInTheDocument();
      });

      // Fill in row 1: P2 -> P3, 20 m
      fireEvent.change(screen.getByTestId('measurement-dist-0-1'), { target: { value: '20' } });
      expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('70.00 m');

      // Add third row: P3 -> P4, 30 m
      fireEvent.click(screen.getByTestId('measurement-add-row-0'));
      await waitFor(() => {
        expect(screen.getByTestId('measurement-dist-0-2')).toBeInTheDocument();
      });
      fireEvent.change(screen.getByTestId('measurement-dist-0-2'), { target: { value: '30' } });
      expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('100.00 m');

      // Remove row 1
      fireEvent.click(screen.getByTestId('measurement-remove-0-1'));
      // Total should now be 50 + 30 = 80 m
      expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('80.00 m');
    });

    it('submits measurement rows array in payload', async () => {
      (createDailyWorkEntry as any).mockResolvedValue({
        id: 'new-entry-m',
        status: 'draft',
      });
      (submitDailyWorkEntry as any).mockResolvedValue({
        id: 'new-entry-m',
        status: 'submitted',
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Work Measurements (Point-to-Point)')).toBeInTheDocument();
      });

      fireEvent.change(screen.getByTestId('measurement-dist-0-0'), { target: { value: '45' } });

      fireEvent.click(screen.getByRole('button', { name: /Submit Work/i }));

      await waitFor(() => {
        expect(screen.getByTestId('submit-confirmation-modal')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Confirm & Submit/i }));

      await waitFor(() => {
        expect(createDailyWorkEntry).toHaveBeenCalledWith(
          expect.objectContaining({
            quantity: 45,
            measurements: [
              expect.objectContaining({
                start_point: 'P1',
                end_point: 'P2',
                distance: 45,
              }),
            ],
          })
        );
      });
    });
  });

  describe('Automatic synchronization between measurements and material transactions', () => {
    it('synchronizes measurement total (100m + 50m = 150m) to matching consumed material and displays 150m instead of 1.00m', async () => {
      const entryWithCableMat: DailyWorkEntry = {
        id: 'entry-cable-sync',
        idempotency_key: 'idemp-cable-sync',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 150,
        uom: 'metres',
        status: 'draft',
        remarks: 'Point-to-point cabling',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 100 },
          { start_point: 'P2', end_point: 'P3', distance: 50 },
        ],
        photos: [],
        materials: [
          {
            id: 'tx-cable-1',
            daily_work_entry_id: 'entry-cable-sync',
            material_id: 'mat-1',
            transaction_type: 'consumed',
            item_name: 'Cat6 Cable 30m',
            quantity: 1.0, // Before synchronization it was 1.00
            amount: 0,
            is_high_value: false,
            status: 'draft',
            created_at: `${today}T10:00:00Z`,
          },
        ],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryWithCableMat]);

      renderComponent();

      // Verify measurement total shows 150.00 m
      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('150.00 m');
      });

      // Expand Attachments & Materials
      const attachmentsToggle = await screen.findByTestId('attachments-toggle-0');
      fireEvent.click(attachmentsToggle);

      // Verify matching material quantity is automatically synchronized to 150.00, not 1.00
      await waitFor(() => {
        expect(screen.getByText('Cat6 Cable 30m')).toBeInTheDocument();
        const qtyCell = screen.getByTestId('material-tx-quantity');
        expect(qtyCell).toHaveTextContent('150.00');
        expect(qtyCell).not.toHaveTextContent('1.00');
      });
    });

    it('immediately updates material transaction quantity when measurement rows are edited, added, or removed', async () => {
      const entryWithCableMat: DailyWorkEntry = {
        id: 'entry-cable-sync-edit',
        idempotency_key: 'idemp-cable-sync-edit',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 150,
        uom: 'metres',
        status: 'draft',
        remarks: 'Editing test',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 100 },
          { start_point: 'P2', end_point: 'P3', distance: 50 },
        ],
        photos: [],
        materials: [
          {
            id: 'tx-cable-edit',
            daily_work_entry_id: 'entry-cable-sync-edit',
            material_id: 'mat-1',
            transaction_type: 'consumed',
            item_name: 'Cat6 Cable 30m',
            quantity: 150,
            amount: 0,
            is_high_value: false,
            status: 'draft',
            created_at: `${today}T10:00:00Z`,
          },
        ],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryWithCableMat]);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('150.00 m');
      });

      // Expand attachments
      fireEvent.click(await screen.findByTestId('attachments-toggle-0'));

      await waitFor(() => {
        expect(screen.getByTestId('material-tx-quantity')).toHaveTextContent('150.00');
      });

      // 1. Edit row 1 distance from 100 to 80 (Total becomes 80 + 50 = 130)
      const distInput0 = screen.getByTestId('measurement-dist-0-0');
      fireEvent.change(distInput0, { target: { value: '80' } });

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('130.00 m');
        expect(screen.getByTestId('material-tx-quantity')).toHaveTextContent('130.00');
      });

      // 2. Add measurement row (P3 -> P4 = 20m, Total becomes 130 + 20 = 150)
      fireEvent.click(screen.getByTestId('measurement-add-row-0'));
      await waitFor(() => {
        expect(screen.getByTestId('measurement-dist-0-2')).toBeInTheDocument();
      });
      fireEvent.change(screen.getByTestId('measurement-dist-0-2'), { target: { value: '20' } });

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('150.00 m');
        expect(screen.getByTestId('material-tx-quantity')).toHaveTextContent('150.00');
      });

      // 3. Remove row 1 (P2 -> P3 = 50m, Total becomes 80 + 20 = 100)
      fireEvent.click(screen.getByTestId('measurement-remove-0-1'));

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('100.00 m');
        expect(screen.getByTestId('material-tx-quantity')).toHaveTextContent('100.00');
      });
    });

    it('preserves unrelated consumable and purchased-locally items without modifying their quantities', async () => {
      const entryWithMultipleMats: DailyWorkEntry = {
        id: 'entry-multi-mat',
        idempotency_key: 'idemp-multi-mat',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 150,
        uom: 'metres',
        status: 'draft',
        remarks: 'Multiple materials test',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 100 },
          { start_point: 'P2', end_point: 'P3', distance: 50 },
        ],
        photos: [],
        materials: [
          {
            id: 'tx-cable-sync',
            daily_work_entry_id: 'entry-multi-mat',
            material_id: 'mat-1',
            transaction_type: 'consumed',
            item_name: 'Cat6 Cable 30m',
            quantity: 150,
            amount: 0,
            is_high_value: false,
            status: 'draft',
            created_at: `${today}T10:00:00Z`,
          },
          {
            id: 'tx-rj45-unrelated',
            daily_work_entry_id: 'entry-multi-mat',
            material_id: 'mat-2',
            transaction_type: 'consumed',
            item_name: 'RJ45 Connectors',
            quantity: 10,
            amount: 0,
            is_high_value: false,
            status: 'draft',
            created_at: `${today}T10:00:00Z`,
          },
          {
            id: 'tx-tape-purchased',
            daily_work_entry_id: 'entry-multi-mat',
            transaction_type: 'purchased',
            item_name: 'PVC Insulation Tape',
            quantity: 5,
            amount: 50,
            is_high_value: false,
            status: 'draft',
            created_at: `${today}T10:00:00Z`,
          },
        ],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryWithMultipleMats]);

      renderComponent();

      fireEvent.click(await screen.findByTestId('attachments-toggle-0'));

      // Change measurement row from 100 to 200 (Total becomes 200 + 50 = 250)
      const distInput0 = screen.getByTestId('measurement-dist-0-0');
      fireEvent.change(distInput0, { target: { value: '200' } });

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('250.00 m');
      });

      // Verify: Cable updated to 250.00, RJ45 is STILL 10, PVC Tape is STILL 5
      const txRows = screen.getAllByTestId('material-tx-row');
      expect(txRows).toHaveLength(3);

      const cableRow = txRows.find((r) => within(r).queryByText('Cat6 Cable 30m'));
      const rj45Row = txRows.find((r) => within(r).queryByText('RJ45 Connectors'));
      const tapeRow = txRows.find((r) => within(r).queryByText('PVC Insulation Tape'));

      expect(cableRow).toBeDefined();
      expect(within(cableRow!).getByTestId('material-tx-quantity')).toHaveTextContent('250.00');

      expect(rj45Row).toBeDefined();
      expect(within(rj45Row!).getByTestId('material-tx-quantity')).toHaveTextContent('10.00');

      expect(tapeRow).toBeDefined();
      expect(within(tapeRow!).getByTestId('material-tx-quantity')).toHaveTextContent('5.00');
    });

    it('defaults form quantity to measurement total and displays mapping notice; displays explanation warning when unmapped', async () => {
      const entryCable: DailyWorkEntry = {
        id: 'entry-cable-form',
        idempotency_key: 'idemp-cable-form',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 150,
        uom: 'metres',
        status: 'draft',
        remarks: '',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 100 },
          { start_point: 'P2', end_point: 'P3', distance: 50 },
        ],
        photos: [],
        materials: [],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryCable]);

      renderComponent();

      fireEvent.click(await screen.findByTestId('attachments-toggle-0'));

      // Open Add Material form
      fireEvent.click(await screen.findByTestId('add-material-btn'));

      // Check auto-linked status notice
      await waitFor(() => {
        expect(screen.getByTestId('mapping-status-notice')).toHaveTextContent(
          /Auto-linked to activity: Cable Pulling/i
        );
      });

      // Check quantity input is 150.00, not 1.00
      const qtyInput = screen.getByTestId('material-form-quantity') as HTMLInputElement;
      expect(qtyInput.value).toBe('150.00');

      // Now switch activity to unmapped Camera Mounting (act-2)
      const actSelect = screen.getByLabelText(/Activity #1 \*/i);
      fireEvent.change(actSelect, { target: { value: 'act-2' } });

      // Check warning notice explains missing configuration
      await waitFor(() => {
        expect(screen.getByTestId('mapping-warning-notice')).toHaveTextContent(
          /No active catalogue material found for activity category "device"/i
        );
      });
    });
  });

  describe('Dynamic unit display in point-to-point measurement table', () => {
    it('displays distance unit, total, and help text in metres for a metre activity (e.g. Cat 6 cable laying)', async () => {
      const entryCable: DailyWorkEntry = {
        id: 'entry-cable-unit',
        idempotency_key: 'idemp-cable-unit',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-1',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 100,
        uom: 'metres',
        status: 'draft',
        remarks: '',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 70 },
          { start_point: 'P2', end_point: 'P3', distance: 30 },
        ],
        photos: [],
        materials: [],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryCable]);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('100.00 metres');
        expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('metres');
        expect(screen.getByTestId('measurement-total-label-0')).toHaveTextContent('Total Distance');
        expect(screen.getByTestId('measurement-header-unit-0')).toHaveTextContent('Distance (metres) *');
        expect(screen.getByTestId('measurements-help-0')).toHaveTextContent(
          'Record start/end points and distance in metres. The total distance automatically derives the activity quantity.'
        );
      });
    });

    it('displays quantity unit, total, and help text in pcs for a pcs activity (e.g. CCTV installation)', async () => {
      const entryDevice: DailyWorkEntry = {
        id: 'entry-cctv-unit',
        idempotency_key: 'idemp-cctv-unit',
        attendance_record_id: 'att-1',
        employee_id: 'emp-1',
        site_id: 'site-1',
        activity_id: 'act-2',
        work_order_id: 'wo-1',
        work_date: today,
        quantity: 100,
        uom: 'pcs',
        status: 'draft',
        remarks: '',
        measurements: [
          { start_point: 'P1', end_point: 'P2', distance: 60 },
          { start_point: 'P2', end_point: 'P3', distance: 40 },
        ],
        photos: [],
        materials: [],
      };
      (getDailyWorkEntries as any).mockResolvedValue([entryDevice]);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('100.00 pcs');
        expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('pcs');
        expect(screen.getByTestId('measurement-total-label-0')).toHaveTextContent('Total Quantity');
        expect(screen.getByTestId('measurement-header-unit-0')).toHaveTextContent('Quantity (pcs) *');
        expect(screen.getByTestId('measurements-help-0')).toHaveTextContent(
          'Record start/end points and quantity in pcs. The total quantity automatically derives the activity quantity.'
        );
      });
    });

    it('dynamically switches units between metres and pcs when activity is changed', async () => {
      renderComponent();

      // Default activity is act-1 (Cable Pulling - metres)
      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-label-0')).toHaveTextContent('Total Distance');
        expect(screen.getByTestId('measurement-header-unit-0')).toHaveTextContent('Distance (metres) *');
        expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('metres');
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('0.00 metres');
      });

      // Enter 50 distance
      const distInput = screen.getByTestId('measurement-dist-0-0');
      fireEvent.change(distInput, { target: { value: '50' } });

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('50.00 metres');
      });

      // Switch activity to Camera Mounting (act-2 - pcs)
      const actSelect = screen.getByLabelText(/Activity #1 \*/i);
      fireEvent.change(actSelect, { target: { value: 'act-2' } });

      // Verifies dynamic update to pcs
      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-label-0')).toHaveTextContent('Total Quantity');
        expect(screen.getByTestId('measurement-header-unit-0')).toHaveTextContent('Quantity (pcs) *');
        expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('pcs');
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('50.00 pcs');
        expect(screen.getByTestId('measurements-help-0')).toHaveTextContent(/quantity in pcs/i);
      });

      // Switch back to Cable Pulling (act-1 - metres)
      fireEvent.change(actSelect, { target: { value: 'act-1' } });

      await waitFor(() => {
        expect(screen.getByTestId('measurement-total-label-0')).toHaveTextContent('Total Distance');
        expect(screen.getByTestId('measurement-header-unit-0')).toHaveTextContent('Distance (metres) *');
        expect(screen.getByTestId('activity-uom-badge-0')).toHaveTextContent('metres');
        expect(screen.getByTestId('measurement-total-0')).toHaveTextContent('50.00 metres');
        expect(screen.getByTestId('measurements-help-0')).toHaveTextContent(/distance in metres/i);
      });
    });
  });
});


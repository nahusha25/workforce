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
  type Activity,
  type WorkOrder,
  type DailyWorkEntry,
} from '../api/dailyWork';
import { getAttendanceRecords, type AttendanceRecord } from '../api/attendance';

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

    // Now enter a quantity > 0
    const qtyInput = screen.getByLabelText(/Quantity \*/i);
    fireEvent.change(qtyInput, { target: { value: '25.5' } });

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
      expect(screen.getByLabelText(/Quantity \*/i)).toBeInTheDocument();
    });

    // Enter values
    fireEvent.change(screen.getByLabelText(/Quantity \*/i), { target: { value: '50.5' } });
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
      const qtyInput = screen.getByLabelText(/Quantity \*/i) as HTMLInputElement;
      expect(qtyInput.value).toBe('4');
      const remarksInput = screen.getByLabelText(/Remarks & Notes/i) as HTMLTextAreaElement;
      expect(remarksInput.value).toBe('Mounting cameras');
    });

    // Update quantity
    fireEvent.change(screen.getByLabelText(/Quantity \*/i), { target: { value: '6' } });

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

    // Enter quantities on both lines
    const qtyInputs = screen.getAllByLabelText(/Quantity \*/i);
    expect(qtyInputs.length).toBe(2);
    fireEvent.change(qtyInputs[0], { target: { value: '100' } });
    fireEvent.change(qtyInputs[1], { target: { value: '8' } });

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

    fireEvent.change(screen.getByLabelText(/Quantity \*/i), { target: { value: '12' } });

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

    const qtyInputs = screen.getAllByLabelText(/Quantity \*/i);
    fireEvent.change(qtyInputs[0], { target: { value: '50' } });
    fireEvent.change(qtyInputs[1], { target: { value: '10' } });

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
    const qtyInput = screen.getByLabelText(/Quantity \*/i) as HTMLInputElement;
    expect(qtyInput.value).toBe('0');
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
      const qtyInputs = screen.getAllByLabelText(/Quantity \*/i) as HTMLInputElement[];
      expect(qtyInputs[0].value).toBe('75');
      expect(qtyInputs[1].value).toBe('12');
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
});

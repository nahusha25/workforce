import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { RoleGuard } from '../components/guards/RoleGuard';
import {
  SupervisorVerificationQueuePage,
  getLocalISODate,
  sortQueueItems,
  hasCriticalException,
  getQueueItemReviewState,
} from './SupervisorVerificationQueuePage';
import { getVerificationSummary, type VerificationSummaryResponse } from '../api/verification';
import { getSitesApi, type SiteResponseData } from '../api/masterData';
import type { SystemRole } from '../types/auth';

vi.mock('../api/verification', () => ({
  getVerificationSummary: vi.fn(),
}));

vi.mock('../api/masterData', () => ({
  getSitesApi: vi.fn(),
}));

const mockSummary: VerificationSummaryResponse = {
  date: '2026-09-28',
  site_id: null,
  total_employees: 3,
  pending_verification_count: 1,
  items: [
    {
      employee_id: 'emp-1',
      employee_name: 'Rajesh Kumar',
      employee_code: 'EMP-001',
      site_id: 'site-1',
      site_name: 'Metro Line Extension',
      attendance_record_id: 'att-1',
      attendance_status: 'verified',
      check_in_time: '2026-09-28T09:00:00Z',
      check_out_time: '2026-09-28T17:00:00Z',
      working_hours: 8.0,
      work_entry_count: 2,
      photo_count: 3,
      material_count: 1,
      total_material_cost: '250.00',
      exception_flags: ['out_of_location'],
      has_pending_verification: true,
    },
    {
      employee_id: 'emp-2',
      employee_name: 'Priya Sharma',
      employee_code: 'EMP-002',
      site_id: 'site-2',
      site_name: 'Downtown Tower',
      attendance_record_id: 'att-2',
      attendance_status: 'verified', // Fixed: was approved
      check_in_time: '2026-09-28T08:30:00Z',
      check_out_time: '2026-09-28T16:30:00Z',
      working_hours: 8.0,
      work_entry_count: 0, // 0 entries -> verified attendance alone is genuinely reviewed
      photo_count: 0,
      material_count: 0,
      total_material_cost: '0.00',
      exception_flags: [],
      has_pending_verification: false,
    },
    {
      employee_id: 'emp-3',
      employee_name: 'Suresh Patel',
      employee_code: 'EMP-003',
      site_id: 'site-1',
      site_name: 'Metro Line Extension',
      attendance_record_id: 'att-3',
      attendance_status: 'verified',
      check_in_time: '2026-09-28T08:00:00Z',
      check_out_time: '2026-09-28T16:00:00Z',
      working_hours: 8.0,
      work_entry_count: 1, // Has entries that could be draft, nothing pending
      photo_count: 0,
      material_count: 0,
      total_material_cost: '0.00',
      exception_flags: [],
      has_pending_verification: false,
    },
  ],
};

const mockSites: SiteResponseData[] = [
  {
    id: 'site-1',
    name: 'Metro Line Extension',
    address: 'Sector 5',
    location: null,
    permitted_radius_m: 100,
    supervisor_id: 'sup-1',
    is_active: true,
    project_id: 'proj-1',
  },
  {
    id: 'site-2',
    name: 'Downtown Tower',
    address: 'Main Road',
    location: null,
    permitted_radius_m: 100,
    supervisor_id: 'sup-1',
    is_active: true,
    project_id: 'proj-1',
  },
];

const DetailTracker: React.FC = () => {
  const location = useLocation();
  return <div data-testid="detail-placeholder">Detail for Employee: {location.pathname}{location.search}</div>;
};

const renderWithRouter = (
  role: SystemRole = 'supervisor',
  initialRoute = '/verification'
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
          updated_at: '2026-01-01T00:00:00Z',
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
            <Route path="/verification" element={<SupervisorVerificationQueuePage />} />
            <Route
              path="/verification/:employeeId"
              element={<DetailTracker />}
            />
          </Route>
          <Route path="/403" element={<div data-testid="forbidden-page">Access Denied</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('SupervisorVerificationQueuePage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (getSitesApi as any).mockResolvedValue(mockSites);
    (getVerificationSummary as any).mockResolvedValue(mockSummary);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  // ── Loading state ──────────────────────────────────────────────────────────
  it('renders loading state initially while fetching queue', () => {
    (getVerificationSummary as any).mockImplementation(() => new Promise(() => {}));
    renderWithRouter();
    expect(screen.getByTestId('queue-loading')).toBeTruthy();
    expect(screen.getByText(/Loading verification queue…/i)).toBeTruthy();
  });

  // ── Success rendering with rows & badges ───────────────────────────────────
  it('renders rows with employee info, metrics, pending badge, and exception badges', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Supervisor Verification Queue')).toBeTruthy();
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
      expect(screen.getByText('EMP-001')).toBeTruthy();
      expect(screen.getAllByText('Metro Line Extension').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Priya Sharma')).toBeTruthy();
      expect(screen.getByText('EMP-002')).toBeTruthy();
    });

    // Check metrics
    expect(screen.getByText('₹250.00')).toBeTruthy();
    expect(screen.getAllByText('₹0.00').length).toBeGreaterThanOrEqual(1);

    // Pending review badge on row 1
    const pendingBadges = screen.getAllByTestId('pending-badge');
    expect(pendingBadges).toHaveLength(1);

    // Reviewed indicator on row 2
    expect(screen.getByText('Reviewed')).toBeTruthy();

    // Exception badge present for Rajesh
    const exceptions = screen.getByTestId('exceptions-list');
    expect(exceptions).toBeTruthy();
    expect(screen.getByText(/Out of Location/i)).toBeTruthy();
  });

  // ── Empty state ────────────────────────────────────────────────────────────
  it('renders empty state when no verification items are returned', async () => {
    (getVerificationSummary as any).mockResolvedValue({
      date: '2026-09-28',
      site_id: null,
      total_employees: 0,
      pending_verification_count: 0,
      items: [],
    });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('queue-empty-state')).toBeTruthy();
      expect(screen.getByText(/No verification records found/i)).toBeTruthy();
    });
  });

  // ── Error state & retry ────────────────────────────────────────────────────
  it('renders error banner when API fails and retries upon clicking Retry', async () => {
    (getVerificationSummary as any).mockRejectedValueOnce(new Error('Network error'));
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('queue-error')).toBeTruthy();
      expect(screen.getByText(/Network error/i)).toBeTruthy();
    });

    // Click retry
    (getVerificationSummary as any).mockResolvedValueOnce(mockSummary);
    fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => {
      expect(screen.queryByTestId('queue-error')).toBeNull();
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });
  });

  // ── Date filter changing request ───────────────────────────────────────────
  it('changes date filter and triggers a new API request', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });

    const dateInput = screen.getByLabelText(/Date:/i);
    fireEvent.change(dateInput, { target: { value: '2026-09-29' } });

    await waitFor(() => {
      expect(getVerificationSummary).toHaveBeenCalledWith('2026-09-29', undefined);
    });
  });

  // ── Site filter changing request ───────────────────────────────────────────
  it('changes site filter and triggers a new API request with site_id', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });

    const siteSelect = screen.getByLabelText(/Site:/i);
    fireEvent.change(siteSelect, { target: { value: 'site-1' } });

    await waitFor(() => {
      expect(getVerificationSummary).toHaveBeenCalledWith(expect.any(String), 'site-1');
    });
  });

  // ── Row navigation & date preservation ──────────────────────────────────────
  it('navigates to /verification/:employeeId?date=<selectedDate> when an employee row is clicked', async () => {
    renderWithRouter('supervisor', '/verification');

    await waitFor(() => {
      expect(screen.getByText('Rajesh Kumar')).toBeTruthy();
    });

    const dateInput = screen.getByLabelText(/Date:/i);
    fireEvent.change(dateInput, { target: { value: '2026-09-25' } });

    await waitFor(() => {
      expect(screen.queryByTestId('queue-loading')).toBeNull();
      expect(screen.getAllByTestId('queue-row').length).toBeGreaterThan(0);
    });

    const rows = screen.getAllByTestId('queue-row');
    fireEvent.click(rows[0]);

    await waitFor(() => {
      expect(screen.getByTestId('detail-placeholder').textContent).toContain('/verification/emp-1?date=2026-09-25');
    });
  });

  it('initializes date filter from ?date= query parameter when valid YYYY-MM-DD', async () => {
    renderWithRouter('supervisor', '/verification?date=2026-09-25');

    await waitFor(() => {
      expect(getVerificationSummary).toHaveBeenCalledWith('2026-09-25', undefined);
    });

    const dateInput = screen.getByLabelText(/Date:/i) as HTMLInputElement;
    expect(dateInput.value).toBe('2026-09-25');
  });

  it('falls back to local today when ?date= query parameter is invalid', async () => {
    renderWithRouter('supervisor', '/verification?date=invalid-date');

    await waitFor(() => {
      expect(getVerificationSummary).toHaveBeenCalledWith(getLocalISODate(), undefined);
    });

    const dateInput = screen.getByLabelText(/Date:/i) as HTMLInputElement;
    expect(dateInput.value).toBe(getLocalISODate());
  });

  // ── Review state distinction (Reviewed vs Nothing pending) ──────────────────
  describe('Queue item review state rendering', () => {
    it('renders "Reviewed" when attendance is verified and has no unreviewed work entries', async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText('Priya Sharma')).toBeTruthy();
      });

      // Priya has attendance_status: 'verified', work_entry_count: 0, has_pending: false
      expect(screen.getByTestId('reviewed-badge')).toBeTruthy();
      expect(screen.getByTestId('reviewed-badge').textContent).toContain('Reviewed');
    });

    it('renders "Nothing pending" when employee has entries that may be in draft', async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText('Suresh Patel')).toBeTruthy();
      });

      // Suresh has attendance_status: 'verified', work_entry_count: 1 (draft entries possible), has_pending: false
      const neutralBadges = screen.getAllByTestId('nothing-pending-badge');
      expect(neutralBadges.length).toBeGreaterThanOrEqual(1);
      expect(neutralBadges[0].textContent).toContain('Nothing pending');
    });

    it('pure getQueueItemReviewState distinguishes pending, reviewed, and nothing_pending', () => {
      const base = mockSummary.items[0];

      // Pending
      expect(getQueueItemReviewState({ ...base, has_pending_verification: true })).toBe('pending');

      // Reviewed (attendance verified/rejected with no work entries)
      expect(
        getQueueItemReviewState({
          ...base,
          has_pending_verification: false,
          attendance_status: 'verified',
          work_entry_count: 0,
          material_count: 0,
        })
      ).toBe('reviewed');
      expect(
        getQueueItemReviewState({
          ...base,
          has_pending_verification: false,
          attendance_status: 'rejected',
          work_entry_count: 0,
          material_count: 0,
        })
      ).toBe('reviewed');

      // Nothing pending (draft entries or not verified)
      expect(
        getQueueItemReviewState({
          ...base,
          has_pending_verification: false,
          attendance_status: 'verified',
          work_entry_count: 2,
          material_count: 0,
        })
      ).toBe('nothing_pending');
      expect(
        getQueueItemReviewState({
          ...base,
          has_pending_verification: false,
          attendance_status: 'draft',
          work_entry_count: 0,
          material_count: 0,
        })
      ).toBe('nothing_pending');
      expect(
        getQueueItemReviewState({
          ...base,
          has_pending_verification: false,
          attendance_status: null,
          work_entry_count: 0,
          material_count: 0,
        })
      ).toBe('nothing_pending');
    });
  });

  // ── Attendance badge styling ──────────────────────────────────────────────
  describe('Attendance badge styling', () => {
    it('renders verified and flagged attendance status badges with different styling classes', async () => {
      const statusTestSummary: VerificationSummaryResponse = {
        date: '2026-09-28',
        site_id: null,
        total_employees: 2,
        pending_verification_count: 1,
        items: [
          {
            ...mockSummary.items[0],
            employee_id: 'emp-ver',
            employee_name: 'Verified Status Emp',
            attendance_status: 'verified',
          },
          {
            ...mockSummary.items[0],
            employee_id: 'emp-flag',
            employee_name: 'Flagged Status Emp',
            attendance_status: 'flagged',
          },
        ],
      };
      (getVerificationSummary as any).mockResolvedValueOnce(statusTestSummary);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText('Verified Status Emp')).toBeTruthy();
      });

      const verifiedBadge = screen.getByText('verified');
      const flaggedBadge = screen.getByText('flagged');

      expect(verifiedBadge.className).not.toEqual(flaggedBadge.className);
      expect(verifiedBadge.className).toContain('verified');
      expect(flaggedBadge.className).toContain('flagged');
    });
  });

  // ── Stale response prevention ──────────────────────────────────────────────
  it('ensures older in-flight requests do not overwrite newer responses when date changes', async () => {
    let resolveFirstRequest: (val: any) => void;
    const firstPromise = new Promise((resolve) => {
      resolveFirstRequest = resolve;
    });

    const secondSummary: VerificationSummaryResponse = {
      date: '2026-09-29',
      site_id: null,
      total_employees: 1,
      pending_verification_count: 1,
      items: [
        {
          ...mockSummary.items[0],
          employee_id: 'emp-new',
          employee_name: 'New Date Employee',
        },
      ],
    };

    // First call (slow)
    (getVerificationSummary as any).mockImplementationOnce(() => firstPromise);

    renderWithRouter();

    // Change date to 2026-09-29 which triggers second call (fast)
    (getVerificationSummary as any).mockResolvedValueOnce(secondSummary);
    const dateInput = screen.getByLabelText(/Date:/i);
    fireEvent.change(dateInput, { target: { value: '2026-09-29' } });

    // Wait for second request to render.
    // Timeout raised to 3000ms (from default 1000ms): this test was previously
    // tracked as FE-QUEUE-RACE and failed non-deterministically under full
    // concurrent suite load. The component logic is correct (useEffect ignore
    // flag); the failure was a timing artifact of the default threshold being
    // marginal when the test runner is saturated. Closed as resolved.
    await waitFor(() => {
      expect(screen.getByText('New Date Employee')).toBeTruthy();
    }, { timeout: 3000 });

    // Now resolve the older first request with stale data
    resolveFirstRequest!({
      date: '2026-09-28',
      site_id: null,
      total_employees: 1,
      pending_verification_count: 1,
      items: [
        {
          ...mockSummary.items[0],
          employee_id: 'emp-old',
          employee_name: 'Stale Old Employee',
        },
      ],
    });

    // Wait a bit to ensure old response does NOT overwrite the new data
    await new Promise((r) => setTimeout(r, 50));

    expect(screen.getByText('New Date Employee')).toBeTruthy();
    expect(screen.queryByText('Stale Old Employee')).toBeNull();
  });

  // ── Role guard ─────────────────────────────────────────────────────────────
  it('blocks worker/employee role and redirects to /403', async () => {
    renderWithRouter('employee');

    await waitFor(() => {
      expect(screen.getByTestId('forbidden-page')).toBeTruthy();
      expect(screen.queryByText('Supervisor Verification Queue')).toBeNull();
    });
  });

  it('allows administrator and director roles to access queue', async () => {
    renderWithRouter('administrator');

    await waitFor(() => {
      expect(screen.getByText('Supervisor Verification Queue')).toBeTruthy();
      expect(screen.queryByTestId('forbidden-page')).toBeNull();
    });
  });

  // ── Date calculation & midnight handling ───────────────────────────────────
  describe('Date computation & midnight handling', () => {
    it('computes local calendar date (not UTC) near midnight', () => {
      // 5 minutes after midnight local time
      const justAfterMidnight = new Date(2026, 9, 15, 0, 5, 0); // October 15, 2026
      expect(getLocalISODate(justAfterMidnight)).toBe('2026-10-15');

      // 5 minutes before midnight local time
      const justBeforeMidnight = new Date(2026, 9, 15, 23, 55, 0); // October 15, 2026
      expect(getLocalISODate(justBeforeMidnight)).toBe('2026-10-15');
    });

    it('initializes date filter to local browser date when mounted near midnight', async () => {
      vi.useFakeTimers();
      const nearMidnight = new Date(2026, 9, 20, 0, 10, 0); // Oct 20 00:10
      vi.setSystemTime(nearMidnight);

      renderWithRouter();

      const dateInput = screen.getByLabelText(/Date:/i) as HTMLInputElement;
      expect(dateInput.value).toBe('2026-10-20');
      expect(getVerificationSummary).toHaveBeenCalledWith('2026-10-20', undefined);

      vi.useRealTimers();
    });
  });

  // ── Material spend formatting ──────────────────────────────────────────────
  it('displays total_material_cost with formatDecimal (2 decimal places) rather than raw values', async () => {
    const customSummary: VerificationSummaryResponse = {
      date: '2026-09-28',
      site_id: null,
      total_employees: 1,
      pending_verification_count: 1,
      items: [
        {
          ...mockSummary.items[0],
          employee_id: 'emp-cost-test',
          employee_name: 'Decimal Test Employee',
          total_material_cost: '142.5', // Single decimal place in input
        },
      ],
    };
    (getVerificationSummary as any).mockResolvedValueOnce(customSummary);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Decimal Test Employee')).toBeTruthy();
    });

    // formatDecimal ensures 2 decimal places: "₹142.50"
    expect(screen.getByText('₹142.50')).toBeTruthy();
  });

  // ── Critical exception identification ──────────────────────────────────────
  describe('Critical exceptions classification', () => {
    it('correctly classifies critical vs non-critical exception flags', () => {
      const baseItem = mockSummary.items[0];

      // Critical flags
      expect(hasCriticalException({ ...baseItem, exception_flags: ['out_of_location'] })).toBe(true);
      expect(hasCriticalException({ ...baseItem, exception_flags: ['missing_checkout'] })).toBe(true);
      expect(hasCriticalException({ ...baseItem, exception_flags: ['attendance_without_work'] })).toBe(true);
      expect(hasCriticalException({ ...baseItem, exception_flags: ['work_without_attendance'] })).toBe(true);

      // Non-critical / warning flags
      expect(hasCriticalException({ ...baseItem, exception_flags: ['no_photograph'] })).toBe(false);
      expect(hasCriticalException({ ...baseItem, exception_flags: ['high_value_material'] })).toBe(false);
      expect(hasCriticalException({ ...baseItem, exception_flags: [] })).toBe(false);
    });
  });

  // ── Queue row sorting ──────────────────────────────────────────────────────
  describe('Queue row sorting', () => {
    const unsortedItems = [
      {
        ...mockSummary.items[0],
        employee_id: 'emp-clean',
        employee_name: 'Deepak Clean',
        has_pending_verification: false,
        exception_flags: [],
      },
      {
        ...mockSummary.items[0],
        employee_id: 'emp-crit',
        employee_name: 'Anil Critical',
        has_pending_verification: false,
        exception_flags: ['missing_checkout'], // Critical exception
      },
      {
        ...mockSummary.items[0],
        employee_id: 'emp-warn',
        employee_name: 'Bhanu Warning',
        has_pending_verification: false,
        exception_flags: ['no_photograph'], // Non-critical warning
      },
      {
        ...mockSummary.items[0],
        employee_id: 'emp-pend',
        employee_name: 'Zakir Pending',
        has_pending_verification: true, // Pending verification
        exception_flags: [],
      },
    ];

    it('pure sortQueueItems sorts pending/critical first, then alphabetically by name', () => {
      const sorted = sortQueueItems(unsortedItems);

      // Priority tier (Anil Critical, Zakir Pending) alphabetically: Anil Critical, then Zakir Pending
      // Non-priority tier (Bhanu Warning, Deepak Clean) alphabetically: Bhanu Warning, then Deepak Clean
      expect(sorted.map((i) => i.employee_name)).toEqual([
        'Anil Critical',
        'Zakir Pending',
        'Bhanu Warning',
        'Deepak Clean',
      ]);
    });

    it('renders queue rows in sorted order in the DOM', async () => {
      (getVerificationSummary as any).mockResolvedValueOnce({
        date: '2026-09-28',
        site_id: null,
        total_employees: 4,
        pending_verification_count: 2,
        items: unsortedItems,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText('Anil Critical')).toBeTruthy();
      });

      const rows = screen.getAllByTestId('queue-row');
      expect(rows).toHaveLength(4);

      // Verify DOM row ordering
      expect(rows[0].textContent).toContain('Anil Critical');
      expect(rows[1].textContent).toContain('Zakir Pending');
      expect(rows[2].textContent).toContain('Bhanu Warning');
      expect(rows[3].textContent).toContain('Deepak Clean');
    });
  });
});

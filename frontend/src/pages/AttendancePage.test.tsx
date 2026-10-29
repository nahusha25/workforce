
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AttendancePage, checkSessionDailyWorkStatus } from './AttendancePage';
import { getAttendanceRecords, checkIn, checkOut } from '../api/attendance';
import { getDailyWorkEntries } from '../api/dailyWork';
import * as useGeoMock from '../hooks/useGeolocation';

// Mock child components if needed
vi.mock('../components/ui/Card', () => ({
  Card: ({ children, title, subtitle }: any) => (
    <div data-testid="card">
      <h1>{title}</h1>
      <h2>{subtitle}</h2>
      {children}
    </div>
  )
}));

vi.mock('../components/ui/Button', () => ({
  Button: ({ children, onClick, isLoading, disabled, 'data-testid': testId, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled || isLoading} data-testid={testId || "button"} {...rest}>
      {isLoading ? 'Loading...' : children}
    </button>
  )
}));

// Mock API
vi.mock('../api/attendance', () => ({
  getAttendanceRecords: vi.fn(),
  checkIn: vi.fn(),
  checkOut: vi.fn(),
}));

vi.mock('../api/dailyWork', () => ({
  getDailyWorkEntries: vi.fn(),
}));

import { AuthContext } from '../context/AuthContext';
import type { EmployeeProfile } from '../types/auth';

// Mock Geolocation hook
vi.mock('../hooks/useGeolocation', () => ({
  useGeolocation: vi.fn(),
}));

const mockGetLocation = vi.fn();

const defaultAuthUser: EmployeeProfile = {
  id: 'emp-1',
  user_id: 'user-1',
  employee_code: 'EMP-001',
  mobile_id: '+919123456789',
  name: 'Standard Employee',
  system_role: 'employee',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  trade_roles: [],
  active_sites: [{ id: 'site-1', name: 'Central Station Site' }],
};

const renderComponent = (user: EmployeeProfile | null = defaultAuthUser, initialEntries = ['/attendance']) =>
  render(
    <AuthContext.Provider
      value={{
        user,
        role: user?.system_role || null,
        accessToken: 'mock-token',
        isAuthenticated: !!user,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/attendance" element={<AttendancePage />} />
          <Route path="/daily-work" element={<div data-testid="daily-work-page">Daily Work Page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );

describe('AttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: null,
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });
    
    (getAttendanceRecords as any).mockResolvedValue([]);
    (getDailyWorkEntries as any).mockResolvedValue([
      {
        id: 'dwe-1',
        attendance_record_id: '1',
        work_date: '2026-08-17',
        status: 'submitted',
      },
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders loading state initially while fetching attendance', async () => {
    renderComponent();
    expect(screen.getByText('Loading attendance status...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.queryByText('Loading attendance status...')).not.toBeInTheDocument();
    });
  });

  it('loads check-in state correctly (user is checked out)', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText('Current Status:')).toBeInTheDocument();
      expect(screen.getByText('Checked Out')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /CHECK IN/i })).toBeInTheDocument();
    });
  });

  it('loads check-in state correctly (user is checked in)', async () => {
    const mockRecord = {
      id: '1',
      employee_id: 'e1',
      date: '2026-08-17',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
      site_id: 's1',
    };
    (getAttendanceRecords as any).mockResolvedValue([mockRecord]);

    renderComponent();
    await waitFor(() => {
      expect(screen.getByText('Current Status:')).toBeInTheDocument();
      expect(screen.getByText('Checked In')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });
  });

  it('shows GPS error if geolocation fails', async () => {
    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: null,
      error: 'Location permission denied',
      loading: false,
      getLocation: mockGetLocation,
    });

    renderComponent();
    await waitFor(() => {
      expect(screen.getByText('Location permission denied')).toBeInTheDocument();
      const checkInBtn = screen.getByRole('button', { name: /CHECK IN/i });
      expect(checkInBtn).toBeDisabled();
    });
  });

  it('allows check-in when GPS is ready', async () => {
    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 10, longitude: 20 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });
    
    (checkIn as any).mockResolvedValue({
      id: '2',
      check_in_time: '2026-08-17T09:00:00Z',
      check_out_time: null,
    });

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('GPS Ready')).toBeInTheDocument();
    });

    const checkInBtn = screen.getByRole('button', { name: /CHECK IN/i });
    fireEvent.click(checkInBtn);

    await waitFor(() => {
      expect(checkIn).toHaveBeenCalledWith({ latitude: 10, longitude: 20 });
      expect(screen.getByText('Successfully checked in!')).toBeInTheDocument();
    });
  });

  it('displays API error during check-in', async () => {
    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 10, longitude: 20 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });
    
    (checkIn as any).mockRejectedValue({
      response: {
        status: 422,
        data: { error: { message: 'Outside geofence' } }
      }
    });

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK IN/i })).toBeInTheDocument();
    });

    const checkInBtn = screen.getByRole('button', { name: /CHECK IN/i });
    fireEvent.click(checkInBtn);

    await waitFor(() => {
      expect(screen.getByText('Outside geofence')).toBeInTheDocument();
    });
  });

  it('allows check-out when GPS is ready and user is checked in', async () => {
    // Already checked in
    (getAttendanceRecords as any).mockResolvedValue([{
      id: '1',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 10, longitude: 20 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (checkOut as any).mockResolvedValue({
      status: 'success',
      record_id: '1',
    });

    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(checkOut).toHaveBeenCalledWith({ latitude: 10, longitude: 20 });
      expect(screen.getByText('Successfully checked out!')).toBeInTheDocument();
    });
  });

  it('checkout warning modal appears when daily work has not been submitted and does NOT invoke checkout API', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-warn-1',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (getDailyWorkEntries as any).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(screen.getByTestId('checkout-warning-modal')).toBeInTheDocument();
      expect(screen.getByText('Check-Out Warning')).toBeInTheDocument();
      expect(
        screen.getByText('No daily work entries submitted for this session. Please confirm check-out.')
      ).toBeInTheDocument();
      expect(screen.getByTestId('complete-daily-work-btn')).toBeInTheDocument();
      expect(screen.getByTestId('check-out-anyway-btn')).toBeInTheDocument();
      // Crucial: checkOut API must NOT have been called!
      expect(checkOut).not.toHaveBeenCalled();
      // Should not display success banner while warning modal is open
      expect(screen.queryByText('Successfully checked out!')).not.toBeInTheDocument();
    });
  });

  it('checkout warning modal does NOT appear on a normal checkout when daily work is completed', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-normal-1',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (getDailyWorkEntries as any).mockResolvedValue([
      {
        id: 'dwe-normal-1',
        attendance_record_id: 'rec-normal-1',
        work_date: '2026-08-17',
        status: 'submitted',
      },
    ]);

    (checkOut as any).mockResolvedValue({
      status: 'success',
      record_id: 'rec-normal-1',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(checkOut).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Successfully checked out!')).toBeInTheDocument();
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
    });
  });

  it('clicking "Complete Daily Work" closes modal, navigates to Daily Work, does not call checkout, and preserves session', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-warn-nav',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (getDailyWorkEntries as any).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(screen.getByTestId('checkout-warning-modal')).toBeInTheDocument();
    });

    // Check that checkout API was not called
    expect(checkOut).not.toHaveBeenCalled();

    // Click "Complete Daily Work"
    const completeBtn = screen.getByTestId('complete-daily-work-btn');
    fireEvent.click(completeBtn);

    await waitFor(() => {
      // Modal is closed
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
      // Navigated to /daily-work
      expect(screen.getByTestId('daily-work-page')).toBeInTheDocument();
      // checkout was NEVER called
      expect(checkOut).not.toHaveBeenCalled();
      // No success banner was emitted
      expect(screen.queryByText('Successfully checked out!')).not.toBeInTheDocument();
    });
  });

  it('closing the warning modal does not invoke checkout and preserves active session', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-close-modal',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (getDailyWorkEntries as any).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(screen.getByTestId('checkout-warning-modal')).toBeInTheDocument();
    });

    expect(checkOut).not.toHaveBeenCalled();

    // Click the X close button
    const closeBtn = screen.getByRole('button', { name: /Close modal/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
      expect(checkOut).not.toHaveBeenCalled();
      expect(screen.queryByText('Successfully checked out!')).not.toBeInTheDocument();
      expect(screen.getByText('Checked In')).toBeInTheDocument();
    });
  });

  it('"check out anyway" proceeds successfully and invokes checkout exactly once', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-anyway-1',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    (getDailyWorkEntries as any).mockResolvedValue([
      {
        id: 'dwe-draft-1',
        attendance_record_id: 'rec-anyway-1',
        status: 'draft',
      },
    ]);

    (checkOut as any).mockResolvedValue({
      status: 'success',
      record_id: 'rec-anyway-1',
      requires_confirmation: true,
      warning: 'You have unsubmitted draft work entries. Please confirm check-out.',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    const checkOutBtn = screen.getByRole('button', { name: /CHECK OUT/i });
    fireEvent.click(checkOutBtn);

    await waitFor(() => {
      expect(screen.getByTestId('checkout-warning-modal')).toBeInTheDocument();
    });

    // Check that checkOut was not yet invoked
    expect(checkOut).not.toHaveBeenCalled();

    // Click "Check out anyway"
    const anywayBtn = screen.getByTestId('check-out-anyway-btn');
    fireEvent.click(anywayBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
      expect(checkOut).toHaveBeenCalledTimes(1);
      expect(checkOut).toHaveBeenCalledWith({ latitude: 12.9716, longitude: 77.5946 });
      expect(screen.getByText('Successfully checked out!')).toBeInTheDocument();
      expect(getAttendanceRecords).toHaveBeenCalled();
    });
  });

  it('displays unassigned message and hides check-in button when employee has no active site assignments', async () => {
    const unassignedUser: EmployeeProfile = {
      ...defaultAuthUser,
      active_sites: [],
    };
    renderComponent(unassignedUser);

    await waitFor(() => {
      expect(screen.getByTestId('unassigned-site-message')).toBeInTheDocument();
    });
    expect(
      screen.getByText("You don't have an active site assignment yet — contact your administrator")
    ).toBeInTheDocument();
    expect(screen.queryByTestId('attendance-check-in-btn')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /CHECK IN/i })).not.toBeInTheDocument();
  });

  it('renders check-in button when employee has at least one active site assignment', async () => {
    renderComponent(defaultAuthUser);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-check-in-btn')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /CHECK IN/i })).toBeInTheDocument();
    });
    expect(screen.queryByTestId('unassigned-site-message')).not.toBeInTheDocument();
  });

  it('allows employee to return to attendance and check out normally after completing daily work', async () => {
    (getAttendanceRecords as any).mockResolvedValue([{
      id: 'rec-return-1',
      check_in_time: '2026-08-17T08:00:00Z',
      check_out_time: null,
    }]);

    (useGeoMock.useGeolocation as any).mockReturnValue({
      location: { latitude: 12.9716, longitude: 77.5946 },
      error: null,
      loading: false,
      getLocation: mockGetLocation,
    });

    // Step 1: No daily work entries initially -> warning appears
    (getDailyWorkEntries as any).mockResolvedValue([]);

    const { unmount } = renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /CHECK OUT/i }));

    await waitFor(() => {
      expect(screen.getByTestId('checkout-warning-modal')).toBeInTheDocument();
    });

    expect(checkOut).not.toHaveBeenCalled();

    // Click "Complete Daily Work" -> modal closes, navigates away
    fireEvent.click(screen.getByTestId('complete-daily-work-btn'));

    await waitFor(() => {
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
      expect(screen.getByTestId('daily-work-page')).toBeInTheDocument();
    });

    expect(checkOut).not.toHaveBeenCalled();
    unmount();

    // Step 2: Employee completes daily work and returns to Attendance page
    (getDailyWorkEntries as any).mockResolvedValue([
      {
        id: 'dwe-completed-1',
        attendance_record_id: 'rec-return-1',
        work_date: '2026-08-17',
        status: 'submitted',
      },
    ]);

    (checkOut as any).mockResolvedValue({
      status: 'success',
      record_id: 'rec-return-1',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /CHECK OUT/i })).toBeInTheDocument();
    });

    // Employee clicks CHECK OUT now -> normal checkout without warning modal
    fireEvent.click(screen.getByRole('button', { name: /CHECK OUT/i }));

    await waitFor(() => {
      expect(checkOut).toHaveBeenCalledTimes(1);
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
      expect(screen.getByText('Successfully checked out!')).toBeInTheDocument();
    });
  });
});

describe('checkSessionDailyWorkStatus helper', () => {
  it('returns requiresConfirmation true when no entries exist', () => {
    const result = checkSessionDailyWorkStatus([], 'att-1', '2026-10-14');
    expect(result.requiresConfirmation).toBe(true);
    expect(result.warning).toContain('No daily work entries submitted for this session');
  });

  it('returns requiresConfirmation true when draft entries exist for the session', () => {
    const result = checkSessionDailyWorkStatus([
      {
        id: 'dwe-1',
        attendance_record_id: 'att-1',
        work_date: '2026-10-14',
        status: 'draft',
      } as any,
    ], 'att-1');
    expect(result.requiresConfirmation).toBe(true);
    expect(result.warning).toContain('unsubmitted draft work entries');
  });

  it('returns requiresConfirmation false when entries are submitted', () => {
    const result = checkSessionDailyWorkStatus([
      {
        id: 'dwe-1',
        attendance_record_id: 'att-1',
        work_date: '2026-10-14',
        status: 'submitted',
      } as any,
    ], 'att-1');
    expect(result.requiresConfirmation).toBe(false);
    expect(result.warning).toBeUndefined();
  });

  it('filters entries by attendance_record_id correctly', () => {
    // Only entries from other attendance sessions exist
    const result = checkSessionDailyWorkStatus([
      {
        id: 'dwe-other',
        attendance_record_id: 'att-other',
        work_date: '2026-10-14',
        status: 'submitted',
      } as any,
    ], 'att-current');
    expect(result.requiresConfirmation).toBe(true);
    expect(result.warning).toContain('No daily work entries submitted for this session');
  });
});

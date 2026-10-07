
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { AttendancePage } from './AttendancePage';
import { getAttendanceRecords, checkIn, checkOut } from '../api/attendance';
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

const renderComponent = (user: EmployeeProfile | null = defaultAuthUser) =>
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
      <MemoryRouter>
        <AttendancePage />
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

  it('checkout warning modal appears when requires_confirmation is true', async () => {
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

    (checkOut as any).mockResolvedValue({
      status: 'success',
      record_id: 'rec-warn-1',
      requires_confirmation: true,
      warning: 'No daily work entries submitted for this session. Please confirm check-out.',
    });

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
      expect(screen.getByRole('button', { name: /Complete Daily Work/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Check out anyway/i })).toBeInTheDocument();
      // Should not immediately display success banner while warning modal is open
      expect(screen.queryByText('Successfully checked out!')).not.toBeInTheDocument();
    });
  });

  it('checkout warning modal does NOT appear on a normal checkout', async () => {
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

    // Normal checkout with no requires_confirmation flag
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
      expect(screen.getByText('Successfully checked out!')).toBeInTheDocument();
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
    });
  });

  it('"check out anyway" proceeds successfully', async () => {
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

    // Click "Check out anyway"
    const anywayBtn = screen.getByRole('button', { name: /Check out anyway/i });
    fireEvent.click(anywayBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('checkout-warning-modal')).not.toBeInTheDocument();
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
});

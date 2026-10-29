import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { SupervisorAttendancePage } from './SupervisorAttendancePage';
import { getAttendanceRecords, overrideAttendance, type AttendanceRecord } from '../api/attendance';

// Mock API
vi.mock('../api/attendance', () => ({
  getAttendanceRecords: vi.fn(),
  overrideAttendance: vi.fn(),
}));

const today = new Date().toISOString().split('T')[0];

const mockRecords: AttendanceRecord[] = [
  {
    id: 'rec-1',
    employee_id: 'emp-uuid-1111',
    employee_name: 'Alice Worker',
    site_id: 'site-uuid-1',
    site_name: 'Alpha Site',
    date: today,
    check_in_time: `${today}T08:00:00Z`,
    check_out_time: `${today}T17:00:00Z`,
    status: 'draft',
    working_hours: 9.0,
    is_within_geofence: true,
  },
  {
    id: 'rec-2',
    employee_id: 'emp-uuid-2222',
    employee_name: 'Bob Builder',
    site_id: 'site-uuid-1',
    site_name: 'Alpha Site',
    date: today,
    check_in_time: `${today}T08:30:00Z`,
    check_out_time: null,
    status: 'flagged',
    working_hours: null,
    is_within_geofence: false,
  },
  {
    id: 'rec-3',
    employee_id: 'emp-uuid-3333',
    employee_name: null,
    site_id: 'site-uuid-2',
    site_name: 'Beta Site',
    date: today,
    check_in_time: `${today}T09:00:00Z`,
    check_out_time: null,
    status: 'approved',
    working_hours: null,
    is_within_geofence: false,
  },
];

describe('SupervisorAttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getAttendanceRecords as any).mockResolvedValue(mockRecords);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders loading indicator initially then displays records', async () => {
    render(<SupervisorAttendancePage />);
    expect(screen.getByText('Loading team attendance records...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Team Attendance Review')).toBeInTheDocument();
      expect(screen.getByText('Alice Worker')).toBeInTheDocument();
      expect(screen.getByText('Bob Builder')).toBeInTheDocument();
      // rec-3 has null employee_name, falls back to employee_id
      expect(screen.getByText('emp-uuid-3333')).toBeInTheDocument();
      // rec-1 working_hours: 9.0 formatted as "9 hrs"
      expect(screen.getByText('9 hrs')).toBeInTheDocument();
    });
  });

  it('shows Override button only for flagged records', async () => {
    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('Team Attendance Review')).toBeInTheDocument();
    });

    const overrideButtons = screen.getAllByRole('button', { name: /override/i });
    expect(overrideButtons).toHaveLength(1);
  });

  it('filters records when clicking Flagged Only', async () => {
    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('All (3)')).toBeInTheDocument();
      expect(screen.getByText('Flagged Only (1)')).toBeInTheDocument();
    });

    // Click Flagged Only
    const flaggedFilterBtn = screen.getByText('Flagged Only (1)');
    fireEvent.click(flaggedFilterBtn);

    // Only rec-2 should be in table
    expect(screen.getByText('Outside')).toBeInTheDocument();
    expect(screen.queryByText('Within')).not.toBeInTheDocument();
  });

  it('shows empty state when no records are returned', async () => {
    (getAttendanceRecords as any).mockResolvedValue([]);
    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('No attendance records found')).toBeInTheDocument();
    });
  });

  it('opens override modal and enforces mandatory reason > 10 characters', async () => {
    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /override/i })).toBeInTheDocument();
    });

    // Click Override button
    const overrideBtn = screen.getByRole('button', { name: /override/i });
    fireEvent.click(overrideBtn);

    // Modal should be open
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText('Authorize Geofence Override')).toBeInTheDocument();
    expect(within(dialog).getByText('Flagged (Outside Geofence)')).toBeInTheDocument();
    expect(within(dialog).getByText('Bob Builder')).toBeInTheDocument();
    expect(within(dialog).getByText('Alpha Site')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/Provide a specific explanation/i);
    const submitBtn = screen.getByRole('button', { name: /Submit Override/i });

    // Initially disabled because reason is empty
    expect(submitBtn).toBeDisabled();

    // Type 10 characters (not enough)
    fireEvent.change(textarea, { target: { value: 'Short 1234' } }); // 10 chars
    expect(submitBtn).toBeDisabled();
    expect(screen.getByText(/Need 1 more characters/i)).toBeInTheDocument();

    // Type valid reason (>10 chars)
    fireEvent.change(textarea, {
      target: { value: 'Approved by supervisor due to verified GPS drift at site perimeter' },
    });
    expect(submitBtn).not.toBeDisabled();
  });

  it('successfully submits override and refreshes records', async () => {
    (overrideAttendance as any).mockResolvedValue({ status: 'success', record_id: 'rec-2' });

    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /override/i })).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /override/i }));

    const textarea = screen.getByPlaceholderText(/Provide a specific explanation/i);
    fireEvent.change(textarea, {
      target: { value: 'Authorized exception due to adjacent workstation location' },
    });

    const submitBtn = screen.getByRole('button', { name: /Submit Override/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(overrideAttendance).toHaveBeenCalledWith('rec-2', {
        override_reason: 'Authorized exception due to adjacent workstation location',
      });
      // Modal should be closed
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      // Success message displayed
      expect(screen.getByText(/Successfully overridden attendance record for Bob Builder/i)).toBeInTheDocument();
      // getAttendanceRecords called again for refresh
      expect(getAttendanceRecords).toHaveBeenCalledTimes(2);
    });
  });

  it('can close override modal without submitting', async () => {
    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /override/i })).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /override/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Click Cancel
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    // Modal closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(overrideAttendance).not.toHaveBeenCalled();
  });

  it('displays actual distance and coordinates for flagged records in the table', async () => {
    const customRecords: AttendanceRecord[] = [
      {
        id: 'rec-flagged-gps',
        employee_id: 'emp-uuid-5555',
        employee_name: 'Charlie Field',
        site_id: 'site-uuid-1',
        site_name: 'Metro Station Site',
        date: today,
        check_in_time: `${today}T08:15:00Z`,
        check_out_time: null,
        status: 'flagged',
        working_hours: null,
        is_within_geofence: false,
        check_in_latitude: 12.98000,
        check_in_longitude: 77.52000,
        check_in_distance_m: 1250,
      },
    ];
    (getAttendanceRecords as any).mockResolvedValue(customRecords);

    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('Charlie Field')).toBeInTheDocument();
    });

    expect(screen.getByText('Outside')).toBeInTheDocument();
    expect(screen.getByText('1.25 km (1,250 m) from site')).toBeInTheDocument();
    expect(screen.getByText('12.9800°, 77.5200°')).toBeInTheDocument();
  });

  it('prominently displays reported location, distance, and safe OpenStreetMap link in override modal', async () => {
    const customRecords: AttendanceRecord[] = [
      {
        id: 'rec-flagged-osm',
        employee_id: 'emp-uuid-5555',
        employee_name: 'Charlie Field',
        site_id: 'site-uuid-1',
        site_name: 'Metro Station Site',
        site_latitude: 12.96630,
        site_longitude: 77.50960,
        site_permitted_radius_m: 100,
        date: today,
        check_in_time: `${today}T08:15:00Z`,
        check_out_time: null,
        status: 'flagged',
        working_hours: null,
        is_within_geofence: false,
        check_in_latitude: 12.98000,
        check_in_longitude: 77.52000,
        check_in_distance_m: 1250,
      },
    ];
    (getAttendanceRecords as any).mockResolvedValue(customRecords);

    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /override/i })).toBeInTheDocument();
    });

    // Open Override Modal
    fireEvent.click(screen.getByRole('button', { name: /override/i }));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();

    // Verify Reported Check-In Location card
    expect(within(dialog).getByText('Reported Check-In Location')).toBeInTheDocument();
    expect(within(dialog).getByText(/12.980000° N, 77.520000° E/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1.25 km \(1,250 m\) from site/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1,150m outside permitted 100m radius/)).toBeInTheDocument();

    // Verify OpenStreetMap link
    const osmLink = within(dialog).getByRole('link', { name: /View on OpenStreetMap/i });
    expect(osmLink).toBeInTheDocument();
    expect(osmLink).toHaveAttribute('href', 'https://www.openstreetmap.org/?mlat=12.98&mlon=77.52#map=17/12.98/77.52');
    expect(osmLink).toHaveAttribute('target', '_blank');
    expect(osmLink).toHaveAttribute('rel', 'noopener noreferrer');

    // Verify Registered Site Location card
    expect(within(dialog).getByText('Registered Site Location')).toBeInTheDocument();
    expect(within(dialog).getByText(/12.966300° N, 77.509600° E/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Permitted Radius:/)).toBeInTheDocument();
    expect(within(dialog).getByText(/100 m/)).toBeInTheDocument();
  });

  it('handles missing coordinates gracefully with fallback text in table and modal', async () => {
    const customRecords: AttendanceRecord[] = [
      {
        id: 'rec-missing-coords',
        employee_id: 'emp-uuid-6666',
        employee_name: 'No GPS Worker',
        site_id: 'site-uuid-2',
        site_name: 'Remote Substation',
        site_latitude: null,
        site_longitude: null,
        site_permitted_radius_m: null,
        date: today,
        check_in_time: `${today}T08:30:00Z`,
        check_out_time: null,
        status: 'flagged',
        working_hours: null,
        is_within_geofence: false,
        check_in_latitude: null,
        check_in_longitude: null,
        check_in_distance_m: null,
      },
    ];
    (getAttendanceRecords as any).mockResolvedValue(customRecords);

    render(<SupervisorAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('No GPS Worker')).toBeInTheDocument();
    });

    // In Table: should display fallback "No GPS coords"
    expect(screen.getByText('No GPS coords')).toBeInTheDocument();

    // Open Override Modal
    fireEvent.click(screen.getByRole('button', { name: /override/i }));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();

    // Fallback notice displayed in modal
    expect(within(dialog).getByText('Actual check-in coordinates are unavailable for this record.')).toBeInTheDocument();
    expect(within(dialog).getByText('Site coordinates are not configured for this location.')).toBeInTheDocument();

    // No OpenStreetMap link rendered when coordinates are missing
    expect(within(dialog).queryByRole('link', { name: /View on OpenStreetMap/i })).not.toBeInTheDocument();
  });
});

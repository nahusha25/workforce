import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { BottomNav } from './BottomNav';
import { AuthContext } from '../../context/AuthContext';
import type { EmployeeProfile, SystemRole } from '../../types/auth';

const createMockUser = (
  role: SystemRole,
  activeSites: Array<{ id: string; name: string }> = []
): EmployeeProfile => ({
  id: 'emp-1',
  user_id: 'user-1',
  employee_code: 'EMP-001',
  mobile_id: '+919123456789',
  name: 'Test User',
  system_role: role,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  trade_roles: [],
  active_sites: activeSites,
});

const renderNavWithRole = (
  role: SystemRole,
  activeSites: Array<{ id: string; name: string }> = []
) => {
  const user = createMockUser(role, activeSites);
  return render(
    <AuthContext.Provider
      value={{
        user,
        role,
        accessToken: 'mock-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter>
        <div>
          <Sidebar />
          <BottomNav />
        </div>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('Navigation Attendance Link Visibility', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows "My Attendance" in Sidebar and "Attendance" in BottomNav for employee with active site assignments', () => {
    renderNavWithRole('employee', [{ id: 'site-1', name: 'Central Station Site' }]);

    // Sidebar link
    expect(screen.getByRole('link', { name: 'My Attendance' })).toBeInTheDocument();
    // BottomNav link
    expect(screen.getByRole('link', { name: 'Attendance' })).toBeInTheDocument();
  });

  it('shows "My Attendance" and "Attendance" nav links for employee without active site assignments', () => {
    renderNavWithRole('employee', []);

    // Visible so employee can navigate and see the contact admin unassigned notice
    expect(screen.getByRole('link', { name: 'My Attendance' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Attendance' })).toBeInTheDocument();
  });

  it('hides attendance nav links from administrator role', () => {
    renderNavWithRole('administrator', [{ id: 'site-1', name: 'Central Station Site' }]);

    expect(screen.queryByRole('link', { name: 'My Attendance' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Attendance' })).not.toBeInTheDocument();
  });

  it('hides attendance nav links from director role', () => {
    renderNavWithRole('director', [{ id: 'site-1', name: 'Central Station Site' }]);

    expect(screen.queryByRole('link', { name: 'My Attendance' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Attendance' })).not.toBeInTheDocument();
  });

  it('hides attendance nav links from supervisor role', () => {
    renderNavWithRole('supervisor', [{ id: 'site-1', name: 'Central Station Site' }]);

    expect(screen.queryByRole('link', { name: 'My Attendance' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Attendance' })).not.toBeInTheDocument();
  });
});

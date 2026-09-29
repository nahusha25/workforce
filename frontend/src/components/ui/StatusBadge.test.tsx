import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { StatusBadge, mapAttendanceStatusToBadge } from './StatusBadge';

// ── mapAttendanceStatusToBadge unit tests ─────────────────────────────────────

describe('mapAttendanceStatusToBadge', () => {
  it("maps 'submitted' to 'submitted'", () => {
    expect(mapAttendanceStatusToBadge('submitted')).toBe('submitted');
  });

  it("maps 'draft' to 'draft'", () => {
    expect(mapAttendanceStatusToBadge('draft')).toBe('draft');
  });

  it("maps 'flagged' to 'flagged'", () => {
    expect(mapAttendanceStatusToBadge('flagged')).toBe('flagged');
  });

  it("maps 'verified' to 'verified'", () => {
    expect(mapAttendanceStatusToBadge('verified')).toBe('verified');
  });

  it("maps 'rejected' to 'rejected'", () => {
    expect(mapAttendanceStatusToBadge('rejected')).toBe('rejected');
  });

  it("maps 'correction_required' to 'correction_required'", () => {
    expect(mapAttendanceStatusToBadge('correction_required')).toBe('correction_required');
  });

  describe('unrecognized status — does NOT silently render as "Draft"', () => {
    let warnSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
      warnSpy.mockRestore();
    });

    it('returns the raw unknown status string instead of "draft"', () => {
      const result = mapAttendanceStatusToBadge('unknown_future_status');
      expect(result).toBe('unknown_future_status');
      expect(result).not.toBe('draft');
    });

    it('emits a console.warn for unrecognized statuses', () => {
      mapAttendanceStatusToBadge('totally_new_status');
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unrecognized attendance status'),
      );
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('totally_new_status'),
      );
    });

    it('handles null gracefully without throwing', () => {
      expect(() => mapAttendanceStatusToBadge(null)).not.toThrow();
    });

    it('handles undefined gracefully without throwing', () => {
      expect(() => mapAttendanceStatusToBadge(undefined)).not.toThrow();
    });
  });
});

// ── <StatusBadge> render tests ────────────────────────────────────────────────

describe('StatusBadge', () => {
  afterEach(cleanup);

  it('renders "submitted" status with correct label (not "draft")', () => {
    render(<StatusBadge status="submitted" />);
    // The badge renders the raw status string as label
    expect(screen.getByText('submitted')).toBeInTheDocument();
    expect(screen.queryByText('draft')).not.toBeInTheDocument();
  });

  it('renders "submitted" status with the .submitted CSS class', () => {
    const { container } = render(<StatusBadge status="submitted" />);
    const badge = container.querySelector('span');
    // The CSS module normalizes to submitted → class includes 'submitted'
    expect(badge?.className).toMatch(/submitted/);
  });

  it('renders a custom label when provided', () => {
    render(<StatusBadge status="submitted" label="Awaiting Review" />);
    expect(screen.getByText('Awaiting Review')).toBeInTheDocument();
  });

  it('renders "draft" correctly', () => {
    render(<StatusBadge status="draft" />);
    expect(screen.getByText('draft')).toBeInTheDocument();
  });

  it('renders "verified" correctly', () => {
    render(<StatusBadge status="verified" />);
    expect(screen.getByText('verified')).toBeInTheDocument();
  });
});

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ExceptionBadge } from '../../components/ui/ExceptionBadge';

afterEach(cleanup);

describe('ExceptionBadge', () => {
  it('renders the correct label for out_of_location', () => {
    render(<ExceptionBadge flag="out_of_location" />);
    expect(screen.getByText('Out of Location')).toBeTruthy();
  });

  it('renders the correct label for missing_checkout', () => {
    render(<ExceptionBadge flag="missing_checkout" />);
    expect(screen.getByText('Missing Check-out')).toBeTruthy();
  });

  it('renders the correct label for attendance_without_work', () => {
    render(<ExceptionBadge flag="attendance_without_work" />);
    expect(screen.getByText('No Work Logged')).toBeTruthy();
  });

  it('renders the correct label for work_without_attendance', () => {
    render(<ExceptionBadge flag="work_without_attendance" />);
    expect(screen.getByText('Work Without Attendance')).toBeTruthy();
  });

  it('renders the correct label for no_photograph', () => {
    render(<ExceptionBadge flag="no_photograph" />);
    expect(screen.getByText('No Photo')).toBeTruthy();
  });

  it('renders the correct label for high_value_material', () => {
    render(<ExceptionBadge flag="high_value_material" />);
    expect(screen.getByText('High-Value Material')).toBeTruthy();
  });

  it('accepts an override label prop', () => {
    render(<ExceptionBadge flag="out_of_location" label="Custom Label" />);
    expect(screen.getByText('Custom Label')).toBeTruthy();
  });

  it('marks critical flags with data-severity="critical"', () => {
    const { container } = render(<ExceptionBadge flag="out_of_location" />);
    const badge = container.querySelector('[data-severity="critical"]');
    expect(badge).toBeTruthy();
  });

  it('marks warning flags with data-severity="warning"', () => {
    const { container } = render(<ExceptionBadge flag="no_photograph" />);
    const badge = container.querySelector('[data-severity="warning"]');
    expect(badge).toBeTruthy();
  });

  it('all four critical flags carry data-severity="critical"', () => {
    const criticals = [
      'out_of_location',
      'missing_checkout',
      'attendance_without_work',
      'work_without_attendance',
    ] as const;

    criticals.forEach((flag) => {
      const { container, unmount } = render(<ExceptionBadge flag={flag} />);
      const badge = container.querySelector('[data-severity="critical"]');
      expect(badge, `${flag} should be critical`).toBeTruthy();
      unmount();
    });
  });

  it('both warning flags carry data-severity="warning"', () => {
    const warnings = ['no_photograph', 'high_value_material'] as const;

    warnings.forEach((flag) => {
      const { container, unmount } = render(<ExceptionBadge flag={flag} />);
      const badge = container.querySelector('[data-severity="warning"]');
      expect(badge, `${flag} should be warning`).toBeTruthy();
      unmount();
    });
  });

  it('renders unknown flags without crashing, defaulting to warning severity', () => {
    const { container } = render(<ExceptionBadge flag="some_future_flag" />);
    // Falls through to default: flag text used as label, warning severity
    const badge = container.querySelector('[data-flag="some_future_flag"]');
    expect(badge).toBeTruthy();
    expect(badge?.getAttribute('data-severity')).toBe('warning');
  });

  it('sets an accessible title attribute', () => {
    const { container } = render(<ExceptionBadge flag="missing_checkout" />);
    const badge = container.querySelector('[data-flag="missing_checkout"]');
    expect(badge?.getAttribute('title')).toContain('Exception:');
  });
});

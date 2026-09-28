import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { AuditHistoryTimeline, type VerificationEvent } from '../../components/verification/AuditHistoryTimeline';

afterEach(cleanup);

const baseEvent = (overrides: Partial<VerificationEvent> = {}): VerificationEvent => ({
  id: 'evt-1',
  action: 'approved',
  entityLabel: 'Attendance',
  verified_by: '00000000-0000-0000-0000-000000000001',
  verified_by_name: 'Ravi Kumar',
  verified_at: '2024-09-28T14:30:00Z',
  remarks: null,
  ...overrides,
});

describe('AuditHistoryTimeline', () => {
  // ── Empty state ────────────────────────────────────────────────────────────

  it('renders the empty state when events array is empty', () => {
    render(<AuditHistoryTimeline events={[]} />);
    expect(screen.getByTestId('audit-timeline-empty')).toBeTruthy();
    expect(screen.getByText(/No verification actions recorded yet/i)).toBeTruthy();
  });

  it('does NOT render the empty state when events are present', () => {
    render(<AuditHistoryTimeline events={[baseEvent()]} />);
    expect(screen.queryByTestId('audit-timeline-empty')).toBeNull();
  });

  // ── Loading state ──────────────────────────────────────────────────────────

  it('renders a loading indicator when isLoading=true', () => {
    render(<AuditHistoryTimeline events={[]} isLoading={true} />);
    expect(screen.getByText(/Loading history/i)).toBeTruthy();
    // empty-state sentinel must NOT appear
    expect(screen.queryByTestId('audit-timeline-empty')).toBeNull();
  });

  // ── Event rendering ────────────────────────────────────────────────────────

  it('renders the entity label', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ entityLabel: 'Daily Work Entry' })]} />);
    expect(screen.getByText('Daily Work Entry')).toBeTruthy();
  });

  it('renders "Approved" action label', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ action: 'approved' })]} />);
    expect(screen.getByText('Approved')).toBeTruthy();
  });

  it('renders "Rejected" action label', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ action: 'rejected' })]} />);
    expect(screen.getByText('Rejected')).toBeTruthy();
  });

  it('renders "Returned for Correction" action label', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ action: 'correction_required' })]} />);
    expect(screen.getByText('Returned for Correction')).toBeTruthy();
  });

  it('renders actor name when provided', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ verified_by_name: 'Suresh Rao' })]} />);
    expect(screen.getByText(/Suresh Rao/)).toBeTruthy();
  });

  it('does not render actor section when verified_by_name is null', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ verified_by_name: null })]} />);
    expect(screen.queryByText(/by /)).toBeNull();
  });

  it('renders remarks blockquote when remarks are present', () => {
    render(
      <AuditHistoryTimeline
        events={[baseEvent({ remarks: 'Location mismatch at site boundary' })]}
      />,
    );
    expect(screen.getByText('Location mismatch at site boundary')).toBeTruthy();
  });

  it('does not render remarks blockquote when remarks are null', () => {
    render(<AuditHistoryTimeline events={[baseEvent({ remarks: null })]} />);
    // No blockquote text content visible
    expect(screen.queryByRole('blockquote')).toBeNull();
  });

  it('renders a <time> element with the verified_at value as dateTime', () => {
    const { container } = render(
      <AuditHistoryTimeline events={[baseEvent({ verified_at: '2024-09-28T14:30:00Z' })]} />,
    );
    const time = container.querySelector('time');
    expect(time).toBeTruthy();
    expect(time?.getAttribute('dateTime')).toBe('2024-09-28T14:30:00Z');
  });

  // ── Multi-event / ordering ─────────────────────────────────────────────────

  it('renders multiple events', () => {
    const events: VerificationEvent[] = [
      baseEvent({ id: '1', entityLabel: 'Attendance', action: 'rejected' }),
      baseEvent({ id: '2', entityLabel: 'Work Entry', action: 'approved' }),
    ];
    render(<AuditHistoryTimeline events={events} />);
    expect(screen.getByText('Attendance')).toBeTruthy();
    expect(screen.getByText('Work Entry')).toBeTruthy();
  });

  it('orders events chronologically (oldest first)', () => {
    const events: VerificationEvent[] = [
      baseEvent({ id: 'b', entityLabel: 'Later', verified_at: '2024-09-28T16:00:00Z' }),
      baseEvent({ id: 'a', entityLabel: 'Earlier', verified_at: '2024-09-28T10:00:00Z' }),
    ];
    render(<AuditHistoryTimeline events={events} />);
    const labels = screen.getAllByText(/Earlier|Later/);
    // "Earlier" event should appear first in the DOM
    expect(labels[0].textContent).toBe('Earlier');
    expect(labels[1].textContent).toBe('Later');
  });

  // ── Accessibility ──────────────────────────────────────────────────────────

  it('renders a list with aria-label="Verification audit history"', () => {
    render(<AuditHistoryTimeline events={[baseEvent()]} />);
    const list = screen.getByRole('list', { name: /Verification audit history/i });
    expect(list).toBeTruthy();
  });
});

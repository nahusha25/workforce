import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { VerificationRemarksModal } from '../../components/verification/VerificationRemarksModal';

/** Default props that satisfy a valid, ready-to-submit state */
const defaultProps = {
  action: 'reject' as const,
  entityDescription: 'Attendance — 2024-09-28',
  remarks: 'This entry has incorrect location data beyond acceptable threshold',
  onRemarksChange: vi.fn(),
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe('VerificationRemarksModal', () => {
  // ── Rendering ──────────────────────────────────────────────────────────────

  it('renders the reject title for action="reject"', () => {
    render(<VerificationRemarksModal {...defaultProps} />);
    expect(screen.getByText(/Reject — Mandatory Remarks/i)).toBeTruthy();
  });

  it('renders the return title for action="return"', () => {
    render(<VerificationRemarksModal {...defaultProps} action="return" />);
    expect(screen.getByText(/Return for Correction/i)).toBeTruthy();
  });

  it('renders the entity description', () => {
    render(<VerificationRemarksModal {...defaultProps} />);
    expect(screen.getByText('Attendance — 2024-09-28')).toBeTruthy();
  });

  it('renders the textarea with current remarks value', () => {
    render(<VerificationRemarksModal {...defaultProps} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toBe(defaultProps.remarks);
  });

  it('displays an API error when provided', () => {
    render(<VerificationRemarksModal {...defaultProps} error="Server error occurred" />);
    expect(screen.getByText('Server error occurred')).toBeTruthy();
  });

  it('shows correct submit label for reject action', () => {
    render(<VerificationRemarksModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Confirm Rejection/i })).toBeTruthy();
  });

  it('shows correct submit label for return action', () => {
    render(<VerificationRemarksModal {...defaultProps} action="return" />);
    expect(screen.getByRole('button', { name: /Send for Correction/i })).toBeTruthy();
  });

  // ── Validation: trimmed length ─────────────────────────────────────────────

  it('disables the submit button when remarks are empty', () => {
    render(<VerificationRemarksModal {...defaultProps} remarks="" />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('disables the submit button when trimmed remarks are < 10 characters', () => {
    render(<VerificationRemarksModal {...defaultProps} remarks="short" />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('REJECTS whitespace-padded remarks that are < 10 chars when trimmed', () => {
    // "   hi   " → trimmed = "hi" = 2 chars → invalid
    render(<VerificationRemarksModal {...defaultProps} remarks="   hi   " />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('REJECTS remarks that reach 10 chars only via padding whitespace', () => {
    // "     x    " → trimmed = "x" = 1 char → still invalid
    render(<VerificationRemarksModal {...defaultProps} remarks="         x" />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('enables submit when trimmed remarks are exactly 10 characters', () => {
    render(<VerificationRemarksModal {...defaultProps} remarks="1234567890" />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);
  });

  it('enables submit when trimmed remarks are exactly 10 chars with surrounding spaces', () => {
    // "  1234567890  " → trimmed = 10 chars → valid
    render(<VerificationRemarksModal {...defaultProps} remarks="  1234567890  " />);
    const submitBtn = screen.getByRole('button', { name: /Confirm Rejection/i }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);
  });

  it('calls onRemarksChange when the textarea changes', () => {
    const onRemarksChange = vi.fn();
    render(<VerificationRemarksModal {...defaultProps} onRemarksChange={onRemarksChange} />);
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'new value typed' } });
    expect(onRemarksChange).toHaveBeenCalledWith('new value typed');
  });

  // ── Confirm action ─────────────────────────────────────────────────────────

  it('calls onConfirm with trimmed remarks when form is submitted', () => {
    const onConfirm = vi.fn();
    // remarks has trailing space; onConfirm should receive trimmed string
    render(
      <VerificationRemarksModal
        {...defaultProps}
        remarks="Valid remark with enough chars  "
        onConfirm={onConfirm}
      />,
    );
    const form = screen.getByRole('button', { name: /Confirm Rejection/i }).closest('form')!;
    fireEvent.submit(form);
    expect(onConfirm).toHaveBeenCalledWith('Valid remark with enough chars');
  });

  it('does NOT call onConfirm when remarks are too short', () => {
    const onConfirm = vi.fn();
    render(<VerificationRemarksModal {...defaultProps} remarks="short" onConfirm={onConfirm} />);
    const form = screen.getByRole('button', { name: /Confirm Rejection/i }).closest('form')!;
    fireEvent.submit(form);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  // ── Cancel action ──────────────────────────────────────────────────────────

  it('calls onCancel when the Cancel button is clicked', () => {
    const onCancel = vi.fn();
    render(<VerificationRemarksModal {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when the × close button is clicked', () => {
    const onCancel = vi.fn();
    render(<VerificationRemarksModal {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByLabelText('Close modal'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('does NOT call onCancel when isSubmitting=true and Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(
      <VerificationRemarksModal {...defaultProps} isSubmitting={true} onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('does NOT call the action when isSubmitting=true and Cancel (×) is clicked', () => {
    const onCancel = vi.fn();
    render(
      <VerificationRemarksModal {...defaultProps} isSubmitting={true} onCancel={onCancel} />,
    );
    const closeBtns = screen.getAllByLabelText('Close modal') as HTMLButtonElement[];
    // Click all disabled close buttons — none should fire onCancel
    closeBtns.forEach((btn) => fireEvent.click(btn));
    expect(onCancel).not.toHaveBeenCalled();
  });

  // ── Submitting state ───────────────────────────────────────────────────────

  it('disables textarea while isSubmitting', () => {
    render(<VerificationRemarksModal {...defaultProps} isSubmitting={true} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(true);
  });

  it('disables the × button while isSubmitting', () => {
    render(<VerificationRemarksModal {...defaultProps} isSubmitting={true} />);
    const closeBtn = screen.getByLabelText('Close modal') as HTMLButtonElement;
    expect(closeBtn.disabled).toBe(true);
  });

  // ── Accessibility ──────────────────────────────────────────────────────────

  it('renders a dialog with aria-modal="true"', () => {
    const { container } = render(<VerificationRemarksModal {...defaultProps} />);
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog?.getAttribute('aria-modal')).toBe('true');
  });

  it('labels the dialog via aria-labelledby pointing to the title', () => {
    const { container } = render(<VerificationRemarksModal {...defaultProps} />);
    const dialog = container.querySelector('[role="dialog"]');
    const titleId = dialog?.getAttribute('aria-labelledby');
    expect(document.getElementById(titleId!)).toBeTruthy();
  });

  // ── Reopen Mode ────────────────────────────────────────────────────────────

  it('renders the reopen title for action="reopen"', () => {
    render(<VerificationRemarksModal {...defaultProps} action="reopen" />);
    expect(screen.getByText(/Reopen — Mandatory Remarks/i)).toBeTruthy();
  });

  it('shows correct submit label for reopen action', () => {
    render(<VerificationRemarksModal {...defaultProps} action="reopen" />);
    expect(screen.getByRole('button', { name: /Confirm Reopen/i })).toBeTruthy();
  });

  it('renders reopen-specific placeholder', () => {
    render(<VerificationRemarksModal {...defaultProps} action="reopen" remarks="" />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.placeholder).toContain('Provide a specific reason for reopening');
  });
});


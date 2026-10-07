import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';

describe('ConfirmDeleteModal', () => {
  afterEach(() => {
    cleanup();
  });

  it('does not render when isOpen is false', () => {
    render(
      <ConfirmDeleteModal
        isOpen={false}
        title="Delete Test"
        message="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
  });

  it('renders title, message, and buttons when isOpen is true', () => {
    render(
      <ConfirmDeleteModal
        isOpen={true}
        title="Delete Employee"
        message="Are you sure you want to delete John?"
        confirmLabel="Confirm Delete"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText('Delete Employee')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete John?')).toBeInTheDocument();
    expect(screen.getByTestId('confirm-delete-btn')).toHaveTextContent('Confirm Delete');
    expect(screen.getByTestId('cancel-delete-btn')).toHaveTextContent('Cancel');
  });

  it('calls onCancel when cancel button or close button is clicked', () => {
    const handleCancel = vi.fn();
    render(
      <ConfirmDeleteModal
        isOpen={true}
        title="Delete Item"
        message="Delete message"
        onConfirm={vi.fn()}
        onCancel={handleCancel}
      />
    );

    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(handleCancel).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByLabelText('Close modal'));
    expect(handleCancel).toHaveBeenCalledTimes(2);
  });

  it('calls onConfirm when confirm button is clicked', () => {
    const handleConfirm = vi.fn();
    render(
      <ConfirmDeleteModal
        isOpen={true}
        title="Delete Item"
        message="Delete message"
        onConfirm={handleConfirm}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('confirm-delete-btn'));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('handles Escape key to cancel when not deleting', () => {
    const handleCancel = vi.fn();
    render(
      <ConfirmDeleteModal
        isOpen={true}
        title="Delete Item"
        message="Delete message"
        onConfirm={vi.fn()}
        onCancel={handleCancel}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it('disables cancel and close buttons and indicates loading when isDeleting is true', () => {
    const handleCancel = vi.fn();
    render(
      <ConfirmDeleteModal
        isOpen={true}
        title="Deleting Item"
        message="Please wait"
        isDeleting={true}
        onConfirm={vi.fn()}
        onCancel={handleCancel}
      />
    );

    expect(screen.getByTestId('cancel-delete-btn')).toBeDisabled();
    expect(screen.getByLabelText('Close modal')).toBeDisabled();

    // Escape key should NOT trigger cancel during deletion
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleCancel).not.toHaveBeenCalled();
  });
});

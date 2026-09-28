import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MaterialTransactionEntry, formatDecimal } from './MaterialTransactionEntry';
import {
  getMaterialTransactions,
  createMaterialTransaction,
  deleteMaterialTransaction,
  type MaterialTransaction,
} from '../api/dailyWork';

vi.mock('../api/dailyWork', () => ({
  getMaterialTransactions: vi.fn(),
  createMaterialTransaction: vi.fn(),
  deleteMaterialTransaction: vi.fn(),
}));

vi.mock('../utils/imageCompression', () => ({
  compressImage: vi.fn(async (file: File) => file),
}));

// Mock URL.createObjectURL / revokeObjectURL for JSDOM
if (typeof URL.createObjectURL === 'undefined') {
  URL.createObjectURL = vi.fn(() => 'blob:mock-url');
}
if (typeof URL.revokeObjectURL === 'undefined') {
  URL.revokeObjectURL = vi.fn();
}

describe('MaterialTransactionEntry Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getMaterialTransactions as any).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders and records a successful consumed transaction', async () => {
    const createdTx: MaterialTransaction = {
      id: 'tx-1',
      daily_work_entry_id: 'entry-1',
      transaction_type: 'consumed',
      item_name: 'Cat6 Cable 30m',
      quantity: 2.5,
      amount: 0,
      is_high_value: false,
      status: 'draft',
      created_at: '2026-09-25T10:00:00Z',
    };
    (createMaterialTransaction as any).mockResolvedValue(createdTx);
    const onMaterialAdded = vi.fn();

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={[]}
        onMaterialAdded={onMaterialAdded}
      />
    );

    // Open form
    const addBtn = screen.getByRole('button', { name: /Add Material/i });
    fireEvent.click(addBtn);

    // Fill fields
    const nameInput = screen.getByLabelText(/Item Name/i);
    const qtyInput = screen.getByLabelText(/Quantity/i);
    const amountInput = screen.getByLabelText(/Amount/i);

    fireEvent.change(nameInput, { target: { value: 'Cat6 Cable 30m' } });
    fireEvent.change(qtyInput, { target: { value: '2.50' } });
    fireEvent.change(amountInput, { target: { value: '0.00' } });

    // Submit
    const submitBtn = screen.getByRole('button', { name: /Record Material/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createMaterialTransaction).toHaveBeenCalledWith('entry-1', {
        transaction_type: 'consumed',
        item_name: 'Cat6 Cable 30m',
        quantity: 2.5,
        amount: 0,
        bill_file: null,
      });
    });

    // Check newly added item in list
    await waitFor(() => {
      expect(screen.getByText('Cat6 Cable 30m')).toBeInTheDocument();
      expect(screen.getByText('consumed')).toBeInTheDocument();
      expect(screen.getByText('2.50')).toBeInTheDocument();
    });

    expect(onMaterialAdded).toHaveBeenCalledWith(createdTx);
  });

  it('renders and records a successful purchased transaction with bill attachment', async () => {
    const createdTx: MaterialTransaction = {
      id: 'tx-2',
      daily_work_entry_id: 'entry-1',
      transaction_type: 'purchased',
      item_name: 'Emergency Circuit Breaker',
      quantity: 1,
      amount: 450,
      bill_image_url: 'http://localhost:8000/storage/bills/bill-1.jpg',
      is_high_value: true,
      status: 'draft',
      created_at: '2026-09-25T10:15:00Z',
    };
    (createMaterialTransaction as any).mockResolvedValue(createdTx);

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={[]}
      />
    );

    // Open form
    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    // Switch to Purchased
    fireEvent.click(screen.getByRole('button', { name: /Purchased Material/i }));

    // Fill form
    fireEvent.change(screen.getByLabelText(/Item Name/i), {
      target: { value: 'Emergency Circuit Breaker' },
    });
    fireEvent.change(screen.getByLabelText(/Quantity/i), { target: { value: '1.00' } });
    fireEvent.change(screen.getByLabelText(/Amount/i), { target: { value: '450.00' } });

    // Attach bill
    const billInput = screen.getByLabelText(/Attach bill receipt photo/i);
    const billFile = new File(['receipt-content'], 'receipt.jpg', { type: 'image/jpeg' });
    fireEvent.change(billInput, { target: { files: [billFile] } });

    // Verify preview is shown
    await waitFor(() => {
      expect(screen.getByAltText('Receipt Preview')).toBeInTheDocument();
    });

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /Record Material/i }));

    await waitFor(() => {
      expect(createMaterialTransaction).toHaveBeenCalledWith(
        'entry-1',
        expect.objectContaining({
          transaction_type: 'purchased',
          item_name: 'Emergency Circuit Breaker',
          quantity: 1,
          amount: 450,
          bill_file: expect.any(File),
        })
      );
    });

    // Check item rendered with bill receipt link and high value badge
    await waitFor(() => {
      expect(screen.getByText('Emergency Circuit Breaker')).toBeInTheDocument();
      expect(screen.getByText('Receipt')).toBeInTheDocument();
      expect(screen.getByText('High Value')).toBeInTheDocument();
    });
  });

  it('displays is_high_value badge only on flagged transactions', () => {
    const mockList: MaterialTransaction[] = [
      {
        id: 'tx-high',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'purchased',
        item_name: 'Uncataloged Drill Tool',
        quantity: 1,
        amount: 800,
        is_high_value: true,
        status: 'draft',
        created_at: '2026-09-25T10:00:00Z',
      },
      {
        id: 'tx-normal',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'consumed',
        item_name: 'Standard Cable Ties',
        quantity: 20,
        amount: 0,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:05:00Z',
      },
    ];

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={mockList}
      />
    );

    expect(screen.getByText('Uncataloged Drill Tool')).toBeInTheDocument();
    expect(screen.getByText('Standard Cable Ties')).toBeInTheDocument();

    // High Value badge should be visible once (for tx-high)
    const badges = screen.getAllByText('High Value');
    expect(badges).toHaveLength(1);
    expect(badges[0]).toBeInTheDocument();
  });

  it('allows deleting a material transaction while entry is in draft status', async () => {
    (deleteMaterialTransaction as any).mockResolvedValue({
      status: 'success',
      message: 'Transaction deleted',
    });

    const onMaterialDeleted = vi.fn();
    const mockList: MaterialTransaction[] = [
      {
        id: 'tx-to-delete',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'consumed',
        item_name: 'Spare Screws',
        quantity: 10,
        amount: 0,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:00:00Z',
      },
    ];

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={mockList}
        onMaterialDeleted={onMaterialDeleted}
      />
    );

    expect(screen.getByText('Spare Screws')).toBeInTheDocument();
    const deleteBtn = screen.getByLabelText('Delete material');
    expect(deleteBtn).toBeInTheDocument();

    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(deleteMaterialTransaction).toHaveBeenCalledWith('tx-to-delete');
    });

    await waitFor(() => {
      expect(screen.queryByText('Spare Screws')).not.toBeInTheDocument();
    });

    expect(onMaterialDeleted).toHaveBeenCalledWith('tx-to-delete');
  });

  it('hides delete button and add form toggle when entry is submitted', () => {
    const mockList: MaterialTransaction[] = [
      {
        id: 'tx-submitted',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'consumed',
        item_name: 'Locked Material',
        quantity: 5,
        amount: 0,
        is_high_value: false,
        status: 'submitted',
        created_at: '2026-09-25T10:00:00Z',
      },
    ];

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="submitted"
        initialMaterials={mockList}
      />
    );

    expect(screen.getByText('Locked Material')).toBeInTheDocument();
    expect(screen.queryByLabelText('Delete material')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Add Material/i })).not.toBeInTheDocument();
  });

  it('formats quantity and amount with exact 2-decimal precision without floating point noise', () => {
    // Test the helper function directly
    expect(formatDecimal(150.00000000001)).toBe('150.00');
    expect(formatDecimal(15.75)).toBe('15.75');
    expect(formatDecimal(100)).toBe('100.00');
    expect(formatDecimal('25.5')).toBe('25.50');
    expect(formatDecimal(null)).toBe('0.00');
    expect(formatDecimal(undefined)).toBe('0.00');

    // Test in component rendering
    const mockList: MaterialTransaction[] = [
      {
        id: 'tx-precision',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'purchased',
        item_name: 'Optical Fiber Joint',
        quantity: 15.750000000001,
        amount: 1234.5600000002,
        is_high_value: true,
        status: 'draft',
        created_at: '2026-09-25T10:00:00Z',
      },
      {
        id: 'tx-int',
        daily_work_entry_id: 'entry-1',
        transaction_type: 'consumed',
        item_name: 'Anchor Screws',
        quantity: 100,
        amount: 15,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:05:00Z',
      },
    ];

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={mockList}
      />
    );

    // 15.75 and 1234.56 exact
    expect(screen.getByText('15.75')).toBeInTheDocument();
    expect(screen.getByText('1234.56')).toBeInTheDocument();

    // 100.00 and 15.00 exact
    expect(screen.getByText('100.00')).toBeInTheDocument();
    expect(screen.getByText('15.00')).toBeInTheDocument();

    // Verify raw floating point noise is NOT present
    expect(screen.queryByText(/150\.00000000001/)).not.toBeInTheDocument();
    expect(screen.queryByText(/1234\.5600000002/)).not.toBeInTheDocument();
  });
});

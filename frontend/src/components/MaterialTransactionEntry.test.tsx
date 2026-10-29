import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MaterialTransactionEntry, formatDecimal } from './MaterialTransactionEntry';
import {
  getMaterialTransactions,
  createMaterialTransaction,
  deleteMaterialTransaction,
  getMaterialsCatalogue,
  type MaterialTransaction,
} from '../api/dailyWork';
import { getMaterialStockAvailabilityApi } from '../api/inventory';

vi.mock('../api/dailyWork', () => ({
  getMaterialTransactions: vi.fn(),
  createMaterialTransaction: vi.fn(),
  deleteMaterialTransaction: vi.fn(),
  getMaterialsCatalogue: vi.fn(),
}));

vi.mock('../api/inventory', () => ({
  getMaterialStockAvailabilityApi: vi.fn(),
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
    (getMaterialsCatalogue as any).mockResolvedValue([
      {
        id: 'mat-1',
        name: 'Cat6 Cable 30m',
        unit_of_measure: 'mtr',
        category: 'cable',
        purchase_approval_limit: 1000,
        is_active: true,
      },
      {
        id: 'mat-2',
        name: 'RJ45 Connectors',
        unit_of_measure: 'pcs',
        category: 'accessories',
        purchase_approval_limit: 500,
        is_active: true,
      },
      {
        id: 'mat-3',
        name: 'CCTV Camera Dome',
        unit_of_measure: 'pcs',
        category: 'cameras',
        purchase_approval_limit: 2000,
        is_active: true,
      },
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders and records a successful consumed transaction', async () => {
    const createdTx: MaterialTransaction = {
      id: 'tx-1',
      daily_work_entry_id: 'entry-1',
      material_id: 'mat-1',
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

    // Select material from catalogue dropdown
    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    // Fill quantity and amount
    const qtyInput = screen.getByLabelText(/Quantity/i);
    const amountInput = screen.getByLabelText(/Amount/i);

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
        material_id: 'mat-1',
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

  it('displays available stock when catalogue material is selected at assigned site', async () => {
    (getMaterialStockAvailabilityApi as any).mockResolvedValue({
      site_id: 'site-1',
      site_name: 'Alpha Site',
      material_id: 'mat-1',
      material_code: 'MAT-001',
      material_name: 'Cat6 Cable 30m',
      unit_of_measure: 'mtr',
      category: 'cable',
      quantity_available: 15.0,
      is_active: true,
    });

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        siteId="site-1"
        initialMaterials={[]}
      />
    );

    // Open add form
    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    // Select material
    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    await waitFor(() => {
      expect(getMaterialStockAvailabilityApi).toHaveBeenCalledWith('site-1', 'mat-1');
    });

    await waitFor(() => {
      expect(screen.getByLabelText('Available Stock')).toHaveTextContent('Available: 15.00 mtr');
    });
  });

  it('displays stock warning when available stock is 0.00', async () => {
    (getMaterialStockAvailabilityApi as any).mockResolvedValue({
      site_id: 'site-1',
      site_name: 'Alpha Site',
      material_id: 'mat-1',
      material_code: 'MAT-001',
      material_name: 'Cat6 Cable 30m',
      unit_of_measure: 'mtr',
      category: 'cable',
      quantity_available: 0.0,
      is_active: true,
    });

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        siteId="site-1"
        initialMaterials={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    await waitFor(() => {
      expect(screen.getByLabelText('Stock Warning')).toBeInTheDocument();
      expect(screen.getByText(/Zero available stock for this material at site/i)).toBeInTheDocument();
    });
  });

  it('displays stock warning when entered quantity exceeds available stock', async () => {
    (getMaterialStockAvailabilityApi as any).mockResolvedValue({
      site_id: 'site-1',
      site_name: 'Alpha Site',
      material_id: 'mat-1',
      material_code: 'MAT-001',
      material_name: 'Cat6 Cable 30m',
      unit_of_measure: 'mtr',
      category: 'cable',
      quantity_available: 5.0,
      is_active: true,
    });

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        siteId="site-1"
        initialMaterials={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    await waitFor(() => {
      expect(screen.getByLabelText('Available Stock')).toHaveTextContent('Available: 5.00 mtr');
    });

    // Enter quantity 10.00 > available 5.00
    const qtyInput = screen.getByLabelText(/Quantity/i);
    fireEvent.change(qtyInput, { target: { value: '10.00' } });

    await waitFor(() => {
      expect(screen.getByLabelText('Stock Warning')).toBeInTheDocument();
      expect(screen.getByText(/exceeds available stock/i)).toBeInTheDocument();
    });
  });

  it('displays material unit of measure next to quantity input when material is selected', async () => {
    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={[]}
      />
    );

    // Open form
    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    // Before selection, no UOM badge is shown
    expect(screen.queryByTestId('material-uom-badge')).not.toBeInTheDocument();

    // Select RJ45 Connectors (pcs)
    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-2' } });

    // Unit badge next to input should display pcs
    await waitFor(() => {
      const uomBadge = screen.getByTestId('material-uom-badge');
      expect(uomBadge).toBeInTheDocument();
      expect(uomBadge).toHaveTextContent('pcs');
      expect(screen.getByText(/Quantity \(pcs\) \*/i)).toBeInTheDocument();
    });
  });

  it('updates unit label and badge dynamically when selected material changes', async () => {
    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    const matSelect = await screen.findByLabelText(/Catalogue Material/i);

    // 1. Select RJ45 Connectors (pcs)
    fireEvent.change(matSelect, { target: { value: 'mat-2' } });
    await waitFor(() => {
      expect(screen.getByTestId('material-uom-badge')).toHaveTextContent('pcs');
      expect(screen.getByText(/Quantity \(pcs\) \*/i)).toBeInTheDocument();
    });

    // 2. Switch to Cat6 Cable 30m (mtr)
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });
    await waitFor(() => {
      expect(screen.getByTestId('material-uom-badge')).toHaveTextContent('mtr');
      expect(screen.getByText(/Quantity \(mtr\) \*/i)).toBeInTheDocument();
    });

    // 3. Switch to CCTV Camera Dome (pcs)
    fireEvent.change(matSelect, { target: { value: 'mat-3' } });
    await waitFor(() => {
      expect(screen.getByTestId('material-uom-badge')).toHaveTextContent('pcs');
      expect(screen.getByText(/Quantity \(pcs\) \*/i)).toBeInTheDocument();
    });
  });

  it('displays correct units stored in existing catalogue for recorded material cards', async () => {
    const mockList: MaterialTransaction[] = [
      {
        id: 'tx-rj45',
        daily_work_entry_id: 'entry-1',
        material_id: 'mat-2',
        transaction_type: 'consumed',
        item_name: 'RJ45 Connectors',
        quantity: 2,
        amount: 0,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:00:00Z',
      },
      {
        id: 'tx-cable',
        daily_work_entry_id: 'entry-1',
        material_id: 'mat-1',
        transaction_type: 'consumed',
        item_name: 'Cat6 Cable 30m',
        quantity: 20,
        amount: 0,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:05:00Z',
      },
      {
        id: 'tx-camera',
        daily_work_entry_id: 'entry-1',
        material_id: 'mat-3',
        transaction_type: 'consumed',
        item_name: 'CCTV Camera Dome',
        quantity: 2,
        amount: 0,
        is_high_value: false,
        status: 'draft',
        created_at: '2026-09-25T10:10:00Z',
      },
    ];

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={mockList}
      />
    );

    // Wait for catalogue materials to load and resolve units
    await waitFor(() => {
      const uomElements = screen.getAllByTestId('material-tx-uom');
      expect(uomElements).toHaveLength(3);
      expect(uomElements[0]).toHaveTextContent('pcs');
      expect(uomElements[1]).toHaveTextContent('mtr');
      expect(uomElements[2]).toHaveTextContent('pcs');
    });

    // Verify quantities and units in each card
    expect(screen.getByText('RJ45 Connectors')).toBeInTheDocument();
    expect(screen.getByText('Cat6 Cable 30m')).toBeInTheDocument();
    expect(screen.getByText('CCTV Camera Dome')).toBeInTheDocument();
  });

  it('keeps numeric quantity input editable and preserves API payload format', async () => {
    const createdTx: MaterialTransaction = {
      id: 'tx-new',
      daily_work_entry_id: 'entry-1',
      material_id: 'mat-1',
      transaction_type: 'consumed',
      item_name: 'Cat6 Cable 30m',
      quantity: 20,
      amount: 0,
      is_high_value: false,
      status: 'draft',
      created_at: '2026-09-25T10:00:00Z',
    };
    (createMaterialTransaction as any).mockResolvedValue(createdTx);

    render(
      <MaterialTransactionEntry
        dailyWorkEntryId="entry-1"
        status="draft"
        initialMaterials={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Add Material/i }));

    const matSelect = await screen.findByLabelText(/Catalogue Material/i);
    fireEvent.change(matSelect, { target: { value: 'mat-1' } });

    // Editable numeric input: enter '20'
    const qtyInput = screen.getByLabelText(/Quantity/i);
    fireEvent.change(qtyInput, { target: { value: '20' } });
    expect((qtyInput as HTMLInputElement).value).toBe('20');

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /Record Material/i }));

    await waitFor(() => {
      // Must preserve pure numeric quantity and payload schema
      expect(createMaterialTransaction).toHaveBeenCalledWith('entry-1', {
        transaction_type: 'consumed',
        item_name: 'Cat6 Cable 30m',
        quantity: 20,
        amount: 0,
        material_id: 'mat-1',
        bill_file: null,
      });
    });
  });

  describe('Loading Lifecycle and Flicker Prevention', () => {
    it('does not display loading spinner or call getMaterialTransactions when initialMaterials is provided as empty array', () => {
      render(
        <MaterialTransactionEntry
          dailyWorkEntryId="entry-empty"
          status="draft"
          initialMaterials={[]}
        />
      );

      // Loading spinner should never be in the document
      expect(screen.queryByText(/Loading material transactions/i)).not.toBeInTheDocument();
      // Empty state hint should be directly visible
      expect(screen.getByText(/No materials recorded for today yet/i)).toBeInTheDocument();
      // No unnecessary network request
      expect(getMaterialTransactions).not.toHaveBeenCalled();
    });

    it('shows genuine loading feedback when initialMaterials is undefined and fetches transactions', async () => {
      const serverMaterials: MaterialTransaction[] = [
        {
          id: 'tx-server-1',
          daily_work_entry_id: 'entry-fetch',
          transaction_type: 'consumed',
          item_name: 'Cat6 Cable 30m',
          quantity: 10,
          amount: 0,
          is_high_value: false,
          status: 'draft',
          created_at: '2026-09-25T10:00:00Z',
        },
      ];
      let resolvePromise: (val: MaterialTransaction[]) => void;
      const deferred = new Promise<MaterialTransaction[]>((resolve) => {
        resolvePromise = resolve;
      });
      (getMaterialTransactions as any).mockReturnValue(deferred);

      render(
        <MaterialTransactionEntry
          dailyWorkEntryId="entry-fetch"
          status="draft"
        />
      );

      // Spinner must be visible while promise is pending
      expect(screen.getByText(/Loading material transactions/i)).toBeInTheDocument();
      expect(getMaterialTransactions).toHaveBeenCalledWith('entry-fetch');

      // Resolve API call
      resolvePromise!(serverMaterials);

      // Spinner disappears and material is rendered
      await waitFor(() => {
        expect(screen.queryByText(/Loading material transactions/i)).not.toBeInTheDocument();
        expect(screen.getByText('Cat6 Cable 30m')).toBeInTheDocument();
      });
    });

    it('avoids duplicate API requests when parent re-renders with the same dailyWorkEntryId', async () => {
      (getMaterialTransactions as any).mockResolvedValue([]);

      const { rerender } = render(
        <MaterialTransactionEntry
          dailyWorkEntryId="entry-stable"
          status="draft"
        />
      );

      await waitFor(() => {
        expect(getMaterialTransactions).toHaveBeenCalledTimes(1);
      });

      // Parent re-renders (simulating typing in parent form with new callback references)
      rerender(
        <MaterialTransactionEntry
          dailyWorkEntryId="entry-stable"
          status="draft"
          onMaterialsLoaded={() => {}}
        />
      );

      // Should still be called only once
      expect(getMaterialTransactions).toHaveBeenCalledTimes(1);
    });

    it('allows retry when fetching fails for undefined initialMaterials', async () => {
      (getMaterialTransactions as any).mockRejectedValueOnce(new Error('Network failure'));

      render(
        <MaterialTransactionEntry
          dailyWorkEntryId="entry-err"
          status="draft"
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
      });

      (getMaterialTransactions as any).mockResolvedValueOnce([
        {
          id: 'tx-retried',
          daily_work_entry_id: 'entry-err',
          transaction_type: 'consumed',
          item_name: 'Cat6 Cable 30m',
          quantity: 5,
          amount: 0,
          is_high_value: false,
          status: 'draft',
          created_at: '2026-09-25T10:00:00Z',
        },
      ]);

      fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

      await waitFor(() => {
        expect(getMaterialTransactions).toHaveBeenCalledTimes(2);
        expect(screen.getByText('Cat6 Cable 30m')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      });
    });
  });
});

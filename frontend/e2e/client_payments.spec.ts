import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';

let testData: any;

test.beforeAll(async () => {
  const backendDir = path.resolve(process.cwd(), '../backend');
  const winVenv = path.resolve(backendDir, '.venv/Scripts/python.exe');
  const winFallback = path.resolve(backendDir, 'venv/Scripts/python.exe');
  const unixVenv = path.resolve(backendDir, '.venv/bin/python');

  let pythonCmd = 'python';
  if (process.platform === 'win32') {
    if (fs.existsSync(winVenv)) pythonCmd = winVenv;
    else if (fs.existsSync(winFallback)) pythonCmd = winFallback;
  } else {
    if (fs.existsSync(unixVenv)) pythonCmd = unixVenv;
  }

  const scriptPath = path.resolve(backendDir, 'e2e_seed_client_payments.py');
  const output = execSync(`"${pythonCmd}" "${scriptPath}"`, { cwd: backendDir, encoding: 'utf-8' });

  const jsonMatch = output.match(/\{.*\}/s);
  if (jsonMatch) {
    testData = JSON.parse(jsonMatch[0]);
  } else {
    throw new Error('Failed to parse client payments seeder output: ' + output);
  }
});

async function setupAuthContext(context: any, token: string) {
  await context.addInitScript((authToken: string) => {
    localStorage.setItem('access_token', authToken);
  }, token);
}

test.describe.serial('E2E Client Payments & Receipts Flow & RBAC Verification (Mobile Viewport)', () => {
  test('Step 1: Employee and Supervisor access to invoice detail is blocked (403)', async ({ context, page }) => {
    // 1. Employee access
    await setupAuthContext(context, testData.workerToken);
    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();

    // 2. Supervisor access
    await setupAuthContext(context, testData.supervisorToken);
    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();
  });

  test('Step 2: Director views issued invoice and validates overpayment rejection', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('ISSUED').first()).toBeVisible();
    await expect(page.getByText(/₹10,000\.00/).first()).toBeVisible();

    // Verify initial payment history card
    await expect(page.getByText(/Payments & Receipts/i).first()).toBeVisible();
    await expect(page.getByText(/No payments recorded yet for this invoice/i)).toBeVisible();

    // Open Record Payment modal
    await page.getByRole('button', { name: 'Record Payment' }).first().click();
    await expect(page.getByRole('heading', { name: 'Record Client Payment' })).toBeVisible();

    // Test overpayment client validation
    const amountInput = page.getByLabel(/Payment Amount \(₹\) \*/i);
    await amountInput.fill('15000');
    await page.getByRole('button', { name: 'Confirm & Record Payment' }).click();
    await expect(page.getByText(/Payment amount cannot exceed outstanding balance of ₹10,000\.00/i)).toBeVisible();

    // Close modal
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  });

  test('Step 3: Director records partial payment (₹4,000 via UPI) -> Transitions to PARTIALLY_PAID', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });

    // Open Record Payment modal
    await page.getByRole('button', { name: 'Record Payment' }).first().click();
    await expect(page.getByRole('heading', { name: 'Record Client Payment' })).toBeVisible();

    // Fill valid partial payment details
    await page.getByLabel(/Payment Amount \(₹\) \*/i).fill('4000');
    await page.getByLabel(/Payment Method \*/i).selectOption('upi');
    await page.getByLabel(/Reference \/ UTR \/ Cheque Number/i).fill('UPI-UTR-998877');
    await page.getByLabel(/Notes \/ Remarks/i).fill('Partial advance tranche received');

    // Submit payment
    await page.getByRole('button', { name: 'Confirm & Record Payment' }).click();

    // Verify success notice and modal close
    await expect(page.getByText(/recorded successfully/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Record Client Payment' })).not.toBeVisible();

    // Verify status transition to PARTIALLY_PAID
    await expect(page.getByText('PARTIALLY_PAID').first()).toBeVisible();

    // Verify Paid Amount and Balance Due updates
    await expect(page.locator('div').filter({ hasText: /^Paid Amount:/ }).getByText('₹4,000.00')).toBeVisible();
    await expect(page.locator('div').filter({ hasText: /^Balance Due:/ }).getByText('₹6,000.00')).toBeVisible();

    // Verify Payment row in table
    await expect(page.getByText('UPI-UTR-998877')).toBeVisible();
    await expect(page.getByText('recorded').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Void' })).toBeVisible();
  });

  test('Step 4: Administrator records remaining payment (₹6,000 via NEFT) -> Transitions to PAID', async ({ context, page }) => {
    await setupAuthContext(context, testData.adminToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('PARTIALLY_PAID').first()).toBeVisible();

    // Open Record Payment modal
    await page.getByRole('button', { name: 'Record Payment' }).first().click();
    await expect(page.getByRole('heading', { name: 'Record Client Payment' })).toBeVisible();

    // Fill remaining balance
    await page.getByLabel(/Payment Amount \(₹\) \*/i).fill('6000');
    await page.getByLabel(/Payment Method \*/i).selectOption('neft');
    await page.getByLabel(/Reference \/ UTR \/ Cheque Number/i).fill('NEFT-UTR-667788');

    // Submit payment
    await page.getByRole('button', { name: 'Confirm & Record Payment' }).click();

    // Verify success notice
    await expect(page.getByText(/recorded successfully/i)).toBeVisible({ timeout: 10000 });

    // Verify status transition to PAID
    await expect(page.getByText('PAID').first()).toBeVisible();

    // Verify Paid Amount = ₹10,000.00 and Balance Due = ₹0.00
    await expect(page.locator('div').filter({ hasText: /^Paid Amount:/ }).getByText('₹10,000.00')).toBeVisible();
    await expect(page.locator('div').filter({ hasText: /^Balance Due:/ }).getByText('₹0.00')).toBeVisible();

    // "Record Payment" button should no longer be visible because invoice is fully settled
    await expect(page.getByRole('button', { name: 'Record Payment' })).not.toBeVisible();
  });

  test('Step 5: Administrator voids the first payment with mandatory audit reason -> Transitions back to PARTIALLY_PAID', async ({ context, page }) => {
    await setupAuthContext(context, testData.adminToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('PAID').first()).toBeVisible();

    // Find the first payment row (with UPI-UTR-998877) and click Void
    const firstRow = page.locator('tr').filter({ hasText: 'UPI-UTR-998877' });
    await expect(firstRow).toBeVisible();
    await firstRow.getByRole('button', { name: 'Void' }).click();

    // Verify Void Payment modal
    await expect(page.getByRole('heading', { name: 'Void Payment' })).toBeVisible();
    const voidReasonInput = page.getByPlaceholder(/State mandatory audit reason \(at least 10 characters\)/i);
    const confirmVoidBtn = page.getByRole('button', { name: 'Confirm & Void Payment' });

    // Test < 10 characters validation (button disabled)
    await voidReasonInput.fill('Too short');
    await expect(confirmVoidBtn).toBeDisabled();

    // Fill valid audit reason
    await voidReasonInput.fill('Client duplicate transfer reversed per bank advice');
    await expect(confirmVoidBtn).toBeEnabled();

    // Confirm Void
    await confirmVoidBtn.click();

    // Verify success message
    await expect(page.getByText(/voided successfully/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Void Payment' })).not.toBeVisible();

    // Status transitions back to PARTIALLY_PAID!
    await expect(page.getByText('PARTIALLY_PAID').first()).toBeVisible();

    // Paid amount decreased to ₹6,000.00, Balance Due is ₹4,000.00
    await expect(page.locator('div').filter({ hasText: /^Paid Amount:/ }).getByText('₹6,000.00')).toBeVisible();
    await expect(page.locator('div').filter({ hasText: /^Balance Due:/ }).getByText('₹4,000.00')).toBeVisible();

    // Verify voided payment display
    await expect(page.getByText('voided').first()).toBeVisible();
    await expect(page.getByText(/Reason: Client duplicate transfer reversed per bank advice/i)).toBeVisible();

    // Record Payment button is now visible again!
    await expect(page.getByRole('button', { name: 'Record Payment' }).first()).toBeVisible();
  });

  test('Step 6: Administrator attaches a receipt to an active recorded payment via Attach Receipt modal', async ({ context, page }) => {
    await setupAuthContext(context, testData.adminToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });

    // Locate active recorded payment row (NEFT-UTR-667788)
    const neftRow = page.locator('tr').filter({ hasText: 'NEFT-UTR-667788' });
    await expect(neftRow).toBeVisible();

    // Verify "Attach Receipt" button is displayed
    const attachBtn = neftRow.getByRole('button', { name: 'Attach Receipt' });
    await expect(attachBtn).toBeVisible();
    await attachBtn.click();

    // Verify Attach Receipt modal opens
    await expect(page.getByRole('heading', { name: 'Attach Receipt' })).toBeVisible();

    // Attach sample receipt PDF
    const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
    await fileInput.setInputFiles({
      name: 'bank_transfer_slip.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'),
    });

    // Submit upload
    await page.getByRole('button', { name: 'Upload Receipt' }).click();

    // Verify success notice and modal close
    await expect(page.getByText(/Receipt attached successfully/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Attach Receipt' })).not.toBeVisible();

    // Row now shows "View Receipt" button
    await expect(neftRow.getByRole('button', { name: 'View Receipt' })).toBeVisible();
  });

  test('Step 7: Director records final payment with optional receipt attached directly in Record Payment modal', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/invoices/${testData.invoiceId}`);
    await expect(page.getByText(testData.invoiceNumber).first()).toBeVisible({ timeout: 10000 });

    // Open Record Payment modal
    await page.getByRole('button', { name: 'Record Payment' }).first().click();
    await expect(page.getByRole('heading', { name: 'Record Client Payment' })).toBeVisible();

    // Fill remaining balance (₹4,000)
    await page.getByLabel(/Payment Amount \(₹\) \*/i).fill('4000');
    await page.getByLabel(/Payment Method \*/i).selectOption('rtgs');
    await page.getByLabel(/Reference \/ UTR \/ Cheque Number/i).fill('RTGS-RECEIPT-554433');

    // Attach receipt in modal
    const fileInput = page.locator('input[type="file"][accept*=".pdf"]');
    await fileInput.setInputFiles({
      name: 'rtgs_ack.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'),
    });
    await expect(page.getByText(/Selected: rtgs_ack\.pdf/i)).toBeVisible();

    // Submit payment
    await page.getByRole('button', { name: 'Confirm & Record Payment' }).click();

    // Verify success notice
    await expect(page.getByText(/recorded and receipt attached successfully/i)).toBeVisible({ timeout: 10000 });

    // Verify table row has "View Receipt"
    const rtgsRow = page.locator('tr').filter({ hasText: 'RTGS-RECEIPT-554433' });
    await expect(rtgsRow).toBeVisible();
    await expect(rtgsRow.getByRole('button', { name: 'View Receipt' })).toBeVisible();
  });
});


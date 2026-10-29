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

  const scriptPath = path.resolve(backendDir, 'e2e_seed_employee_payments.py');
  const output = execSync(`"${pythonCmd}" "${scriptPath}"`, { cwd: backendDir, encoding: 'utf-8' });

  const jsonMatch = output.match(/\{.*\}/s);
  if (jsonMatch) {
    testData = JSON.parse(jsonMatch[0]);
  } else {
    throw new Error('Failed to parse seeder output: ' + output);
  }
});

async function setupAuthContext(context: any, token: string) {
  await context.addInitScript((authToken: string) => {
    localStorage.setItem('access_token', authToken);
  }, token);
}

test.describe.serial('E2E Employee Payments Lifecycle & RBAC Verification (Phase 5E - Batch 5)', () => {
  test('Step 1: Director login -> /employee-payments loads with header, KPI cards and list item link', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto('/employee-payments');
    await expect(page.getByRole('heading', { level: 2, name: 'Employee Payments' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: '+ Generate Payments' })).toBeVisible();

    // Verify all 5 KPI cards
    await expect(page.getByTestId('kpi-total')).toBeVisible();
    await expect(page.getByTestId('kpi-draft')).toBeVisible();
    await expect(page.getByTestId('kpi-approved')).toBeVisible();
    await expect(page.getByTestId('kpi-paid')).toBeVisible();
    await expect(page.getByTestId('kpi-cancelled')).toBeVisible();

    // Verify Sidebar contains Employee Payments on desktop viewport
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.getByRole('link', { name: 'Employee Payments' })).toBeVisible();

    // Verify seeded draft payment link appears in table
    const paymentLink = page.getByRole('link', { name: testData.lifecyclePaymentNumber });
    await expect(paymentLink).toBeVisible();
  });

  test('Step 2: Director opens payment detail -> verifies metadata, rate bands, and itemized lines', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page.getByRole('heading', { level: 2, name: testData.lifecyclePaymentNumber })).toBeVisible({ timeout: 10000 });

    // Overview details
    await expect(page.getByText(testData.lifecycleEmployeeName)).toBeVisible();
    await expect(page.getByText('DRAFT').first()).toBeVisible();

    // Rate Band Summaries
    await expect(page.getByRole('heading', { level: 3, name: 'Rate Band Summaries' })).toBeVisible();

    // Itemized lines
    await expect(page.getByRole('heading', { level: 3, name: 'Itemized Payment Lines' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Attendance' }).first()).toBeVisible();

    // Action buttons visible for draft state
    await expect(page.getByRole('button', { name: 'Approve Payment' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel Payment' })).toBeVisible();
  });

  test('Step 3: Director approves draft payment (Draft -> Approved)', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page.getByRole('button', { name: 'Approve Payment' })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'Approve Payment' }).click();

    // Approve confirmation dialog
    await expect(page.getByRole('heading', { level: 3, name: 'Approve Employee Payment' })).toBeVisible();
    await page.getByRole('button', { name: 'Confirm Approval' }).click();

    // Verify transition to APPROVED state
    await expect(page.getByText(/approved successfully/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('APPROVED').first()).toBeVisible();

    // Approve button replaced by Mark Paid
    await expect(page.getByRole('button', { name: 'Approve Payment' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Mark Paid' })).toBeVisible();
  });

  test('Step 4: Director records settlement (Approved -> Paid) -> read-only state', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page.getByRole('button', { name: 'Mark Paid' })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'Mark Paid' }).click();

    // Settlement modal
    await expect(page.getByRole('heading', { level: 3, name: 'Record Payment Settlement' })).toBeVisible();
    await page.getByPlaceholder(/UTR \/ Cheque \/ Txn Number/i).fill('UTR-E2E-999888');
    await page.getByPlaceholder(/Cleared through bank transfer/i).fill('Direct NEFT transfer verified');

    await page.getByRole('button', { name: 'Confirm & Mark Paid' }).click();

    // Verify transition to PAID state
    await expect(page.getByText(/marked as paid successfully/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('PAID').first()).toBeVisible();

    // Paid settlement banner is displayed
    await expect(page.getByTestId('paid-banner')).toBeVisible();
    await expect(page.getByText('UTR-E2E-999888')).toBeVisible();

    // Action buttons removed (read-only)
    await expect(page.getByRole('button', { name: 'Approve Payment' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Mark Paid' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel Payment' })).not.toBeVisible();
  });

  test('Step 5: Director cancels eligible draft payment with reason -> releases locks and read-only', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto(`/employee-payments/${testData.cancellablePaymentId}`);
    await expect(page.getByRole('heading', { level: 2, name: testData.cancellablePaymentNumber })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: 'Cancel Payment' })).toBeVisible();

    await page.getByRole('button', { name: 'Cancel Payment' }).click();

    // Cancel modal
    await expect(page.getByRole('heading', { level: 3, name: 'Cancel Employee Payment' })).toBeVisible();
    const reasonInput = page.getByPlaceholder(/Provide a mandatory reason for cancelling/i);
    await reasonInput.fill('Duplicate run generated during E2E test suite');

    await page.getByRole('button', { name: 'Confirm Cancellation' }).click();

    // Verify transition to CANCELLED state
    await expect(page.getByText(/cancelled and source records unlocked/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('CANCELLED').first()).toBeVisible();

    // Cancellation banner displayed
    await expect(page.getByTestId('cancellation-banner')).toBeVisible();
    await expect(page.getByText('Duplicate run generated during E2E test suite')).toBeVisible();

    // Action buttons removed (read-only)
    await expect(page.getByRole('button', { name: 'Approve Payment' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Mark Paid' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel Payment' })).not.toBeVisible();
  });

  test('Step 6: Administrator login -> accesses list and detail successfully', async ({ context, page }) => {
    await setupAuthContext(context, testData.adminToken);

    await page.goto('/employee-payments');
    await expect(page.getByRole('heading', { level: 2, name: 'Employee Payments' })).toBeVisible({ timeout: 10000 });

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page.getByRole('heading', { level: 2, name: testData.lifecyclePaymentNumber })).toBeVisible({ timeout: 10000 });
  });

  test('Step 7: Employee login -> /employee-payments and detail route redirect to /403', async ({ context, page }) => {
    await setupAuthContext(context, testData.workerToken);

    await page.goto('/employee-payments');
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();
  });

  test('Step 8: Supervisor login -> /employee-payments and detail route redirect to /403', async ({ context, page }) => {
    await setupAuthContext(context, testData.supervisorToken);

    await page.goto('/employee-payments');
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();

    await page.goto(`/employee-payments/${testData.lifecyclePaymentId}`);
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();
  });
});

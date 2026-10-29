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

  const scriptPath = path.resolve(backendDir, 'e2e_seed_invoices.py');
  const output = execSync(`"${pythonCmd}" "${scriptPath}"`, { cwd: backendDir, encoding: 'utf-8' });

  const jsonMatch = output.match(/\{.*\}/s);
  if (jsonMatch) {
    testData = JSON.parse(jsonMatch[0]);
  } else {
    throw new Error('Failed to parse invoice seeder output: ' + output);
  }
});

async function setupAuthContext(context: any, token: string) {
  await context.addInitScript((authToken: string) => {
    localStorage.setItem('access_token', authToken);
  }, token);
}

async function selectOrFill(page: any, label: string, value: string) {
  const el = page.getByLabel(label);
  await el.waitFor({ state: 'visible' });
  const tagName = await el.evaluate((node: HTMLElement) => node.tagName.toLowerCase());
  if (tagName === 'select') {
    await el.selectOption(value);
  } else {
    await el.fill(value);
  }
}

test.describe.serial('E2E Invoicing Lifecycle & RBAC Verification (Mobile Viewport)', () => {

  test('Step 1: Director login -> Invoices page loads with summary cards', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    await page.goto('/invoices');
    await expect(page.getByText('Client Invoices').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Total Invoices').first()).toBeVisible();
    await expect(page.getByText('Draft Invoices').first()).toBeVisible();
    await expect(page.getByRole('button', { name: '+ New Invoice' })).toBeVisible();
  });

  test('Step 2: Administrator login -> Invoices page loads', async ({ context, page }) => {
    await setupAuthContext(context, testData.adminToken);

    await page.goto('/invoices');
    await expect(page.getByText('Client Invoices').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: '+ New Invoice' })).toBeVisible();
  });

  test('Step 3: Employee -> /invoices redirects to /403', async ({ context, page }) => {
    await setupAuthContext(context, testData.workerToken);

    await page.goto('/invoices');
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();
    await expect(page.getByText('Client Invoices')).not.toBeVisible();
  });

  test('Step 4: Supervisor -> /invoices redirects to /403', async ({ context, page }) => {
    await setupAuthContext(context, testData.supervisorToken);

    await page.goto('/invoices');
    await expect(page).toHaveURL(/\/403/, { timeout: 10000 });
    await expect(page.getByText(/403 — Access Denied/i)).toBeVisible();
    await expect(page.getByText('Client Invoices')).not.toBeVisible();
  });

  test('Step 5-9: Director generates draft invoice from unbilled approved data, overrides rate with mandatory reason, edits tax, issues with confirmation, and verifies read-only state', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    // 1. Navigate to Invoices page
    await page.goto('/invoices');
    await expect(page.getByText('Client Invoices').first()).toBeVisible({ timeout: 10000 });

    // 2. Open Generate Modal
    await page.getByRole('button', { name: '+ New Invoice' }).click();
    await expect(page.getByRole('heading', { name: 'Preview & Generate Invoice' })).toBeVisible();

    // 3. Fill required filters for Dataset A
    await selectOrFill(page, 'Client *', testData.clientAId);
    await selectOrFill(page, 'Project *', testData.projectAId);
    await selectOrFill(page, 'Site *', testData.siteAId);
    await page.getByLabel('Period Start *').fill('2026-10-01');
    await page.getByLabel('Period End *').fill(testData.today);
    await page.getByPlaceholder('e.g. PO-2026-001').fill('PO-E2E-ALPHA-001');

    // 4. Click Preview Billable Records
    const previewBtn = page.getByRole('button', { name: '1. Preview Billable Records' });
    await expect(previewBtn).toBeEnabled();
    await previewBtn.click();

    // Verify unbilled preview results
    await expect(page.getByText('Billable Work Entries')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(testData.activityName).first()).toBeVisible();

    // 5. Generate Draft Invoice
    const genBtn = page.getByRole('button', { name: '2. Generate Draft Invoice' });
    await expect(genBtn).toBeEnabled();
    await genBtn.click();

    // 6. Verify redirection to Draft Invoice Detail
    await expect(page).toHaveURL(/\/invoices\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.getByText(testData.clientAName)).toBeVisible();
    await expect(page.getByText(testData.projectAName)).toBeVisible();
    await expect(page.getByText(testData.siteAName)).toBeVisible();
    await expect(page.getByText('DRAFT').first()).toBeVisible();

    // 7. Change line unit rate
    const rateInput = page.locator('table input[type="number"]').first();
    await expect(rateInput).toBeVisible();
    await rateInput.fill('150');

    // Attempt to save without mandatory override reason -> Assert error validation
    await page.getByRole('button', { name: 'Save Draft' }).click();
    await expect(page.getByText(/Rate override reason is mandatory for line/i)).toBeVisible({ timeout: 10000 });

    // Provide mandatory rate override reason
    const reasonInput = page.getByPlaceholder('* Mandatory reason for override');
    await expect(reasonInput).toBeVisible();
    await reasonInput.fill('Director rate adjustment approved for high-elevation works');

    // 8. Edit tax amount
    const taxInput = page.locator('div').filter({ hasText: /^Tax Amount:/ }).locator('input[type="number"]');
    await expect(taxInput).toBeVisible();
    await taxInput.fill('125.50');

    // Save draft successfully
    await page.getByRole('button', { name: 'Save Draft' }).click();
    await expect(page.getByText('Invoice draft updated successfully.')).toBeVisible({ timeout: 10000 });

    // 9. Issue Confirmation flow
    await page.getByRole('button', { name: 'Issue Invoice' }).click();
    await expect(page.getByRole('heading', { name: 'Issue Invoice' })).toBeVisible();
    await expect(page.getByText(/permanently frozen and immutable/i)).toBeVisible();

    // Confirm Issue
    await page.getByRole('button', { name: 'Confirm & Issue Invoice' }).click();
    await expect(page.getByText(/Invoice issued successfully/i)).toBeVisible({ timeout: 10000 });

    // Verify Read-Only State for Issued Invoice
    await expect(page.getByText('ISSUED').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save Draft' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Issue Invoice' })).not.toBeVisible();
    await expect(page.locator('table input[type="number"]')).not.toBeVisible();
    await expect(page.getByPlaceholder('* Mandatory reason for override')).not.toBeVisible();
  });

  test('Step 10: Cancel confirmation works and cancelled invoice becomes read-only', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    // 1. Generate second draft invoice from Dataset B
    await page.goto('/invoices');
    await expect(page.getByText('Client Invoices').first()).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '+ New Invoice' }).click();
    await expect(page.getByRole('heading', { name: 'Preview & Generate Invoice' })).toBeVisible();

    await selectOrFill(page, 'Client *', testData.clientBId);
    await selectOrFill(page, 'Project *', testData.projectBId);
    await selectOrFill(page, 'Site *', testData.siteBId);
    await page.getByLabel('Period Start *').fill('2026-10-01');
    await page.getByLabel('Period End *').fill(testData.today);

    await page.getByRole('button', { name: '1. Preview Billable Records' }).click();
    await expect(page.getByText('Billable Work Entries')).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '2. Generate Draft Invoice' }).click();
    await expect(page).toHaveURL(/\/invoices\/[a-f0-9-]+/, { timeout: 10000 });

    // 2. Open Cancel Modal
    await expect(page.getByText('DRAFT').first()).toBeVisible();
    await page.getByRole('button', { name: 'Cancel Invoice' }).click();
    await expect(page.getByRole('heading', { name: 'Cancel Invoice' })).toBeVisible();
    await expect(page.getByText(/atomically release its source locks/i)).toBeVisible();

    // 3. Fill mandatory cancellation reason
    const cancelReasonInput = page.getByPlaceholder('State mandatory reason for cancellation');
    await cancelReasonInput.fill('Client contract rescheduled for next billing quarter');

    // 4. Confirm Cancellation
    await page.getByRole('button', { name: 'Confirm Cancellation' }).click();
    await expect(page.getByText('CANCELLED').first()).toBeVisible({ timeout: 10000 });

    // 5. Verify Read-Only State for Cancelled Invoice
    await expect(page.getByRole('button', { name: 'Save Draft' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Issue Invoice' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel Invoice' })).not.toBeVisible();
    await expect(page.locator('table input[type="number"]')).not.toBeVisible();
  });
});

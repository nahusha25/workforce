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
    throw new Error('Failed to parse seeder output: ' + output);
  }
});

async function setupAuthContext(context: any, token: string) {
  await context.addInitScript((authToken: string) => {
    localStorage.setItem('access_token', authToken);
  }, token);
}

test.describe.serial('Payment Summary Scope Filter & Export E2E (D-4)', () => {
  test('Complete Scope Filter & Export Journey (Default all -> Unbilled Only -> Export xlsx/pdf -> Restore all)', async ({ context, page }) => {
    await setupAuthContext(context, testData.directorToken);

    // 1. Initial page load: Director opens Payment Summary
    const initialReportRequestPromise = page.waitForRequest(req =>
      req.url().includes('/api/v1/reports/payment-summary') && req.method() === 'GET'
    );

    await page.goto('/reports/payment-summary');

    const initialReq = await initialReportRequestPromise;
    const reqUrl = new URL(initialReq.url());
    const scopeParam = reqUrl.searchParams.get('scope');
    expect(scopeParam === 'all' || scopeParam === null).toBe(true);

    // Verify title and page loaded
    await expect(page.getByText('Estimated Payment Summary').first()).toBeVisible({ timeout: 10000 });

    // Verify Scope dropdown defaults to 'all' (All Earned Labor)
    const scopeSelect = page.getByTestId('filter-payment-scope');
    await expect(scopeSelect).toBeVisible();
    await expect(scopeSelect).toHaveValue('all');

    // Verify explanatory notice banner text for Total Earned Labor Scope
    const notice = page.getByTestId('payment-scope-notice');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText('Total Earned Labor Scope');
    await expect(notice).toContainText('Does not reflect unpaid payroll liabilities');

    // Verify preview disclaimer banner is present
    const disclaimer = page.getByTestId('payment-disclaimer-banner');
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toContainText('Default view reflects total earned labor value, not unpaid liabilities');

    // 2. Switching to unbilled_only updates notice banner and sends scope=unbilled_only to API
    const scopedRequestPromise = page.waitForRequest(req =>
      req.url().includes('/api/v1/reports/payment-summary') &&
      req.url().includes('scope=unbilled_only') &&
      req.method() === 'GET'
    );

    await scopeSelect.selectOption('unbilled_only');

    const scopedReq = await scopedRequestPromise;
    const scopedUrl = new URL(scopedReq.url());
    expect(scopedUrl.searchParams.get('scope')).toBe('unbilled_only');

    await expect(scopeSelect).toHaveValue('unbilled_only');

    // Verify notice banner updates text to Unbilled Only Scope
    await expect(notice).toContainText('Unbilled Only Scope');
    await expect(notice).toContainText('Cancelled payment records release their source entries back to this view');

    // 3. Excel and PDF export requests carry selected scope (unbilled_only)
    const excelRequestPromise = page.waitForRequest(req =>
      req.url().includes('/api/v1/reports/payment-summary/export') &&
      req.url().includes('format=xlsx') &&
      req.method() === 'GET'
    );

    const excelBtn = page.getByTestId('export-excel-btn');
    await expect(excelBtn).toBeVisible();
    await excelBtn.click();

    const excelReq = await excelRequestPromise;
    const excelUrl = new URL(excelReq.url());
    expect(excelUrl.searchParams.get('scope')).toBe('unbilled_only');
    expect(excelUrl.searchParams.get('format')).toBe('xlsx');

    const pdfRequestPromise = page.waitForRequest(req =>
      req.url().includes('/api/v1/reports/payment-summary/export') &&
      req.url().includes('format=pdf') &&
      req.method() === 'GET'
    );

    const pdfBtn = page.getByTestId('export-pdf-btn');
    await expect(pdfBtn).toBeVisible();
    await pdfBtn.click();

    const pdfReq = await pdfRequestPromise;
    const pdfUrl = new URL(pdfReq.url());
    expect(pdfUrl.searchParams.get('scope')).toBe('unbilled_only');
    expect(pdfUrl.searchParams.get('format')).toBe('pdf');

    // 4. Switching back to all restores default scope, notice, and export parameter
    await scopeSelect.selectOption('all');
    await expect(scopeSelect).toHaveValue('all');

    // Verify notice banner restores Total Earned Labor text
    await expect(notice).toContainText('Total Earned Labor Scope');
    await expect(notice).toContainText('Does not reflect unpaid payroll liabilities');

    // Verify export with scope restored to 'all'
    const defaultExportPromise = page.waitForRequest(req =>
      req.url().includes('/api/v1/reports/payment-summary/export') &&
      req.url().includes('format=xlsx') &&
      req.method() === 'GET'
    );

    await excelBtn.click();

    const defaultExportReq = await defaultExportPromise;
    const defaultExportUrl = new URL(defaultExportReq.url());
    expect(defaultExportUrl.searchParams.get('scope')).toBe('all');
    expect(defaultExportUrl.searchParams.get('format')).toBe('xlsx');
  });
});

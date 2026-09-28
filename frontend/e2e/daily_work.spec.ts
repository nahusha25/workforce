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

  const scriptPath = path.resolve(backendDir, 'e2e_seed.py');
  const output = execSync(`"${pythonCmd}" "${scriptPath}"`, { cwd: backendDir, encoding: 'utf-8' });
  
  const jsonMatch = output.match(/\{.*\}/s);
  if (jsonMatch) {
    testData = JSON.parse(jsonMatch[0]);
  } else {
    throw new Error('Failed to parse seeder output: ' + output);
  }
});

async function setupAuthenticatedEmployeeContext(context: any, token: string) {
  await context.addInitScript((authToken: string) => {
    localStorage.setItem('access_token', authToken);
  }, token);
}

test.describe.serial('Daily Work & Cross-Day Attendance E2E (Mobile Viewport)', () => {

  test('E2E-J06: Complete Daily Work Multi-Activity Capture Journey (Lines -> Attachments -> Submit -> Read-only)', async ({ context, page, request }) => {
    // 1. Establish authenticated context
    await setupAuthenticatedEmployeeContext(context, testData.employeeToken);
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.siteLat, longitude: testData.siteLng });

    // 2. Ensure employee is checked in for today via attendance API
    await request.post('/api/v1/attendance/check-in', {
      headers: { Authorization: `Bearer ${testData.employeeToken}` },
      data: {
        latitude: testData.siteLat,
        longitude: testData.siteLng,
      },
    });

    // 3. Navigate to Daily Work page
    await page.goto('/daily-work');
    await expect(page.getByText('Daily Work Entry').first()).toBeVisible({ timeout: 10000 });
    
    // Ensure "not checked in" banner is NOT present
    await expect(page.getByTestId('attendance-banner-not-checked-in')).not.toBeVisible();

    // 4. Line 1: Activity, Quantity, UOM auto-derivation, Remarks
    const activitySelect1 = page.locator('select').first();
    await activitySelect1.selectOption({ label: 'Cable Pulling (CABLE) - metres' });
    
    // Verify auto-derived UOM badge appears
    await expect(page.locator('[title="Auto-derived Unit of Measure"]').first()).toHaveText('metres');

    // Fill quantity and remarks for line 1
    const qtyInput1 = page.locator('#quantity-input-0');
    await qtyInput1.fill('45');
    
    const remarksInput1 = page.locator('#remarks-input-0');
    await remarksInput1.fill('Pulling CAT6 across corridor A');

    // 5. Line 2: Add another activity line
    const addLineBtn = page.getByRole('button', { name: /Add Another Activity Line/i });
    await expect(addLineBtn).toBeVisible();
    await addLineBtn.click();

    // Line 2 should now be visible
    const activitySelect2 = page.getByLabel('Activity #2 *');
    await activitySelect2.selectOption({ label: 'Device Installation (DEVICE) - devices' });
    await expect(page.locator('[title="Auto-derived Unit of Measure"]').nth(1)).toHaveText('devices');

    const qtyInput2 = page.locator('#quantity-input-1');
    await qtyInput2.fill('6');

    // 6. Expand Attachments on Line 1 & Auto-save
    const toggleAttachmentsBtn = page.getByRole('button', { name: /Attachments & Materials/i }).first();
    await toggleAttachmentsBtn.click();

    // Prompt to auto-save appears
    const autoSaveBtn = page.getByRole('button', { name: /Auto-save & Attach/i });
    await expect(autoSaveBtn).toBeVisible();
    await autoSaveBtn.click();

    // Line is now saved and attachments controls are available
    await expect(page.getByRole('heading', { name: 'Site Progress Photos' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Material Transactions' })).toBeVisible();

    // 7. Attach a photo using file input
    const photoInput = page.locator('input[type="file"][aria-label="Select photo from files"]').first();
    // Valid 1x1 JPEG buffer
    const sampleJpeg = Buffer.from(
      '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=',
      'base64'
    );
    await photoInput.setInputFiles({
      name: 'corridor_cabling.jpg',
      mimeType: 'image/jpeg',
      buffer: sampleJpeg,
    });

    // Wait for photo upload to finish and thumbnail image to appear
    await expect(page.getByAltText('Work site progress').first()).toBeVisible({ timeout: 10000 });

    // 8. Attach a consumed material
    const addMatBtn = page.getByRole('button', { name: 'Add Material' }).first();
    await addMatBtn.click();

    await page.locator('#material-item-name').fill('Cat6 Cable Box');
    await page.locator('#material-quantity').fill('2');
    await page.locator('#material-amount').fill('250.00');

    const recordMatBtn = page.getByRole('button', { name: 'Record Material' });
    await recordMatBtn.click();

    // Verify material appears in the list
    await expect(page.getByTestId('materials-list').getByText('Cat6 Cable Box').first()).toBeVisible({ timeout: 10000 });

    // 9. Open Submission Confirmation Modal
    const submitBtn = page.getByRole('button', { name: /Submit Work/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Modal opens with review summary
    await expect(page.getByTestId('submit-confirmation-modal')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Review & Submit Daily Work' })).toBeVisible();
    await expect(page.getByTestId('submit-confirmation-modal').getByText('Cable Pulling')).toBeVisible();
    await expect(page.getByTestId('submit-confirmation-modal').getByText('Device Installation')).toBeVisible();

    // 10. Confirm and Submit
    const confirmBtn = page.getByRole('button', { name: 'Confirm & Submit' });
    await confirmBtn.click();

    // Verify success banner and locked state
    await expect(page.getByText('Work entry submitted successfully! Submitted for supervisor review.')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('locked-notice')).toBeVisible();

    // Inputs are now disabled in submitted view
    await expect(qtyInput1).toBeDisabled();
    await expect(submitBtn).not.toBeVisible();
  });

  test('E2E-J07: Cross-Day Checkout Scenario (Unclosed prior-day session can check out)', async ({ context, page }) => {
    // Employee 4 was seeded with an unclosed session from yesterday
    await setupAuthenticatedEmployeeContext(context, testData.employee4Token);
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.siteLat, longitude: testData.siteLng });

    // Navigate to /attendance
    await page.goto('/attendance');
    await expect(page.locator('text=GPS Ready')).toBeVisible({ timeout: 10000 });

    // Verify system shows employee as currently checked in from prior day
    await expect(page.getByText('Current Status:')).toBeVisible();
    await expect(page.getByText('Checked In', { exact: true })).toBeVisible();
    await expect(page.locator('text=Since:')).toBeVisible();

    // Click CHECK OUT
    const checkOutBtn = page.getByRole('button', { name: /CHECK OUT/i });
    await expect(checkOutBtn).toBeEnabled();
    await checkOutBtn.click();

    // Wait for either the warning modal or the success message
    const warningBtn = page.getByRole('button', { name: 'Check out anyway' });
    const successMsg = page.getByText('Successfully checked out!', { exact: true });

    try {
      await warningBtn.waitFor({ state: 'visible', timeout: 5000 });
      await warningBtn.click();
    } catch {
      // No warning modal appeared, checkout completed directly
    }

    // Verify checkout succeeds without any "No active check-in found for today" error!
    await expect(page.getByText(/No active check-in found for today/i)).not.toBeVisible();
    await expect(successMsg).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Checked Out', { exact: true })).toBeVisible();
  });
});

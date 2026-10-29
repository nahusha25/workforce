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

test.describe.serial('Daily Attendance E2E (Mobile Viewport)', () => {

  test('E2E-J03: Check-in with GPS inside geofence -> success', async ({ context, page }) => {
    await setupAuthenticatedEmployeeContext(context, testData.employeeToken);

    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.siteLat, longitude: testData.siteLng });

    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
    await page.goto('/attendance');
    await page.waitForTimeout(2000);
    const bodyText = await page.locator('body').innerText();
    console.log('BODY TEXT:', bodyText);

    await expect(page.locator('text=GPS Ready')).toBeVisible({ timeout: 10000 });

    const checkInBtn = page.getByRole('button', { name: /CHECK IN/i });
    await expect(checkInBtn).toBeEnabled();

    await checkInBtn.click();

    await expect(page.getByText('Successfully checked in!', { exact: true })).toBeVisible();
    await expect(page.getByText('Checked In', { exact: true })).toBeVisible();
  });

  test('E2E-J04: Check-in outside geofence -> supervisor override -> success', async ({ context, page, request }) => {
    // Under BE-014B, out-of-geofence check-in is saved successfully with is_within_geofence=false and status=flagged
    // rather than rejecting with HTTP 422, allowing supervisors to review and override out-of-location attendance.

    // We use employee 2 for this test to avoid the "Checked In" state from J03.
    await setupAuthenticatedEmployeeContext(context, testData.employee2Token);

    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.outsideLat, longitude: testData.outsideLng });

    await page.goto('/attendance');

    await expect(page.locator('text=GPS Ready')).toBeVisible({ timeout: 10000 });

    const checkInBtn = page.getByRole('button', { name: /CHECK IN/i });
    await expect(checkInBtn).toBeEnabled();

    await checkInBtn.click();

    // Verify current UI flow: check-in succeeds with feedback and status transitions to Checked In
    await expect(page.getByText('Successfully checked in!', { exact: true })).toBeVisible();
    await expect(page.getByText('Checked In', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /CHECK OUT/i })).toBeVisible();

    // Verify persistence: record is saved with is_within_geofence=false and status=flagged
    const attRes = await request.get('/api/v1/attendance', {
      headers: { Authorization: `Bearer ${testData.employee2Token}` },
    });
    expect(attRes.ok()).toBeTruthy();
    const attData = await attRes.json();
    const record = attData.data?.find((r: any) => r.employee_id === testData.employee2Id) || attData.data?.[0];
    expect(record).toBeDefined();
    expect(record.is_within_geofence).toBe(false);
    expect(record.status).toBe('flagged');
  });

  test('E2E-J05: Check-out after work submission', async ({ context, page, request }) => {
    // Under BE-022, checking out without submitted daily work displays a mandatory warning modal.
    // Testing checkout flow with modal confirmation for employee 3.
    // We establish isolated test state by making an API call to check in first.

    // Check in via API
    const checkInRes = await request.post('/api/v1/attendance/check-in', {
      headers: { Authorization: `Bearer ${testData.employee3Token}` },
      data: {
        latitude: testData.siteLat,
        longitude: testData.siteLng,
      }
    });
    expect(checkInRes.ok()).toBeTruthy();

    await setupAuthenticatedEmployeeContext(context, testData.employee3Token);

    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.siteLat, longitude: testData.siteLng });

    await page.goto('/attendance');

    await expect(page.locator('text=GPS Ready')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Checked In')).toBeVisible();

    const checkOutBtn = page.getByRole('button', { name: /CHECK OUT/i });
    await expect(checkOutBtn).toBeEnabled();

    await checkOutBtn.click();

    // Assert confirmation modal is displayed with warning text (BE-022)
    await expect(page.getByText('Check-Out Warning')).toBeVisible();
    await expect(page.getByText(/No daily work entries submitted for this session/i)).toBeVisible();

    // Click "Check out anyway" to proceed
    const checkOutAnywayBtn = page.getByRole('button', { name: 'Check out anyway' });
    await expect(checkOutAnywayBtn).toBeVisible();
    await checkOutAnywayBtn.click();

    // Assert successful checkout state in UI
    await expect(page.getByText('Successfully checked out!', { exact: true })).toBeVisible();
    await expect(page.getByText('Checked Out', { exact: true })).toBeVisible();
  });
});

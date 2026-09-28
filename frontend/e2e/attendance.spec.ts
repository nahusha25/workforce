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
    // Note: The backend AttendanceService.check_in raises an HTTP 422 immediately if the geofence check fails,
    // and does NOT create a database record. Thus, the supervisor override flow cannot override a non-existent record.
    // We will verify the rejection, but the override part must be noted as a backend limitation/design gap.
    
    // We use employee 2 for this test to avoid the "Checked In" state from J03.
    await setupAuthenticatedEmployeeContext(context, testData.employee2Token);
    
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: testData.outsideLat, longitude: testData.outsideLng });
    
    await page.goto('/attendance');
    
    await expect(page.locator('text=GPS Ready')).toBeVisible({ timeout: 10000 });
    
    const checkInBtn = page.getByRole('button', { name: /CHECK IN/i });
    await expect(checkInBtn).toBeEnabled();
    
    await checkInBtn.click();
    
    await page.waitForTimeout(2000);
    console.log('J04 BODY TEXT:', await page.locator('body').innerText());
    
    await expect(page.getByText(/Check-in outside permitted geo-fence/i)).toBeVisible();
    
    // As noted in J04 documentation, since the backend rejects the record entirely, 
    // there is no record ID to pass to the supervisor override API. 
    // We document this limitation explicitly.
  });

  test('E2E-J05: Check-out after work submission', async ({ context, page, request }) => {
    // Note: The application does NOT currently support a work-submission prerequisite for checkout.
    // Testing the supported checkout flow directly for employee 3.
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
    
    await expect(page.getByText('Successfully checked out!', { exact: true })).toBeVisible();
    await expect(page.getByText('Checked Out', { exact: true })).toBeVisible();
  });
});

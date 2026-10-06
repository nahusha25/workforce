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

  const scriptPath = path.resolve(backendDir, 'e2e_seed_verification.py');
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

test.describe.serial('E2E-005: Supervisor Verification & Admin Reopen Flow (Mobile Viewport)', () => {

  test('Step 1-4: Supervisor views queue with exception badges, approves work entry & normal material, confirms high-value warning modal, and verifies reviewed state', async ({ context, page }) => {
    // 1. Authenticate as Supervisor
    await setupAuthContext(context, testData.supervisorToken);

    // 2. Navigate to Verification Queue for today's date
    await page.goto(`/verification?date=${testData.today}`);
    await expect(page.getByText('Supervisor Verification Queue').first()).toBeVisible({ timeout: 10000 });

    // 3. Locate Worker 1 queue card
    const workerCard = page.locator(`[aria-label="Verify records for ${testData.worker1Name}"]`);
    await expect(workerCard).toBeVisible({ timeout: 10000 });

    // Verify exception badges on queue card:
    // Out of location (from geofence violation) and High-Value Material (amount > purchase_approval_limit)
    await expect(workerCard.getByText('Out of Location')).toBeVisible();
    await expect(workerCard.getByText(/High[- ]Value Material/i)).toBeVisible();

    // Verify queue card shows Pending Review
    await expect(workerCard.getByTestId('pending-badge')).toBeVisible();

    // 4. Click queue card to navigate to Employee Day Detail
    await workerCard.click();
    await expect(page).toHaveURL(new RegExp(`/verification/${testData.worker1Id}`));
    await expect(page.getByText(testData.worker1Name).first()).toBeVisible({ timeout: 10000 });

    // 5. Approve Attendance Record
    const approveAttBtn = page.getByTestId('approve-attendance-btn');
    await expect(approveAttBtn).toBeVisible();
    await approveAttBtn.click();

    // Confirmation modal opens
    const confirmApproveBtn = page.getByTestId('confirm-approve-btn');
    await expect(confirmApproveBtn).toBeVisible();
    await confirmApproveBtn.click();
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // 6. Approve Daily Work Entry
    const approveWorkBtn = page.getByTestId(`approve-work-entry-${testData.dwe1Id}`);
    await expect(approveWorkBtn).toBeVisible();
    await approveWorkBtn.click();

    await expect(confirmApproveBtn).toBeVisible();
    await confirmApproveBtn.click();
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // 7. Approve Normal Material (Heat Shrink Sleeve - consumed, amount 150 < 5000 limit)
    const approveNormMatBtn = page.getByTestId(`approve-material-${testData.matNormalId}`);
    await expect(approveNormMatBtn).toBeVisible();
    await approveNormMatBtn.click();

    // Normal material modal should NOT display high-value warning
    await expect(page.getByTestId('high-value-warning')).not.toBeVisible();
    await expect(confirmApproveBtn).toBeVisible();
    await confirmApproveBtn.click();
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // 8. Approve High-Value Material (Fusion Cleaver Blade - purchased, amount 4500 > 1000 limit)
    const approveHighMatBtn = page.getByTestId(`approve-material-${testData.matHighId}`);
    await expect(approveHighMatBtn).toBeVisible();
    await approveHighMatBtn.click();

    // Explicitly verify high-value warning modal is displayed
    const highValWarning = page.getByTestId('high-value-warning');
    await expect(highValWarning).toBeVisible();
    await expect(highValWarning.getByText('Approval Limit Warning')).toBeVisible();
    await expect(highValWarning.getByText('This purchase exceeds the approval limit')).toBeVisible();

    // Explicitly confirm approval in the warning modal
    await confirmApproveBtn.click();
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // 9. Return to Verification Queue and verify reviewed state
    const backLink = page.getByTestId('back-link');
    await backLink.click();
    await expect(page).toHaveURL(new RegExp(`/verification\\?date=${testData.today}`));

    // Worker 1 card should now show that it is no longer pending (all submitted items verified)
    const reviewedCard = page.locator(`[aria-label="Verify records for ${testData.worker1Name}"]`);
    await expect(reviewedCard).toBeVisible({ timeout: 10000 });
    await expect(reviewedCard.getByTestId('pending-badge')).not.toBeVisible();
    await expect(reviewedCard.getByTestId('nothing-pending-badge')).toBeVisible();
    await expect(reviewedCard.getByText('Nothing pending')).toBeVisible();
  });

  test('Step 5: Administrator logs in, reopens approved item with mandatory remarks, and timeline shows chronological events with actor names', async ({ context, page }) => {
    // 1. Authenticate as Administrator
    await setupAuthContext(context, testData.adminToken);
    await page.goto(`/verification/${testData.worker1Id}?date=${testData.today}`);
    await page.evaluate((tok) => {
      localStorage.setItem('access_token', tok);
    }, testData.adminToken);
    await page.reload();
    await expect(page.getByText(testData.worker1Name).first()).toBeVisible({ timeout: 10000 });

    // 3. Admin sees Reopen action on approved work entry
    const reopenWorkBtn = page.getByTestId(`reopen-work-entry-${testData.dwe1Id}`);
    await expect(reopenWorkBtn).toBeVisible();
    await reopenWorkBtn.click({ force: true });

    // 4. VerificationRemarksModal opens with title "Reopen — Mandatory Remarks"
    await expect(page.getByText('Reopen — Mandatory Remarks')).toBeVisible();
    const confirmReopenBtn = page.getByRole('button', { name: 'Confirm Reopen' });
    await expect(confirmReopenBtn).toBeDisabled(); // Disabled before 10 chars

    // Fill valid mandatory remarks (>= 10 chars)
    const remarksInput = page.locator('textarea[placeholder*="Provide a specific reason"]');
    await remarksInput.fill('Reopening entry for supervisor measurement audit and joint recalculation');
    await expect(confirmReopenBtn).toBeEnabled();

    await confirmReopenBtn.click({ force: true });
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // Work entry status is now updated to correction_required / Returned for Correction
    await expect(page.getByText(/correction_required|Returned for Correction/i).first()).toBeVisible();

    // 5. Verify AuditHistoryTimeline shows both events in chronological order with correct actor names
    // Target the specific work entry's audit history section (excluding nested material timelines)
    const workEntryCard = page.locator('[data-testid="work-entry-card"]').filter({ hasText: testData.activity1Name });
    await expect(workEntryCard).toBeVisible();
    const auditTimeline = workEntryCard
      .locator('div')
      .filter({ hasText: 'Work Entry Audit History' })
      .locator('ol[aria-label="Verification audit history"]');
    await expect(auditTimeline).toBeVisible();

    // Event 1: Approved by Supervisor
    await expect(auditTimeline.getByText('Approved').first()).toBeVisible();
    await expect(auditTimeline.getByText(`by ${testData.supervisorName}`)).toBeVisible();

    // Event 2: Returned for Correction by Administrator with remarks
    await expect(auditTimeline.getByText('Returned for Correction').first()).toBeVisible();
    await expect(auditTimeline.getByText(`by ${testData.adminName}`)).toBeVisible();
    await expect(auditTimeline.getByText('Reopening entry for supervisor measurement audit and joint recalculation')).toBeVisible();
  });

  test('Step 6: Supervisor rejects submitted item with mandatory remarks, confirmed excluded from further action buttons', async ({ context, page }) => {
    // 1. Authenticate as Supervisor
    await setupAuthContext(context, testData.supervisorToken);

    // 2. Navigate to Worker 2 day detail
    await page.goto(`/verification/${testData.worker2Id}?date=${testData.today}`);
    await page.evaluate((tok) => {
      localStorage.setItem('access_token', tok);
    }, testData.supervisorToken);
    await page.reload();
    await expect(page.getByText(testData.worker2Name).first()).toBeVisible({ timeout: 10000 });

    // 3. Click Reject on submitted Daily Work Entry 2
    const rejectBtn = page.getByTestId(`reject-work-entry-${testData.dwe2Id}`);
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click({ force: true });

    // 4. VerificationRemarksModal opens with title "Reject — Mandatory Remarks"
    await expect(page.getByText('Reject — Mandatory Remarks')).toBeVisible();
    const confirmRejectBtn = page.getByRole('button', { name: 'Confirm Rejection' });
    await expect(confirmRejectBtn).toBeDisabled();

    // Fill valid mandatory remarks (>= 10 chars)
    const remarksInput = page.locator('textarea[placeholder*="Provide a specific reason"]');
    await remarksInput.fill('Fiber attenuation test failed standards. Re-splicing required.');
    await expect(confirmRejectBtn).toBeEnabled();

    await confirmRejectBtn.click({ force: true });
    await expect(page.getByTestId('success-notice')).toBeVisible({ timeout: 10000 });

    // 5. Status shows Rejected
    await expect(page.getByText(/rejected/i).first()).toBeVisible();

    // 6. Action buttons (Approve, Reject, Return) are now excluded from the card
    await expect(page.getByTestId(`approve-work-entry-${testData.dwe2Id}`)).not.toBeVisible();
    await expect(page.getByTestId(`reject-work-entry-${testData.dwe2Id}`)).not.toBeVisible();
    await expect(page.getByTestId(`return-work-entry-${testData.dwe2Id}`)).not.toBeVisible();
  });
});

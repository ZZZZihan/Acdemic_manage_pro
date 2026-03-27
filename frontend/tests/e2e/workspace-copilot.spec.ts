import { expect, test } from '@playwright/test'

test.describe('Workspace Copilot', () => {
  test('creates approval and task flow from real UI actions', async ({ page }) => {
    await page.goto('/workspace')

    await expect(page.getByTestId('workspace-title')).toBeVisible()
    const approvalCards = page.getByTestId('approval-card')
    const approvalCountBefore = await approvalCards.count()

    await page.getByTestId('send-message-button').click()
    await expect(approvalCards).toHaveCount(approvalCountBefore + 1)

    await page.getByTestId('quick-action-task').click()
    await page.getByTestId('send-message-button').click()
    await expect(page.getByText('task.create')).toBeVisible()

    const newlyCreatedApprovalCard = approvalCards.nth(approvalCountBefore)
    await newlyCreatedApprovalCard.getByTestId('approval-approve-button').click()
    await expect(newlyCreatedApprovalCard).toContainText('approved')
  })
})

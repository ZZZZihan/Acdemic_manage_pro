import { expect, test } from '@playwright/test'

test.describe('Ollama Local Mode', () => {
  test('keeps external-write request in local read-only mode', async ({ page }) => {
    await page.goto('/workspace')
    await expect(page.getByTestId('workspace-title')).toBeVisible()

    const approvalCards = page.getByTestId('approval-card')
    const approvalCountBefore = await approvalCards.count()

    await page.getByTestId('provider-select').click()
    await page.getByRole('option', { name: 'ollama' }).click()
    await page.getByTestId('send-message-button').click()

    await expect(approvalCards).toHaveCount(approvalCountBefore)

    const assistantMessages = page
      .locator('[data-testid="thread-message"][data-role="assistant"]')
      .filter({ has: page.locator('[data-testid="message-provider"]', { hasText: 'ollama' }) })
    await expect(assistantMessages.last()).toContainText('本地/只读能力')
  })
})

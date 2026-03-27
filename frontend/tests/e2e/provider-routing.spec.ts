import { expect, test } from '@playwright/test'

test.describe('Provider Routing', () => {
  test('escalates deepseek external write request to openai', async ({ page }) => {
    await page.goto('/workspace')
    await expect(page.getByTestId('workspace-title')).toBeVisible()

    await page.getByTestId('provider-select').click()
    await page.getByRole('option', { name: 'deepseek' }).click()

    await page.getByTestId('send-message-button').click()
    await expect(page.getByTestId('approval-card').first()).toBeVisible()

    const assistantMessages = page
      .getByTestId('thread-message')
      .filter({ has: page.locator('[data-testid="message-provider"]', { hasText: 'openai' }) })
    await expect(assistantMessages.last()).toContainText('高风险外部协同请求')
  })
})

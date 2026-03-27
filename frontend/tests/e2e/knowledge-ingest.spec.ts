import { expect, test } from '@playwright/test'

test.describe('Knowledge Ingest', () => {
  test('seeds MCP note and can retrieve it through knowledge.search', async ({ page, request }) => {
    await page.goto('/workspace')
    await expect(page.getByTestId('workspace-title')).toBeVisible()

    await page.getByTestId('quick-action-seed-knowledge').click()
    await expect(page.getByText('已写入一条示例知识')).toBeVisible()

    const response = await request.post('http://127.0.0.1:8003/mcp/tools/call', {
      data: {
        name: 'knowledge.search',
        arguments: {
          query: 'tools、resources、prompts',
          limit: 5,
        },
      },
    })
    expect(response.ok()).toBeTruthy()
    const payload = await response.json()
    const titles = payload.result.items.map((item: { title: string }) => item.title)
    expect(titles).toContain('MCP 设计笔记')
  })
})

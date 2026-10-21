import { expect, test } from './authenticated-test'

test.describe('Knowledge Ingest', () => {
  test('seeds MCP note and can retrieve it through knowledge.search', async ({ page, request }) => {
    await page.goto('/workspace')
    await expect(page.getByTestId('workspace-title')).toBeVisible()

    const ingested = page.waitForResponse(response => response.url().endsWith('/api/v2/knowledge/assets') && response.request().method() === 'POST')
    await page.getByTestId('quick-action-seed-knowledge').click()
    const ingestResponse = await ingested
    expect(ingestResponse.status()).toBe(201)
    const asset = (await ingestResponse.json()).asset
    await expect(page.getByText('已写入一条示例知识')).toBeVisible()

    const response = await request.post('/mcp/tools/call', {
      headers: { Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('token'))}` },
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
    expect(payload.result.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: asset.id, title: 'MCP 设计笔记' }),
    ]))
  })
})

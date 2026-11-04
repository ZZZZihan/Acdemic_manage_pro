import { test as base, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const test = process.env.PW_EXECUTABLE_PATH ? base.extend({
  context: async ({ playwright, launchOptions, baseURL }, use) => {
    const browser = await playwright.chromium.launch(launchOptions)
    const context = await browser.newContext({ baseURL })
    await use(context)
    await context.close()
    await browser.close()
  },
}) : base

const seed = JSON.parse(fs.readFileSync(path.join(process.env.AUTH_E2E_DATA_DIR!, 'seed.json'), 'utf8'))

for (const view of ['create', 'edit', 'detail']) {
  test(`meeting ${view} upload refreshes an expired access token`, async ({ page, request }) => {
    let url = '/meetings/create'
    if (view !== 'create') {
      const created = await request.post('/api/v1/meetings', {
        headers: { Authorization: `Bearer ${seed.access_token}` },
        data: { title: `Auth upload ${view}`, start_time: '2030-01-01T10:00:00', end_time: '2030-01-01T11:00:00' },
      })
      expect(created.status()).toBe(201)
      const meeting = await created.json()
      url = `/meetings/${meeting.id}${view === 'edit' ? '/edit' : ''}`
    }
    await page.addInitScript((session) => {
      localStorage.setItem('token', session.access_token)
      localStorage.setItem('refreshToken', session.refresh_token)
      localStorage.setItem('user', JSON.stringify(session.user))
    }, seed)
    await page.goto(url)
    await expect(page.locator('input[type=file]').first()).toBeAttached()
    await page.waitForLoadState('networkidle')
    await page.evaluate(async (expired) => {
      const { updateAuthData } = await import('/src/utils/authSession.js')
      updateAuthData({ access_token: expired })
    }, seed.expired_token)

    let refreshes = 0
    page.on('request', request => { if (request.url().includes('/auth/refresh')) refreshes++ })
    const uploaded = page.waitForResponse(response =>
      response.url().includes('/meetings/attachments/upload') && response.status() === 200)
    await page.locator('input[type=file]').first().setInputFiles({
      name: `auth-meeting-${view}.txt`, mimeType: 'text/plain', buffer: Buffer.from('isolated auth regression'),
    })
    expect((await (await uploaded).json()).file_path).toMatch(/\.txt$/)
    expect(refreshes).toBe(1)
    expect(await page.evaluate(() => localStorage.getItem('token'))).not.toBe(seed.expired_token)
  })
}

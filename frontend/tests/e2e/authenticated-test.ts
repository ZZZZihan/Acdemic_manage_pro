import { test as base, expect } from '@playwright/test'
import { randomUUID } from 'node:crypto'

// Serverless Chromium needs a fresh process when its last context has closed.
const browserTest = process.env.PW_EXECUTABLE_PATH ? base.extend({
  context: async ({ playwright, launchOptions, baseURL }, use) => {
    const browser = await playwright.chromium.launch(launchOptions)
    const context = await browser.newContext({ baseURL })
    await use(context)
    await context.close()
    await browser.close()
  },
}) : base

export const test = browserTest.extend<{ authSession: unknown }>({
  authSession: [async ({ page, request }, use) => {
    const suffix = randomUUID()
    const credentials = { email: `${suffix}@example.test`, password: 'FixturePass123!' }
    const registered = await request.post('/api/v1/auth/register', { data: { ...credentials, username: suffix } })
    expect(registered.status()).toBe(201)
    const response = await request.post('/api/v1/auth/login', { data: credentials })
    expect(response.ok()).toBeTruthy()
    const data = await response.json()
    await page.addInitScript((session) => {
      localStorage.setItem('token', session.access_token)
      localStorage.setItem('refreshToken', session.refresh_token)
      localStorage.setItem('user', JSON.stringify(session.user))
    }, data)
    await use(data)
  }, { auto: true }],
})
export { expect }

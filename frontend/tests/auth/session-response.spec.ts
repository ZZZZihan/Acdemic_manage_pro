import { test as base, expect } from '@playwright/test'
import { randomUUID } from 'node:crypto'

const test = process.env.PW_EXECUTABLE_PATH ? base.extend({
  context: async ({ playwright, launchOptions, baseURL }, use) => {
    const browser = await playwright.chromium.launch(launchOptions)
    const context = await browser.newContext({ baseURL })
    await use(context)
    await context.close()
    await browser.close()
  },
}) : base

for (const url of ['/api/v1/auth/user']) {
  test(`discards a late successful ${url} response after logout`, async ({ page }) => {
    await page.goto('/auth/login')
    await page.getByPlaceholder('请输入邮箱').fill('auth-member@example.test')
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('FixturePass123!')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page.getByTestId('workspace-title')).toBeVisible()
    await page.waitForLoadState('networkidle')

    let release!: () => void
    const held = new Promise<void>(resolve => { release = resolve })
    let received!: () => void
    const responseReceived = new Promise<void>(resolve => { received = resolve })
    // Hold the real backend's successful response; no endpoint payload/status is mocked.
    await page.route(`**${url}?late-session-response=1`, async route => {
      const response = await route.fetch()
      expect(response.status()).toBe(200)
      received()
      await held
      await route.fulfill({ response })
    })
    await page.evaluate(async (url) => {
      const module = url.startsWith('/api/v2/') ? await import('/src/utils/axiosV2.js') : await import('/src/utils/axios.js')
      window.pendingSessionResponse = module.default.get(`${url}?late-session-response=1`)
        .then(() => 'accepted', () => 'discarded')
    }, url)
    await responseReceived
    await page.evaluate(async () => {
      const { useAuthStore } = await import('/src/stores/auth.js')
      await useAuthStore().logout()
    })
    release()
    expect(await page.evaluate(() => window.pendingSessionResponse)).toBe('discarded')
    await expect(page).toHaveURL(/auth\/login/)
  })
}

test('administrator demotion takes effect for old tokens and the role-management UI', async ({ page, request }) => {
  const suffix = randomUUID()
  const credentials = { email: `${suffix}@example.test`, password: 'FixturePass123!' }
  const registered = await request.post('/api/v1/auth/register', { data: { ...credentials, username: suffix } })
  expect(registered.status()).toBe(201)
  const member = (await registered.json()).user
  const adminLogin = await request.post('/api/v1/auth/login', { data: {
    email: 'auth-admin@example.test', password: 'FixturePass123!',
  } })
  expect(adminLogin.status()).toBe(200)
  const adminHeaders = { Authorization: `Bearer ${(await adminLogin.json()).access_token}` }
  expect((await request.put(`/api/v1/users/${member.id}/role`, {
    headers: adminHeaders, data: { role: 'Administrator' },
  })).status()).toBe(200)

  await page.goto('/auth/login')
  await page.getByPlaceholder('请输入邮箱').fill(credentials.email)
  await page.getByPlaceholder('请输入密码', { exact: true }).fill(credentials.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByTestId('workspace-title')).toBeVisible()
  await page.getByRole('menuitem', { name: '角色管理' }).click()
  await expect(page.getByRole('heading', { name: '成员角色管理' })).toBeVisible()
  const tokens = await page.evaluate(() => ({ access: localStorage.getItem('token'), refresh: localStorage.getItem('refreshToken') }))

  expect((await request.put(`/api/v1/users/${member.id}/role`, {
    headers: adminHeaders, data: { role: 'User' },
  })).status()).toBe(200)
  const oldHeaders = { Authorization: `Bearer ${tokens.access}` }
  expect((await request.get('/api/v1/roles', { headers: oldHeaders })).status()).toBe(403)
  const identity = await request.get('/api/v1/auth/user', { headers: oldHeaders })
  expect(identity.status()).toBe(200)
  expect((await identity.json()).role).toBe('User')
  // V2 currently requires identity, not an administrator role or tenant policy.
  expect((await request.get('/api/v2/providers', { headers: oldHeaders })).status()).toBe(200)
  const refreshed = await request.post('/api/v1/auth/refresh', { headers: { Authorization: `Bearer ${tokens.refresh}` } })
  expect(refreshed.status()).toBe(200)
  expect((await refreshed.json()).user.role).toBe('User')

  await page.getByRole('menuitem', { name: '智能工作台' }).click()
  await expect(page.getByTestId('workspace-title')).toBeVisible()
  await page.getByRole('menuitem', { name: '角色管理' }).click()
  await expect(page).toHaveURL(/profile/)
  await expect(page.getByRole('menuitem', { name: '角色管理' })).toHaveCount(0)
  await expect(page.locator('.user-dropdown-link')).toContainText(suffix)
})

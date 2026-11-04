import { test as base, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

// Serverless Chromium cannot reuse a process after its last context closes.
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

async function login(page, name = 'auth-member') {
  await page.goto('/auth/login')
  await page.getByPlaceholder('请输入邮箱').fill(`${name}@example.test`)
  await page.getByPlaceholder('请输入密码', { exact: true }).fill('FixturePass123!')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/workspace/)
  await expect(page.getByTestId('workspace-title')).toBeVisible()
}

test('login survives reload; ordinary member cannot enter role management', async ({ page }) => {
  await login(page)
  await page.reload()
  await expect(page.getByTestId('workspace-title')).toBeVisible()
  await expect(page.getByRole('menuitem', { name: '角色管理' })).toHaveCount(0)
  await page.goto('/admin/users')
  await expect(page).toHaveURL(/profile/)
})

test('wrong password stays at login without attempting refresh', async ({ page }) => {
  let refreshes = 0
  page.on('request', request => { if (request.url().includes('/auth/refresh')) refreshes++ })
  await page.goto('/auth/login')
  await page.getByPlaceholder('请输入邮箱').fill('auth-member@example.test')
  await page.getByPlaceholder('请输入密码', { exact: true }).fill('WrongPass123!')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('邮箱或密码错误', { exact: true })).toBeVisible()
  expect(refreshes).toBe(0)
  await expect(page).toHaveURL(/auth\/login/)
})

test('administrator assigns Moderator through the real UI and server', async ({ page, request }) => {
  await login(page, 'auth-admin')
  await page.getByRole('menuitem', { name: '角色管理' }).click()
  const row = page.getByRole('row').filter({ has: page.getByText('auth-member', { exact: true }) })
  await row.locator('.el-select').click()
  await page.getByRole('option', { name: '协管员', exact: true }).click()
  await row.getByRole('button', { name: '保存角色' }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page.getByText('角色已更新', { exact: true })).toBeVisible()
  const response = await request.post('/api/v1/auth/login', { data: {
    email: 'auth-member@example.test', password: 'FixturePass123!',
  } })
  expect((await response.json()).user.role).toBe('Moderator')
})

test('concurrent expired requests share one refresh and sync state; 403 keeps login', async ({ page }) => {
  await login(page)
  let refreshes = 0
  page.on('request', request => { if (request.url().includes('/auth/refresh')) refreshes++ })
  const results = await page.evaluate(async ({ expired, refresh }) => {
    const session = await import('/src/utils/authSession.js')
    session.updateAuthData({ access_token: expired, refresh_token: refresh })
    const { default: api } = await import('/src/utils/axios.js')
    const { default: v2 } = await import('/src/utils/axiosV2.js')
    const responses = await Promise.all([api.get('/api/v1/auth/user'), v2.get('/api/v2/providers'), api.get('/api/v1/users')])
    let denied = 0
    try { await api.get('/api/v1/roles', { silent: true }) } catch (error) { denied = error.response.status }
    return { statuses: responses.map(x => x.status), denied,
      synced: session.authSession.token === localStorage.getItem('token'),
      renewed: session.authSession.token !== expired, loggedIn: session.authSession.validated }
  }, { expired: seed.expired_token, refresh: seed.refresh_token })
  expect(results).toEqual({ statuses: [200, 200, 200], denied: 403, synced: true, renewed: true, loggedIn: true })
  expect(refreshes).toBe(1)
})

test('upload uses renewed access token and multipart request', async ({ page }) => {
  await login(page)
  await page.goto('/achievements/create')
  await page.evaluate(async ({ expired, refresh }) => {
    const session = await import('/src/utils/authSession.js')
    session.updateAuthData({ access_token: expired, refresh_token: refresh })
  }, { expired: seed.expired_token, refresh: seed.refresh_token })
  const uploaded = page.waitForResponse(response => response.url().includes('/files/upload') && response.status() === 200)
  await page.locator('input[type=file]').first().setInputFiles({ name: 'auth-check.txt', mimeType: 'text/plain', buffer: Buffer.from('authentication regression') })
  const result = await (await uploaded).json()
  expect(result.file_path).toMatch(/\.txt$/)
})

test('logout revokes refresh and access on both APIs', async ({ page, request }) => {
  await login(page)
  const tokens = await page.evaluate(() => ({ access: localStorage.getItem('token'), refresh: localStorage.getItem('refreshToken') }))
  await page.locator('.user-dropdown-link').click()
  const revoked = page.waitForResponse(response => response.url().includes('/auth/logout'))
  await page.getByText('退出登录', { exact: true }).click()
  expect((await revoked).status()).toBe(200)
  await expect(page).toHaveURL(/auth\/login/)
  for (const url of ['/api/v1/auth/user', '/api/v2/providers']) {
    expect((await request.get(url, { headers: { Authorization: `Bearer ${tokens.access}` } })).status()).toBe(401)
  }
  expect((await request.post('/api/v1/auth/refresh', { headers: { Authorization: `Bearer ${tokens.refresh}` } })).status()).toBe(401)
})

test('corrupt stored user is recovered from server without blank screen', async ({ page }) => {
  await page.addInitScript(({ access, refresh }) => {
    localStorage.setItem('token', access)
    localStorage.setItem('refreshToken', refresh)
    localStorage.setItem('user', '{broken-json')
  }, { access: seed.access_token, refresh: seed.refresh_token })
  await page.goto('/workspace')
  await expect(page.getByTestId('workspace-title')).toBeVisible()
})


test('invalid refresh clears reactive state and sends user to login', async ({ page }) => {
  await login(page)
  const state = await page.evaluate(async (expired) => {
    const session = await import('/src/utils/authSession.js')
    const { default: api } = await import('/src/utils/axios.js')
    session.updateAuthData({ access_token: expired, refresh_token: 'invalid-refresh-token' })
    try { await api.get('/api/v1/auth/user', { silent: true }) } catch { /* expected 401 */ }
    return { token: session.authSession.token, user: session.authSession.user, stored: localStorage.getItem('token') }
  }, seed.expired_token)
  expect(state).toEqual({ token: '', user: null, stored: null })
  await expect(page).toHaveURL(/auth\/login/)
})

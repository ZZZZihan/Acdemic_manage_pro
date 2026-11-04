import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    browserName: 'chromium',
    channel: process.env.PW_CHANNEL || undefined,
    launchOptions: {
      executablePath: process.env.PW_EXECUTABLE_PATH,
      args: process.env.PW_EXECUTABLE_PATH ? ['--no-sandbox', '--disable-dev-shm-usage', '--in-process-gpu', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--single-process', '--no-zygote'] : [],
    },
    headless: true,
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
})

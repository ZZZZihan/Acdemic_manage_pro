import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/auth',
  workers: 1,
  retries: 0,
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:5174', browserName: 'chromium', headless: true, launchOptions: { executablePath: process.env.PW_EXECUTABLE_PATH, args: process.env.PW_EXECUTABLE_PATH ? ['--no-sandbox', '--disable-dev-shm-usage', '--in-process-gpu', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--single-process', '--no-zygote'] : [] }, trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174',
    reuseExistingServer: false,
    env: { V1_PROXY_TARGET: 'http://127.0.0.1:5103', V2_PROXY_TARGET: 'http://127.0.0.1:8103' },
  },
})

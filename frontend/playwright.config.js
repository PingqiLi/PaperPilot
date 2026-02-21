import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command: 'cd .. && .venv/bin/uvicorn src.main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 15000,
    },
    {
      command: 'npx vite --port 3000',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 15000,
    },
  ],
})

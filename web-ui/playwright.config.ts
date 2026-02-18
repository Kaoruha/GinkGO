import { defineConfig } from '@playwright/test'

// 环境变量或默认值
const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }]
  ],

  outputDir: 'test-results',

  use: {
    // 通过全局配置注入，测试脚本通过 fixture 访问
    baseURL: WEB_UI_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'remote-chrome',
      use: {
        // 自定义配置，测试脚本可通过 use 访问
        remoteBrowser: REMOTE_BROWSER,
      },
    },
  ],
})

// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Ginkgo WebUI E2E测试配置 - 使用已安装的浏览器
 */
module.exports = defineConfig({
  testDir: './',
  testMatch: '**/ginkgo-e2e-test.spec.js',

  // 超时设置
  timeout: 60000,
  expect: {
    timeout: 10000
  },

  // 使用已安装的Chrome浏览器
  use: {
    // 使用已安装的Chrome
    channel: 'chrome', // 使用系统Chrome
    headless: true,

    // 基础URL
    baseURL: 'http://127.0.0.1:8080',

    // 浏览器上下文选项
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // 网络选项
    offline: false,

    // 操作选项
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },

  // 测试运行配置
  fullyParallel: false, // 关闭并行以避免资源冲突
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,

  // 报告器配置
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list']
  ],

  // 输出目录
  outputDir: 'test-results',
});
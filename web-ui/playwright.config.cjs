// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Ginkgo WebUI E2E测试配置
 * 连接到远程Chrome CDP实例进行测试
 */
module.exports = defineConfig({
  testDir: './',
  testMatch: '**/ginkgo-e2e-test.spec.js',

  // 超时设置
  timeout: 60000,
  expect: {
    timeout: 10000
  },

  // 使用远程Chrome CDP实例
  use: {
    // 连接到远程Chrome实例
    launchOptions: {
      args: ['--remote-debugging-port=9222'],
      headless: false
    },

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
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // 使用单个worker避免并发问题

  // 报告器配置
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list']
  ],

  // 输出目录
  outputDir: 'test-results',
});
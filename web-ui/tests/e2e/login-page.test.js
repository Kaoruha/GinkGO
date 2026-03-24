/**
 * 登录页面 E2E 测试
 *
 * 测试登录页面的功能和像素风格设计
 */

import { test, expect } from '@playwright/test'

const WEB_UI_URL = process.env.WEB_UI_URL || 'http://localhost:5173'
const LOGIN_PATH = '/login'

test.describe.configure({ mode: 'serial' })

test.describe('登录页面 E2E 测试', () => {
  test('应该正确显示登录页面', async ({ page, context }) => {
    // 清除 cookies 并导航
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 验证当前是登录页面
    expect(page.url()).toContain('/login')

    // 验证登录卡片存在
    const loginCard = page.locator('.login-card')
    await expect(loginCard).toBeVisible()

    // 验证 Logo 显示
    const logo = page.locator('.pixel-logo .letter')
    await expect(logo).toContainText('G')

    // 验证标题
    const titleEl = page.locator('.title')
    await expect(titleEl).toContainText('GINKGO')

    // 验证用户名输入框
    const usernameInput = page.locator('#username')
    await expect(usernameInput).toBeVisible()
    await expect(usernameInput).toHaveAttribute('placeholder', 'enter username')

    // 验证密码输入框
    const passwordInput = page.locator('#password')
    await expect(passwordInput).toBeVisible()
    await expect(passwordInput).toHaveAttribute('type', 'password')

    // 验证密码切换按钮存在
    const passwordToggle = page.locator('.password-toggle')
    await expect(passwordToggle).toBeVisible()

    // 验证登录按钮
    const loginBtn = page.locator('.login-btn')
    await expect(loginBtn).toBeVisible()
    await expect(loginBtn).toContainText('[ EXECUTE ]')

    // 验证 Demo 提示
    const demoHint = page.locator('.comment')
    await expect(demoHint).toContainText('Demo: admin / admin123')

    // 验证股票滚动条存在
    const stockTicker = page.locator('.stock-ticker')
    await expect(stockTicker).toBeVisible()

    // 验证开机日志区域
    const bootLog = page.locator('.boot-log')
    await expect(bootLog).toBeVisible()
  })

  test('应该显示表单验证错误', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 不填写任何内容，直接点击登录
    const loginBtn = page.locator('.login-btn')
    await loginBtn.click()

    // 验证错误消息显示
    const usernameError = page.locator('.input-group:first-child .error-message')
    await expect(usernameError).toBeVisible({ timeout: 1000 })
    await expect(usernameError).toContainText('required')

    const passwordError = page.locator('.input-group:nth-child(2) .error-message')
    await expect(passwordError).toBeVisible({ timeout: 1000 })
    await expect(passwordError).toContainText('required')
  })

  test('应该能够切换密码可见性', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    const passwordInput = page.locator('#password')
    const passwordToggle = page.locator('.password-toggle')

    // 初始状态应该是隐藏密码
    await expect(passwordInput).toHaveAttribute('type', 'password')

    // 点击切换按钮
    await passwordToggle.click()
    await expect(passwordInput).toHaveAttribute('type', 'text')

    // 再次点击切换
    await passwordToggle.click()
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('应该能够成功登录', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 填写登录表单
    await page.fill('#username', 'admin')
    await page.fill('#password', 'admin123')

    // 点击登录按钮
    const loginBtn = page.locator('.login-btn')
    await loginBtn.click()

    // 等待跳转到 dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 5000 })

    // 验证已经跳转
    expect(page.url()).toContain('/dashboard')
  })

  test('应该显示登录失败错误', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 使用错误的凭证
    await page.fill('#username', 'wrong')
    await page.fill('#password', 'wrong')

    const loginBtn = page.locator('.login-btn')
    await loginBtn.click()

    // 验证错误提示（等待 toast 出现）
    const toast = page.locator('.toast-message.error')
    await expect(toast).toBeVisible({ timeout: 5000 })
  })

  test('应该验证像素风格设计元素', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 验证主色调
    const logo = page.locator('.pixel-logo')
    const logoBg = await logo.evaluate((el) => {
      return window.getComputedStyle(el).background
    })
    expect(logoBg).toContain('rgb(0, 255, 136)') // #00ff88

    // 验证字体
    const titleEl = page.locator('.title')
    const titleFont = await titleEl.evaluate((el) => {
      return window.getComputedStyle(el).fontFamily
    })
    expect(titleFont).toContain('Silkscreen')

    // 验证输入框样式
    const usernameInput = page.locator('#username')
    const inputBg = await usernameInput.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor
    })
    expect(inputBg).toContain('rgb(13, 13, 21)') // #0d0d15
  })

  test('应该验证动画效果', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    // 验证粒子元素存在
    const particles = page.locator('.particle')

    // 等待粒子元素渲染完成
    await page.waitForSelector('.particle', { state: 'attached', timeout: 5000 })
    const particleCount = await particles.count()
    expect(particleCount).toBeGreaterThan(0)
    console.log(`找到 ${particleCount} 个粒子元素`)

    // 验证股票滚动条动画（Vue scoped CSS 可能添加后缀）
    const tickerContent = page.locator('.ticker-content')
    const animationName = await tickerContent.evaluate((el) => {
      return window.getComputedStyle(el).animationName
    })
    expect(animationName).toContain('ticker-scroll')

    // 验证终端光标闪烁
    const cursor = page.locator('.boot-cursor')
    const cursorAnimation = await cursor.evaluate((el) => {
      return window.getComputedStyle(el).animationName
    })
    expect(cursorAnimation).toContain('blink')

    // 验证输入框焦点效果
    const usernameInput = page.locator('#username')
    await usernameInput.focus()
    const boxShadow = await usernameInput.evaluate((el) => {
      return window.getComputedStyle(el).boxShadow
    })
    expect(boxShadow).toContain('0')
  })

  test('应该验证输入框交互效果', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    const loginCard = page.locator('.login-card')

    // 测试鼠标移动效果
    await loginCard.click()
    await page.mouse.move(100, 100)

    // 获取卡片样式变量
    const cardStyle = await loginCard.evaluate((el) => {
      return {
        mouseX: el.style.getPropertyValue('--mouse-x'),
        mouseY: el.style.getPropertyValue('--mouse-y')
      }
    })

    console.log('卡片鼠标位置:', cardStyle)
  })

  test('应该验证股票滚动条内容', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto(`${WEB_UI_URL}${LOGIN_PATH}`)

    const stockItems = page.locator('.stock-item')

    // 等待股票数据加载
    await page.waitForTimeout(2000)

    // 验证股票代码显示
    const firstStock = stockItems.first()
    await expect(firstStock).toBeVisible()

    const stockCode = await firstStock.locator('.stock-code').textContent()
    console.log('股票代码:', stockCode)
    expect(stockCode).toBeTruthy()

    // 验证至少有一些股票数据
    const itemCount = await stockItems.count()
    expect(itemCount).toBeGreaterThan(10)
  })
})

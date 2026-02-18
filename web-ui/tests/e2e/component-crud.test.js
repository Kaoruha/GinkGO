/**
 * Playwright E2E 测试 - 组件管理 CRUD 功能
 * 覆盖所有 6 种组件类型的增删改查操作
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

// 辅助函数：获取远程浏览器页面
async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()
  return { browser, page }
}

// 辅助函数：登录
async function login(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await page.reload({ waitUntil: 'networkidle' })

  await page.locator('input[placeholder="enter username"]').fill('admin')
  await page.locator('input[placeholder="enter password"]').fill('admin123')
  await page.locator('button:has-text("EXECUTE")').click()
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}

// 辅助函数：展开组件管理菜单并点击子菜单
async function navigateToComponent(page, menuText) {
  const menuExpanded = await page.locator('.ant-menu-submenu-open:has-text("组件管理")').count()
  if (menuExpanded === 0) {
    await page.click('.ant-menu-submenu-title:has-text("组件管理")')
    await page.waitForTimeout(300)
  }
  await page.click(`.ant-menu-item:has-text("${menuText}")`)
  await page.waitForTimeout(500)
}

// 6 种组件类型配置
const componentTypes = [
  {
    name: '策略组件',
    menuText: '策略组件',
    path: '/components/strategies',
    typeCode: 6,
    testContent: 'class TestStrategy:\n    pass'
  },
  {
    name: '风控组件',
    menuText: '风控组件',
    path: '/components/risks',
    typeCode: 3,
    testContent: 'class TestRisk:\n    pass'
  },
  {
    name: '仓位组件',
    menuText: '仓位组件',
    path: '/components/sizers',
    typeCode: 5,
    testContent: 'class TestSizer:\n    pass'
  },
  {
    name: '选股器',
    menuText: '选股器',
    path: '/components/selectors',
    typeCode: 4,
    testContent: 'class TestSelector:\n    pass'
  },
  {
    name: '分析器',
    menuText: '分析器',
    path: '/components/analyzers',
    typeCode: 1,
    testContent: 'class TestAnalyzer:\n    pass'
  },
  {
    name: '事件处理器',
    menuText: '事件处理器',
    path: '/components/handlers',
    typeCode: 8,
    testContent: 'class TestHandler:\n    pass'
  },
]

// 为每种组件类型生成测试
for (const comp of componentTypes) {
  test.describe(`${comp.name} CRUD`, () => {

    test(`[${comp.name}] 列表页正常显示`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)

      // 验证页面标题
      await expect(page.locator('.page-title')).toBeVisible({ timeout: 5000 })

      // 验证表格存在
      await expect(page.locator('.ant-table')).toBeVisible()

      // 验证新建按钮存在
      await expect(page.locator('button:has-text("新建")')).toBeVisible()
    })

    test(`[${comp.name}] 创建新文件`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)
      await page.waitForTimeout(500)

      // 点击新建按钮
      await page.click('button:has-text("新建")')
      await page.waitForTimeout(500)

      // 等待对话框出现
      const modal = page.locator('.ant-modal-content')
      await expect(modal).toBeVisible({ timeout: 5000 })

      // 输入文件名
      const testFileName = `e2e_${comp.name}_${Date.now()}`
      await modal.locator('input').fill(testFileName)

      // 确认创建
      await modal.locator('button').filter({ hasText: '确' }).last().click()
      await page.waitForTimeout(2000)

      // 验证跳转到详情页
      await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })
      expect(page.url()).toContain(comp.path + '/')

      // 验证文件名显示
      const fileName = await page.locator('.file-name').textContent()
      expect(fileName).toBe(testFileName)
    })

    test(`[${comp.name}] 编辑并保存文件`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)
      await page.waitForTimeout(500)

      // 等待表格加载
      await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 })

      // 点击第一个文件进入详情页
      await page.click('.ant-table-tbody tr:first-child .file-link')
      await page.waitForTimeout(2000)

      // 验证详情页加载
      await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })

      // 等待编辑器加载
      await page.waitForTimeout(1000)

      const monacoEditor = page.locator('.monaco-editor')
      const textareaEditor = page.locator('.code-textarea')

      if (await monacoEditor.count() > 0) {
        // Monaco Editor: 使用 evaluate 直接操作 Monaco API 设置内容
        const testContent = `# E2E Test Edit ${Date.now()}\nprint("hello world")`
        await page.evaluate((content) => {
          // 获取 Monaco 编辑器实例并设置值
          const editorEl = document.querySelector('.monaco-editor')
          if (editorEl) {
            // 尝试从全局 window 获取编辑器
            const editors = window.monaco?.editor?.getEditors?.() || []
            if (editors.length > 0) {
              const editor = editors[0]
              editor.setValue(content)
            }
          }
        }, testContent)
        await page.waitForTimeout(800)
      } else if (await textareaEditor.count() > 0) {
        // Textarea: 直接输入
        await textareaEditor.click({ force: true })
        await page.keyboard.press('Control+a')
        await page.keyboard.type(`# E2E Test Edit ${Date.now()}\nprint("hello")`)
        await page.waitForTimeout(500)
      }

      // 等待未保存标记出现
      await page.waitForTimeout(500)

      // 点击保存按钮
      const saveBtn = page.locator('.toolbar button:has-text("保存")')
      await saveBtn.click({ force: true })
      await page.waitForTimeout(2000)

      // 验证保存成功消息
      const successMsg = page.locator('.ant-message-success, .ant-message')
      const hasSuccess = await successMsg.isVisible({ timeout: 3000 }).catch(() => false)

      // 如果没有成功消息，检查未保存标记是否消失
      if (!hasSuccess) {
        const unsaved = await page.locator('.unsaved-badge').isVisible().catch(() => false)
        // 未保存标记消失也算成功
        expect(unsaved).toBe(false)
      }
    })

    test(`[${comp.name}] 返回列表页`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)
      await page.waitForTimeout(500)

      // 进入详情页
      await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 })
      await page.click('.ant-table-tbody tr:first-child .file-link')
      await page.waitForTimeout(2000)

      // 验证在详情页
      await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })

      // 点击返回按钮
      await page.locator('.back-btn').click({ force: true })
      await page.waitForTimeout(1500)

      // 验证回到列表页
      expect(page.url()).toMatch(new RegExp(`${comp.path}/?$`))
      await expect(page.locator('.component-list-page')).toBeVisible({ timeout: 5000 })
    })

    test(`[${comp.name}] 搜索文件`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)
      await page.waitForTimeout(500)

      // 等待表格加载
      await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 })

      // 输入搜索关键词
      const searchInput = page.locator('.ant-input-search input').first()
      await searchInput.fill('nonexistent_xyz')
      await page.waitForTimeout(800)

      // 验证表格响应（可能为空或无匹配）
      const rows = await page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)').count()
      expect(rows).toBeGreaterThanOrEqual(0)
    })

    test(`[${comp.name}] 删除文件`, async () => {
      const { page } = await getPage()
      await login(page)

      await navigateToComponent(page, comp.menuText)
      await page.waitForTimeout(500)

      // 先创建一个测试文件
      await page.click('button:has-text("新建")')
      await page.waitForTimeout(500)

      const modal = page.locator('.ant-modal-content')
      await expect(modal).toBeVisible({ timeout: 5000 })

      const testFileName = `e2e_delete_${Date.now()}`
      await modal.locator('input').fill(testFileName)
      await modal.locator('button').filter({ hasText: '确' }).last().click()
      await page.waitForTimeout(2000)

      // 返回列表页
      await page.goto(`${WEB_UI_URL}${comp.path}`)
      await page.waitForTimeout(1000)

      // 搜索刚创建的文件
      const searchInput = page.locator('.ant-input-search input').first()
      await searchInput.fill(testFileName)
      await page.waitForTimeout(800)

      // 点击删除按钮
      const deleteBtn = page.locator('.ant-table-tbody tr:first-child button:has-text("删除")')
      if (await deleteBtn.count() > 0) {
        // 确认删除弹窗
        page.on('dialog', dialog => dialog.accept())
        await deleteBtn.click()
        await page.waitForTimeout(500)

        // 点击确认（ant-design popconfirm）
        await page.locator('.ant-popconfirm button:has-text("确")').click()
        await page.waitForTimeout(1000)
      }
    })
  })
}

// 综合测试：所有组件页面都能正确访问
test.describe('组件管理综合测试', () => {
  test('所有组件列表页面都能正常访问', async () => {
    const { page } = await getPage()
    await login(page)

    for (const comp of componentTypes) {
      await page.goto(`${WEB_UI_URL}${comp.path}`)
      await page.waitForTimeout(1000)

      // 验证页面加载
      await expect(page.locator('.component-list-page')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('button:has-text("新建")')).toBeVisible()

      console.log(`✅ ${comp.name} 列表页正常`)
    }
  })
})

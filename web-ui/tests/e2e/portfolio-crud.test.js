/**
 * Playwright E2E 测试 - Portfolio CRUD 流程（含版本管理）
 * 测试创建投资组合、搜索、筛选、详情验证、删除、版本管理功能
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

// 辅助函数：获取远程浏览器页面
async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || context.pages()[0]
  return { browser, page }
}

// 生成唯一的组合名称
const portfolioName = `E2E_Version_Test_${Date.now()}`

// 测试配置：参数名和值
// 注意：params 中使用 label 文本作为 key（fillParamByLabel 会通过 includes() 匹配）
const TEST_CONFIG = {
  selector: {
    name: 'fixed_selector',
    params: {
      name: 'FixedSelector_E2E',
      'codes': '000001.SZ,000002.SZ'  // 会匹配 label "codes (逗号分隔)"
    }
  },
  sizer: {
    name: 'fixed_sizer',
    params: {
      name: 'FixedSizer_E2E',
      volume: '1000'
    }
  },
  strategy: {
    name: 'random_signal_strategy',
    params: {
      name: 'RandomStrategy_E2E',
      buy_probability: '0.9',
      sell_probability: '0.05',
      max_signals: '4'
    }
  }
}

// 辅助函数：根据label填写参数
// label: 显示的标签文本，支持包含匹配（如 "codes" 可匹配 "codes (逗号分隔)"）
async function fillParamByLabel(page, sectionSelector, label, value) {
  const paramRows = await page.$$(sectionSelector + ' .param-row')
  for (const row of paramRows) {
    const labelEl = await row.$('.param-label')
    if (labelEl) {
      const labelText = await labelEl.textContent()
      // 支持包含匹配：如果 labelText 包含 label，则匹配成功
      if (labelText && labelText.includes(label)) {
        const numInput = await row.$('.ant-input-number-input')
        if (numInput) {
          await numInput.click()  // 先点击确保聚焦
          await numInput.fill(String(value))  // fill()会自动清空
          console.log(`  ✓ ${labelText.trim()} = ${value}`)
          return true
        }
        const input = await row.$('.ant-input')
        if (input) {
          await input.click()
          await input.fill(String(value))
          console.log(`  ✓ ${labelText.trim()} = ${value}`)
          return true
        }
      }
    }
  }
  console.log(`  ⚠ 未找到参数: ${label}`)
  return false
}

// 辅助函数：检查组件下拉选项中的版本标签
async function verifyVersionTagsInDropdown(page) {
  const options = await page.$$('.ant-select-dropdown .ant-select-item-option')
  let versionFound = false
  let latestTagFound = false

  for (const option of options) {
    const text = await option.textContent()
    // 检查是否有版本号（格式如 1.0.0）
    if (text && /\d+\.\d+\.\d+/.test(text)) {
      versionFound = true
      console.log('  ✓ 发现版本号:', text.trim())
    }
    // 检查是否有"最新"标签
    if (text && text.includes('最新')) {
      latestTagFound = true
      console.log('  ✓ 发现最新标签:', text.trim())
    }
  }

  return { versionFound, latestTagFound }
}

// 辅助函数：检查组件配置中的版本选择器
async function verifyVersionSelector(page) {
  // 检查 .item-info 内是否有版本相关内容
  const itemInfos = await page.$$('.ant-modal .item-info')
  if (itemInfos.length > 0) {
    const lastItemInfo = itemInfos[itemInfos.length - 1]

    // 获取 item-info 的文本内容，检查是否包含版本号
    const textContent = await lastItemInfo.textContent()
    const hasVersion = /\d+\.\d+\.\d+/.test(textContent)

    console.log(`  ✓ item-info 存在`)
    console.log(`  内容: ${textContent.trim()}`)

    if (hasVersion) {
      const versionMatch = textContent.match(/(\d+\.\d+\.\d+)/)
      console.log(`  ✓ 发现版本号: ${versionMatch ? versionMatch[1] : 'UNKNOWN'}`)

      // 检查是否禁用（通过检查是否有 .ant-select-disabled 类）
      const hasDisabledClass = await lastItemInfo.evaluate(el => {
        const selectEl = el.querySelector('.ant-select')
        return selectEl ? selectEl.classList.contains('ant-select-disabled') : false
      })

      console.log(`  版本选择器禁用: ${hasDisabledClass}`)

      return { exists: true, version: versionMatch ? versionMatch[1] : 'UNKNOWN', disabled: hasDisabledClass }
    }
  }

  console.log('  ⚠ 版本选择器未找到')
  return { exists: false }
}

test.describe.serial('Portfolio CRUD Flow (Version Management)', () => {

  test('1. Create portfolio - verify version tags in component selector', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    const modal = await page.$('.ant-modal')
    expect(modal).not.toBeNull()

    await page.fill('.ant-modal input[placeholder="组合名称"]', portfolioName)
    await page.fill('.ant-modal .ant-input-number-input', '100000')
    await page.waitForTimeout(300)

    // ========== 测试选股器选择器的版本标签 ==========
    console.log('\n=== 测试选股器选择器的版本标签 ===')
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)

    // 点击组件下拉框
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(800)

    // 验证版本标签
    const selectorVersionResult = await verifyVersionTagsInDropdown(page)
    expect(selectorVersionResult.versionFound).toBeTruthy()
    console.log('✅ 选股器下拉框包含版本信息')

    // 选择组件
    await page.keyboard.type(TEST_CONFIG.selector.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    // ========== 验证右侧配置区域的版本选择器 ==========
    console.log('\n=== 验证选股器配置区域的版本选择器 ===')
    const selectorVersionInfo = await verifyVersionSelector(page)
    expect(selectorVersionInfo.exists).toBeTruthy()

    // 配置选股器参数 - 只操作最后一个 config-section（最新添加的组件）
    console.log('配置选股器参数:')
    const configSections = await page.$$('.ant-modal .config-section')
    const lastSectionIndex = configSections.length
    for (const [key, value] of Object.entries(TEST_CONFIG.selector.params)) {
      await fillParamByLabel(page, `.ant-modal .config-section:nth-child(${lastSectionIndex})`, key, value)
    }
    await page.waitForTimeout(500)

    // ========== 测试仓位管理器 ==========
    console.log('\n=== 测试仓位管理器版本标签 ===')
    await page.click('.ant-modal .type-btn:nth-child(2)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(800)

    const sizerVersionResult = await verifyVersionTagsInDropdown(page)
    expect(sizerVersionResult.versionFound).toBeTruthy()

    await page.keyboard.type(TEST_CONFIG.sizer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    console.log('\n=== 验证仓位管理器配置区域的版本选择器 ===')
    const sizerVersionInfo = await verifyVersionSelector(page)
    expect(sizerVersionInfo.exists).toBeTruthy()

    console.log('配置仓位管理器参数:')
    const configSections2 = await page.$$('.ant-modal .config-section')
    const lastSectionIndex2 = configSections2.length
    for (const [key, value] of Object.entries(TEST_CONFIG.sizer.params)) {
      await fillParamByLabel(page, `.ant-modal .config-section:nth-child(${lastSectionIndex2})`, key, value)
    }
    await page.waitForTimeout(500)

    // ========== 测试策略 ==========
    console.log('\n=== 测试策略版本标签 ===')
    await page.click('.ant-modal .type-btn:nth-child(3)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(800)

    const strategyVersionResult = await verifyVersionTagsInDropdown(page)
    expect(strategyVersionResult.versionFound).toBeTruthy()

    await page.keyboard.type(TEST_CONFIG.strategy.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    console.log('\n=== 验证策略配置区域的版本选择器 ===')
    const strategyVersionInfo = await verifyVersionSelector(page)
    expect(strategyVersionInfo.exists).toBeTruthy()

    console.log('配置策略参数:')
    const configSections3 = await page.$$('.ant-modal .config-section')
    const lastSectionIndex3 = configSections3.length
    for (const [key, value] of Object.entries(TEST_CONFIG.strategy.params)) {
      await fillParamByLabel(page, `.ant-modal .config-section:nth-child(${lastSectionIndex3})`, key, value)
    }
    await page.waitForTimeout(500)

    // ========== 提交创建 ==========
    await page.click('.ant-modal button.ant-btn-primary')
    await page.waitForTimeout(3000)

    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('\n✅ 投资组合创建成功（含版本信息）')
  })

  test('2. Verify version info in portfolio detail', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // 搜索刚创建的组合
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const card = await page.$('.portfolio-card')
    expect(card).not.toBeNull()
    await card.click()
    await page.waitForTimeout(3000)

    const currentUrl = page.url()
    expect(currentUrl).toContain('/portfolio/')
    console.log('详情页URL:', currentUrl)

    // 验证页面标题
    const pageTitle = await page.$('.page-title')
    if (pageTitle) {
      const title = await pageTitle.evaluate(el => el.textContent)
      expect(title).toBe(portfolioName)
      console.log('页面标题:', title)
    }

    // ========== 验证组件配置卡片中的版本信息 ==========
    console.log('\n=== 验证详情页版本信息 ===')

    const componentsCard = await page.$('.components-card')
    expect(componentsCard).not.toBeNull()

    // 检查每个组件的版本标签
    const componentItems = await page.$$('.component-item')
    console.log(`组件数量: ${componentItems.length}`)

    for (let i = 0; i < Math.min(componentItems.length, 3); i++) {
      const item = componentItems[i]

      // 获取组件名称
      const nameEl = await item.$('.component-name')
      const componentName = nameEl ? await nameEl.textContent() : 'Unknown'
      console.log(`\n组件 ${i + 1}: ${componentName}`)

      // 检查版本标签
      const versionTag = await item.$('.ant-tag[color="default"]')
      if (versionTag) {
        const version = await versionTag.textContent()
        console.log(`  版本: ${version}`)
        // 验证版本格式 (x.x.x)
        expect(version).toMatch(/\d+\.\d+\.\d+/)
      }

      // 检查"最新"标签
      const latestTag = await item.$('.ant-tag[color="blue"]')
      if (latestTag) {
        const latestText = await latestTag.textContent()
        console.log(`  ${latestText}`)
      }
    }

    console.log('\n✅ 详情页版本信息验证成功')
  })

  test('3. Version selector disabled when only one version', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    console.log('\n=== 测试单版本组件禁用版本选择器 ===')

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 点击创建按钮
    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    await page.fill('.ant-modal input[placeholder="组合名称"]', `Test_Disable_${Date.now()}`)
    await page.waitForTimeout(300)

    // 添加一个组件
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type('fixed_selector')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    // 检查版本选择器状态
    const versionSelectors = await page.$$('.ant-modal .config-section:first-child .item-info a-select')
    if (versionSelectors.length > 0) {
      const isDisabled = await versionSelectors[0].isDisabled()

      // 获取可用版本数量
      await versionSelectors[0].click()
      await page.waitForTimeout(500)

      const versionOptions = await page.$$('.ant-modal .ant-select-dropdown .ant-select-item')
      const versionCount = versionOptions.length

      console.log(`可用版本数: ${versionCount}`)
      console.log(`版本选择器禁用状态: ${isDisabled}`)

      // 如果只有一个版本，应该被禁用
      if (versionCount <= 1) {
        expect(isDisabled).toBeTruthy()
        console.log('✅ 单版本组件正确禁用版本选择器')
      } else {
        expect(isDisabled).toBeFalsy()
        console.log('✅ 多版本组件正确启用版本选择器')
      }

      await page.keyboard.press('Escape')
    }

    // 关闭模态框
    await page.click('.ant-modal .ant-btn-default')
  })

  test('4. Search and filter functionality', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('\n=== 测试搜索功能 ===')

    const beforeCards = await page.$$('.portfolio-card')
    console.log('搜索前卡片数:', beforeCards.length)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1000)

    const afterCards = await page.$$('.portfolio-card')
    console.log('搜索后卡片数:', afterCards.length)
    expect(afterCards.length).toBeGreaterThanOrEqual(1)

    if (afterCards.length > 0) {
      const firstName = await afterCards[0].evaluate(el => {
        return el.querySelector('.card-title .name')?.textContent
      })
      expect(firstName).toBe(portfolioName)
      console.log('✅ 搜索验证成功，找到组合:', firstName)
    }
  })

  test('5. Filter by mode', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('\n=== 测试模式筛选 ===')

    const beforeCards = await page.$$('.portfolio-card')
    const beforeCount = beforeCards.length
    console.log('筛选前卡片数:', beforeCount)

    await page.click('.ant-radio-button-wrapper:has-text("回测")')
    await page.waitForTimeout(1000)

    const afterCards = await page.$$('.portfolio-card')
    console.log('筛选后卡片数:', afterCards.length)

    for (const card of afterCards) {
      const modeTag = await card.$('.card-title .ant-tag')
      if (modeTag) {
        const tagText = await modeTag.textContent()
        expect(tagText).toBe('回测')
      }
    }

    await page.click('.ant-radio-button-wrapper:has-text("全部")')
    await page.waitForTimeout(1000)

    console.log('✅ 模式筛选功能正常')
  })

  test('6. Statistics cards', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('\n=== 测试统计卡片 ===')

    const statCards = await page.$$('.stat-card')
    expect(statCards.length).toBe(4)
    console.log('统计卡片数量:', statCards.length)

    const statValues = await page.$$eval('.ant-statistic-title', elements =>
      elements.map(el => el.textContent)
    )
    expect(statValues).toContain('总投资组合')
    expect(statValues).toContain('运行中')
    expect(statValues).toContain('平均净值')
    expect(statValues).toContain('总资产')

    console.log('✅ 统计卡片验证成功')
  })

  test('7. Delete portfolio', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const cards = await page.$$('.portfolio-card')
    expect(cards.length).toBeGreaterThanOrEqual(1)

    const moreBtn = await cards[0].$('.ant-dropdown-trigger')
    await moreBtn.click()
    await page.waitForTimeout(800)

    const menuItems = await page.$$('.ant-dropdown-menu-item')
    await menuItems[1].click()
    await page.waitForTimeout(800)

    await page.click('.ant-modal .ant-btn-dangerous')
    await page.waitForTimeout(3000)

    await page.fill('.ant-input-search input', '')
    await page.waitForTimeout(500)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const remainingCards = await page.$$('.portfolio-card')
    const hasEmpty = await page.$('.ant-empty') !== null

    expect(remainingCards.length === 0 || hasEmpty).toBeTruthy()
    console.log('✅ 删除验证成功')
  })
})

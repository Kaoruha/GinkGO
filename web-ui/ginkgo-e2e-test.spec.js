import { test, expect } from '@playwright/test';

// 测试配置
const BASE_URL = 'http://127.0.0.1:8080';
const CDP_REMOTE_URL = 'http://50.10:9222'; // 远程Chrome CDP实例

test.describe('Ginkgo量化交易平台 - 核心功能测试', () => {

  test.beforeEach(async ({ page }) => {
    // 每个测试前导航到首页
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('1. 页面加载与基础结构验证', async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/Ginkgo.*量化交易平台/);

    // 验证主要容器存在
    const app = page.locator('#app');
    await expect(app).toBeVisible();

    // 检查是否有关键导航元素
    const navigation = page.locator('nav, header, [role="navigation"]');
    const hasNavigation = await navigation.count() > 0;
    console.log(`导航元素存在: ${hasNavigation}`);

    // 检查页面性能指标
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        totalLoadTime: navigation.loadEventEnd - navigation.fetchStart
      };
    });
    console.log('页面性能指标:', performanceMetrics);
  });

  test('2. 登录功能测试', async ({ page }) => {
    // 检查登录表单是否存在
    const loginForm = page.locator('form').filter({ hasText: /登录|login|username|password/i });
    const hasLoginForm = await loginForm.count() > 0;

    if (hasLoginForm) {
      await expect(loginForm).toBeVisible();

      // 填写测试账号（如果存在）
      const usernameInput = page.locator('input[type="text"], input[name="username"]').first();
      const passwordInput = page.locator('input[type="password"]').first();
      const submitButton = page.locator('button[type="submit"]').filter({ hasText: /登录|login/i });

      const hasUsername = await usernameInput.count() > 0;
      const hasPassword = await passwordInput.count() > 0;
      const hasSubmit = await submitButton.count() > 0;

      console.log(`登录表单元素 - 用户名: ${hasUsername}, 密码: ${hasPassword}, 提交: ${hasSubmit}`);

      // 如果需要登录，这里可以添加测试账号逻辑
      // await usernameInput.fill('test_user');
      // await passwordInput.fill('test_password');
      // await submitButton.click();
    } else {
      console.log('未发现登录表单，可能已经登录或无需登录');
    }
  });

  test('3. 导航菜单与功能模块测试', async ({ page }) => {
    // 检查主导航菜单
    const mainNav = page.locator('nav, .navigation, .menu, [role="navigation"]').first();
    const hasMainNav = await mainNav.count() > 0;

    if (hasMainNav) {
      await expect(mainNav).toBeVisible();

      // 获取所有导航链接
      const navLinks = mainNav.locator('a, button, [role="menuitem"]');
      const linkCount = await navLinks.count();
      console.log(`导航菜单项数量: ${linkCount}`);

      // 测试前5个导航项（避免过多点击）
      const testCount = Math.min(linkCount, 5);
      for (let i = 0; i < testCount; i++) {
        const link = navLinks.nth(i);
        const linkText = await link.textContent();
        console.log(`测试导航项: ${linkText}`);

        await link.click();
        await page.waitForTimeout(1000); // 等待页面加载

        // 检查页面是否正常加载
        const currentUrl = page.url();
        console.log(`  -> 导航到: ${currentUrl}`);

        // 返回首页
        await page.goto(BASE_URL);
        await page.waitForLoadState('networkidle');
      }
    } else {
      console.log('未发现主导航菜单');
    }
  });

  test('4. 数据可视化组件测试', async ({ page }) => {
    // 等待页面完全加载
    await page.waitForTimeout(2000);

    // 检查图表组件
    const charts = page.locator('canvas, svg, [class*="chart"], [class*="graph"], [id*="chart"]');
    const chartCount = await charts.count();
    console.log(`图表组件数量: ${chartCount}`);

    // 检查数据表格
    const tables = page.locator('table, [role="table"]');
    const tableCount = await tables.count();
    console.log(`数据表格数量: ${tableCount}`);

    // 检查数据卡片/统计面板
    const dataCards = page.locator('[class*="card"], [class*="panel"], [class*="stat"], [class*="metric"]');
    const cardCount = await dataCards.count();
    console.log(`数据卡片/面板数量: ${cardCount}`);

    // 如果有图表，检查其加载状态
    if (chartCount > 0) {
      const firstChart = charts.first();
      await expect(firstChart).toBeVisible();

      // 检查图表是否有尺寸（说明已正确渲染）
      const chartSize = await firstChart.boundingBox();
      if (chartSize) {
        console.log(`首个图表尺寸: ${JSON.stringify(chartSize)}`);
        expect(chartSize.width).toBeGreaterThan(0);
        expect(chartSize.height).toBeGreaterThan(0);
      }
    }
  });

  test('5. 交互功能测试', async ({ page }) => {
    // 检查按钮交互
    const buttons = page.locator('button:not([disabled])');
    const buttonCount = await buttons.count();
    console.log(`可交互按钮数量: ${buttonCount}`);

    // 检查表单元素
    const formElements = page.locator('input, select, textarea');
    const formCount = await formElements.count();
    console.log(`表单元素数量: ${formCount}`);

    // 检查下拉菜单
    const dropdowns = page.locator('[role="combobox"], select, .dropdown, .select');
    const dropdownCount = await dropdowns.count();
    console.log(`下拉菜单数量: ${dropdownCount}`);

    // 测试一些基本交互
    if (buttonCount > 0) {
      const firstButton = buttons.first();
      const buttonText = await firstButton.textContent();
      console.log(`测试按钮交互: ${buttonText}`);

      // 检查按钮hover效果
      await firstButton.hover();
      await page.waitForTimeout(500);
    }
  });

  test('6. 响应式设计测试', async ({ page }) => {
    // 测试不同屏幕尺寸
    const sizes = [
      { width: 1920, height: 1080, name: '桌面大屏' },
      { width: 1366, height: 768, name: '桌面标准' },
      { width: 768, height: 1024, name: '平板' },
      { width: 375, height: 667, name: '手机' }
    ];

    for (const size of sizes) {
      await page.setViewportSize({ width: size.width, height: size.height });
      await page.waitForTimeout(1000); // 等待响应式布局调整

      // 检查页面是否正常显示
      const isVisible = await page.locator('body').isVisible();
      console.log(`${size.name} (${size.width}x${size.height}): 页面正常显示 = ${isVisible}`);

      // 检查是否有横向滚动条（布局问题）
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.body.scrollWidth > window.innerWidth;
      });
      console.log(`  -> 横向滚动: ${hasHorizontalScroll ? '是' : '否'}`);
    }

    // 恢复默认视口
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('7. 性能与加载时间测试', async ({ page }) => {
    // 收集性能指标
    const performanceData = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      const paints = performance.getEntriesByType('paint');
      const resources = performance.getEntriesByType('resource');

      return {
        // 导航时间
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
        loadComplete: navigation.loadEventEnd - navigation.fetchStart,

        // 首次渲染时间
        firstPaint: paints.find(p => p.name === 'first-paint')?.startTime,
        firstContentfulPaint: paints.find(p => p.name === 'first-contentful-paint')?.startTime,

        // 资源加载数量
        totalResources: resources.length,
        scriptResources: resources.filter(r => r.name.endsWith('.js')).length,
        styleResources: resources.filter(r => r.name.endsWith('.css')).length,

        // 内存使用
        memory: performance.memory ? {
          used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
          total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
          limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
        } : null
      };
    });

    console.log('性能数据:', JSON.stringify(performanceData, null, 2));

    // 基本性能断言
    expect(performanceData.domContentLoaded).toBeLessThan(3000); // 3秒内完成DOM加载
    expect(performanceData.totalResources).toBeGreaterThan(0); // 有资源加载
  });

  test('8. 内容可访问性测试', async ({ page }) => {
    // 检查图片alt属性
    const images = page.locator('img');
    const imageCount = await images.count();
    console.log(`图片数量: ${imageCount}`);

    if (imageCount > 0) {
      let imagesWithAlt = 0;
      for (let i = 0; i < imageCount; i++) {
        const alt = await images.nth(i).getAttribute('alt');
        if (alt !== null) imagesWithAlt++;
      }
      console.log(`有alt属性的图片: ${imagesWithAlt}/${imageCount}`);
    }

    // 检查标题层次结构
    const headings = page.locator('h1, h2, h3, h4, h5, h6');
    const headingCount = await headings.count();
    console.log(`标题数量: ${headingCount}`);

    // 检查焦点管理
    const focusableElements = page.locator('button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])');
    const focusableCount = await focusableElements.count();
    console.log(`可聚焦元素数量: ${focusableCount}`);

    // 测试键盘导航
    if (focusableCount > 0) {
      await focusableElements.first().focus();
      const isFocused = await focusableElements.first().evaluate(el => document.activeElement === el);
      console.log(`键盘导航正常: ${isFocused}`);
    }
  });

  test('9. API集成测试', async ({ page }) => {
    // 监听网络请求
    const apiRequests = [];

    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/') || url.includes('/data/')) {
        apiRequests.push({
          method: request.method(),
          url: url,
          resourceType: request.resourceType()
        });
      }
    });

    // 执行一些操作来触发API请求
    await page.waitForTimeout(3000);

    // 尝试点击一些可能触发API请求的元素
    const potentialTriggers = page.locator('button, a, [onclick], [data-action]').all();
    const triggers = await potentialTriggers;

    if (triggers.length > 0) {
      // 点击前3个可能的触发器
      for (let i = 0; i < Math.min(3, triggers.length); i++) {
        try {
          const element = await triggers[i];
          await element.click();
          await page.waitForTimeout(1000);

          // 返回首页
          await page.goto(BASE_URL);
          await page.waitForLoadState('networkidle');
        } catch (error) {
          console.log(`点击元素失败: ${error.message}`);
        }
      }
    }

    console.log(`API请求数量: ${apiRequests.length}`);
    if (apiRequests.length > 0) {
      console.log('API请求示例:', apiRequests.slice(0, 5));
    }
  });

  test('10. 错误处理与边界情况测试', async ({ page }) => {
    // 检查是否有错误消息或警告
    const consoleMessages = [];
    page.on('console', msg => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        consoleMessages.push({
          type: msg.type(),
          text: msg.text()
        });
      }
    });

    // 尝试访问不存在的页面
    await page.goto(`${BASE_URL}/non-existent-page`);
    await page.waitForTimeout(2000);

    // 检查是否正确处理404
    const currentUrl = page.url();
    console.log(`访问不存在页面后的URL: ${currentUrl}`);

    // 返回首页
    await page.goto(BASE_URL);

    // 检查控制台错误
    await page.waitForTimeout(2000);
    console.log(`控制台错误/警告数量: ${consoleMessages.length}`);
    if (consoleMessages.length > 0) {
      console.log('控制台消息示例:', consoleMessages.slice(0, 3));
    }
  });
});

test.describe('Ginkgo量化交易平台 - 量化研究员视角测试', () => {

  test('11. 投资组合管理功能测试', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 寻找投资组合相关的导航或功能
    const portfolioSelectors = [
      'a:has-text("投资组合")',
      'a:has-text("Portfolio")',
      'button:has-text("投资组合")',
      '[href*="portfolio"]',
      '[href*="portfolio"]'
    ];

    let portfolioLink = null;
    for (const selector of portfolioSelectors) {
      try {
        portfolioLink = page.locator(selector).first();
        if (await portfolioLink.count() > 0) {
          console.log(`找到投资组合入口: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (portfolioLink && await portfolioLink.count() > 0) {
      await portfolioLink.click();
      await page.waitForLoadState('networkidle');
      console.log('成功进入投资组合管理页面');

      // 检查投资组合相关功能
      const portfolioItems = page.locator('[class*="portfolio"], [class*="portfolio-card"], tr').all();
      const items = await portfolioItems;
      console.log(`投资组合项目数量: ${items.length}`);

      // 检查是否有创建新投资组合的功能
      const createButton = page.locator('button:has-text("创建"), button:has-text("新建"), button:has-text("Create")');
      const hasCreateFunction = await createButton.count() > 0;
      console.log(`创建投资组合功能: ${hasCreateFunction ? '存在' : '未找到'}`);

    } else {
      console.log('未找到投资组合管理入口');
    }
  });

  test('12. 回测功能测试', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 寻找回测相关功能
    const backtestSelectors = [
      'a:has-text("回测")',
      'a:has-text("Backtest")',
      'button:has-text("回测")',
      '[href*="backtest"]',
      '[href*="backtest"]'
    ];

    let backtestLink = null;
    for (const selector of backtestSelectors) {
      try {
        backtestLink = page.locator(selector).first();
        if (await backtestLink.count() > 0) {
          console.log(`找到回测入口: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (backtestLink && await backtestLink.count() > 0) {
      await backtestLink.click();
      await page.waitForLoadState('networkidle');
      console.log('成功进入回测页面');

      // 检查回测配置表单
      const formElements = page.locator('input, select, textarea').all();
      const forms = await formElements;
      console.log(`回测配置项数量: ${forms.length}`);

      // 检查是否有时间范围选择
      const datePickers = page.locator('[type="date"], input[placeholder*="日期"], input[placeholder*="Date"]').all();
      const datePickersArray = await datePickers;
      console.log(`日期选择器数量: ${datePickersArray.length}`);

      // 检查是否有运行回测按钮
      const runButton = page.locator('button:has-text("运行"), button:has-text("Run"), button:has-text("开始")');
      const hasRunButton = await runButton.count() > 0;
      console.log(`运行回测按钮: ${hasRunButton ? '存在' : '未找到'}`);

    } else {
      console.log('未找到回测功能入口');
    }
  });

  test('13. 数据查询与展示功能测试', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 寻找数据查询相关功能
    const dataSelectors = [
      'a:has-text("数据")',
      'a:has-text("Data")',
      'a:has-text("查询")',
      'a:has-text("Query")',
      '[href*="data"]'
    ];

    let dataLink = null;
    for (const selector of dataSelectors) {
      try {
        dataLink = page.locator(selector).first();
        if (await dataLink.count() > 0) {
          console.log(`找到数据入口: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (dataLink && await dataLink.count() > 0) {
      await dataLink.click();
      await page.waitForLoadState('networkidle');
      console.log('成功进入数据查询页面');

      // 检查数据展示组件
      const tables = page.locator('table').all();
      const tablesArray = await tables;
      console.log(`数据表格数量: ${tablesArray.length}`);

      const charts = page.locator('canvas, svg, [class*="chart"]').all();
      const chartsArray = await charts;
      console.log(`数据图表数量: ${chartsArray.length}`);

    } else {
      console.log('未找到数据查询功能入口');
    }
  });

  test('14. 策略管理功能测试', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 寻找策略管理相关功能
    const strategySelectors = [
      'a:has-text("策略")',
      'a:has-text("Strategy")',
      'a:has-text("算法")',
      '[href*="strategy"]',
      '[href*="strategy"]'
    ];

    let strategyLink = null;
    for (const selector of strategySelectors) {
      try {
        strategyLink = page.locator(selector).first();
        if (await strategyLink.count() > 0) {
          console.log(`找到策略入口: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (strategyLink && await strategyLink.count() > 0) {
      await strategyLink.click();
      await page.waitForLoadState('networkidle');
      console.log('成功进入策略管理页面');

      // 检查策略列表
      const strategyItems = page.locator('[class*="strategy"], [class*="strategy-card"], tr').all();
      const items = await strategyItems;
      console.log(`策略项目数量: ${items.length}`);

      // 检查策略参数配置界面
      const paramElements = page.locator('[class*="parameter"], [class*="config"], label').all();
      const params = await paramElements;
      console.log(`策略参数项数量: ${params.length}`);

    } else {
      console.log('未找到策略管理功能入口');
    }
  });

  test('15. 工作流程合理性测试', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    console.log('=== 工作流程分析 ===');

    // 分析页面布局和功能组织
    const mainContainers = page.locator('main, .main-content, .content, [role="main"]').all();
    const mainCount = await mainContainers.length;
    console.log(`主要内容区域: ${mainCount}`);

    // 检查功能分组
    const sections = page.locator('section, .section, [class*="panel"], [class*="card"]').all();
    const sectionCount = await sections.length;
    console.log(`功能分组数量: ${sectionCount}`);

    // 检查面包屑导航
    const breadcrumbs = page.locator('[class*="breadcrumb"], nav[aria-label="Breadcrumb"]').all();
    const breadcrumbCount = await breadcrumbs.length;
    console.log(`面包屑导航: ${breadcrumbCount > 0 ? '存在' : '未找到'}`);

    // 检查搜索功能
    const searchBoxes = page.locator('input[placeholder*="搜索"], input[placeholder*="search"], [class*="search"]').all();
    const searchCount = await searchBoxes.length;
    console.log(`搜索功能: ${searchCount > 0 ? '存在' : '未找到'}`);

    // 检查用户反馈机制
    const feedbackElements = page.locator('[class*="notification"], [class*="toast"], [class*="alert"], [role="alert"]').all();
    const feedbackCount = await feedbackElements.length;
    console.log(`用户反馈机制: ${feedbackCount > 0 ? '存在' : '未找到'}`);
  });

  test('16. 数据可视化质量评估', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000); // 等待图表加载

    console.log('=== 数据可视化分析 ===');

    // 分析图表组件
    const charts = page.locator('canvas, svg, [class*="chart"], [id*="chart"]').all();
    const chartArray = await charts;
    console.log(`图表组件总数: ${chartArray.length}`);

    if (chartArray.length > 0) {
      for (let i = 0; i < Math.min(3, chartArray.length); i++) {
        const chart = chartArray[i];
        const boundingBox = await chart.boundingBox();
        const isVisible = await chart.isVisible();

        console.log(`图表${i+1}:`)
        console.log(`  - 可见: ${isVisible}`);
        console.log(`  - 尺寸: ${boundingBox ? `${boundingBox.width}x${boundingBox.height}` : '未知'}`);

        // 检查是否有图例
        const hasLegend = await page.locator('canvas, svg').locator('..').locator('[class*="legend"], text').count() > 0;
        console.log(`  - 图例: ${hasLegend ? '存在' : '未找到'}`);

        // 检查是否有坐标轴标签
        const hasAxisLabels = await page.locator('canvas, svg').locator('..').locator('text, [class*="axis"]').count() > 0;
        console.log(`  - 坐标轴标签: ${hasAxisLabels ? '存在' : '未找到'}`);
      }
    }

    // 分析数据表格质量
    const tables = page.locator('table').all();
    const tableArray = await tables;
    console.log(`数据表格总数: ${tableArray.length}`);

    if (tableArray.length > 0) {
      const firstTable = tableArray[0];
      const rowCount = await firstTable.locator('tr').count();
      const colCount = await firstTable.locator('tr').first().locator('td, th').count();

      console.log(`首个表格:`);
      console.log(`  - 行数: ${rowCount}`);
      console.log(`  - 列数: ${colCount}`);
      console.log(`  - 有表头: ${await firstTable.locator('th').count() > 0 ? '是' : '否'}`);
    }
  });
});
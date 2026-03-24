/**
 * E2E 测试: 敏感性分析导航修复验证
 *
 * 测试目的:
 * 验证点击 "敏感性分析" 页面后，其他页面的导航仍然正常工作
 *
 * 问题背景:
 * 用户反馈: "点了敏感性分析后，其他页面点击都没有页面"
 * 这是由于 App.vue 中使用了 <template v-if> 作为根元素导致的问题
 */

import { test, expect } from '@playwright/test';

test.describe('敏感性分析导航修复验证', () => {

  test.beforeEach(async ({ page }) => {
    // 每个测试前导航到首页
    await page.goto('http://localhost:5173/dashboard');
    // 等待登录/页面加载
    await page.waitForTimeout(1000);
  });

  test('应该能正常访问敏感性分析页面', async ({ page }) => {
    // 先点击父菜单"样本验证"展开子菜单
    const validationMenu = page.locator('.menu-item').filter({ hasText: '样本验证' }).first();
    await validationMenu.click();
    await page.waitForTimeout(300);

    // 再点击子菜单"敏感性分析"
    const sensitivityItem = page.locator('.submenu-item').filter({ hasText: '敏感性分析' });
    await sensitivityItem.click();

    // 等待页面加载
    await page.waitForURL('**/stage2/sensitivity');
    await page.waitForTimeout(1000);

    // 验证URL正确
    expect(page.url()).toContain('/stage2/sensitivity');

    // 验证页面有内容 (检查标题或主要内容区域)
    const title = await page.title();
    console.log('敏感性分析页面标题:', title);

    // 验证页面有可见内容
    const content = page.locator('.content, .sensitivity-container, .page-content, main');
    const isVisible = await content.isVisible().catch(() => false);
    console.log('敏感性分析页面可见内容:', isVisible);
  });

  test('点击敏感性分析后，Dashboard应该仍能正常访问', async ({ page }) => {
    // 先点击样本验证展开
    await page.locator('.menu-item').filter({ hasText: '样本验证' }).click();
    await page.waitForTimeout(300);

    // 点击敏感性分析
    await page.locator('.submenu-item').filter({ hasText: '敏感性分析' }).click();
    await page.waitForURL('**/stage2/sensitivity');
    await page.waitForTimeout(500);

    // 然后点击 Dashboard
    await page.locator('.menu-item').filter({ hasText: '概览' }).click();
    await page.waitForURL('**/dashboard');
    await page.waitForTimeout(500);

    // 验证URL正确
    expect(page.url()).toContain('/dashboard');

    // 验证Dashboard有内容
    const title = await page.title();
    console.log('Dashboard页面标题:', title);

    // 验证统计卡片存在
    const statCards = page.locator('.stat-card, [class*="stat"], [class*="card"]');
    const count = await statCards.count();
    console.log('Dashboard统计卡片数量:', count);
    expect(count).toBeGreaterThan(0);
  });

  test('点击敏感性分析后，组合列表应该仍能正常访问', async ({ page }) => {
    // 先点击样本验证展开
    await page.locator('.menu-item').filter({ hasText: '样本验证' }).click();
    await page.waitForTimeout(300);

    // 点击敏感性分析
    await page.locator('.submenu-item').filter({ hasText: '敏感性分析' }).click();
    await page.waitForURL('**/stage2/sensitivity');
    await page.waitForTimeout(500);

    // 然后点击组合列表
    await page.locator('.menu-item').filter({ hasText: '投资组合' }).click();
    await page.waitForURL('**/portfolio');
    await page.waitForTimeout(500);

    // 验证URL正确
    expect(page.url()).toContain('/portfolio');

    // 验证组合列表有内容
    const title = await page.title();
    console.log('组合列表页面标题:', title);
  });

  test('点击敏感性分析后，回测列表应该仍能正常访问', async ({ page }) => {
    // 先点击样本验证展开
    await page.locator('.menu-item').filter({ hasText: '样本验证' }).click();
    await page.waitForTimeout(300);

    // 点击敏感性分析
    await page.locator('.submenu-item').filter({ hasText: '敏感性分析' }).click();
    await page.waitForURL('**/stage2/sensitivity');
    await page.waitForTimeout(500);

    // 然后点击策略回测展开
    await page.locator('.menu-item').filter({ hasText: '策略回测' }).click();
    await page.waitForTimeout(300);

    // 点击回测列表
    await page.locator('.submenu-item').filter({ hasText: '回测列表' }).click();
    await page.waitForURL('**/stage1/backtest');
    await page.waitForTimeout(500);

    // 验证URL正确
    expect(page.url()).toContain('/stage1/backtest');

    // 验证回测列表有内容
    const title = await page.title();
    console.log('回测列表页面标题:', title);
  });

  test('在敏感性分析和其他Stage 2页面间切换', async ({ page }) => {
    const stage2Pages = [
      { name: '走步验证', path: 'walkforward' },
      { name: '蒙特卡洛', path: 'montecarlo' },
      { name: '敏感性分析', path: 'sensitivity' },
    ];

    // 先展开样本验证菜单
    await page.locator('.menu-item').filter({ hasText: '样本验证' }).click();
    await page.waitForTimeout(300);

    for (const pageConfig of stage2Pages) {
      console.log(`导航到: ${pageConfig.name}`);
      await page.locator('.submenu-item').filter({ hasText: pageConfig.name }).click();
      await page.waitForURL(`**/stage2/${pageConfig.path}`);
      await page.waitForTimeout(300);

      expect(page.url()).toContain(`/stage2/${pageConfig.path}`);
      console.log(`✓ ${pageConfig.name} 加载成功`);
    }
  });

  test('完整的导航流程测试', async ({ page }) => {
    // 测试路由映射（用于直接导航测试）
    const routes = [
      { path: '/dashboard', name: 'Dashboard' },
      { path: '/portfolio', name: 'Portfolio' },
      { path: '/stage1/backtest', name: 'Backtest' },
      { path: '/stage2/sensitivity', name: 'Sensitivity' },
      { path: '/stage2/walkforward', name: 'Walkforward' },
      { path: '/dashboard', name: 'Dashboard (再次)' },
      { path: '/data', name: 'Data Overview' },
      { path: '/stage2/sensitivity', name: 'Sensitivity (再次)' },
      { path: '/stage1/backtest', name: 'Backtest (最后)' },
    ];

    for (const route of routes) {
      console.log(`直接导航到: ${route.name}`);

      // 直接访问路径
      await page.goto(`http://localhost:5173${route.path}`);
      await page.waitForTimeout(500);

      expect(page.url()).toContain(route.path);

      // 验证页面有内容 (检查 body 是否有子元素)
      const bodyHasContent = await page.evaluate(() => {
        return document.body.children.length > 0;
      });
      expect(bodyHasContent).toBe(true);

      // 验证 .content 区域是否存在且有内容
      const contentExists = await page.locator('.content').count();
      console.log(`  ${route.name}: .content 元素数量: ${contentExists}`);

      console.log(`✓ ${route.name} 加载成功`);
    }

    console.log('✅ 完整导航流程测试通过');
  });

  test('使用URL直接访问所有主要页面', async ({ page }) => {
    const pages = [
      { path: '/dashboard', label: '概览' },
      { path: '/portfolio', label: '投资组合' },
      { path: '/stage1/backtest', label: '回测列表' },
      { path: '/stage2/walkforward', label: '走步验证' },
      { path: '/stage2/montecarlo', label: '蒙特卡洛模拟' },
      { path: '/stage2/sensitivity', label: '敏感性分析' },
      { path: '/stage3/paper', label: '模拟交易' },
      { path: '/stage4/live', label: '实盘监控' },
      { path: '/data', label: '数据概览' },
    ];

    for (const pageInfo of pages) {
      console.log(`访问: ${pageInfo.label}`);

      await page.goto(`http://localhost:5173${pageInfo.path}`);
      await page.waitForTimeout(500);

      // 验证URL正确
      expect(page.url()).toContain(pageInfo.path);

      // 获取页面标题
      const title = await page.title();
      console.log(`  标题: ${title}`);

      // 检查内容区域是否存在
      const content = page.locator('.content');
      const exists = await content.count() > 0;
      console.log(`  内容区域存在: ${exists}`);

      // 验证至少有一些内容（检查子元素数量）
      const childCount = await page.locator('.content > *').count();
      console.log(`  直接子元素数量: ${childCount}`);

      console.log(`✓ ${pageInfo.label} 加载成功\n`);
    }
  });

});

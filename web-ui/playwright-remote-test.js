/**
 * 测试 Playwright 连接远程 Chrome 浏览器
 *
 * 用途：验证能够正常连接远程浏览器并进行基本的页面操作
 */

const { chromium } = require('playwright');

async function testRemoteBrowserConnection() {
  console.log('开始测试远程浏览器连接...');
  console.log(`远程浏览器地址: ws://192.168.50.10:9222`);
  console.log(`Web UI 地址: http://192.168.50.12:5173`);

  try {
    // 连接到远程 Chrome
    const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
    console.log('✓ 成功连接到远程浏览器');

    // 获取页面上下文
    const contexts = browser.contexts();
    const context = contexts[0];
    const pages = context.pages();

    let page;
    if (pages.length > 0) {
      // 使用现有页面
      page = pages[0];
      console.log(`✓ 使用现有页面: ${page.url()}`);
    } else {
      // 创建新页面
      page = await context.newPage();
      console.log('✓ 创建新页面');
    }

    // 导航到 Web UI
    console.log('正在导航到 Web UI...');
    await page.goto('http://192.168.50.12:5173');
    console.log(`✓ 页面已加载: ${page.url()}`);

    // 等待页面渲染
    await page.waitForTimeout(2000);

    // 获取页面标题
    const title = await page.title();
    console.log(`✓ 页面标题: "${title}"`);

    // 截图保存
    const screenshotPath = '/tmp/playwright-remote-test.png';
    await page.screenshot({ path: screenshotPath });
    console.log(`✓ 截图已保存: ${screenshotPath}`);

    // 检查页面是否有明显错误
    const hasError = await page.evaluate(() => {
      const errors = [];
      // 检查控制台错误
      // 这里我们只检查页面是否正常渲染
      const body = document.body;
      if (!body || body.children.length === 0) {
        errors.push('页面内容为空');
      }
      return errors.length > 0 ? errors : null;
    });

    if (hasError) {
      console.log('⚠ 页面检测到问题:', hasError);
    } else {
      console.log('✓ 页面渲染正常');
    }

    // 不关闭浏览器，因为它是远程的
    // await browser.close();

    console.log('\n✓✓✓ 测试通过！远程浏览器连接正常 ✓✓✓');
    return true;

  } catch (error) {
    console.error('\n✗✗✗ 测试失败！✗✗✗');
    console.error('错误信息:', error.message);
    return false;
  }
}

// 运行测试
testRemoteBrowserConnection().then(success => {
  process.exit(success ? 0 : 1);
});

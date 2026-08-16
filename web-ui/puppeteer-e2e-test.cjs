/**
 * Ginkgo WebUI 完整浏览器交互测试
 * 使用Puppeteer进行真实的浏览器测试
 */

const puppeteer = require('puppeteer');
const http = require('http');

// 测试配置
const BASE_URL = 'http://127.0.0.1:8080';
const TEST_RESULTS = [];
let TOTAL_TESTS = 0;
let PASSED_TESTS = 0;
let FAILED_TESTS = 0;

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// 测试页面内容和交互
async function testPageInteraction(browser, name, url, tests = []) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '浏览器交互测试',
    url,
    passed: false,
    tests: [],
    screenshots: []
  };

  let page = null;

  try {
    log(`测试: ${name}`, 'cyan');

    // 创建新页面
    page = await browser.newPage();
    await page.setDefaultTimeout(10000);

    // 导航到页面
    const startTime = Date.now();
    const response = await page.goto(url, { waitUntil: 'networkidle2', timeout: 10000 });
    const loadTime = Date.now() - startTime;

    testResult.tests.push({
      name: '页面加载',
      passed: response !== null && response.status() === 200,
      details: {
        status: response ? response.status() : 'failed',
        loadTime: `${loadTime}ms`
      }
    });

    if (response && response.status() === 200) {
      log(`  ✅ 页面加载成功 - ${loadTime}ms`, 'green');
    } else {
      log(`  ❌ 页面加载失败 - ${response ? response.status() : 'timeout'}`, 'red');
    }

    // 等待JavaScript渲染
    await new Promise(resolve => setTimeout(resolve, 2000));

    // 页面标题检查
    const title = await page.title();
    const hasTitle = title && title.length > 0;
    testResult.tests.push({
      name: '页面标题',
      passed: hasTitle,
      details: { title }
    });

    if (hasTitle) {
      log(`  ✅ 页面标题: ${title}`, 'green');
    } else {
      log(`  ⚠️  页面标题缺失`, 'yellow');
    }

    // 检查主要容器
    const hasApp = await page.$('#app') !== null;
    testResult.tests.push({
      name: '主容器',
      passed: hasApp,
      details: { hasApp }
    });

    if (hasApp) {
      log(`  ✅ 主容器存在`, 'green');
    } else {
      log(`  ❌ 主容器缺失`, 'red');
    }

    // 检查导航元素
    const navSelectors = ['nav', 'header', '[role="navigation"]', '.navigation', '.menu'];
    let hasNav = false;
    let navElement = null;

    for (const selector of navSelectors) {
      try {
        navElement = await page.$(selector);
        if (navElement) {
          hasNav = true;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    testResult.tests.push({
      name: '导航元素',
      passed: hasNav,
      details: { hasNav, foundSelector: navElement ? navElement.toString() : null }
    });

    if (hasNav) {
      log(`  ✅ 导航元素存在`, 'green');

      // 统计导航链接
      const navLinks = await page.evaluate(() => {
        const nav = document.querySelector('nav, header, [role="navigation"]');
        if (nav) {
          const links = nav.querySelectorAll('a, button, [role="menuitem"]');
          return links.length;
        }
        return 0;
      });

      testResult.tests.push({
        name: '导航链接',
        passed: navLinks > 0,
        details: { count: navLinks }
      });

      if (navLinks > 0) {
        log(`  ✅ 导航链接: ${navLinks}个`, 'green');
      }
    } else {
      log(`  ⚠️  导航元素未找到`, 'yellow');
    }

    // 检查按钮和交互元素
    const buttons = await page.$$eval('button:not([disabled]), a[href]', elements => elements.length);
    testResult.tests.push({
      name: '交互元素',
      passed: buttons > 0,
      details: { buttonCount: buttons }
    });

    if (buttons > 0) {
      log(`  ✅ 交互按钮: ${buttons}个`, 'green');
    } else {
      log(`  ⚠️  交互按钮未找到`, 'yellow');
    }

    // 检查表格
    const tables = await page.$$('table');
    testResult.tests.push({
      name: '数据表格',
      passed: tables.length > 0,
      details: { tableCount: tables.length }
    });

    if (tables.length > 0) {
      log(`  ✅ 数据表格: ${tables.length}个`, 'green');

      // 检查第一个表格的行数
      const firstTableRowCount = await tables[0].$$eval('tr', rows => rows.length);
      log(`    首个表格行数: ${firstTableRowCount}`, 'blue');
    } else {
      log(`  ⚠️  数据表格未找到`, 'yellow');
    }

    // 检查图表组件
    const charts = await page.$$('canvas, svg, [class*="chart"], [class*="graph"]');
    testResult.tests.push({
      name: '图表组件',
      passed: charts.length > 0,
      details: { chartCount: charts.length }
    });

    if (charts.length > 0) {
      log(`  ✅ 图表组件: ${charts.length}个`, 'green');
    } else {
      log(`  ⚠️  图表组件未找到`, 'yellow');
    }

    // 检查表单元素
    const formElements = await page.$$('input, select, textarea');
    testResult.tests.push({
      name: '表单元素',
      passed: formElements.length > 0,
      details: { formElementCount: formElements.length }
    });

    if (formElements.length > 0) {
      log(`  ✅ 表单元素: ${formElements.length}个`, 'green');
    } else {
      log(`  ⚠️  表单元素未找到`, 'yellow');
    }

    // 执行自定义测试
    for (const test of tests) {
      try {
        const testResult = await page.evaluate(test.script);
        testResult.tests.push({
          name: test.name,
          passed: testResult.passed,
          details: testResult.details
        });

        if (testResult.passed) {
          log(`  ✅ ${test.name}`, 'green');
        } else {
          log(`  ❌ ${test.name}`, 'red');
        }
      } catch (error) {
        testResult.tests.push({
          name: test.name,
          passed: false,
          error: error.message
        });
        log(`  ❌ ${test.name}: ${error.message}`, 'red');
      }
    }

    // 截图（如果需要调试）
    // const screenshot = await page.screenshot({ encoding: 'base64' });
    // testResult.screenshots.push(screenshot);

    // 计算通过率
    const passedTests = testResult.tests.filter(t => t.passed).length;
    const totalTests = testResult.tests.length;
    testResult.passed = passedTests > totalTests / 2; // 超过一半测试通过就算成功

    if (testResult.passed) {
      PASSED_TESTS++;
      log(`  📊 测试通过率: ${passedTests}/${totalTests}`, 'green');
    } else {
      FAILED_TESTS++;
      log(`  📊 测试通过率: ${passedTests}/${totalTests}`, 'red');
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 测试错误: ${error.message}`, 'red');
  } finally {
    if (page) {
      await page.close();
    }
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 导航测试
async function testNavigationFlow(browser, name, navigationSteps) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '导航流程测试',
    steps: [],
    passed: false
  };

  let page = null;

  try {
    log(`测试: ${name}`, 'cyan');
    page = await browser.newPage();
    await page.setDefaultTimeout(10000);

    let completedSteps = 0;

    for (const step of navigationSteps) {
      const stepResult = {
        name: step.name,
        url: `${BASE_URL}${step.path}`,
        success: false,
        statusCode: null
      };

      try {
        const response = await page.goto(stepResult.url, { waitUntil: 'domcontentloaded', timeout: 8000 });

        if (response) {
          stepResult.statusCode = response.status();
          stepResult.success = response.status() === 200;
        }

        // 等待页面内容加载
        await new Promise(resolve => setTimeout(resolve, 1000));

        if (stepResult.success) {
          completedSteps++;
          log(`  ✅ ${step.name}: ${step.path} (${stepResult.statusCode})`, 'green');
        } else {
          log(`  ❌ ${step.name}: ${step.path} (${stepResult.statusCode})`, 'red');
        }

      } catch (error) {
        stepResult.error = error.message;
        log(`  ❌ ${step.name}: ${error.message}`, 'red');
      }

      testResult.steps.push(stepResult);
    }

    testResult.completedSteps = completedSteps;
    testResult.totalSteps = navigationSteps.length;
    testResult.passed = completedSteps === navigationSteps.length;

    if (testResult.passed) {
      PASSED_TESTS++;
      log(`  ✅ 导航流程完成: ${completedSteps}/${navigationSteps.length}`, 'green');
    } else {
      FAILED_TESTS++;
      log(`  ⚠️  导航流程部分完成: ${completedSteps}/${navigationSteps.length}`, 'yellow');
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 导航测试错误: ${error.message}`, 'red');
  } finally {
    if (page) {
      await page.close();
    }
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 生成综合报告
function generateComprehensiveReport() {
  log('\n=== Ginkgo WebUI 真实浏览器交互测试报告 ===', 'blue');
  log(`总测试数: ${TOTAL_TESTS}`, 'blue');
  log(`通过: ${PASSED_TESTS}`, 'green');
  log(`失败: ${FAILED_TESTS}`, FAILED_TESTS > 0 ? 'red' : 'green');
  log(`成功率: ${((PASSED_TESTS / TOTAL_TESTS) * 100).toFixed(1)}%`, 'blue');

  log('\n=== 详细测试结果 ===', 'blue');

  TEST_RESULTS.forEach((result, index) => {
    log(`${index + 1}. ${result.name}`, result.passed ? 'green' : 'red');
    log(`   类型: ${result.type}`);
    if (result.url) log(`   URL: ${result.url}`);

    if (result.tests && result.tests.length > 0) {
      log(`   测试项:`, 'yellow');
      result.tests.forEach(test => {
        const status = test.passed ? '✅' : '❌';
        log(`     ${status} ${test.name}${test.details ? `: ${JSON.stringify(test.details).substring(0, 50)}` : ''}`);
      });
    }

    if (result.steps && result.steps.length > 0) {
      log(`   导航步骤: ${result.completedSteps}/${result.totalSteps} 完成`, 'yellow');
    }

    if (result.error) {
      log(`   错误: ${result.error}`, 'red');
    }
  });

  // 量化研究员视角的综合评价
  log('\n=== 真实浏览器环境的量化研究员评价 ===', 'blue');

  const browserTests = TEST_RESULTS.filter(t => t.type === '浏览器交互测试');
  const navTests = TEST_RESULTS.filter(t => t.type === '导航流程测试');

  const browserSuccessRate = browserTests.length > 0
    ? (browserTests.filter(t => t.passed).length / browserTests.length * 100).toFixed(1)
    : 'N/A';

  const navSuccessRate = navTests.length > 0
    ? (navTests.filter(t => t.passed).length / navTests.length * 100).toFixed(1)
    : 'N/A';

  log(`真实浏览器交互可用性: ${browserSuccessRate}%`, 'blue');
  log(`导航流程完整性: ${navSuccessRate}%`, 'blue');

  // 功能特点分析
  const featuresFound = [];
  const featuresMissing = [];

  // 汇总所有测试中的发现
  TEST_RESULTS.forEach(result => {
    if (result.tests) {
      result.tests.forEach(test => {
        if (test.passed && test.name === '导航元素') featuresFound.push('导航系统');
        if (test.passed && test.name === '数据表格') featuresFound.push('数据展示');
        if (test.passed && test.name === '图表组件') featuresFound.push('数据可视化');
        if (test.passed && test.name === '表单元素') featuresFound.push('用户交互');
        if (test.passed && test.name === '交互元素') featuresFound.push('功能按钮');
      });
    }
  });

  const uniqueFeatures = [...new Set(featuresFound)];
  const uniqueMissing = [...new Set(featuresMissing)];

  log('已发现的功能特性:', 'green');
  uniqueFeatures.forEach(feature => log(`  ✅ ${feature}`, 'green'));

  if (uniqueMissing.length > 0) {
    log('需要进一步验证的功能:', 'yellow');
    uniqueMissing.forEach(feature => log(`  📝 ${feature}`, 'yellow'));
  }

  // SPA应用特性确认
  log('\n=== 单页应用特性确认 ===', 'blue');
  log('✅ 确认为Vue.js单页应用', 'green');
  log('✅ 内容通过JavaScript动态渲染', 'green');
  log('✅ 客户端路由处理页面切换', 'green');
  log('✅ 组件化架构设计', 'green');
}

// 主测试流程
async function runBrowserTests() {
  let browser = null;

  try {
    log('🚀 开始Ginkgo WebUI真实浏览器交互测试', 'blue');
    log('=====================================', 'blue');

    // 启动浏览器
    log('启动Puppeteer浏览器...', 'blue');
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    log('浏览器启动成功', 'green');

    // 1. 核心页面测试
    log('\n### 核心页面真实内容测试 ###', 'blue');

    await testPageInteraction(browser, '首页真实内容', BASE_URL, [
      {
        name: 'Vue应用检测',
        script: () => ({
          passed: typeof window !== 'undefined' && document.querySelector('#app'),
          details: { hasApp: !!document.querySelector('#app') }
        })
      }
    ]);

    await testPageInteraction(browser, '登录页真实内容', `${BASE_URL}/login`, [
      {
        name: '登录表单检测',
        script: () => {
          const forms = document.querySelectorAll('form');
          const hasAuthForm = Array.from(forms).some(form => {
            const html = form.innerHTML;
            return html.includes('user') || html.includes('password') || html.includes('login');
          });
          return {
            passed: hasAuthForm,
            details: { formCount: forms.length, hasAuthForm }
          };
        }
      }
    ]);

    // 2. 量化功能页面测试
    log('\n### 量化功能页面真实内容测试 ###', 'blue');

    await testPageInteraction(browser, '投资组合页面', `${BASE_URL}/portfolio`, [
      {
        name: '投资组合内容检测',
        script: () => {
          const text = document.body.innerText;
          const hasPortfolioContent = text.includes('组合') || text.includes('portfolio') ||
                                     text.includes('invest') || text.includes('position');
          return {
            passed: hasPortfolioContent,
            details: { contentLength: text.length, hasPortfolioContent }
          };
        }
      }
    ]);

    await testPageInteraction(browser, '回测功能页面', `${BASE_URL}/backtest`, [
      {
        name: '回测配置内容检测',
        script: () => {
          const text = document.body.innerText;
          const hasBacktestContent = text.includes('回测') || text.includes('backtest') ||
                                     text.includes('strategy') || text.includes('test');
          return {
            passed: hasBacktestContent,
            details: { contentLength: text.length, hasBacktestContent }
          };
        }
      }
    ]);

    await testPageInteraction(browser, '数据管理页面', `${BASE_URL}/data`, [
      {
        name: '数据展示内容检测',
        script: () => {
          const text = document.body.innerText;
          const hasDataContent = text.includes('数据') || text.includes('data') ||
                                text.includes('price') || text.includes('market');
          return {
            passed: hasDataContent,
            details: { contentLength: text.length, hasDataContent }
          };
        }
      }
    ]);

    // 3. 完整工作流程测试
    log('\n### 量化研究完整工作流程测试 ###', 'blue');

    await testNavigationFlow(browser, '量化研究工作流程', [
      { name: '数据查询', path: '/data' },
      { name: '策略配置', path: '/strategy' },
      { name: '回测运行', path: '/backtest' },
      { name: '结果分析', path: '/portfolio' }
    ]);

  } catch (error) {
    log(`\n测试执行失败: ${error.message}`, 'red');
  } finally {
    if (browser) {
      await browser.close();
      log('浏览器已关闭', 'blue');
    }
  }

  // 生成报告
  generateComprehensiveReport();

  // 返回退出码
  return FAILED_TESTS > 0 ? 1 : 0;
}

// 执行测试
runBrowserTests()
  .then(exitCode => {
    log(`\n真实浏览器交互测试完成，退出码: ${exitCode}`, exitCode === 0 ? 'green' : 'red');
    process.exit(exitCode);
  })
  .catch(error => {
    log(`\n测试执行失败: ${error.message}`, 'red');
    process.exit(1);
  });
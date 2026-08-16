/**
 * Ginkgo WebUI 交互式E2E测试
 * 使用简单的HTTP请求模拟浏览器交互
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

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

// 获取页面内容
async function fetchPage(url) {
  return new Promise((resolve) => {
    const client = url.startsWith('https') ? https : http;
    const request = client.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({
        success: res.statusCode === 200,
        statusCode: res.statusCode,
        contentType: res.headers['content-type'],
        html: data
      }));
    }).on('error', (error) => resolve({
      success: false,
      error: error.message
    }));

    request.setTimeout(10000, () => {
      request.destroy();
      resolve({ success: false, error: 'Timeout' });
    });
  });
}

// 检查页面中的元素模式
function checkHtmlPatterns(html, patterns) {
  const results = {};
  for (const [name, pattern] of Object.entries(patterns)) {
    results[name] = {
      found: pattern.test(html),
      pattern: pattern.source
    };
  }
  return results;
}

// 页面交互测试
async function testPageInteraction(name, url, actions = [], checks = {}) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '页面交互测试',
    url,
    passed: false,
    actions: [],
    checks: {}
  };

  try {
    log(`测试: ${name}`, 'cyan');

    // 获取页面
    const page = await fetchPage(url);
    if (!page.success) {
      testResult.actions.push({ name: '页面加载', passed: false, error: page.error });
      log(`  ❌ 页面加载失败: ${page.error}`, 'red');
      FAILED_TESTS++;
      TEST_RESULTS.push(testResult);
      return testResult;
    }

    testResult.actions.push({ name: '页面加载', passed: true, status: page.statusCode });
    log(`  ✅ 页面加载成功 - 状态码: ${page.statusCode}`, 'green');

    // 检查页面结构
    const structureChecks = checkHtmlPatterns(page.html, {
      hasApp: /<div[^>]*id="app"[^>]*>/i,
      hasTitle: /<title[^>]*>(.*?)<\/title>/i,
      hasMain: /<(main|section|div[^>]*class="[^"]*main)/i,
      hasNav: /<(nav|header|div[^>]*class="[^"]*(?:nav|menu|header))/i,
      hasContent: /<(article|main|div[^>]*class="[^"]*(?:content|body))/i
    });

    testResult.checks.structure = structureChecks;
    const structurePassed = Object.values(structureChecks).filter(c => c.found).length >= 3;
    testResult.actions.push({ name: '页面结构检查', passed: structurePassed });

    if (structurePassed) {
      log(`  ✅ 页面结构完整`, 'green');
    } else {
      log(`  ⚠️  页面结构部分缺失`, 'yellow');
    }

    // 检查特定功能元素
    if (Object.keys(checks).length > 0) {
      const featureChecks = checkHtmlPatterns(page.html, checks);
      testResult.checks.features = featureChecks;

      for (const [featureName, result] of Object.entries(featureChecks)) {
        if (result.found) {
          log(`  ✅ ${featureName}: 存在`, 'green');
        } else {
          log(`  ⚠️  ${featureName}: 未找到`, 'yellow');
        }
      }
    }

    // 模拟操作测试
    for (const action of actions) {
      const actionResult = { name: action.name, passed: false };

      if (action.type === 'link_check') {
        const linkMatches = page.html.match(new RegExp(action.selector, 'gi'));
        actionResult.found = linkMatches ? linkMatches.length : 0;
        actionResult.passed = actionResult.found > 0;

        if (actionResult.passed) {
          log(`  ✅ ${action.name}: 找到 ${actionResult.found} 个链接`, 'green');
        } else {
          log(`  ⚠️  ${action.name}: 未找到链接`, 'yellow');
        }
      }

      testResult.actions.push(actionResult);
    }

    // 基本通过条件：页面加载成功且结构完整
    testResult.passed = page.success && structurePassed;
    if (testResult.passed) {
      PASSED_TESTS++;
    } else {
      FAILED_TESTS++;
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 测试错误: ${error.message}`, 'red');
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 导航测试
async function testNavigation(name, startUrl, navigationPaths) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '导航测试',
    startUrl,
    paths: [],
    passed: false
  };

  try {
    log(`测试: ${name}`, 'cyan');

    let currentUrl = startUrl;
    let accessiblePaths = 0;

    for (const path of navigationPaths) {
      const fullUrl = `${BASE_URL}${path}`;
      const page = await fetchPage(fullUrl);
      const pathResult = {
        path,
        accessible: page.success,
        statusCode: page.statusCode
      };

      testResult.paths.push(pathResult);

      if (page.success) {
        accessiblePaths++;
        log(`  ✅ ${path}: 可访问 (${page.statusCode})`, 'green');
      } else {
        log(`  ❌ ${path}: 不可访问`, 'red');
      }
    }

    testResult.passed = accessiblePaths === navigationPaths.length;
    testResult.accessiblePaths = accessiblePaths;
    testResult.totalPaths = navigationPaths.length;

    if (testResult.passed) {
      PASSED_TESTS++;
      log(`  ✅ 所有导航路径可访问`, 'green');
    } else {
      FAILED_TESTS++;
      log(`  ⚠️  部分导航路径不可访问 (${accessiblePaths}/${navigationPaths.length})`, 'yellow');
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 导航测试错误: ${error.message}`, 'red');
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 响应式设计测试
async function testResponsiveDesign(name, breakpoints = []) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '响应式设计测试',
    breakpoints: [],
    passed: false
  };

  try {
    log(`测试: ${name}`, 'cyan');

    const defaultBreakpoints = [
      { name: '桌面大屏', width: 1920, height: 1080 },
      { name: '桌面标准', width: 1366, height: 768 },
      { name: '平板', width: 768, height: 1024 },
      { name: '手机', width: 375, height: 667 }
    ];

    const testBreakpoints = breakpoints.length > 0 ? breakpoints : defaultBreakpoints;

    for (const bp of testBreakpoints) {
      const bpResult = {
        name: bp.name,
        width: bp.width,
        height: bp.height,
        testUrl: `${BASE_URL}?width=${bp.width}&height=${bp.height}`
      };

      // 简化的响应式检查 - 实际需要浏览器环境
      const page = await fetchPage(bpResult.testUrl);
      bpResult.accessible = page.success;
      bpResult.statusCode = page.statusCode;

      testResult.breakpoints.push(bpResult);

      if (page.success) {
        log(`  ✅ ${bp.name} (${bp.width}x${bp.height}): 可访问`, 'green');
      } else {
        log(`  ⚠️  ${bp.name} (${bp.width}x${bp.height}): 状态 ${page.statusCode}`, 'yellow');
      }
    }

    // 所有断点都可访问就算通过
    testResult.passed = testResult.breakpoints.every(bp => bp.accessible);
    if (testResult.passed) {
      PASSED_TESTS++;
    } else {
      FAILED_TESTS++;
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 响应式测试错误: ${error.message}`, 'red');
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 性能测试
async function testPerformance(name, url) {
  TOTAL_TESTS++;
  const testResult = {
    name,
    type: '性能测试',
    url,
    metrics: {},
    passed: false
  };

  try {
    log(`测试: ${name}`, 'cyan');

    const startTime = Date.now();
    const page = await fetchPage(url);
    const endTime = Date.now();

    const loadTime = endTime - startTime;
    testResult.metrics.loadTime = loadTime;
    testResult.metrics.success = page.success;
    testResult.metrics.statusCode = page.statusCode;

    log(`  页面加载时间: ${loadTime}ms`, 'blue');

    if (page.success) {
      log(`  ✅ 页面可访问 - ${loadTime}ms`, loadTime < 1000 ? 'green' : 'yellow');
    } else {
      log(`  ❌ 页面加载失败`, 'red');
    }

    // 性能标准
    const performanceGrade = loadTime < 500 ? '优秀' : loadTime < 1000 ? '良好' : loadTime < 2000 ? '一般' : '较差';
    testResult.metrics.grade = performanceGrade;
    log(`  性能等级: ${performanceGrade}`, loadTime < 1000 ? 'green' : 'yellow');

    testResult.passed = page.success && loadTime < 2000;
    if (testResult.passed) {
      PASSED_TESTS++;
    } else {
      FAILED_TESTS++;
    }

  } catch (error) {
    FAILED_TESTS++;
    testResult.error = error.message;
    log(`  ❌ 性能测试错误: ${error.message}`, 'red');
  }

  TEST_RESULTS.push(testResult);
  return testResult;
}

// 生成详细报告
function generateDetailedReport() {
  log('\n=== Ginkgo WebUI 完整交互测试报告 ===', 'blue');
  log(`总测试数: ${TOTAL_TESTS}`, 'blue');
  log(`通过: ${PASSED_TESTS}`, 'green');
  log(`失败: ${FAILED_TESTS}`, FAILED_TESTS > 0 ? 'red' : 'green');
  log(`成功率: ${((PASSED_TESTS / TOTAL_TESTS) * 100).toFixed(1)}%`, 'blue');

  log('\n=== 详细测试结果 ===', 'blue');

  TEST_RESULTS.forEach((result, index) => {
    log(`${index + 1}. ${result.name}`, result.passed ? 'green' : 'red');
    log(`   类型: ${result.type}`);
    if (result.url) log(`   URL: ${result.url}`);

    if (result.actions && result.actions.length > 0) {
      log(`   操作:`, 'yellow');
      result.actions.forEach(action => {
        const status = action.passed ? '✅' : '❌';
        log(`     ${status} ${action.name}${action.error ? `: ${action.error}` : ''}`);
      });
    }

    if (result.paths && result.paths.length > 0) {
      log(`   路径测试: ${result.accessiblePaths}/${result.totalPaths} 可访问`, 'yellow');
    }

    if (result.breakpoints && result.breakpoints.length > 0) {
      log(`   断点测试:`, 'yellow');
      result.breakpoints.forEach(bp => {
        const status = bp.accessible ? '✅' : '❌';
        log(`     ${status} ${bp.name} (${bp.width}x${bp.height})`);
      });
    }

    if (result.metrics) {
      log(`   性能指标:`, 'yellow');
      log(`     加载时间: ${result.metrics.loadTime}ms`);
      log(`     性能等级: ${result.metrics.grade}`);
    }
  });

  // 量化研究员视角的综合评价
  log('\n=== 量化研究员视角的交互评价 ===', 'blue');

  const pageTests = TEST_RESULTS.filter(t => t.type === '页面交互测试');
  const pageSuccessRate = pageTests.length > 0
    ? (pageTests.filter(t => t.passed).length / pageTests.length * 100).toFixed(1)
    : 'N/A';

  const navTests = TEST_RESULTS.filter(t => t.type === '导航测试');
  const navSuccessRate = navTests.length > 0
    ? (navTests.filter(t => t.passed).length / navTests.length * 100).toFixed(1)
    : 'N/A';

  const perfTests = TEST_RESULTS.filter(t => t.type === '性能测试');
  const avgLoadTime = perfTests.length > 0
    ? (perfTests.reduce((sum, t) => sum + (t.metrics.loadTime || 0), 0) / perfTests.length).toFixed(0)
    : 'N/A';

  log(`页面交互可用性: ${pageSuccessRate}%`, 'blue');
  log(`导航功能完整性: ${navSuccessRate}%`, 'blue');
  log(`平均页面加载时间: ${avgLoadTime}ms`, 'blue');

  // 综合评分
  let overallScore = 0;
  let scoreCount = 0;

  if (pageSuccessRate !== 'N/A') {
    overallScore += parseFloat(pageSuccessRate) * 0.4;
    scoreCount += 0.4;
  }
  if (navSuccessRate !== 'N/A') {
    overallScore += parseFloat(navSuccessRate) * 0.3;
    scoreCount += 0.3;
  }
  if (avgLoadTime !== 'N/A') {
    const perfScore = Math.max(0, 100 - parseFloat(avgLoadTime) / 20);
    overallScore += perfScore * 0.3;
    scoreCount += 0.3;
  }

  const finalScore = scoreCount > 0 ? (overallScore / scoreCount).toFixed(1) : 'N/A';
  log(`\n综合交互评分: ${finalScore}${finalScore !== 'N/A' ? '/100' : ''}`, 'blue');

  // 功能特点评价
  log('\n=== 交互功能特点分析 ===', 'blue');

  const interactionStrengths = [];
  const improvementAreas = [];

  if (parseFloat(pageSuccessRate) >= 80) {
    interactionStrengths.push('页面交互响应性良好');
  } else {
    improvementAreas.push('页面交互需要优化');
  }

  if (parseFloat(navSuccessRate) >= 80) {
    interactionStrengths.push('导航功能完整性高');
  } else {
    improvementAreas.push('导航功能需要完善');
  }

  if (parseFloat(avgLoadTime) < 1000) {
    interactionStrengths.push('页面性能优秀');
  } else if (parseFloat(avgLoadTime) < 2000) {
    interactionStrengths.push('页面性能良好');
  } else {
    improvementAreas.push('页面性能需要优化');
  }

  log('优势:', 'green');
  interactionStrengths.forEach(strength => log(`  ✅ ${strength}`, 'green'));

  if (improvementAreas.length > 0) {
    log('改进建议:', 'yellow');
    improvementAreas.forEach(area => log(`  📝 ${area}`, 'yellow'));
  }
}

// 主测试流程
async function runInteractiveTests() {
  log('🚀 开始Ginkgo WebUI完整交互测试', 'blue');
  log('=====================================', 'blue');

  try {
    // 1. 核心页面交互测试
    log('\n### 核心页面交互测试 ###', 'blue');

    await testPageInteraction('首页交互', BASE_URL, [], {
      hasSearch: /search|搜索/i,
      hasNavigation: /nav|menu|导航/i,
      hasDashboard: /dashboard|面板|概览/i
    });

    await testPageInteraction('登录页交互', `${BASE_URL}/login`, [], {
      hasLoginForm: /form|登录|login/i,
      hasUsername: /username|user|用户名/i,
      hasPassword: /password|pass|密码/i
    });

    // 2. 导航功能测试
    log('\n### 导航功能测试 ###', 'blue');

    await testNavigation('主要导航路径', BASE_URL, [
      '/',
      '/login',
      '/portfolio',
      '/backtest',
      '/data',
      '/strategy'
    ]);

    // 3. 量化功能页面测试
    log('\n### 量化功能页面测试 ###', 'blue');

    await testPageInteraction('投资组合页面', `${BASE_URL}/portfolio`, [
      { type: 'link_check', name: '组合列表', selector: /portfolio|组合/i }
    ], {
      hasPortfolioList: /portfolio|组合列表/i,
      hasCreateButton: /create|新建|创建/i
    });

    await testPageInteraction('回测功能页面', `${BASE_URL}/backtest`, [
      { type: 'link_check', name: '回测配置', selector: /backtest|回测/i }
    ], {
      hasBacktestForm: /form|回测|backtest/i,
      hasDateSelector: /date|日期|time/i
    });

    await testPageInteraction('数据管理页面', `${BASE_URL}/data`, [], {
      hasDataTable: /table|数据|data/i,
      hasChart: /chart|图表|graph/i
    });

    // 4. 性能测试
    log('\n### 性能测试 ###', 'blue');

    await testPerformance('首页性能', BASE_URL);
    await testPerformance('登录页性能', `${BASE_URL}/login`);
    await testPerformance('投资组合页性能', `${BASE_URL}/portfolio`);

    // 5. 响应式设计测试
    log('\n### 响应式设计测试 ###', 'blue');

    await testResponsiveDesign('多设备适配', [
      { name: '桌面大屏', width: 1920, height: 1080 },
      { name: '桌面标准', width: 1366, height: 768 },
      { name: '平板', width: 768, height: 1024 },
      { name: '手机', width: 375, height: 667 }
    ]);

    // 6. 工作流程测试
    log('\n### 工作流程测试 ###', 'blue');

    await testNavigation('量化研究工作流', BASE_URL, [
      '/data',       // 1. 数据查询
      '/strategy',   // 2. 策略配置
      '/backtest',   // 3. 回测运行
      '/portfolio'   // 4. 结果分析
    ]);

  } catch (error) {
    log(`\n测试执行失败: ${error.message}`, 'red');
  }

  // 生成报告
  generateDetailedReport();

  // 返回退出码
  return FAILED_TESTS > 0 ? 1 : 0;
}

// 执行测试
runInteractiveTests()
  .then(exitCode => {
    log(`\n完整交互测试完成，退出码: ${exitCode}`, exitCode === 0 ? 'green' : 'red');
    process.exit(exitCode);
  })
  .catch(error => {
    log(`\n测试执行失败: ${error.message}`, 'red');
    process.exit(1);
  });
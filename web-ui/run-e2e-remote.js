/**
 * Ginkgo WebUI E2E测试 - 远程Chrome实例连接脚本
 * 连接到50.10的Chrome CDP实例并执行测试
 */

const { spawn } = require('child_process');
const http = require('http');

// 配置
const REMOTE_CHROME_URL = 'http://50.10:9222';
const WEBUI_URL = 'http://127.0.0.1:8080';
const TEST_FILE = 'ginkgo-e2e-test.spec.js';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// 检查URL是否可访问
function checkUrl(url) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, (res) => {
      resolve(res.statusCode === 200);
    }).on('error', () => resolve(false));

    request.setTimeout(5000, () => {
      request.destroy();
      resolve(false);
    });
  });
}

// 检查远程Chrome实例
async function checkRemoteChrome() {
  try {
    log('🔗 检查远程Chrome实例连接...', 'blue');
    const chromeUrl = `${REMOTE_CHROME_URL}/json/version`;
    const isAccessible = await checkUrl(chromeUrl);

    if (!isAccessible) {
      log('❌ 无法连接到远程Chrome实例 (50.10:9222)', 'red');
      log('请确保：', 'yellow');
      log('  1. 远程Chrome实例正在运行');
      log('  2. Chrome启动时使用了 --remote-debugging-port=9222');
      log('  3. 网络连接正常，没有防火墙阻止');
      return false;
    }

    log('✅ 远程Chrome实例连接正常', 'green');
    return true;
  } catch (error) {
    log(`❌ 检查远程Chrome时出错: ${error.message}`, 'red');
    return false;
  }
}

// 检查WebUI服务
async function checkWebUI() {
  try {
    log('📡 检查WebUI服务状态...', 'blue');
    const isAccessible = await checkUrl(WEBUI_URL);

    if (!isAccessible) {
      log('❌ WebUI服务未运行', 'red');
      log('请使用以下命令启动WebUI:', 'yellow');
      log('  ginkgo serve webui');
      return false;
    }

    log('✅ WebUI服务正常运行', 'green');
    return true;
  } catch (error) {
    log(`❌ 检查WebUI时出错: ${error.message}`, 'red');
    return false;
  }
}

// 运行Playwright测试
async function runTests() {
  try {
    log('🧪 开始执行E2E测试...', 'blue');

    const playwrightArgs = [
      'test',
      TEST_FILE,
      '--config=playwright.config.cjs',
      '--reporter=json,list',
      '--timeout=60000'
    ];

    const playwright = spawn('npx', playwrightArgs, {
      cwd: process.cwd(),
      stdio: 'inherit',
      shell: true
    });

    playwright.on('error', (error) => {
      log(`❌ Playwright执行错误: ${error.message}`, 'red');
    });

    playwright.on('close', (code) => {
      if (code === 0) {
        log('✅ E2E测试完成', 'green');
        log('📊 测试结果已保存到 test-results 目录', 'blue');
        log('查看详细HTML报告:', 'yellow');
        log('  npx playwright show-report');
      } else {
        log(`❌ E2E测试失败，退出码: ${code}`, 'red');
      }
      process.exit(code);
    });

  } catch (error) {
    log(`❌ 运行测试时出错: ${error.message}`, 'red');
    process.exit(1);
  }
}

// 主函数
async function main() {
  log('🚀 Ginkgo WebUI E2E测试', 'blue');
  log('=====================================', 'blue');

  // 检查环境
  const webuiOk = await checkWebUI();
  if (!webuiOk) {
    process.exit(1);
  }

  const chromeOk = await checkRemoteChrome();
  if (!chromeOk) {
    log('⚠️  警告: 将使用本地浏览器实例', 'yellow');
    log('要使用远程Chrome实例，请先解决连接问题', 'yellow');
  }

  // 运行测试
  await runTests();
}

// 处理错误
process.on('unhandledRejection', (error) => {
  log(`❌ 未处理的Promise拒绝: ${error.message}`, 'red');
  process.exit(1);
});

process.on('SIGINT', () => {
  log('\n⚠️  测试被用户中断', 'yellow');
  process.exit(1);
});

// 启动
main().catch(error => {
  log(`❌ 主函数执行失败: ${error.message}`, 'red');
  process.exit(1);
});
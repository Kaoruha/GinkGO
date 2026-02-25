# E2E 测试

基于 Playwright Python SDK 的端到端测试。

## 安装依赖

```bash
# 安装 Playwright
pip install playwright pytest-playwright

# 安装浏览器 (如需本地运行)
playwright install chromium
```

## 配置

配置文件: `tests/e2e/config.py`

可通过环境变量覆盖:

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `E2E_REMOTE_BROWSER` | `http://192.168.50.10:9222` | 远程浏览器 CDP 地址 |
| `E2E_WEB_UI_URL` | `http://192.168.50.12:5173` | Web UI 地址 |
| `E2E_HEADLESS` | `false` | 无头模式 (本地浏览器时生效) |
| `E2E_TIMEOUT` | `30000` | 超时时间 (毫秒) |
| `E2E_SLOW_MO` | `0` | 慢动作延迟 (毫秒) |
| `E2E_SCREENSHOT_DIR` | `/tmp/e2e-screenshots` | 截图保存目录 |
| `E2E_TEST_USERNAME` | `admin` | 测试用户名 |
| `E2E_TEST_PASSWORD` | `admin123` | 测试密码 |

## 运行测试

```bash
# 运行所有 E2E 测试
pytest -c pytest.e2e.ini

# 运行单个测试文件
pytest -c pytest.e2e.ini tests/e2e/test_login.py

# 运行单个测试方法
pytest -c pytest.e2e.ini tests/e2e/test_login.py::TestLogin::test_login_success

# 使用自定义配置
E2E_WEB_UI_URL=http://localhost:5173 pytest -c pytest.e2e.ini

# 显示详细输出
pytest -c pytest.e2e.ini -v -s

# 并行运行 (需要安装 pytest-xdist)
pytest -c pytest.e2e.ini -n 2
```

## 测试结构

```
tests/e2e/
├── __init__.py          # 包初始化
├── config.py            # 配置文件
├── conftest.py          # Pytest fixtures
├── test_login.py        # 登录测试
├── test_portfolio.py    # Portfolio CRUD 测试
├── test_backtest.py     # Backtest CRUD 测试
└── README.md            # 本文档
```

## 编写测试

### 基本测试

```python
import pytest
from playwright.sync_api import Page, expect
from tests.e2e.config import config


@pytest.mark.e2e
class TestMyFeature:
    def test_something(self, page: Page):
        page.goto(f"{config.web_ui_url}/some-page")
        expect(page.locator("h1")).to_be_visible()
```

### 需要登录的测试

```python
@pytest.mark.e2e
class TestProtectedFeature:
    def test_authenticated(self, authenticated_page: Page):
        # authenticated_page 已经完成登录
        authenticated_page.goto(f"{config.web_ui_url}/dashboard")
        expect(authenticated_page.locator(".user-info")).to_be_visible()
```

### 失败截图

测试失败时会自动截图保存到 `E2E_SCREENSHOT_DIR`。

## 远程浏览器配置

确保远程 Chrome 启用了调试端口:

```bash
# Linux
google-chrome --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
chrome.exe --remote-debugging-port=9222
```

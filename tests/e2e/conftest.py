"""
E2E 测试 Pytest 配置

提供共享的 fixtures 和 hooks。
"""

import pytest
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from .config import config


@pytest.fixture(scope="session")
def browser():
    """
    浏览器 fixture (session 级别)

    只连接远程浏览器，不启动本地浏览器。
    """
    with sync_playwright() as p:
        print(f"\n🔗 连接远程浏览器: {config.remote_browser}")
        browser = p.chromium.connect_over_cdp(config.remote_browser)
        print(f"✅ 已连接远程浏览器: {browser.version}")
        yield browser
        # 不关闭浏览器，因为它是远程的


@pytest.fixture
def page(browser: Browser):
    """
    页面 fixture

    优先使用远程浏览器的现有页面，没有则创建新标签页。
    测试结束后不关闭页面，方便调试。
    """
    # 获取现有上下文
    contexts = browser.contexts
    if contexts:
        context = contexts[0]
        # 获取现有页面
        pages = context.pages
        if pages:
            page = pages[0]
            print(f"📱 使用现有页面: {page.url[:50]}...")
        else:
            page = context.new_page()
            print("📱 创建新标签页")
    else:
        # 没有上下文，创建新的
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = context.new_page()
        print("📱 创建新上下文和页面")

    page.set_default_timeout(config.timeout)
    yield page
    # 不关闭页面，保留给用户查看


@pytest.fixture
def authenticated_page(page: Page):
    """
    已认证的页面 fixture

    检查是否已登录，未登录则自动完成登录流程。
    """
    # 检查是否已在登录页或 localStorage 无 token
    current_url = page.url

    # 如果不在登录页且有 token，说明已登录
    has_token = page.evaluate("localStorage.getItem('access_token')")
    is_logged_in = has_token and "/login" not in current_url

    if is_logged_in:
        print("✅ 已登录，跳过登录流程")
    else:
        # 清除认证状态并重新登录
        page.goto(f"{config.web_ui_url}/login")
        page.evaluate("localStorage.clear(); sessionStorage.clear();")

        # 执行登录
        page.fill('input[placeholder="enter username"]', config.test_username)
        page.fill('input[placeholder="enter password"]', config.test_password)
        page.click('button:has-text("EXECUTE")')

        # 等待跳转
        page.wait_for_url("**/dashboard", timeout=10000)

    yield page


@pytest.fixture
def screenshot_dir() -> Path:
    """截图目录 fixture"""
    dir_path = Path(config.screenshot_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def pytest_configure(config):
    """Pytest 配置钩子"""
    # 添加自定义标记
    config.addinivalue_line("markers", "e2e: E2E 测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "login: 需要登录的测试")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    for item in items:
        # 为 e2e 目录下的测试添加标记
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试失败时截图"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # 获取 page fixture
        page = item.funcargs.get("page") or item.funcargs.get("authenticated_page")
        if page:
            screenshot_dir = Path(config.screenshot_dir)
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            # 生成截图文件名
            test_name = item.name.replace("/", "_").replace("::", "_")
            screenshot_path = screenshot_dir / f"{test_name}_failed.png"

            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"\n📸 失败截图已保存: {screenshot_path}")
            except Exception as e:
                print(f"\n⚠️ 截图失败: {e}")

"""
E2E 测试配置和固定装置

核心原则：页面有错误 = 测试立即失败
每步操作都有明确的断言验证
"""

import os
import pytest
from playwright.sync_api import Page, Browser, BrowserContext, expect
from typing import Generator, Dict, List, Optional

# ========== 环境配置 ==========

REMOTE_BROWSER = os.getenv("REMOTE_BROWSER", "http://192.168.50.10:9222")
WEB_UI_URL = os.getenv("WEB_UI_URL", "http://192.168.50.12:5173")
BACKTEST_PATH = "/stage1/backtest"

# ========== 页面健康检查 ==========


class PageHealth:
    """页面健康状态"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.has_console_errors: bool = False
        self.has_page_errors: bool = False
        self.has_network_errors: bool = False


def collect_page_errors(page: Page, health: PageHealth) -> None:
    """
    收集页面错误

    Args:
        page: Playwright 页面对象
        health: 页面健康状态对象
    """

    def handle_console(msg):
        """处理控制台消息"""
        if msg.type == "error":
            health.errors.append(f"[CONSOLE ERROR] {msg.text}")
            health.has_console_errors = True
            print(f"❌ Console Error: {msg.text}")
        elif msg.type == "warning":
            health.warnings.append(f"[CONSOLE WARN] {msg.text}")
            print(f"⚠️  Console Warning: {msg.text}")

    def handle_page_error(error):
        """处理页面错误"""
        health.errors.append(f"[PAGE ERROR] {error}")
        health.has_page_errors = True
        print(f"❌ Page Error: {error}")

    def handle_request_failed(request):
        """处理网络请求失败"""
        failure = request.failure
        url = request.url

        # 忽略一些可接受的失败（如字体、图片等）
        skippable_patterns = [
            "/fonts/",
            "/images/",
            ".woff",
            ".woff2",
            ".ttf",
            ".svg",
            "favicon",
            "analytics",
        ]

        is_skippable = any(pattern in url for pattern in skippable_patterns)

        if not is_skippable:
            error_text = failure or "Unknown"
            health.errors.append(f"[NETWORK ERROR] {url} - {error_text}")
            health.has_network_errors = True
            print(f"❌ Network Error: {url} - {error_text}")

    # 注册事件监听器
    page.on("console", handle_console)
    page.on("pageerror", handle_page_error)
    page.on("requestfailed", handle_request_failed)


def assert_page_healthy(
    page: Page,
    health: PageHealth,
    *,
    skip_network_check: bool = False,
    timeout: int = 5000,
) -> PageHealth:
    """
    验证页面健康状态

    ⚠️ 如果页面有任何错误，此函数会抛出异常，导致测试立即失败

    Args:
        page: Playwright 页面对象
        health: 页面健康状态对象
        skip_network_check: 是否跳过网络检查
        timeout: 超时时间（毫秒）

    Returns:
        PageHealth: 页面健康状态对象

    Raises:
        AssertionError: 页面不健康时抛出异常
    """
    # 等待页面稳定，让错误有时间浮现
    page.wait_for_timeout(timeout)

    # ========== 检查 1: 页面标题不能是错误标题 ==========
    title = page.title()
    url = page.url

    error_keywords = ["404", "500", "Error", "NotFound", "Internal Server Error"]
    for keyword in error_keywords:
        assert keyword not in title, (
            f"❌ 页面加载失败！\n"
            f"   标题: \"{title}\"\n"
            f"   URL: \"{url}\"\n"
            f"   原因: 包含错误关键词 '{keyword}'"
        )

    # ========== 检查 2: 不能有任何 JavaScript 错误 ==========
    assert not (health.has_console_errors or health.has_page_errors), (
        f"❌ 页面有 JavaScript 错误！\n"
        f"   发现 {len(health.errors)} 个错误\n"
        f"   错误列表:\n    " + "\n    ".join(health.errors[:10])
    )

    # ========== 检查 3: 不能有关键网络错误 ==========
    if not skip_network_check and health.has_network_errors:
        network_errors = [e for e in health.errors if "[NETWORK ERROR]" in e]
        assert False, (
            f"❌ 页面有关键网络请求失败！\n"
            f"   失败的请求:\n    " + "\n    ".join(network_errors[:5])
        )

    # ========== 检查 4: 基础页面结构必须存在 ==========
    body_text = page.locator("body").text_content()

    error_messages = [
        "Internal Server Error",
        "This page could not be found",
        "Application error",
    ]

    for msg in error_messages:
        assert msg not in (body_text or ""), (
            f"❌ 页面显示错误信息！\n"
            f"   Body内容: {(body_text or '')[:200]}..."
        )

    # ========== 健康检查通过 ==========
    print("✅ 页面健康检查通过")
    if health.warnings:
        print(f"   ⚠️  有 {len(health.warnings)} 个警告（不影响测试）")

    return health


# ========== Pytest 固定装置 ==========


@pytest.fixture(scope="function")
def browser() -> Generator[Browser, None, None]:
    """
    创建远程浏览器实例

    Yields:
        Browser: Playwright 浏览器对象
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser: Browser) -> Generator[Page, None, None]:
    """
    创建页面实例，自动进行健康检查

    Yields:
        Page: Playwright 页面对象
    """
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()

    yield page

    # 清理：关闭所有页面（除了第一个）
    for p in context.pages[1:]:
        p.close()


@pytest.fixture(scope="function")
def healthy_page(page: Page) -> Generator[Page, None, None]:
    """
    创建健康页面实例，自动导航到回测列表并进行健康检查

    Yields:
        Page: 已验证健康的 Playwright 页面对象
    """
    health = PageHealth()
    collect_page_errors(page, health)

    # 导航到回测列表页
    page.goto(f"{WEB_UI_URL}{BACKTEST_PATH}", wait_until="domcontentloaded")

    # 执行健康检查
    assert_page_healthy(page, health)

    yield page


# ========== 测试辅助函数 ==========


def get_healthy_page(browser: Browser, url: str) -> tuple[Browser, Page]:
    """
    获取远程浏览器页面，并自动设置错误监听

    ⚠️ 此函数返回的 page 会自动监听错误
    如果页面有错误，后续的 assert_page_healthy() 会抛出异常

    Args:
        browser: Playwright 浏览器对象
        url: 目标 URL

    Returns:
        tuple[Browser, Page]: 浏览器和页面对象
    """
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()

    # 导航到目标 URL
    page.goto(url, wait_until="domcontentloaded", timeout=15000)

    # 创建健康状态对象并收集错误
    health = PageHealth()
    collect_page_errors(page, health)

    # 立即执行健康检查
    assert_page_healthy(page, health)

    return browser, page

"""
回测任务操作 E2E 测试

覆盖：
- 任务状态显示
- 页面健康检查
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


def _goto_list(page: Page):
    page.goto(f"{config.web_ui_url}/backtest")
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
class TestBacktestTaskStatus:
    """任务状态显示"""

    def test_status_tags_in_table(self, authenticated_page: Page):
        """表格中显示状态标签"""
        _goto_list(authenticated_page)
        authenticated_page.wait_for_timeout(1000)

        rows = authenticated_page.locator("[data-testid='backtest-table'] tbody tr")
        expect(rows.first).to_be_visible()

        tags = rows.first.locator(".tag, .status-tag, .badge")
        assert tags.count() >= 1


@pytest.mark.e2e
class TestBacktestPageHealth:
    """页面健康检查"""

    def test_no_console_errors(self, authenticated_page: Page):
        """页面无严重控制台错误"""
        errors = []

        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)

        authenticated_page.on("console", handle_console)
        _goto_list(authenticated_page)
        authenticated_page.wait_for_timeout(2000)

        real_errors = [e for e in errors if "favicon" not in e.lower() and "404" not in e]
        assert len(real_errors) == 0, f"控制台错误: {real_errors[:3]}"

    def test_page_navigates_back_and_forth(self, authenticated_page: Page):
        """页面来回导航不报错"""
        _goto_list(authenticated_page)
        rows = authenticated_page.locator("[data-testid='backtest-table'] tbody tr")
        expect(rows.first).to_be_visible()

        rows.first.click()
        authenticated_page.wait_for_url("**/backtest/*", timeout=5000)

        authenticated_page.goto(f"{config.web_ui_url}/backtest")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/backtest" in authenticated_page.url

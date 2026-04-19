"""
系统状态 E2E 测试

测试系统相关页面：
- 系统状态
- 基础设施
- Worker 列表
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import CARD, STAT_CARD, TABLE, SWITCH


@pytest.mark.e2e
class TestSystemStatus:
    """系统状态测试"""

    def test_system_status_loads(self, authenticated_page: Page):
        """系统状态页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/system/status" in page.url

    def test_system_overview(self, authenticated_page: Page):
        """系统概览统计卡片可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator(STAT_CARD).first).to_be_visible()

    def test_infrastructure_status(self, authenticated_page: Page):
        """基础设施状态可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        infra = page.locator(f"{CARD}, .infra-grid, .infra-card").first
        expect(infra).to_be_visible()

    def test_worker_list(self, authenticated_page: Page):
        """Worker 区域可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        worker_section = page.locator(f"{CARD}:has-text('Worker'), {CARD}:has-text('组件')").first
        expect(worker_section).to_be_visible()

    def test_auto_refresh_toggle(self, authenticated_page: Page):
        """自动刷新开关可见且可点击"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        toggle = page.locator(f"{SWITCH}, button:has-text('自动刷新')").first
        expect(toggle).to_be_visible()
        toggle.click()
        page.wait_for_timeout(500)

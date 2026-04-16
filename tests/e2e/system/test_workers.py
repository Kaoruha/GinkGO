"""
Worker 管理与告警 E2E 测试

测试：
- Worker 管理页面加载
- 告警中心页面加载
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


@pytest.mark.e2e
class TestWorkerManagement:
    """Worker 管理测试"""

    def test_worker_management_loads(self, authenticated_page: Page):
        """Worker 管理页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/workers")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ Worker 管理页面加载成功")


@pytest.mark.e2e
class TestAlertCenter:
    """告警中心测试"""

    def test_alert_center_loads(self, authenticated_page: Page):
        """告警中心页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/alerts")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 告警中心页面加载成功")

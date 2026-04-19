"""
Walk-Forward 与蒙特卡洛 E2E 测试

测试：
- Walk-Forward 验证页面
- 蒙特卡洛模拟页面
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


@pytest.mark.e2e
class TestWalkForward:
    """Walk-Forward 验证测试"""

    def test_walkforward_page_loads(self, authenticated_page: Page):
        """Walk-Forward 页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/walkforward")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/validation/walkforward" in page.url

    def test_walkforward_form(self, authenticated_page: Page):
        """Walk-Forward 表单可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/walkforward")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("select, input").first).to_be_visible()


@pytest.mark.e2e
class TestMonteCarlo:
    """蒙特卡洛模拟测试"""

    def test_montecarlo_page_loads(self, authenticated_page: Page):
        """蒙特卡洛页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/montecarlo")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/validation/montecarlo" in page.url

    def test_montecarlo_form(self, authenticated_page: Page):
        """蒙特卡洛表单可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/montecarlo")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("input, select").first).to_be_visible()

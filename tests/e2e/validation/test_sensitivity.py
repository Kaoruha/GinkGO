"""
敏感性分析 E2E 测试

测试：
- 敏感性分析页面加载
- 敏感性分析表单元素
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


@pytest.mark.e2e
class TestSensitivity:
    """敏感性分析测试"""

    def test_sensitivity_page_loads(self, authenticated_page: Page):
        """敏感性分析页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/sensitivity")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/validation/sensitivity" in page.url

    def test_sensitivity_form(self, authenticated_page: Page):
        """敏感性分析表单存在"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/validation/sensitivity")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("select.form-select").first).to_be_visible()
        expect(page.locator("input.form-input[type='text']").first).to_be_visible()

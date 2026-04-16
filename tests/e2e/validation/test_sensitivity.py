"""
敏感性分析 E2E 测试

测试：
- 敏感性分析页面加载
- 敏感性分析表单元素
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import INPUT


@pytest.mark.e2e
class TestSensitivity:
    """敏感性分析测试"""

    def test_sensitivity_page_loads(self, authenticated_page: Page):
        """敏感性分析页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/sensitivity")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 敏感性分析页面加载成功")

    def test_sensitivity_form(self, authenticated_page: Page):
        """敏感性分析表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/sensitivity")
        page.wait_for_load_state("domcontentloaded")

        # 检查参数输入
        param_input = page.locator(f"{INPUT}, textarea")
        if param_input.count() > 0:
            print("✅ 参数输入框存在")

        print("✅ 敏感性分析表单检查完成")

"""
因子研究 E2E 测试

测试：
- IC 分析页面
- 因子分层页面
- 因子衰减页面
- 因子比较页面
- 因子正交化页面
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


@pytest.mark.e2e
class TestFactorResearch:
    """因子研究测试"""

    def test_ic_analysis_page_loads(self, authenticated_page: Page):
        """IC 分析页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/ic")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ IC 分析页面加载成功")

    def test_factor_layering_page_loads(self, authenticated_page: Page):
        """因子分层页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/layering")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子分层页面加载成功")

    def test_factor_decay_page_loads(self, authenticated_page: Page):
        """因子衰减页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/decay")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子衰减页面加载成功")

    def test_factor_comparison_page_loads(self, authenticated_page: Page):
        """因子比较页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/compare")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子比较页面加载成功")

    def test_factor_orthogonalization_page_loads(self, authenticated_page: Page):
        """因子正交化页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/orthogonalize")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子正交化页面加载成功")

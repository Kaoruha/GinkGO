"""
参数优化 E2E 测试

测试：
- 网格搜索页面
- 遗传算法页面
- 贝叶斯优化页面
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config


@pytest.mark.e2e
class TestOptimization:
    """参数优化测试"""

    def test_grid_search_page_loads(self, authenticated_page: Page):
        """网格搜索页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/grid")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 网格搜索页面加载成功")

    def test_genetic_optimizer_page_loads(self, authenticated_page: Page):
        """遗传算法页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/genetic")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 遗传算法页面加载成功")

    def test_bayesian_optimizer_page_loads(self, authenticated_page: Page):
        """贝叶斯优化页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/bayesian")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 贝叶斯优化页面加载成功")

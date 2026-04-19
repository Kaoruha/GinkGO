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

    @pytest.mark.parametrize("path", [
        "/optimization/grid",
        "/optimization/genetic",
        "/optimization/bayesian",
    ], ids=["网格搜索", "遗传算法", "贝叶斯优化"])
    def test_page_loads(self, authenticated_page: Page, path):
        """优化页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}{path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert path in page.url

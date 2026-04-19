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

    @pytest.mark.parametrize("path", [
        "/research/ic",
        "/research/layering",
        "/research/decay",
        "/research/comparison",
        "/research/orthogonal",
    ], ids=["IC分析", "分层", "衰减", "比较", "正交化"])
    def test_page_loads(self, authenticated_page: Page, path):
        """因子研究页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}{path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert path in page.url

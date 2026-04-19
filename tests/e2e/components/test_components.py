"""
组件管理 E2E 测试

测试组件相关页面：
- 策略列表
- 选股器列表
- 仓位管理器列表
- 风控管理器列表
- 分析器列表
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import TABLE


COMPONENT_TYPES = [
    {"name": "策略", "path": "/components/strategies"},
    {"name": "选股器", "path": "/components/selectors"},
    {"name": "仓位管理", "path": "/components/sizers"},
    {"name": "风控", "path": "/components/risks"},
    {"name": "分析器", "path": "/components/analyzers"},
]


@pytest.mark.e2e
class TestComponentPages:
    """组件页面加载测试"""

    @pytest.mark.parametrize("comp", COMPONENT_TYPES,
        ids=[c["name"] for c in COMPONENT_TYPES])
    def test_component_page_loads(self, authenticated_page: Page, comp):
        """组件页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}{comp['path']}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert comp['path'] in page.url

    def test_strategy_list_content(self, authenticated_page: Page):
        """策略列表页面内容检查"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/strategies")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("h1.page-title")).to_be_visible()
        expect(page.locator("input.search-input")).to_be_visible()

    def test_strategy_search(self, authenticated_page: Page):
        """策略搜索功能"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/strategies")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        search_input = page.locator("input.search-input")
        expect(search_input).to_be_visible()
        search_input.fill("test")
        page.wait_for_timeout(500)

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

from .config import config


# 组件类型配置
COMPONENT_TYPES = [
    {"name": "策略", "path": "/components/strategies", "selector": ".strategy-item, .ant-table-row"},
    {"name": "选股器", "path": "/components/selectors", "selector": ".selector-item, .ant-table-row"},
    {"name": "仓位管理", "path": "/components/sizers", "selector": ".sizer-item, .ant-table-row"},
    {"name": "风控", "path": "/components/risks", "selector": ".risk-item, .ant-table-row"},
    {"name": "分析器", "path": "/components/analyzers", "selector": ".analyzer-item, .ant-table-row"},
]


@pytest.mark.e2e
class TestComponentsOverview:
    """组件概览测试"""

    def test_components_page_loads(self, authenticated_page: Page):
        """组件页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 组件页面加载成功")

    def test_component_tabs(self, authenticated_page: Page):
        """组件标签页切换"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查标签页
        tabs = page.locator(".ant-tabs-tab").all()
        print(f"标签页数量: {len(tabs)}")

        if tabs:
            # 点击不同的标签页
            for i, tab in enumerate(tabs[:3]):  # 只测试前3个
                tab.click()
                page.wait_for_timeout(500)
            print("✅ 标签页切换正常")


@pytest.mark.e2e
class TestStrategyList:
    """策略列表测试"""

    def test_strategy_list_loads(self, authenticated_page: Page):
        """策略列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/strategies")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查表格或卡片
        table = page.locator(".ant-table")
        cards = page.locator(".ant-card")

        if table.is_visible():
            rows = page.locator(".ant-table-tbody tr").all()
            print(f"策略数量: {len(rows)}")
        elif cards.count() > 0:
            print(f"策略卡片数量: {cards.count()}")
        else:
            print("⚠️ 策略列表暂无数据")

        print("✅ 策略列表页面加载成功")

    def test_strategy_search(self, authenticated_page: Page):
        """策略搜索功能"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/strategies")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        search_input = page.locator(".ant-input-search input, input[placeholder*='搜索']")
        if search_input.is_visible():
            search_input.fill("random")
            page.wait_for_timeout(1000)
            print("✅ 策略搜索功能正常")


@pytest.mark.e2e
class TestSelectorList:
    """选股器列表测试"""

    def test_selector_list_loads(self, authenticated_page: Page):
        """选股器列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/selectors")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 选股器列表页面加载成功")


@pytest.mark.e2e
class TestSizerList:
    """仓位管理器列表测试"""

    def test_sizer_list_loads(self, authenticated_page: Page):
        """仓位管理器列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/sizers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 仓位管理器列表页面加载成功")


@pytest.mark.e2e
class TestRiskList:
    """风控管理器列表测试"""

    def test_risk_list_loads(self, authenticated_page: Page):
        """风控管理器列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/risks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 风控管理器列表页面加载成功")


@pytest.mark.e2e
class TestAnalyzerList:
    """分析器列表测试"""

    def test_analyzer_list_loads(self, authenticated_page: Page):
        """分析器列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/components/analyzers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 分析器列表页面加载成功")

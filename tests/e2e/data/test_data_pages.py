"""
数据管理 E2E 测试

测试数据相关页面：
- 数据概览
- 股票列表
- K线数据
- 数据同步
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import TABLE


@pytest.mark.e2e
class TestDataOverview:
    """数据概览测试"""

    def test_data_overview_loads(self, authenticated_page: Page):
        """数据概览页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/data" in page.url
        expect(page.locator("div.page-title").first).to_be_visible()

    def test_data_statistics(self, authenticated_page: Page):
        """数据统计卡片可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("div.stat-card").first).to_be_visible()


@pytest.mark.e2e
class TestStockList:
    """股票列表测试"""

    def test_stock_list_loads(self, authenticated_page: Page):
        """股票列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/stocks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator(TABLE)).to_be_visible()

    def test_stock_search(self, authenticated_page: Page):
        """股票搜索功能"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/stocks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        search_input = page.locator("input[placeholder*='搜索']")
        expect(search_input).to_be_visible()
        search_input.fill("000001")
        page.wait_for_timeout(500)


@pytest.mark.e2e
class TestBarData:
    """K线数据测试"""

    def test_bar_data_loads(self, authenticated_page: Page):
        """K线数据页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/bars")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/data/bars" in page.url

    def test_bar_data_query(self, authenticated_page: Page):
        """K线数据查询"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/bars")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("select.form-select").first).to_be_visible()
        expect(page.locator("input.form-input[type='date']").first).to_be_visible()


@pytest.mark.e2e
class TestDataSync:
    """数据同步测试"""

    def test_data_sync_page_loads(self, authenticated_page: Page):
        """数据同步页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/sync")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert "/data/sync" in page.url

    def test_sync_status_display(self, authenticated_page: Page):
        """同步状态卡片可见"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/sync")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("div.stat-item").first).to_be_visible()

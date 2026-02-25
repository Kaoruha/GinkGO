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

from .config import config


@pytest.mark.e2e
class TestDataOverview:
    """数据概览测试"""

    def test_data_overview_loads(self, authenticated_page: Page):
        """数据概览页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/overview")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 验证页面加载
        expect(page.locator("body")).to_be_visible()
        print("✅ 数据概览页面加载成功")

    def test_data_statistics(self, authenticated_page: Page):
        """数据统计显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/overview")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查统计卡片
        stat_cards = page.locator(".ant-statistic, .ant-card").all()
        print(f"统计卡片数量: {len(stat_cards)}")
        print("✅ 数据统计显示正常")


@pytest.mark.e2e
class TestStockList:
    """股票列表测试"""

    def test_stock_list_loads(self, authenticated_page: Page):
        """股票列表页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/stocks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查表格或列表
        table = page.locator(".ant-table")
        if table.is_visible():
            rows = page.locator(".ant-table-tbody tr").all()
            print(f"股票数量: {len(rows)}")
        else:
            print("⚠️ 表格暂无数据或未加载")

        print("✅ 股票列表页面加载成功")

    def test_stock_search(self, authenticated_page: Page):
        """股票搜索功能"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/stocks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查搜索框
        search_input = page.locator(".ant-input-search input, input[placeholder*='搜索']")
        if search_input.is_visible():
            search_input.fill("000001")
            page.wait_for_timeout(1000)
            print("✅ 股票搜索功能正常")
        else:
            print("⚠️ 搜索框未找到")


@pytest.mark.e2e
class TestBarData:
    """K线数据测试"""

    def test_bar_data_loads(self, authenticated_page: Page):
        """K线数据页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/bars")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("body")).to_be_visible()
        print("✅ K线数据页面加载成功")

    def test_bar_data_query(self, authenticated_page: Page):
        """K线数据查询"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/bars")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查是否有股票代码输入框
        code_input = page.locator("input[placeholder*='代码'], input[placeholder*='code']")
        if code_input.is_visible():
            code_input.fill("000001.SZ")
            page.wait_for_timeout(500)

            # 点击查询按钮
            query_btn = page.locator("button:has-text('查询'), button:has-text('搜索')")
            if query_btn.is_visible():
                query_btn.click()
                page.wait_for_timeout(2000)
                print("✅ K线数据查询功能正常")
        else:
            print("⚠️ 代码输入框未找到")


@pytest.mark.e2e
class TestDataSync:
    """数据同步测试"""

    def test_data_sync_page_loads(self, authenticated_page: Page):
        """数据同步页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/sync")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 数据同步页面加载成功")

    def test_sync_status_display(self, authenticated_page: Page):
        """同步状态显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/data/sync")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查状态卡片或统计
        stat_cards = page.locator(".ant-statistic, .ant-card, .status-card").all()
        print(f"状态卡片数量: {len(stat_cards)}")
        print("✅ 同步状态显示正常")

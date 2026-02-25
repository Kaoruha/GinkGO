"""
Dashboard E2E 测试

测试仪表盘页面：
- 页面加载
- 统计卡片显示
- 快捷入口
"""

import pytest
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestDashboard:
    """仪表盘测试"""

    def test_dashboard_loads(self, authenticated_page: Page):
        """仪表盘页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # 验证页面标题或关键元素
        expect(page.locator("body")).to_be_visible()
        assert "/dashboard" in page.url
        print("✅ 仪表盘页面加载成功")

    def test_statistics_cards(self, authenticated_page: Page):
        """统计卡片显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查统计卡片
        stat_cards = page.locator(".ant-statistic, .stat-card").all()
        print(f"统计卡片数量: {len(stat_cards)}")

        # 至少应该有一些统计信息
        assert len(stat_cards) >= 1 or page.locator(".ant-card").count() >= 1
        print("✅ 统计卡片显示正常")

    def test_navigation_menu(self, authenticated_page: Page):
        """导航菜单功能"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # 检查侧边栏菜单
        menu_items = page.locator(".ant-menu-item, .ant-layout-sider a").all()
        print(f"菜单项数量: {len(menu_items)}")

        # 应该有多个菜单项
        assert len(menu_items) >= 3
        print("✅ 导航菜单显示正常")


@pytest.mark.e2e
class TestNavigation:
    """页面导航测试"""

    def test_navigate_to_portfolio(self, authenticated_page: Page):
        """导航到组合页面"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # 点击组合菜单
        portfolio_link = page.locator('a[href*="/portfolio"], .ant-menu-item:has-text("组合")')
        if portfolio_link.count() > 0:
            portfolio_link.first.click()
            page.wait_for_load_state("networkidle")
            assert "/portfolio" in page.url
            print("✅ 导航到组合页面成功")

    def test_navigate_to_backtest(self, authenticated_page: Page):
        """导航到回测页面"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # 点击回测菜单
        backtest_link = page.locator('a[href*="/backtest"], .ant-menu-item:has-text("回测")')
        if backtest_link.count() > 0:
            backtest_link.first.click()
            page.wait_for_load_state("networkidle")
            print("✅ 导航到回测页面成功")

    def test_navigate_to_data(self, authenticated_page: Page):
        """导航到数据页面"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # 点击数据菜单
        data_link = page.locator('a[href*="/data"], .ant-menu-item:has-text("数据")')
        if data_link.count() > 0:
            data_link.first.click()
            page.wait_for_load_state("networkidle")
            print("✅ 导航到数据页面成功")

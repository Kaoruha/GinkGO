"""
侧边栏导航 E2E 测试

覆盖：
- 侧边栏菜单可见
- 一级菜单导航（概览、组合）
- 子菜单展开和导航（回测、数据）
- 折叠/展开侧边栏
"""

import re

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "nav_dashboard": "[data-testid='nav-dashboard']",
    "nav_portfolio": "[data-testid='nav-portfolio']",
    "nav_backtest": "[data-testid='nav-backtest']",
    "nav_backtest_list": "[data-testid='nav-backtest-list']",
    "nav_data": "[data-testid='nav-data']",
    "nav_data_stocks": "[data-testid='nav-data-stocks']",
    "nav_system": "[data-testid='nav-system']",
    "nav_system_status": "[data-testid='nav-system-status']",
}


def _goto_dashboard(page: Page):
    page.goto(f"{config.web_ui_url}/dashboard")
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
class TestSidebarMenu:
    """侧边栏菜单渲染"""

    def test_sidebar_visible(self, authenticated_page: Page):
        """侧边栏可见"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(".sider")).to_be_visible()

    def test_primary_menu_items_visible(self, authenticated_page: Page):
        """主要一级菜单项可见"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["nav_dashboard"])).to_be_visible()
        expect(authenticated_page.locator(SEL["nav_portfolio"])).to_be_visible()


@pytest.mark.e2e
class TestPrimaryNavigation:
    """一级菜单导航"""

    def test_navigate_to_dashboard(self, authenticated_page: Page):
        """点击概览导航到 dashboard"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_dashboard"])
        authenticated_page.wait_for_load_state("networkidle")
        assert "/dashboard" in authenticated_page.url

    def test_navigate_to_portfolio(self, authenticated_page: Page):
        """点击组合导航到 portfolio"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_portfolio"])
        authenticated_page.wait_for_url("**/portfolio**", timeout=5000)
        assert "/portfolio" in authenticated_page.url


@pytest.mark.e2e
class TestSubMenuNavigation:
    """子菜单展开和导航"""

    def test_expand_backtest_submenu(self, authenticated_page: Page):
        """展开回测子菜单"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_backtest"])
        expect(authenticated_page.locator(SEL["nav_backtest_list"])).to_be_visible()

    def test_navigate_to_backtest_list(self, authenticated_page: Page):
        """导航到回测列表"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_backtest"])
        authenticated_page.click(SEL["nav_backtest_list"])
        authenticated_page.wait_for_url("**/backtest**", timeout=5000)
        assert "/backtest" in authenticated_page.url

    def test_expand_data_submenu(self, authenticated_page: Page):
        """展开数据管理子菜单"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_data"])
        expect(authenticated_page.locator(SEL["nav_data_stocks"])).to_be_visible()

    def test_navigate_to_data_stocks(self, authenticated_page: Page):
        """导航到股票信息页"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_data"])
        authenticated_page.click(SEL["nav_data_stocks"])
        authenticated_page.wait_for_url("**/data/stocks**", timeout=5000)
        assert "/data/stocks" in authenticated_page.url


@pytest.mark.e2e
class TestSidebarCollapse:
    """侧边栏折叠/展开"""

    def test_collapse_and_expand(self, authenticated_page: Page):
        """点击折叠按钮后侧边栏折叠，再点击展开"""
        _goto_dashboard(authenticated_page)

        sider = authenticated_page.locator(".sider")
        trigger = authenticated_page.locator(".trigger")

        # 折叠
        expect(trigger).to_be_visible()
        trigger.click()
        expect(sider).to_have_class(re.compile(r"collapsed"))

        # 展开
        trigger.click()
        expect(sider).not_to_have_class(re.compile(r"collapsed"))

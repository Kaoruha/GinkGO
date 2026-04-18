"""
侧边栏导航 E2E 测试

覆盖：
- 6 个扁平菜单项可见
- 点击导航到对应页面
- 旧路由重定向
- 折叠/展开侧边栏
"""

import re

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "nav_dashboard": "[data-testid='nav-dashboard']",
    "nav_portfolios": "[data-testid='nav-portfolios']",
    "nav_research": "[data-testid='nav-research']",
    "nav_trading": "[data-testid='nav-trading']",
    "nav_data": "[data-testid='nav-data']",
    "nav_admin": "[data-testid='nav-admin']",
}


def _goto_dashboard(page: Page):
    page.goto(f"{config.web_ui_url}/dashboard")
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
class TestSidebarMenu:
    """侧边栏菜单渲染"""

    def test_sidebar_visible(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(".sider")).to_be_visible()

    def test_all_menu_items_visible(self, authenticated_page: Page):
        """6 个菜单项全部可见"""
        _goto_dashboard(authenticated_page)
        for key in SEL:
            expect(authenticated_page.locator(SEL[key])).to_be_visible()


@pytest.mark.e2e
class TestPrimaryNavigation:
    """扁平菜单导航"""

    def test_navigate_to_dashboard(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_dashboard"])
        authenticated_page.wait_for_load_state("networkidle")
        assert "/dashboard" in authenticated_page.url

    def test_navigate_to_portfolios(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_portfolios"])
        authenticated_page.wait_for_url("**/portfolios**", timeout=5000)
        assert "/portfolios" in authenticated_page.url

    def test_navigate_to_research(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_research"])
        authenticated_page.wait_for_url("**/research**", timeout=5000)
        assert "/research" in authenticated_page.url

    def test_navigate_to_trading(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_trading"])
        authenticated_page.wait_for_url("**/trading**", timeout=5000)
        assert "/trading" in authenticated_page.url

    def test_navigate_to_data(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_data"])
        authenticated_page.wait_for_url("**/data**", timeout=5000)
        assert "/data" in authenticated_page.url

    def test_navigate_to_admin(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_admin"])
        authenticated_page.wait_for_url("**/admin**", timeout=5000)
        assert "/admin" in authenticated_page.url


@pytest.mark.e2e
class TestLegacyRedirects:
    """旧路由重定向"""

    def test_portfolio_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/portfolio")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/portfolios" in authenticated_page.url

    def test_backtest_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/backtest")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/portfolios" in authenticated_page.url

    def test_system_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/system/status")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/admin/system" in authenticated_page.url


@pytest.mark.e2e
class TestSidebarCollapse:
    """侧边栏折叠/展开"""

    def test_collapse_and_expand(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        sider = authenticated_page.locator(".sider")
        trigger = authenticated_page.locator(".trigger")
        expect(trigger).to_be_visible()
        trigger.click()
        expect(sider).to_have_class(re.compile(r"collapsed"))
        trigger.click()
        expect(sider).not_to_have_class(re.compile(r"collapsed"))

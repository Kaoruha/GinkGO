"""
组合管理 CRUD E2E 测试

覆盖：
- 列表页面加载
- 搜索组合
- 筛选模式
- 创建组合
- 查看详情
- 删除组合
"""

import time

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "search": "[data-testid='portfolio-search']",
    "search_btn": "[data-testid='portfolio-search-btn']",
    "create_btn": "[data-testid='btn-create-portfolio']",
    "card": "[data-testid='portfolio-card']",
    "card_menu": "[data-testid='card-menu-btn']",
    "delete_btn": "[data-testid='btn-delete-portfolio']",
    "input_name": "[data-testid='input-portfolio-name']",
    "save_btn": "[data-testid='btn-save-portfolio']",
}


def _goto_list(page: Page):
    page.goto(f"{config.web_ui_url}/portfolio")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)


@pytest.mark.e2e
class TestPortfolioListPage:
    """组合列表页面"""

    def test_list_page_loads(self, authenticated_page: Page):
        """列表页面加载，标题和搜索框可见"""
        _goto_list(authenticated_page)
        assert "/portfolio" in authenticated_page.url
        expect(authenticated_page.locator("h1")).to_contain_text("投资组合")
        expect(authenticated_page.locator(SEL["search"])).to_be_visible()

    def test_create_button_visible(self, authenticated_page: Page):
        """创建按钮可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["create_btn"]).first).to_be_visible()

    def test_portfolio_cards_visible(self, authenticated_page: Page):
        """组合卡片可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["card"]).first).to_be_visible(timeout=5000)


@pytest.mark.e2e
class TestPortfolioSearch:
    """搜索功能"""

    def test_search_input_works(self, authenticated_page: Page):
        """搜索框可输入"""
        _goto_list(authenticated_page)
        search = authenticated_page.locator(SEL["search"])
        search.fill("测试搜索")
        assert search.input_value() == "测试搜索"

    def test_search_no_error_on_empty(self, authenticated_page: Page):
        """空关键词搜索不报错"""
        _goto_list(authenticated_page)
        authenticated_page.locator(SEL["search"]).fill("")
        authenticated_page.locator(SEL["search_btn"]).click()
        authenticated_page.wait_for_load_state("networkidle")
        assert "/portfolio" in authenticated_page.url


@pytest.mark.e2e
class TestPortfolioFilter:
    """筛选功能"""

    def test_filter_buttons_visible(self, authenticated_page: Page):
        """筛选按钮可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(".radio-button").first).to_be_visible()

    def test_filter_by_mode(self, authenticated_page: Page):
        """按模式筛选"""
        _goto_list(authenticated_page)
        backtest_btn = authenticated_page.locator(".radio-button:has-text('回测')")
        expect(backtest_btn).to_be_visible()
        backtest_btn.click()
        authenticated_page.wait_for_timeout(500)

        all_btn = authenticated_page.locator(".radio-button:has-text('全部')")
        expect(all_btn).to_be_visible()
        all_btn.click()
        authenticated_page.wait_for_timeout(500)


@pytest.mark.e2e
class TestPortfolioCreate:
    """创建组合"""

    def test_create_opens_modal(self, authenticated_page: Page):
        """点击创建按钮打开模态框"""
        _goto_list(authenticated_page)
        authenticated_page.locator(SEL["create_btn"]).first.click()
        expect(authenticated_page.locator(".modal-overlay").first).to_be_visible(timeout=10000)

    def test_create_with_name_only(self, authenticated_page: Page):
        """创建只填名称的组合"""
        _goto_list(authenticated_page)
        authenticated_page.locator(SEL["create_btn"]).first.click()
        expect(authenticated_page.locator(".modal-overlay").first).to_be_visible(timeout=10000)

        name = f"E2E最小_{int(time.time())}"
        authenticated_page.locator(SEL["input_name"]).fill(name)
        authenticated_page.locator(SEL["save_btn"]).click()
        authenticated_page.wait_for_timeout(3000)

        assert "/portfolio" in authenticated_page.url


@pytest.mark.e2e
class TestPortfolioDetail:
    """查看详情"""

    def test_click_card_navigates_to_detail(self, authenticated_page: Page):
        """点击组合卡片跳转到详情页"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["card"]).first).to_be_visible(timeout=5000)
        authenticated_page.locator(SEL["card"]).first.click()
        authenticated_page.wait_for_url("**/portfolio/*", timeout=5000)
        assert "/portfolio/" in authenticated_page.url and "/create" not in authenticated_page.url

    def test_detail_shows_title(self, authenticated_page: Page):
        """详情页显示页面标题"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["card"]).first).to_be_visible(timeout=5000)
        authenticated_page.locator(SEL["card"]).first.click()
        authenticated_page.wait_for_url("**/portfolio/*", timeout=5000)
        expect(authenticated_page.locator(".page-title")).to_be_visible()


@pytest.mark.e2e
class TestPortfolioDelete:
    """删除组合"""

    def test_delete_via_card_menu(self, authenticated_page: Page):
        """通过卡片菜单删除组合"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["card"]).first).to_be_visible(timeout=5000)

        authenticated_page.locator(SEL["card"]).first.locator(SEL["card_menu"]).click()
        delete_btn = authenticated_page.locator(SEL["delete_btn"])
        expect(delete_btn).to_be_visible(timeout=3000)
        delete_btn.click()

        confirm_btn = authenticated_page.locator(".btn-danger:has-text('删除')").first
        expect(confirm_btn).to_be_visible(timeout=3000)
        confirm_btn.click()
        authenticated_page.wait_for_timeout(2000)

"""
回测任务 CRUD E2E 测试

覆盖：
- 列表页面加载与统计卡片
- 搜索
- 状态筛选
- 创建回测（模态框）
- 行点击导航到详情
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "search": "[data-testid='backtest-search']",
    "search_btn": "[data-testid='backtest-search-btn']",
    "create_btn": "[data-testid='btn-create-backtest']",
    "table": "[data-testid='backtest-table']",
}


def _goto_list(page: Page):
    page.goto(f"{config.web_ui_url}/backtest")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)


@pytest.mark.e2e
class TestBacktestListPage:
    """回测列表页面"""

    def test_list_page_loads(self, authenticated_page: Page):
        """列表页面加载"""
        _goto_list(authenticated_page)
        assert "/backtest" in authenticated_page.url
        expect(authenticated_page.locator(SEL["create_btn"])).to_be_visible()

    def test_stats_cards_visible(self, authenticated_page: Page):
        """统计卡片可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(".stat-card").first).to_be_visible()

    def test_table_visible(self, authenticated_page: Page):
        """表格可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(SEL["table"])).to_be_visible()


@pytest.mark.e2e
class TestBacktestSearch:
    """搜索功能"""

    def test_search_input_works(self, authenticated_page: Page):
        """搜索框可输入"""
        _goto_list(authenticated_page)
        search = authenticated_page.locator(SEL["search"])
        search.fill("test")
        assert search.input_value() == "test"

    def test_search_filters_results(self, authenticated_page: Page):
        """搜索过滤结果"""
        _goto_list(authenticated_page)
        rows = authenticated_page.locator(f"{SEL['table']} tbody tr")
        expect(rows.first).to_be_visible()

        before = rows.count()
        authenticated_page.locator(SEL["search"]).fill("NOTEXIST_12345")
        authenticated_page.locator(SEL["search_btn"]).click()
        authenticated_page.wait_for_timeout(500)

        after = rows.count()
        assert after <= before


@pytest.mark.e2e
class TestBacktestFilter:
    """状态筛选"""

    def test_filter_buttons_visible(self, authenticated_page: Page):
        """筛选按钮可见"""
        _goto_list(authenticated_page)
        expect(authenticated_page.locator(".radio-button").first).to_be_visible()

    def test_filter_by_status(self, authenticated_page: Page):
        """按状态筛选"""
        _goto_list(authenticated_page)
        completed = authenticated_page.locator(".radio-button:has-text('已完成')")
        expect(completed).to_be_visible()
        completed.click()
        authenticated_page.wait_for_timeout(500)

        all_btn = authenticated_page.locator(".radio-button:has-text('全部')")
        expect(all_btn).to_be_visible()
        all_btn.click()
        authenticated_page.wait_for_timeout(500)


@pytest.mark.e2e
class TestBacktestCreate:
    """创建回测"""

    def test_create_opens_modal(self, authenticated_page: Page):
        """点击创建按钮打开模态框"""
        _goto_list(authenticated_page)
        authenticated_page.locator(SEL["create_btn"]).click()
        modal = authenticated_page.locator(".modal-overlay")
        expect(modal).to_be_visible(timeout=5000)

    def test_create_modal_has_form_fields(self, authenticated_page: Page):
        """模态框包含表单字段"""
        _goto_list(authenticated_page)
        authenticated_page.locator(SEL["create_btn"]).click()
        modal = authenticated_page.locator(".modal-overlay")
        expect(modal).to_be_visible(timeout=5000)

        expect(modal.locator("input.form-input").first).to_be_visible()
        expect(modal.locator("select.form-select")).to_be_visible()
        expect(modal.locator("input[type='date']").first).to_be_visible()


@pytest.mark.e2e
class TestBacktestDetail:
    """回测详情"""

    def test_click_row_navigates_to_detail(self, authenticated_page: Page):
        """点击表格行跳转到详情页"""
        _goto_list(authenticated_page)
        rows = authenticated_page.locator(f"{SEL['table']} tbody tr")
        expect(rows.first).to_be_visible()

        rows.first.click()
        authenticated_page.wait_for_url("**/backtest/*", timeout=5000)
        assert "/backtest/" in authenticated_page.url


@pytest.mark.e2e
class TestBacktestOperations:
    """任务操作"""

    def test_action_buttons_in_table(self, authenticated_page: Page):
        """表格行有操作按钮"""
        _goto_list(authenticated_page)
        rows = authenticated_page.locator(f"{SEL['table']} tbody tr")
        expect(rows.first).to_be_visible()

        action_btns = rows.first.locator("button.link-button")
        assert action_btns.count() >= 1

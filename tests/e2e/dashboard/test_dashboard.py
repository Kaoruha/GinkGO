"""
仪表盘 E2E 测试

覆盖：
- 页面加载
- 统计卡片显示
- 4阶段概览卡片
- 阶段快捷入口导航
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "stats_grid": "[data-testid='stats-grid']",
    "stat_portfolio": "[data-testid='stat-portfolio']",
    "stat_backtest": "[data-testid='stat-backtest']",
    "stat_worker": "[data-testid='stat-worker']",
    "stat_system": "[data-testid='stat-system']",
    "stages_grid": "[data-testid='stages-grid']",
    "stage_backtest": "[data-testid='stage-backtest']",
    "stage_validation": "[data-testid='stage-validation']",
    "stage_paper": "[data-testid='stage-paper']",
    "stage_live": "[data-testid='stage-live']",
    "link_backtest": "[data-testid='stage-link-backtest']",
    "link_validation": "[data-testid='stage-link-validation']",
    "link_paper": "[data-testid='stage-link-paper']",
    "link_live": "[data-testid='stage-link-live']",
}


def _goto_dashboard(page: Page):
    page.goto(f"{config.web_ui_url}/dashboard")
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
class TestDashboardPage:
    """仪表盘页面加载"""

    def test_dashboard_loads(self, authenticated_page: Page):
        """仪表盘页面正常加载"""
        _goto_dashboard(authenticated_page)
        assert "/dashboard" in authenticated_page.url

    def test_page_title_visible(self, authenticated_page: Page):
        """页面标题 '概览' 可见"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(".page-title")).to_contain_text("概览")


@pytest.mark.e2e
class TestStatisticsCards:
    """统计卡片"""

    def test_stats_grid_visible(self, authenticated_page: Page):
        """统计卡片网格可见"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["stats_grid"])).to_be_visible()

    def test_four_stat_cards_present(self, authenticated_page: Page):
        """4个统计卡片都存在"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["stat_portfolio"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stat_backtest"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stat_worker"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stat_system"])).to_be_visible()

    def test_stat_card_has_label_and_value(self, authenticated_page: Page):
        """统计卡片包含标签和数值"""
        _goto_dashboard(authenticated_page)
        card = authenticated_page.locator(SEL["stat_portfolio"])
        expect(card.locator(".stat-label")).to_be_visible()
        expect(card.locator(".stat-value")).to_be_visible()


@pytest.mark.e2e
class TestStagesOverview:
    """4阶段概览"""

    def test_stages_grid_visible(self, authenticated_page: Page):
        """阶段卡片网格可见"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["stages_grid"])).to_be_visible()

    def test_four_stage_cards_present(self, authenticated_page: Page):
        """4个阶段卡片都存在"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["stage_backtest"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stage_validation"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stage_paper"])).to_be_visible()
        expect(authenticated_page.locator(SEL["stage_live"])).to_be_visible()

    def test_stage_card_has_link_button(self, authenticated_page: Page):
        """阶段卡片有快捷入口按钮"""
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(SEL["link_backtest"])).to_be_visible()
        expect(authenticated_page.locator(SEL["link_validation"])).to_be_visible()
        expect(authenticated_page.locator(SEL["link_paper"])).to_be_visible()
        expect(authenticated_page.locator(SEL["link_live"])).to_be_visible()

    def test_click_backtest_link_navigates(self, authenticated_page: Page):
        """点击回测快捷入口跳转"""
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["link_backtest"])
        authenticated_page.wait_for_url("**/backtest**", timeout=5000)
        assert "/backtest" in authenticated_page.url

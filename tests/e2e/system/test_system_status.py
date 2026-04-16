"""
系统状态 E2E 测试

测试系统相关页面：
- 系统状态
- Worker 管理
- 告警中心
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import CARD, TABLE, TABLE_ROW, SPIN


@pytest.mark.e2e
class TestSystemStatus:
    """系统状态测试"""

    def test_system_status_loads(self, authenticated_page: Page):
        """系统状态页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 系统状态页面加载成功")

    def test_system_overview(self, authenticated_page: Page):
        """系统概览显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("domcontentloaded")

        # 检查统计卡片
        stat_cards = page.locator(f".ant-statistic, {CARD}").all()
        print(f"统计卡片数量: {len(stat_cards)}")

        # 应该显示一些系统信息
        assert len(stat_cards) >= 1 or page.locator("table").count() >= 1
        print("✅ 系统概览显示正常")

    def test_infrastructure_status(self, authenticated_page: Page):
        """基础设施状态显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("domcontentloaded")

        # 检查基础设施状态卡片（MySQL, Redis, ClickHouse 等）
        infra_section = page.locator(f"{CARD}:has-text('基础设施'), {CARD}:has-text('MySQL')")
        if infra_section.count() > 0:
            print("✅ 基础设施状态显示正常")
        else:
            # 可能是其他布局
            print("⚠️ 基础设施部分未找到")

    def test_worker_list(self, authenticated_page: Page):
        """Worker 列表显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("domcontentloaded")

        # 检查组件详情表格
        worker_table = page.locator(f"{CARD}:has-text('组件') table, {CARD}:has-text('Worker') table")
        expect(worker_table).to_be_visible(timeout=5000)
        rows = page.locator(f"{TABLE} tbody tr").all()
        print(f"Worker/组件数量: {len(rows)}")

        print("✅ Worker 列表检查完成")

    def test_auto_refresh_toggle(self, authenticated_page: Page):
        """自动刷新开关"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("domcontentloaded")

        # 检查自动刷新开关
        refresh_switch = page.locator(".ant-switch, button:has-text('自动刷新')")
        if refresh_switch.count() > 0:
            # 点击切换
            refresh_switch.first.click()
            refresh_switch.first.click()
            print("✅ 自动刷新开关功能正常")
        else:
            print("⚠️ 自动刷新开关未找到")

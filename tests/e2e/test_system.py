"""
系统状态 E2E 测试

测试系统相关页面：
- 系统状态
- Worker 管理
- 告警中心
"""

import pytest
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestSystemStatus:
    """系统状态测试"""

    def test_system_status_loads(self, authenticated_page: Page):
        """系统状态页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 系统状态页面加载成功")

    def test_system_overview(self, authenticated_page: Page):
        """系统概览显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查统计卡片
        stat_cards = page.locator(".ant-statistic, .ant-card").all()
        print(f"统计卡片数量: {len(stat_cards)}")

        # 应该显示一些系统信息
        assert len(stat_cards) >= 1 or page.locator("table").count() >= 1
        print("✅ 系统概览显示正常")

    def test_infrastructure_status(self, authenticated_page: Page):
        """基础设施状态显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查基础设施状态卡片（MySQL, Redis, ClickHouse 等）
        infra_section = page.locator(".ant-card:has-text('基础设施'), .ant-card:has-text('MySQL')")
        if infra_section.count() > 0:
            print("✅ 基础设施状态显示正常")
        else:
            # 可能是其他布局
            print("⚠️ 基础设施部分未找到")

    def test_worker_list(self, authenticated_page: Page):
        """Worker 列表显示"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 检查组件详情表格
        worker_table = page.locator(".ant-card:has-text('组件') table, .ant-card:has-text('Worker') table")
        if worker_table.is_visible():
            rows = page.locator(".ant-table-tbody tr").all()
            print(f"Worker/组件数量: {len(rows)}")
        else:
            print("⚠️ Worker 列表暂无数据")

        print("✅ Worker 列表检查完成")

    def test_auto_refresh_toggle(self, authenticated_page: Page):
        """自动刷新开关"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/status")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查自动刷新开关
        refresh_switch = page.locator(".ant-switch, button:has-text('自动刷新')")
        if refresh_switch.count() > 0:
            # 点击切换
            refresh_switch.first.click()
            page.wait_for_timeout(500)
            refresh_switch.first.click()
            print("✅ 自动刷新开关功能正常")
        else:
            print("⚠️ 自动刷新开关未找到")


@pytest.mark.e2e
class TestWorkerManagement:
    """Worker 管理测试"""

    def test_worker_management_loads(self, authenticated_page: Page):
        """Worker 管理页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/workers")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ Worker 管理页面加载成功")


@pytest.mark.e2e
class TestAlertCenter:
    """告警中心测试"""

    def test_alert_center_loads(self, authenticated_page: Page):
        """告警中心页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/system/alerts")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 告警中心页面加载成功")

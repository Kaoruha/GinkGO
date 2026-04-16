"""
Walk-Forward 与蒙特卡洛 E2E 测试

测试：
- Walk-Forward 验证页面
- 蒙特卡洛模拟页面
"""

import pytest
from playwright.sync_api import Page, expect

from ..config import config
from ..selectors import SELECT, INPUT_NUMBER, INPUT


@pytest.mark.e2e
class TestWalkForward:
    """Walk-Forward 验证测试"""

    def test_walkforward_page_loads(self, authenticated_page: Page):
        """Walk-Forward 页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/walkforward")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ Walk-Forward 页面加载成功")

    def test_walkforward_form(self, authenticated_page: Page):
        """Walk-Forward 表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/walkforward")
        page.wait_for_load_state("domcontentloaded")

        # 检查表单元素
        backtest_select = page.locator(f"{SELECT}, select")
        n_folds_input = page.locator(f"input[type='number'], {INPUT_NUMBER}")

        if backtest_select.count() > 0:
            print("✅ 回测选择器存在")
        if n_folds_input.count() > 0:
            print("✅ Fold 数量输入框存在")

        print("✅ Walk-Forward 表单检查完成")


@pytest.mark.e2e
class TestMonteCarlo:
    """蒙特卡洛模拟测试"""

    def test_montecarlo_page_loads(self, authenticated_page: Page):
        """蒙特卡洛页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/montecarlo")
        page.wait_for_load_state("domcontentloaded")

        expect(page.locator("body")).to_be_visible()
        print("✅ 蒙特卡洛页面加载成功")

    def test_montecarlo_form(self, authenticated_page: Page):
        """蒙特卡洛表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/montecarlo")
        page.wait_for_load_state("domcontentloaded")

        # 检查模拟次数输入框
        sim_input = page.locator("input[placeholder*='模拟'], input[type='number']")
        if sim_input.count() > 0:
            print("✅ 模拟次数输入框存在")

        # 检查运行按钮
        run_btn = page.locator("button:has-text('运行'), button:has-text('开始')")
        if run_btn.count() > 0:
            print("✅ 运行按钮存在")

        print("✅ 蒙特卡洛表单检查完成")

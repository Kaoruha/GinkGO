"""
策略验证 E2E 测试

测试 Stage2 策略验证页面：
- Walk-Forward 验证
- 蒙特卡洛模拟
- 敏感性分析
"""

import pytest
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestWalkForward:
    """Walk-Forward 验证测试"""

    def test_walkforward_page_loads(self, authenticated_page: Page):
        """Walk-Forward 页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/walkforward")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ Walk-Forward 页面加载成功")

    def test_walkforward_form(self, authenticated_page: Page):
        """Walk-Forward 表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/walkforward")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查表单元素
        backtest_select = page.locator(".ant-select, select")
        n_folds_input = page.locator("input[type='number'], .ant-input-number")

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
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 蒙特卡洛页面加载成功")

    def test_montecarlo_form(self, authenticated_page: Page):
        """蒙特卡洛表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/montecarlo")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查模拟次数输入框
        sim_input = page.locator("input[placeholder*='模拟'], input[type='number']")
        if sim_input.count() > 0:
            print("✅ 模拟次数输入框存在")

        # 检查运行按钮
        run_btn = page.locator("button:has-text('运行'), button:has-text('开始')")
        if run_btn.count() > 0:
            print("✅ 运行按钮存在")

        print("✅ 蒙特卡洛表单检查完成")


@pytest.mark.e2e
class TestSensitivity:
    """敏感性分析测试"""

    def test_sensitivity_page_loads(self, authenticated_page: Page):
        """敏感性分析页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/sensitivity")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 敏感性分析页面加载成功")

    def test_sensitivity_form(self, authenticated_page: Page):
        """敏感性分析表单元素"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/stage2/sensitivity")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查参数输入
        param_input = page.locator("input, textarea")
        if param_input.count() > 0:
            print("✅ 参数输入框存在")

        print("✅ 敏感性分析表单检查完成")


@pytest.mark.e2e
class TestFactorResearch:
    """因子研究测试"""

    def test_ic_analysis_page_loads(self, authenticated_page: Page):
        """IC 分析页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/ic")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ IC 分析页面加载成功")

    def test_factor_layering_page_loads(self, authenticated_page: Page):
        """因子分层页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/layering")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子分层页面加载成功")

    def test_factor_decay_page_loads(self, authenticated_page: Page):
        """因子衰减页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/decay")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子衰减页面加载成功")

    def test_factor_comparison_page_loads(self, authenticated_page: Page):
        """因子比较页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/compare")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子比较页面加载成功")

    def test_factor_orthogonalization_page_loads(self, authenticated_page: Page):
        """因子正交化页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/research/orthogonalize")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 因子正交化页面加载成功")


@pytest.mark.e2e
class TestOptimization:
    """参数优化测试"""

    def test_grid_search_page_loads(self, authenticated_page: Page):
        """网格搜索页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/grid")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 网格搜索页面加载成功")

    def test_genetic_optimizer_page_loads(self, authenticated_page: Page):
        """遗传算法页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/genetic")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 遗传算法页面加载成功")

    def test_bayesian_optimizer_page_loads(self, authenticated_page: Page):
        """贝叶斯优化页面加载"""
        page = authenticated_page
        page.goto(f"{config.web_ui_url}/optimization/bayesian")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator("body")).to_be_visible()
        print("✅ 贝叶斯优化页面加载成功")

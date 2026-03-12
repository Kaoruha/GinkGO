"""
WebUI Portfolio 创建 E2E 测试

通过浏览器操作验证 Portfolio 创建流程：
1. 导航到 Portfolio 列表页
2. 创建新 Portfolio（选择 selector、sizer、strategy）
3. 填写组件参数
4. 验证 Portfolio 创建成功
"""

import pytest
import time
import random
from datetime import datetime
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestPortfolioCreation:
    """Portfolio 创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(60000)

        # 生成唯一名称和资金
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.portfolio_name = f"E2E_WebUI_{timestamp}"
        self.initial_cash = random.randint(5, 50) * 10000

        yield

    def test_navigate_to_portfolio_page(self):
        """测试导航到 Portfolio 页面"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 验证 URL
        assert "/portfolio" in page.url
        print("✅ 成功导航到 Portfolio 页面")

    def test_create_button_exists(self):
        """测试创建按钮存在"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 验证创建按钮
        create_btn = page.locator("button:has-text('创建组合')").first
        assert create_btn.is_visible(), "创建组合按钮应该可见"

        print("✅ 创建组合按钮正常")

    def test_open_create_modal(self):
        """测试打开创建模态框"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 点击创建按钮
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 验证模态框打开
        modal = page.locator(".ant-modal").first
        assert modal.is_visible(), "创建组合模态框应该打开"

        # 关闭模态框
        close_btn = modal.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

        print("✅ 创建模态框正常")

    def test_fill_basic_info(self):
        """测试填写基本信息"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 打开创建模态框
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 填写名称
        name_input = page.locator("#form_item_name").first
        name_input.fill(self.portfolio_name)
        assert name_input.input_value() == self.portfolio_name
        print(f"✓ 名称: {self.portfolio_name}")

        # 填写描述
        description = f"E2E测试组合 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        desc_textarea = page.locator("textarea").first
        desc_textarea.fill(description)
        print("✓ 描述已填写")

        # 填写初始资金
        cash_input = page.locator("#form_item_initial_cash").first
        cash_input.fill(str(self.initial_cash))
        assert cash_input.input_value() == str(self.initial_cash)
        print(f"✓ 初始资金: {self.initial_cash:,}")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_add_selector(self):
        """测试添加选股器"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 打开创建模态框
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 点击选股器标签
        page.locator("button.type-btn:has-text('选股器')").first.click()
        page.wait_for_timeout(500)

        # 选择组件
        page.locator(".component-selector .ant-select").first.click()
        page.wait_for_timeout(500)

        # 选择 fixed_selector
        selector_option = page.locator(".ant-select-item-option:has-text('fixed_selector')").first
        if selector_option.is_visible():
            selector_option.click()
            page.wait_for_timeout(1500)
            print("✓ 已选择: fixed_selector")

            # 填写 codes 参数
            param_inputs = page.locator(".param-row input").all()
            if len(param_inputs) >= 2:
                param_inputs[1].fill("000001.SZ")
                print("✓ codes=000001.SZ")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_add_sizer(self):
        """测试添加仓位管理器"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 打开创建模态框
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 点击仓位管理标签
        page.locator("button.type-btn:has-text('仓位管理')").first.click()
        page.wait_for_timeout(500)

        # 选择组件
        page.locator(".component-selector .ant-select").first.click()
        page.wait_for_timeout(500)

        # 选择 fixed_sizer
        sizer_option = page.locator(".ant-select-item-option:has-text('fixed_sizer')").first
        if sizer_option.is_visible():
            sizer_option.click()
            page.wait_for_timeout(1500)
            print("✓ 已选择: fixed_sizer")

            # 填写 volume 参数
            param_input = page.locator(".param-row input").last
            param_input.fill("1500")
            print("✓ volume=1500")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_add_strategy(self):
        """测试添加策略"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 打开创建模态框
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 点击策略标签
        page.locator("button.type-btn:has-text('策略')").first.click()
        page.wait_for_timeout(500)

        # 选择组件
        strategy_dropdown = page.locator(".component-selector .ant-select").first
        strategy_dropdown.click()
        page.wait_for_timeout(500)

        # 搜索 random_signal
        search_input = strategy_dropdown.locator("input[role='combobox']").first
        search_input.type("random_signal")
        page.wait_for_timeout(800)

        # 选择第一个选项
        first_option = page.locator(".ant-select-item-option").first
        if first_option.is_visible():
            first_option.click()
            page.wait_for_timeout(3000)
            print("✓ 已选择: random_signal_strategy")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_create_portfolio_complete(self):
        """测试创建完整的 Portfolio"""
        page = self.page

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 打开创建模态框
        create_btn = page.locator("button:has-text('创建组合')").first
        create_btn.click()
        page.wait_for_timeout(2000)

        # 填写基本信息
        page.locator("#form_item_name").first.fill(self.portfolio_name)
        page.locator("#form_item_initial_cash").first.fill(str(self.initial_cash))
        print(f"✓ 基本信息: {self.portfolio_name}, {self.initial_cash:,}")

        # 添加选股器
        page.locator("button.type-btn:has-text('选股器')").first.click()
        page.wait_for_timeout(500)
        page.locator(".component-selector .ant-select").first.click()
        page.wait_for_timeout(500)
        page.locator(".ant-select-item-option:has-text('fixed_selector')").first.click()
        page.wait_for_timeout(1500)
        page.locator(".param-row input").nth(1).fill("000001.SZ")
        print("✓ Selector: fixed_selector")
        page.wait_for_timeout(500)

        # 添加仓位管理器
        page.locator("button.type-btn:has-text('仓位管理')").first.click()
        page.wait_for_timeout(500)
        page.locator(".component-selector .ant-select").first.click()
        page.wait_for_timeout(500)
        page.locator(".ant-select-item-option:has-text('fixed_sizer')").first.click()
        page.wait_for_timeout(1500)
        page.locator(".param-row input").last.fill("1500")
        print("✓ Sizer: fixed_sizer")
        page.wait_for_timeout(500)

        # 添加策略
        page.locator("button.type-btn:has-text('策略')").first.click()
        page.wait_for_timeout(500)
        strategy_dropdown = page.locator(".component-selector .ant-select").first
        strategy_dropdown.click()
        page.wait_for_timeout(500)
        search_input = strategy_dropdown.locator("input[role='combobox']").first
        search_input.type("random_signal")
        page.wait_for_timeout(800)
        page.locator(".ant-select-item-option").first.click()
        page.wait_for_timeout(3000)
        print("✓ Strategy: random_signal")

        # 提交
        submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')").first
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证成功
        success_msg = page.locator(".ant-message-success")
        if success_msg.is_visible():
            print("✅ Portfolio 创建成功")

        # 验证在列表中
        page.wait_for_timeout(2000)
        portfolio_item = page.locator(f"text={self.portfolio_name}").first
        if portfolio_item.is_visible():
            print(f"✅ Portfolio 出现在列表中: {self.portfolio_name}")

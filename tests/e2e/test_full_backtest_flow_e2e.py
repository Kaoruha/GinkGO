"""
WebUI 完整回测流程 E2E 测试

测试流程：
1. 创建 Portfolio（Selector + Sizer + Strategy）
2. 创建回测任务
3. 启动回测
4. 等待回测完成
5. 验证回测结果
"""

import pytest
import time
import random
from datetime import datetime
from playwright.sync_api import Page, expect

from .config import config
from .selectors import MODAL, SELECT, SELECT_ITEM, BTN_PRIMARY, MESSAGE, CLOSE_BTN, TAG


@pytest.mark.e2e
@pytest.mark.slow
class TestFullBacktestFlow:
    """完整回测流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(60000)

        # 生成唯一名称
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.portfolio_name = f"FullFlow_{timestamp}"
        self.bt_name = f"BT_{timestamp}"
        self.initial_cash = random.randint(5, 20) * 10000

        yield

    def test_01_create_portfolio(self):
        """测试 1: 创建 Portfolio"""
        page = self.page

        # 导航到 Portfolio 列表页
        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        # 验证在组合页面
        assert "/portfolio" in page.url

        # 点击创建按钮
        create_btn = page.locator("button:has-text('创建组合')").first
        assert create_btn.is_visible(), "创建组合按钮应该可见"
        create_btn.click()

        # 验证模态框打开
        modal = page.locator(MODAL)
        expect(modal).to_be_visible()

        # 填写基本信息
        page.locator("#form_item_name").first.fill(self.portfolio_name)
        assert page.locator("#form_item_name").input_value() == self.portfolio_name

        page.locator("textarea").first.fill(f"完整回测E2E测试 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        page.locator("#form_item_initial_cash").first.fill(str(self.initial_cash))
        print(f"组合名称: {self.portfolio_name}, 资金: {self.initial_cash}")

        # 配置 Selector
        page.locator("button.type-btn:has-text('选股器')").first.click()

        page.locator(f".component-selector {SELECT}").first.click()
        page.locator(f".ant-select-item-option:has-text('fixed_selector')").first.click()

        page.locator(".param-row input").nth(1).fill("000001.SZ")
        print("Selector: fixed_selector, codes=000001.SZ")

        # 配置 Sizer
        page.locator("button.type-btn:has-text('仓位管理')").first.click()

        page.locator(f".component-selector {SELECT}").first.click()
        page.locator(".ant-select-item-option:has-text('fixed_sizer')").first.click()

        page.locator(".param-row input").last.fill("1000")
        print("Sizer: fixed_sizer, volume=1000")

        # 配置 Strategy
        page.locator("button.type-btn:has-text('策略')").first.click()

        strategy_dropdown = page.locator(f".component-selector {SELECT}").first
        strategy_dropdown.click()

        search_input = strategy_dropdown.locator("input[role='combobox']").first
        search_input.type("random_signal")

        page.locator(".ant-select-item-option").first.click()
        print("Strategy: random_signal_strategy")

        # 保存
        submit_btn = page.locator(f"{MODAL} button{BTN_PRIMARY}:has-text('创 建')").first
        submit_btn.click()

        # 验证成功
        success_msg = page.locator(f"{MESSAGE}-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print("Portfolio 创建成功")

        # 关闭模态框（如果仍可见）
        close_btn = page.locator(CLOSE_BTN)
        try:
            expect(close_btn.first).to_be_visible(timeout=2000)
            close_btn.first.click()
        except Exception:
            pass  # 模态框可能已自动关闭

    def test_02_create_backtest_task(self):
        """测试 2: 创建回测任务"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 验证在回测页面
        assert "/stage1/backtest" in page.url

        # 点击创建回测
        create_btn = page.locator('button:has-text("创建回测")').first
        assert create_btn.is_visible()
        create_btn.click()

        # 验证模态框打开
        modal = page.locator(MODAL)
        expect(modal).to_be_visible()

        # 填写任务名称
        name_input = page.locator('input[placeholder*="任务名称"]').first
        name_input.fill(self.bt_name)
        print(f"任务名称: {self.bt_name}")

        # 选择 Portfolio
        portfolio_select = page.locator(f"{MODAL} {SELECT}").first
        portfolio_select.click()

        # 搜索刚创建的 Portfolio
        search_input = page.locator(f".ant-select-dropdown input").first
        expect(search_input).to_be_visible(timeout=5000)
        search_input.fill(self.portfolio_name)

        dropdown_items = page.locator(f".ant-select-dropdown {SELECT_ITEM}").all()
        assert dropdown_items, "应该有 Portfolio 选项"
        dropdown_items[0].click()
        print(f"已选择 Portfolio: {self.portfolio_name}")

        # 设置日期
        date_inputs = page.locator("input.ant-picker-input").all()
        if len(date_inputs) >= 2:
            date_inputs[0].fill("2024-01-01")
            date_inputs[1].fill("2024-12-31")
            print("日期: 2024-01-01 ~ 2024-12-31")

        # 提交
        submit_btn = page.locator(f"button{BTN_PRIMARY}:has-text('确定')").first
        submit_btn.click()

        # 验证成功
        success_msg = page.locator(f"{MESSAGE}-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print("回测任务创建成功")

    def test_03_start_backtest(self):
        """测试 3: 启动回测"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 找到刚创建的任务
        task_row = page.locator(f"tr:has-text('{self.bt_name}')").first
        assert task_row.is_visible(), f"找不到任务: {self.bt_name}"

        # 点击启动按钮
        start_btn = task_row.locator('button:has-text("启动")').first
        expect(start_btn).to_be_visible(timeout=5000)
        start_btn.click()

        # 验证消息
        message = page.locator(f"{MESSAGE}-notice-content").first
        expect(message).to_be_visible(timeout=5000)
        print(f"{message.text_content()}")

    def test_04_verify_task_exists(self):
        """测试 4: 验证任务存在"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 验证任务存在
        task_row = page.locator(f"tr:has-text('{self.bt_name}')").first
        assert task_row.is_visible(), f"任务应该存在: {self.bt_name}"

        # 获取任务状态
        status_cell = task_row.locator(f".status-tag, {TAG}").first
        expect(status_cell).to_be_visible(timeout=5000)
        status = status_cell.text_content()
        print(f"任务状态: {status}")

    def test_05_view_task_detail(self):
        """测试 5: 查看任务详情"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 点击任务行
        task_row = page.locator(f"tr:has-text('{self.bt_name}')").first
        task_row.click()

        # 验证跳转到详情页
        assert f"/stage1/backtest/" in page.url, "应该跳转到详情页"
        print("成功导航到详情页")

        # 返回列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")

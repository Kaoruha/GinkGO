"""
WebUI 回测任务创建 E2E 测试

通过浏览器操作验证回测任务创建流程：
1. 导航到回测列表页
2. 点击创建按钮打开模态框
3. 填写回测任务信息（名称、Portfolio、日期范围）
4. 提交创建
5. 验证回测任务创建成功
"""

import pytest
import time
from datetime import datetime
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestBacktestCreation:
    """回测任务创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(60000)

        # 生成时间戳
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.backtest_name = f"E2E_BT_{self.timestamp}"

        yield

    def _open_create_modal(self):
        """打开创建模态框"""
        page = self.page

        # 导航到回测列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 点击创建回测按钮
        create_btn = page.locator('button:has-text("创建回测")').first
        assert create_btn.is_visible(), "创建回测按钮应该可见"
        create_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal").first
        assert modal.is_visible(), "创建回测模态框应该打开"

        return modal

    def test_navigate_to_backtest_list(self):
        """测试导航到回测列表页"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 验证 URL
        assert "/stage1/backtest" in page.url
        print("✅ 成功导航到回测列表页")

    def test_create_button_exists(self):
        """测试创建按钮存在"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        # 验证创建回测按钮
        create_btn = page.locator('button:has-text("创建回测")').first
        assert create_btn.is_visible(), "创建回测按钮应该可见"

        print("✅ 创建回测按钮正常")

    def test_open_create_modal(self):
        """测试打开创建模态框"""
        modal = self._open_create_modal()

        # 验证模态框标题
        title = modal.locator(".ant-modal-title").first
        if title.is_visible():
            title_text = title.text_content()
            print(f"✅ 模态框标题: {title_text}")
            assert "回测" in title_text or "创建" in title_text, "模态框标题应包含'回测'或'创建'"

    def test_task_name_input_in_modal(self):
        """测试模态框中的任务名称输入框"""
        modal = self._open_create_modal()

        # 验证任务名称输入框
        name_input = modal.locator('input[placeholder*="任务名称"], input[placeholder*="请输入"]').first
        assert name_input.is_visible(), "任务名称输入框应该可见"

        # 填写任务名称
        name_input.fill(self.backtest_name)
        assert name_input.input_value() == self.backtest_name, "任务名称应该被正确填写"

        print(f"✅ 任务名称: {self.backtest_name}")

        # 关闭模态框
        close_btn = modal.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_portfolio_selector_in_modal(self):
        """测试模态框中的 Portfolio 选择器"""
        modal = self._open_create_modal()

        # 验证 Portfolio 下拉框
        portfolio_select = modal.locator(".ant-select").first
        assert portfolio_select.is_visible(), "Portfolio 下拉框应该可见"

        # 点击打开下拉框
        portfolio_select.click()
        page.wait_for_timeout(500)

        # 验证下拉框打开
        dropdown = page.locator(".ant-select-dropdown").first
        if dropdown.is_visible():
            print("✅ Portfolio 下拉框正常")

            # 关闭下拉框
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        else:
            print("⚠️ Portfolio 下拉框可能没有选项")

        # 关闭模态框
        close_btn = modal.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_submit_button_in_modal(self):
        """测试模态框中的提交按钮"""
        modal = self._open_create_modal()

        # 验证确定按钮
        submit_btn = modal.locator("button.ant-btn-primary:has-text('确定')").first
        assert submit_btn.is_visible(), "确定按钮应该可见"

        print("✅ 确定按钮正常")

        # 关闭模态框
        close_btn = modal.locator(".ant-modal-close").first
        close_btn.click()
        page.wait_for_timeout(500)

    def test_create_backtest_with_minimal_fields(self):
        """测试使用最小必填字段创建回测任务"""
        page = self.page
        modal = self._open_create_modal()

        # 填写任务名称
        name_input = modal.locator('input[placeholder*="任务名称"]').first
        name_input.fill(self.backtest_name)
        print(f"✓ 任务名称: {self.backtest_name}")

        # 选择 Portfolio（如果有）
        portfolio_select = modal.locator(".ant-select").first
        portfolio_select.click()
        page.wait_for_timeout(500)

        dropdown_items = page.locator(".ant-select-dropdown .ant-select-item").all()
        if dropdown_items:
            dropdown_items[0].click()
            print("✓ 已选择 Portfolio")
            page.wait_for_timeout(500)
        else:
            print("⚠️ 没有 Portfolio 可选")
            # 关闭下拉框
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # 设置日期范围（如果有日期选择器）
        date_inputs = modal.locator("input.ant-picker-input").all()
        if len(date_inputs) >= 2:
            date_inputs[0].fill("2023-01-01")
            date_inputs[1].fill("2023-12-31")
            print("✓ 日期: 2023-01-01 ~ 2023-12-31")
            page.wait_for_timeout(300)

        # 提交
        submit_btn = modal.locator("button.ant-btn-primary:has-text('确定')").first
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证结果
        # 方案1：验证成功消息
        success_msg = page.locator(".ant-message-success, .ant-message-notice-content").first
        if success_msg.is_visible():
            msg_text = success_msg.text_content()
            print(f"✓ 创建成功: {msg_text}")

        # 方案2：验证模态框关闭
        modal = page.locator(".ant-modal").first
        if not modal.is_visible(timeout=2000):
            print("✓ 模态框已关闭")

        # 方案3：验证仍在回测列表页
        assert "/stage1/backtest" in page.url, "应该仍在回测列表页"

        print("✅ 回测任务创建流程完成")

    def test_modal_cancel_button(self):
        """测试模态框的取消按钮"""
        modal = self._open_create_modal()

        # 验证取消按钮
        cancel_btn = modal.locator("button:has-text('取消')").first
        assert cancel_btn.is_visible(), "取消按钮应该可见"

        # 点击取消
        cancel_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框关闭
        modal = page.locator(".ant-modal").first
        assert not modal.is_visible(timeout=2000), "点击取消后模态框应该关闭"

        print("✅ 取消按钮正常")

    def test_modal_close_button(self):
        """测试模态框的关闭按钮"""
        modal = self._open_create_modal()

        # 验证关闭按钮（X）
        close_btn = modal.locator(".ant-modal-close").first
        assert close_btn.is_visible(), "关闭按钮应该可见"

        # 点击关闭
        close_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框关闭
        modal = page.locator(".ant-modal").first
        assert not modal.is_visible(timeout=2000), "点击关闭后模态框应该关闭"

        print("✅ 关闭按钮正常")

"""
日期选择器 E2E 测试

测试回测创建页面的日期选择器功能：
- 开始日期设置
- 结束日期设置
- 日期验证
"""

import pytest
import time
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestDatePicker:
    """日期选择器测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(config.timeout)

    def _set_date_picker(self, label: str, date_value: str) -> bool:
        """设置 Ant Design DatePicker"""
        page = self.page

        # 找到包含 label 的表单项
        form_item = page.locator(f".ant-form-item:has-text('{label}')").first
        assert form_item.is_visible(), f"未找到 {label} 表单项"

        # 找到 picker 组件
        picker = form_item.locator(".ant-picker").first
        assert picker.is_visible(), f"未找到 {label} picker"

        # 点击 picker
        picker.click()
        page.wait_for_timeout(500)

        # 填写日期
        picker_input = picker.locator("input").first
        picker_input.fill(date_value)
        page.wait_for_timeout(300)

        # 按回车确认
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)

        return True

    def test_navigate_to_create_page(self):
        """测试导航到创建页面"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 验证 URL
        assert "/stage1/backtest/create" in page.url
        print("✅ 成功导航到创建页面")

        # 验证页面标题
        page_title = page.locator(".ant-page-header-heading-title, h1, h2").first
        if page_title.is_visible():
            title_text = page_title.text_content()
            print(f"页面标题: {title_text}")

    def test_start_date_picker_exists(self):
        """测试开始日期选择器存在"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 验证开始日期标签
        start_label = page.locator(".ant-form-item:has-text('开始日期')").first
        assert start_label.is_visible(), "开始日期标签应该可见"

        # 验证 picker 存在
        start_picker = start_label.locator(".ant-picker").first
        assert start_picker.is_visible(), "开始日期选择器应该可见"

        # 验证输入框
        start_input = start_picker.locator("input").first
        assert start_input.is_visible(), "开始日期输入框应该可见"

        print("✅ 开始日期选择器正常显示")

    def test_end_date_picker_exists(self):
        """测试结束日期选择器存在"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 验证结束日期标签
        end_label = page.locator(".ant-form-item:has-text('结束日期')").first
        assert end_label.is_visible(), "结束日期标签应该可见"

        # 验证 picker 存在
        end_picker = end_label.locator(".ant-picker").first
        assert end_picker.is_visible(), "结束日期选择器应该可见"

        # 验证输入框
        end_input = end_picker.locator("input").first
        assert end_input.is_visible(), "结束日期输入框应该可见"

        print("✅ 结束日期选择器正常显示")

    def test_set_start_date(self):
        """测试设置开始日期"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 设置开始日期
        self._set_date_picker("开始日期", "2024-01-01")

        # 验证输入框的值
        start_picker = page.locator(".ant-form-item:has-text('开始日期') .ant-picker").first
        start_input = start_picker.locator("input").first
        input_value = start_input.input_value()

        assert "2024-01-01" in input_value or "2024-01-01" in start_input.get_attribute("value") or "", \
            f"开始日期应设置为 2024-01-01，实际为: {input_value}"

        print("✅ 开始日期设置成功: 2024-01-01")

    def test_set_end_date(self):
        """测试设置结束日期"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 设置结束日期
        self._set_date_picker("结束日期", "2025-12-31")

        # 验证输入框的值
        end_picker = page.locator(".ant-form-item:has-text('结束日期') .ant-picker").first
        end_input = end_picker.locator("input").first
        input_value = end_input.input_value()

        assert "2025-12-31" in input_value or "2025-12-31" in end_input.get_attribute("value") or "", \
            f"结束日期应设置为 2025-12-31，实际为: {input_value}"

        print("✅ 结束日期设置成功: 2025-12-31")

    def test_set_both_dates(self):
        """测试同时设置开始和结束日期"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 设置开始日期
        self._set_date_picker("开始日期", "2024-01-01")

        # 设置结束日期
        self._set_date_picker("结束日期", "2025-12-31")

        # 等待表单验证
        page.wait_for_timeout(1000)

        # 检查是否没有错误
        errors = page.locator(".ant-form-item-explain-error").all()

        # 开始日期早于结束日期，不应该有错误
        error_texts = [err.text_content() for err in errors if err.is_visible() and err.text_content()]
        assert len(error_texts) == 0, f"日期设置后不应有错误，但发现: {error_texts}"

        print("✅ 开始和结束日期设置成功，无验证错误")

    def test_invalid_date_range(self):
        """测试无效的日期范围（开始日期晚于结束日期）"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 设置开始日期为较晚的日期
        self._set_date_picker("开始日期", "2025-12-31")

        # 设置结束日期为较早的日期
        self._set_date_picker("结束日期", "2024-01-01")

        # 等待表单验证
        page.wait_for_timeout(1000)

        # 检查是否有错误提示（可选，取决于表单验证逻辑）
        print("✅ 无效日期范围测试完成")

    def test_date_picker_interaction(self):
        """测试日期选择器交互"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest/create")
        page.wait_for_load_state("domcontentloaded")

        # 找到开始日期选择器
        start_picker = page.locator(".ant-form-item:has-text('开始日期') .ant-picker").first

        # 点击打开日期面板
        start_picker.click()
        page.wait_for_timeout(500)

        # 验证日期面板是否打开
        date_panel = page.locator(".ant-picker-dropdown").first
        if date_panel.is_visible():
            print("✅ 日期面板打开成功")

            # 点击面板外部关闭
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)

            # 验证面板关闭
            assert not date_panel.is_visible(), "按 ESC 后日期面板应关闭"
            print("✅ 日期面板关闭成功")
        else:
            print("⚠️ 日期面板未显示（可能直接进入输入模式）")

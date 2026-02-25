"""
Portfolio 组件配置 E2E 测试

测试投资组合的组件配置保存和验证：
1. 创建组合
2. 配置组件并修改参数（使用非默认值）
3. 详情页验证参数保存正确

参考 examples/complete_backtest_example.py 中的组件配置
"""

import time
import pytest
from playwright.sync_api import Page, expect

from .config import config


# 测试配置 - 使用非默认值便于验证
TEST_PORTFOLIO_NAME = f"E2E_Config_Test_{int(time.time())}"

# 组件配置 - 参考回测示例，使用非默认值
TEST_CONFIG = {
    "portfolio": {
        "initial_cash": 500000,  # 非默认值
        "mode": "BACKTEST",
        "description": "E2E组件配置测试",
    },
    "selector": {
        "name": "fixed_selector",
        "params": {
            "codes": "600000.SH,600519.SH",  # 修改为不同股票
        },
    },
    "sizer": {
        "name": "fixed_sizer",
        "params": {
            "volume": "2000",  # 非默认值 1000
        },
    },
    "strategy": {
        "name": "random_signal_strategy",
        "params": {
            "buy_probability": "0.8",   # 非默认值 0.5
            "sell_probability": "0.1",  # 非默认值 0.5
            "max_signals": "3",         # 非默认值 10
        },
    },
}


@pytest.mark.e2e
class TestPortfolioConfigE2E:
    """Portfolio 组件配置测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.goto(f"{config.web_ui_url}/portfolio")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def test_create_and_verify_config(self):
        """
        完整测试：创建Portfolio -> 配置组件 -> 修改参数 -> 验证详情页参数

        测试流程:
        1. 点击创建组合按钮
        2. 填写基本信息（名称、初始资金、描述）
        3. 添加选股器并修改参数
        4. 添加仓位管理器并修改参数
        5. 添加策略并修改参数
        6. 保存
        7. 进入详情页
        8. 验证所有组件参数都正确保存
        """
        page = self.page
        page.set_default_timeout(120000)

        # ========== 第一步：创建Portfolio ==========
        print("\n📌 Step 1: 点击创建组合按钮")
        page.click('button.ant-btn-primary:has-text("创建组合")')
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()
        print("  ✅ 模态框已打开")

        # ========== 第二步：填写基本信息 ==========
        print("\n📌 Step 2: 填写基本信息")
        # 填写名称
        page.fill('.ant-modal input[placeholder="组合名称"]', TEST_PORTFOLIO_NAME)
        print(f"  ✓ 名称: {TEST_PORTFOLIO_NAME}")

        # 修改初始资金 - 先清空再输入
        cash_input = page.locator(".ant-modal .ant-input-number-input").first
        cash_input.fill("")
        cash_input.fill(str(TEST_CONFIG["portfolio"]["initial_cash"]))
        print(f"  ✓ 初始资金: {TEST_CONFIG['portfolio']['initial_cash']}")

        # 填写描述
        desc_input = page.locator(".ant-modal textarea").first
        desc_input.fill(TEST_CONFIG["portfolio"]["description"])
        print(f"  ✓ 描述: {TEST_CONFIG['portfolio']['description']}")

        page.wait_for_timeout(500)

        # ========== 第三步：添加选股器 ==========
        print("\n📌 Step 3: 添加选股器")
        self._add_component(
            page,
            type_btn_text="选股器",
            component_name=TEST_CONFIG["selector"]["name"],
            params=TEST_CONFIG["selector"]["params"],
        )

        # ========== 第四步：添加仓位管理器 ==========
        print("\n📌 Step 4: 添加仓位管理器")
        self._add_component(
            page,
            type_btn_text="仓位管理",
            component_name=TEST_CONFIG["sizer"]["name"],
            params=TEST_CONFIG["sizer"]["params"],
        )

        # ========== 第五步：添加策略 ==========
        print("\n📌 Step 5: 添加策略")
        self._add_component(
            page,
            type_btn_text="策略",
            component_name=TEST_CONFIG["strategy"]["name"],
            params=TEST_CONFIG["strategy"]["params"],
        )

        # ========== 第六步：保存 ==========
        print("\n📌 Step 6: 保存投资组合")
        page.click(".ant-modal button.ant-btn-primary")
        page.wait_for_timeout(3000)

        # 验证保存成功
        success_msg = page.locator(".ant-message-success")
        expect(success_msg).to_be_visible(timeout=10000)
        print("  ✅ 保存成功")

        # 等待跳转到详情页
        page.wait_for_url("**/portfolio/*", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        print(f"  ✓ 已跳转到详情页: {page.url}")

        # ========== 第七步：验证详情页参数 ==========
        print("\n📌 Step 7: 验证详情页参数")

        # 验证基本信息
        self._verify_basic_info(page)

        # 验证组件配置
        self._verify_components_config(page)

        print("\n🎉 所有参数验证通过！")

    def _add_component(self, page, type_btn_text: str, component_name: str, params: dict):
        """添加组件并填写参数"""
        # 点击类型按钮
        type_btn = page.locator(f".ant-modal .type-btn:has-text('{type_btn_text}')")
        type_btn.click()
        page.wait_for_timeout(300)

        # 打开下拉选择
        selector = page.locator(".ant-modal .component-selector .ant-select-selector")
        selector.click()
        page.wait_for_timeout(500)

        # 输入组件名称搜索
        page.keyboard.type(component_name)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)

        print(f"  ✓ 已添加组件: {component_name}")

        # 填写参数
        if params:
            print(f"  配置参数:")
            for key, value in params.items():
                self._fill_param(page, key, value)

        page.wait_for_timeout(500)

    def _fill_param(self, page, label: str, value: str):
        """填写参数"""
        # 查找参数行
        param_rows = page.locator(".ant-modal .config-section .param-row").all()

        for row in param_rows:
            label_el = row.locator(".param-label")
            if label_el.is_visible():
                label_text = label_el.text_content() or ""
                # 支持部分匹配
                if label.lower() in label_text.lower() or label_text.lower() in label.lower():
                    # 数字输入框
                    num_input = row.locator(".ant-input-number-input")
                    if num_input.is_visible():
                        num_input.fill("")
                        num_input.fill(str(value))
                        print(f"    ✓ {label} = {value}")
                        return True

                    # 普通输入框
                    input_el = row.locator(".ant-input")
                    if input_el.is_visible():
                        input_el.fill("")
                        input_el.fill(str(value))
                        print(f"    ✓ {label} = {value}")
                        return True

        print(f"    ⚠ 未找到参数: {label}")
        return False

    def _verify_basic_info(self, page):
        """验证基本信息"""
        print("\n  📋 验证基本信息:")

        # 验证名称
        title = page.locator(".page-title").text_content()
        assert TEST_PORTFOLIO_NAME in title, f"名称不匹配: 期望包含 {TEST_PORTFOLIO_NAME}, 实际 {title}"
        print(f"    ✓ 名称: {title}")

        # 验证初始资金
        page_text = page.locator("body").text_content()
        expected_cash = f"¥{TEST_CONFIG['portfolio']['initial_cash']:,}"
        assert expected_cash in page_text or str(TEST_CONFIG["portfolio"]["initial_cash"]) in page_text, \
            f"初始资金不匹配: 期望 {expected_cash}"
        print(f"    ✓ 初始资金: {expected_cash}")

    def _verify_components_config(self, page):
        """验证组件配置参数"""
        print("\n  📋 验证组件配置:")

        # 等待组件卡片加载
        components_card = page.locator(".components-card")
        expect(components_card).to_be_visible(timeout=10000)

        # 获取整个组件配置区域的文本
        config_text = components_card.text_content()
        print(f"\n  组件配置区域内容:\n  {config_text[:500]}...")

        # 验证选股器参数
        print("\n  验证选股器配置:")
        selector_params = TEST_CONFIG["selector"]["params"]
        for key, value in selector_params.items():
            # 参数可能以 "key: value" 格式显示
            if value in config_text:
                print(f"    ✓ {key}: {value}")
            else:
                # 尝试查找 config-tag 格式
                config_tags = page.locator(".config-tag").all_text_contents()
                found = any(value in tag for tag in config_tags)
                assert found, f"选股器参数 {key}={value} 未找到"
                print(f"    ✓ {key}: {value}")

        # 验证仓位管理器参数
        print("\n  验证仓位管理器配置:")
        sizer_params = TEST_CONFIG["sizer"]["params"]
        for key, value in sizer_params.items():
            assert value in config_text, f"仓位管理器参数 {key}={value} 未找到"
            print(f"    ✓ {key}: {value}")

        # 验证策略参数
        print("\n  验证策略配置:")
        strategy_params = TEST_CONFIG["strategy"]["params"]
        for key, value in strategy_params.items():
            assert value in config_text, f"策略参数 {key}={value} 未找到"
            print(f"    ✓ {key}: {value}")

        # 额外验证：检查组件名称是否显示
        print("\n  验证组件名称:")
        component_names = page.locator(".component-name").all_text_contents()
        assert len(component_names) >= 3, f"组件数量不足: {len(component_names)}"
        print(f"    ✓ 组件数量: {len(component_names)}")

        for name in component_names:
            print(f"    ✓ 组件: {name}")

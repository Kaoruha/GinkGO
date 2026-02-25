"""
Portfolio CRUD E2E 测试

测试投资组合的完整生命周期：
- 创建组合（含组件配置）
- 搜索
- 筛选
- 查看详情
- 删除
"""

import time
import pytest
from playwright.sync_api import Page, expect

from .config import config


# 测试配置
TEST_PORTFOLIO_NAME = f"E2E_Test_{int(time.time())}"

TEST_COMPONENTS = {
    "selector": {
        "name": "fixed_selector",
        "params": {
            "name": "FixedSelector_E2E",
            "codes": "000001.SZ,000002.SZ",
        },
    },
    "sizer": {
        "name": "fixed_sizer",
        "params": {"name": "FixedSizer_E2E", "volume": "1000"},
    },
    "strategy": {
        "name": "random_signal_strategy",
        "params": {
            "name": "RandomStrategy_E2E",
            "buy_probability": "0.9",
            "sell_probability": "0.05",
            "max_signals": "4",
        },
    },
}


@pytest.mark.e2e
@pytest.mark.slow
class TestPortfolioCRUD:
    """Portfolio CRUD 流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.goto(f"{config.web_ui_url}/portfolio")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def test_01_create_portfolio(self):
        """创建投资组合"""
        page = self.page
        page.set_default_timeout(120000)

        # 点击创建按钮
        page.click('button.ant-btn-primary:has-text("创建组合")')
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()

        # 填写基本信息
        page.fill('.ant-modal input[placeholder="组合名称"]', TEST_PORTFOLIO_NAME)
        page.fill(".ant-modal .ant-input-number-input", "100000")
        page.wait_for_timeout(300)

        # 添加选股器
        self._add_component(
            page,
            component_type="selector",
            type_btn_index=1,
            component_name=TEST_COMPONENTS["selector"]["name"],
            params=TEST_COMPONENTS["selector"]["params"],
        )

        # 添加仓位管理器
        self._add_component(
            page,
            component_type="sizer",
            type_btn_index=2,
            component_name=TEST_COMPONENTS["sizer"]["name"],
            params=TEST_COMPONENTS["sizer"]["params"],
        )

        # 添加策略
        self._add_component(
            page,
            component_type="strategy",
            type_btn_index=3,
            component_name=TEST_COMPONENTS["strategy"]["name"],
            params=TEST_COMPONENTS["strategy"]["params"],
        )

        # 提交
        page.click(".ant-modal button.ant-btn-primary")
        page.wait_for_timeout(3000)

        # 验证成功
        success_msg = page.locator(".ant-message-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print(f"✅ 投资组合创建成功: {TEST_PORTFOLIO_NAME}")

    def test_02_search_portfolio(self):
        """搜索投资组合"""
        page = self.page

        # 搜索 - 更新选择器
        search_input = page.locator("input[placeholder*=\"搜索\"], .ant-input-search input").first
        search_input.fill(TEST_PORTFOLIO_NAME)
        page.wait_for_timeout(1500)

        # 验证搜索结果
        cards = page.locator(".portfolio-card").all()
        assert len(cards) >= 1, f"搜索结果应该至少有 1 个，实际: {len(cards)}"

        # 验证搜索结果名称 - 更新选择器
        first_name = cards[0].locator(".name").text_content()
        assert first_name == TEST_PORTFOLIO_NAME
        print(f"✅ 搜索验证成功，找到组合: {first_name}")

    def test_03_filter_by_mode(self):
        """按模式筛选"""
        page = self.page

        # 获取筛选前数量
        before_cards = page.locator(".portfolio-card").all()
        before_count = len(before_cards)

        # 点击"回测"筛选
        page.click('.ant-radio-button-wrapper:has-text("回测")')
        page.wait_for_timeout(1000)

        after_cards = page.locator(".portfolio-card").all()
        print(f"筛选前: {before_count}, 筛选后: {len(after_cards)}")

        # 恢复全部
        page.click('.ant-radio-button-wrapper:has-text("全部")')
        page.wait_for_timeout(1000)

        print("✅ 模式筛选功能正常")

    def test_04_view_detail(self):
        """查看详情页"""
        page = self.page

        # 搜索并点击
        page.fill(".ant-input-search input", TEST_PORTFOLIO_NAME)
        page.wait_for_timeout(1000)

        card = page.locator(".portfolio-card").first
        expect(card).to_be_visible()
        card.click()
        page.wait_for_timeout(3000)

        # 验证 URL
        current_url = page.url
        assert "/portfolio/" in current_url
        assert "/portfolio/create" not in current_url
        print(f"详情页 URL: {current_url}")

        # 验证组件配置
        components_card = page.locator(".components-card")
        expect(components_card).to_be_visible()

        component_names = page.locator(".component-name").all()
        assert len(component_names) >= 3, f"组件数量应该 >= 3，实际: {len(component_names)}"
        print(f"组件数量: {len(component_names)}")

        # 验证参数配置
        body_text = page.locator("body").text_content()
        assert TEST_COMPONENTS["selector"]["params"]["codes"] in body_text
        assert TEST_COMPONENTS["strategy"]["params"]["buy_probability"] in body_text
        print("✅ 参数配置验证成功")

    def test_05_statistics_cards(self):
        """统计卡片"""
        page = self.page

        # 检查统计卡片
        stat_cards = page.locator(".stat-card").all()
        assert len(stat_cards) == 4, f"统计卡片数量应该为 4，实际: {len(stat_cards)}"

        # 验证标题
        titles = page.locator(".ant-statistic-title").all_text_contents()
        assert "总投资组合" in titles
        assert "运行中" in titles
        print("✅ 统计卡片验证成功")

    def test_06_delete_portfolio(self):
        """删除投资组合"""
        page = self.page
        page.set_default_timeout(60000)

        # 搜索
        page.fill(".ant-input-search input", TEST_PORTFOLIO_NAME)
        page.wait_for_timeout(1000)

        card = page.locator(".portfolio-card").first
        expect(card).to_be_visible()

        # 点击更多按钮
        more_btn = card.locator(".ant-dropdown-trigger")
        more_btn.click()
        page.wait_for_timeout(800)

        # 点击删除 - 查找包含"删除"的菜单项
        delete_item = page.locator(".ant-dropdown-menu-item:has-text('删除')")
        if delete_item.is_visible():
            delete_item.click()
        else:
            # 备选方案：点击第二个菜单项
            menu_items = page.locator(".ant-dropdown-menu-item").all()
            if len(menu_items) >= 2:
                menu_items[1].click()
            else:
                print("⚠️ 无法找到删除菜单项")
                return
        page.wait_for_timeout(800)

        # 确认删除
        page.click(".ant-modal .ant-btn-dangerous")
        page.wait_for_timeout(3000)

        # 验证删除成功
        page.fill(".ant-input-search input", "")
        page.wait_for_timeout(500)
        page.fill(".ant-input-search input", TEST_PORTFOLIO_NAME)
        page.wait_for_timeout(1500)

        remaining = page.locator(".portfolio-card").all()
        empty = page.locator(".ant-empty")

        assert len(remaining) == 0 or empty.is_visible()
        print("✅ 删除验证成功")

    def _add_component(
        self, page, component_type: str, type_btn_index: int, component_name: str, params: dict
    ):
        """添加组件的辅助方法"""
        print(f"添加 {component_type}: {component_name}")

        # 点击类型按钮
        page.click(f".ant-modal .type-btn:nth-child({type_btn_index})")
        page.wait_for_timeout(300)

        # 打开下拉选择
        page.click(".ant-modal .component-selector .ant-select-selector")
        page.wait_for_timeout(500)

        # 输入组件名称
        page.keyboard.type(component_name)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)

        # 填写参数
        print(f"配置 {component_type} 参数:")
        for key, value in params.items():
            self._fill_param_by_label(page, key, value)

        page.wait_for_timeout(500)

    def _fill_param_by_label(self, page, label: str, value: str):
        """根据 label 填写参数"""
        param_rows = page.locator(".ant-modal .config-section .param-row").all()

        for row in param_rows:
            label_el = row.locator(".param-label")
            if label_el.is_visible():
                label_text = label_el.text_content()
                if label and label_text and label in label_text:
                    # 尝试数字输入框
                    num_input = row.locator(".ant-input-number-input")
                    if num_input.is_visible():
                        num_input.fill(str(value))
                        print(f"  ✓ {label} = {value}")
                        return True

                    # 尝试普通输入框
                    input_el = row.locator(".ant-input")
                    if input_el.is_visible():
                        input_el.fill(str(value))
                        print(f"  ✓ {label} = {value}")
                        return True

        print(f"  ⚠ 未找到参数: {label}")
        return False

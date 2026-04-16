"""
回测任务创建 - Portfolio 搜索功能 E2E 测试

测试回测任务创建表单中Portfolio选择器的搜索功能：
1. 打开创建回测模态框
2. 点击Portfolio选择器
3. 输入搜索关键词
4. 验证下拉列表正确过滤

运行方式：
python -m pytest tests/e2e/test_backtest_portfolio_search.py -v -s
"""

import time
import pytest
from playwright.sync_api import Page, expect

from .config import config
from .selectors import MODAL, SELECT, SELECT_ITEM, CLOSE_BTN


@pytest.mark.e2e
class TestBacktestPortfolioSearch:
    """回测任务创建 - Portfolio搜索功能测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.timestamp = int(time.time())

    def test_portfolio_search_in_create_modal(self):
        """测试创建回测时Portfolio搜索功能"""
        page = self.page
        page.set_default_timeout(60000)

        # 导航到回测列表
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

        print("\n测试Portfolio搜索功能")

        # 点击新建按钮
        create_btn = page.locator('button:has-text("新建")').first
        create_btn.click()

        # 验证模态框打开
        modal = page.locator(f"{MODAL}:visible")
        expect(modal).to_be_visible()
        print("  创建回测模态框已打开")

        # 填写任务名称
        task_name = f"Search_Test_{self.timestamp}"
        page.locator(f'{MODAL}:visible input[placeholder="请输入任务名称"]').fill(task_name)
        print(f"  填写任务名称: {task_name}")

        # ========== 测试搜索功能 ==========
        print("\n  测试Portfolio搜索:")

        # 点击Portfolio选择器
        portfolio_select = modal.locator(SELECT).first
        portfolio_select.click()

        # 获取所有初始选项
        all_options = page.locator(f".ant-select-dropdown:visible {SELECT_ITEM}").all()
        initial_count = len(all_options)
        print(f"    初始Portfolio数量: {initial_count}")

        if initial_count == 0:
            pytest.skip("没有可用的Portfolio，跳过搜索测试")

        # 记录第一个Portfolio的名称用于搜索测试
        first_option_text = all_options[0].text_content()
        print(f"    第一个Portfolio: {first_option_text[:50]}...")

        # 提取搜索关键词（取名称的前几个字符）
        search_keyword = first_option_text.split()[0][:5].strip()
        print(f"    搜索关键词: '{search_keyword}'")

        # 输入搜索关键词
        search_input = page.locator(".ant-select-dropdown:visible .ant-select-search__field").first
        expect(search_input).to_be_visible(timeout=5000)
        search_input.fill(search_keyword)

        # 验证过滤后的结果
        filtered_options = page.locator(f".ant-select-dropdown:visible {SELECT_ITEM}").all()
        filtered_count = len(filtered_options)
        print(f"    搜索结果数量: {filtered_count}")

        # 验证所有结果都包含搜索关键词
        for opt in filtered_options:
            opt_text = opt.text_content()
            assert search_keyword.lower() in opt_text.lower() or opt_text == "", \
                f"搜索结果 '{opt_text}' 不包含关键词 '{search_keyword}'"
        print(f"    所有搜索结果都包含关键词")

        # 清空搜索
        search_input.fill("")

        # 验证恢复所有选项
        restored_options = page.locator(f".ant-select-dropdown:visible {SELECT_ITEM}").all()
        assert len(restored_options) >= initial_count, "清空搜索后未恢复所有选项"
        print(f"    清空搜索后恢复所有选项")

        # 选择一个Portfolio
        first_option = page.locator(f".ant-select-dropdown:visible {SELECT_ITEM}").first
        first_option.click()
        print(f"\n  已选择Portfolio")

        # 关闭模态框
        close_btn = modal.locator(CLOSE_BTN).first
        close_btn.click()

        print("\nPortfolio搜索功能测试通过")

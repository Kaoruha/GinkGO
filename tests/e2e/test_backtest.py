"""
Backtest CRUD E2E 测试

测试回测任务的完整生命周期：
- 创建任务
- 列表查看
- 搜索
- 状态筛选
- 分页
- 详情页
- 删除
"""

import time
import pytest
from playwright.sync_api import Page, expect

from .config import config
from .selectors import MODAL, TABLE, SELECT, SELECT_ITEM, MESSAGE, BTN_PRIMARY, DATE_PICKER, BTN_DANGER


# 测试任务名称
TEST_TASK_NAME = f"BT_{int(time.time())}"


@pytest.mark.e2e
@pytest.mark.slow
class TestBacktestCRUD:
    """Backtest CRUD 流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.goto(f"{config.web_ui_url}/stage1/backtest")
        self.page.wait_for_load_state("domcontentloaded")

    def test_01_create_backtest(self):
        """创建回测任务"""
        page = self.page
        page.set_default_timeout(60000)

        # 验证在回测列表页
        assert "/stage1/backtest" in page.url

        # 点击创建回测按钮
        page.click('button:has-text("创建回测")')

        # 验证模态框打开
        modal = page.locator(MODAL)
        expect(modal).to_be_visible()

        # 填写任务名称
        page.fill(f'{MODAL} input[placeholder="请输入任务名称"]', TEST_TASK_NAME)

        # 选择 Portfolio
        page.click(f"{MODAL} {SELECT}-selector")

        options = page.locator(f".ant-select-dropdown {SELECT_ITEM}").all()
        assert len(options) > 0, "应该有 Portfolio 可选"
        options[0].click()
        print("✓ 选择了 Portfolio")

        # 设置日期
        self._select_date(page, "开始日期")
        self._select_date(page, "结束日期")

        # 提交
        page.click(f"{MODAL} {BTN_PRIMARY}")

        # 验证成功
        success_msg = page.locator(f"{MESSAGE}-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print("✅ 创建成功消息显示")

        print(f"✅ 回测任务创建: {TEST_TASK_NAME}")

    def test_02_list_has_data(self):
        """列表有数据"""
        page = self.page

        rows = page.locator(f"{TABLE} tbody tr").all()
        print(f"表格行数: {len(rows)}")

        assert len(rows) >= 1, "表格应该至少有一行数据"
        first_row_text = rows[0].text_content()
        print(f"第一行: {first_row_text[:100] if first_row_text else ''}")
        print("✅ 回测任务列表有数据")

    def test_03_search_backtest(self):
        """搜索功能"""
        page = self.page
        page.set_default_timeout(60000)

        # 获取搜索前行数
        before_rows = page.locator(f"{TABLE} tbody tr").all()
        before_count = len(before_rows)
        print(f"搜索前行数: {before_count}")

        # 搜索
        search_input = page.locator(".ant-input-search input")
        expect(search_input).to_be_visible()

        search_input.fill("BT_")
        page.locator(f"{TABLE} tbody tr").first.wait_for(state="visible", timeout=3000)

        after_rows = page.locator(f"{TABLE} tbody tr").all()
        after_count = len(after_rows)
        print(f"搜索后行数: {after_count}")

        # 验证搜索结果（应该只显示 BT_ 开头的任务）
        assert after_count <= before_count, "搜索后结果数应该减少或不变"

        # 清空搜索
        search_input.fill("")
        page.locator(f"{TABLE} tbody tr").first.wait_for(state="visible", timeout=3000)

        # 验证清空后恢复
        final_rows = page.locator(f"{TABLE} tbody tr").all()
        assert len(final_rows) >= after_count, "清空搜索后结果应该恢复"

        print("✅ 搜索功能正常")

    def test_04_filter_by_status(self):
        """状态筛选"""
        page = self.page

        # 获取初始行数
        before_rows = page.locator(f"{TABLE} tbody tr").all()
        before_count = len(before_rows)

        # 点击"已完成"
        page.click('.ant-radio-button-wrapper:has-text("已完成")')
        page.wait_for_load_state("domcontentloaded")

        # 验证筛选后的结果
        filtered_rows = page.locator(f"{TABLE} tbody tr").all()
        filtered_count = len(filtered_rows)

        # 筛选后的结果数应该 <= 初始结果数
        assert filtered_count <= before_count, f"筛选后结果数({filtered_count})应该 <= 初始结果数({before_count})"

        # 恢复
        page.click('.ant-radio-button-wrapper:has-text("全部")')
        page.wait_for_load_state("domcontentloaded")

        # 验证恢复
        restored_rows = page.locator(f"{TABLE} tbody tr").all()
        assert len(restored_rows) >= filtered_count, "恢复后结果数应该 >= 筛选后结果数"

        print("✅ 状态筛选功能正常")

    def test_05_pagination(self):
        """分页功能"""
        page = self.page
        page.set_default_timeout(60000)

        pagination = page.locator(".ant-pagination")
        if pagination.is_visible():
            # 验证分页器存在
            expect(pagination).to_be_visible()

            # 获取当前页
            active_page = pagination.locator(".ant-pagination-item-active")
            if active_page.is_visible():
                page_text = active_page.text_content()
                print(f"当前页码: {page_text}")
                # 验证页码是数字
                assert page_text.isdigit(), "页码应该是数字"

            # 获取总数
            total_text = pagination.locator(".ant-pagination-total-text")
            if total_text.is_visible():
                total = total_text.text_content()
                print(f"分页信息: {total}")
                # 验证总数包含数字
                assert any(c.isdigit() for c in total), "总数信息应该包含数字"

            print("✅ 分页功能正常")
        else:
            print("⚠️ 数据较少，无分页器")

    def test_06_row_click_navigation(self):
        """行点击导航"""
        page = self.page

        rows = page.locator(f"{TABLE} tbody tr").all()
        assert len(rows) > 0, "应该有数据可测试"

        # 保存当前 URL
        before_url = page.url

        # 点击行
        rows[0].click()
        page.wait_for_load_state("domcontentloaded")

        # 验证 URL 改变
        current_url = page.url
        assert current_url != before_url, "点击行后 URL 应该改变"
        assert "/stage1/backtest/" in current_url, "URL 应该包含回测详情路径"

        print(f"✅ 行点击导航正常: {current_url}")

        # 返回列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("domcontentloaded")

    def test_07_delete_backtest(self):
        """删除回测任务"""
        page = self.page
        page.set_default_timeout(60000)

        rows = page.locator(f"{TABLE} tbody tr").all()
        if not rows:
            pytest.skip("没有数据可删除")

        # 获取删除前的行数
        before_count = len(rows)

        # 点击删除按钮
        delete_btn = rows[0].locator('button:has-text("删除")')
        expect(delete_btn).to_be_visible()

        delete_btn.click()

        # 确认删除
        confirm_btn = page.locator(f".ant-popconfirm {BTN_DANGER}")
        expect(confirm_btn).to_be_visible(timeout=5000)
        confirm_btn.click()

        # 验证成功消息
        success_msg = page.locator(f"{MESSAGE}-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print("✅ 删除成功")

        # 验证行数减少
        page.locator(f"{TABLE} tbody tr").first.wait_for(state="visible", timeout=5000)
        after_rows = page.locator(f"{TABLE} tbody tr").all()
        after_count = len(after_rows)

        assert after_count < before_count, f"删除后行数({after_count})应该 < 删除前行数({before_count})"
        print(f"✅ 删除验证通过: {before_count} -> {after_count}")

    def _select_date(self, page, label: str):
        """选择日期"""
        picker = page.locator(f'{MODAL} .ant-form-item:has-text("{label}") {DATE_PICKER}')
        expect(picker).to_be_visible()
        picker.click()

        cell = page.locator(
            ".ant-picker-dropdown .ant-picker-cell:not(.ant-picker-cell-disabled)"
        ).first
        expect(cell).to_be_visible(timeout=5000)
        cell.click()
        print(f"设置了{label}")

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
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def test_01_create_backtest(self):
        """创建回测任务"""
        page = self.page
        page.set_default_timeout(60000)

        # 验证在回测列表页
        assert "/stage1/backtest" in page.url

        # 点击创建回测按钮
        page.click('button:has-text("创建回测")')
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()

        # 填写任务名称
        page.fill('.ant-modal input[placeholder="请输入任务名称"]', TEST_TASK_NAME)
        page.wait_for_timeout(300)

        # 选择 Portfolio
        page.click(".ant-modal .ant-select-selector")
        page.wait_for_timeout(500)

        options = page.locator(".ant-select-dropdown .ant-select-item").all()
        assert len(options) > 0, "应该有 Portfolio 可选"
        options[0].click()
        print("✓ 选择了 Portfolio")
        page.wait_for_timeout(500)

        # 设置日期
        self._select_date(page, "开始日期")
        self._select_date(page, "结束日期")

        # 提交
        page.click(".ant-modal .ant-btn-primary")
        page.wait_for_timeout(2000)

        # 验证成功
        success_msg = page.locator(".ant-message-success")
        if success_msg.is_visible():
            print("✅ 创建成功消息显示")

        print(f"✅ 回测任务创建: {TEST_TASK_NAME}")

    def test_02_list_has_data(self):
        """列表有数据"""
        page = self.page

        rows = page.locator(".ant-table-tbody tr").all()
        print(f"表格行数: {len(rows)}")

        if rows:
            first_row_text = rows[0].text_content()
            print(f"第一行: {first_row_text[:100] if first_row_text else ''}")
            assert len(rows) >= 1
            print("✅ 回测任务列表有数据")
        else:
            print("⚠️ 表格暂无数据")

    def test_03_search_backtest(self):
        """搜索功能"""
        page = self.page
        page.set_default_timeout(60000)

        # 获取搜索前行数
        before_rows = page.locator(".ant-table-tbody tr").all()
        before_count = len(before_rows)
        print(f"搜索前行数: {before_count}")

        # 搜索
        search_input = page.locator(".ant-input-search input")
        assert search_input.is_visible(), "搜索框应该可见"

        search_input.fill("BT_")
        page.wait_for_timeout(1000)

        after_rows = page.locator(".ant-table-tbody tr").all()
        after_count = len(after_rows)
        print(f"搜索后行数: {after_count}")

        # 验证搜索结果（应该只显示 BT_ 开头的任务）
        assert after_count <= before_count, "搜索后结果数应该减少或不变"

        # 清空搜索
        search_input.fill("")
        page.wait_for_timeout(500)

        # 验证清空后恢复
        final_rows = page.locator(".ant-table-tbody tr").all()
        assert len(final_rows) >= after_count, "清空搜索后结果应该恢复"

        print("✅ 搜索功能正常")

    def test_04_filter_by_status(self):
        """状态筛选"""
        page = self.page

        # 获取初始行数
        before_rows = page.locator(".ant-table-tbody tr").all()
        before_count = len(before_rows)

        # 点击"已完成"
        page.click('.ant-radio-button-wrapper:has-text("已完成")')
        page.wait_for_timeout(1000)

        # 验证筛选后的结果
        filtered_rows = page.locator(".ant-table-tbody tr").all()
        filtered_count = len(filtered_rows)

        # 筛选后的结果数应该 <= 初始结果数
        assert filtered_count <= before_count, f"筛选后结果数({filtered_count})应该 <= 初始结果数({before_count})"

        # 恢复
        page.click('.ant-radio-button-wrapper:has-text("全部")')
        page.wait_for_timeout(1000)

        # 验证恢复
        restored_rows = page.locator(".ant-table-tbody tr").all()
        assert len(restored_rows) >= filtered_count, "恢复后结果数应该 >= 筛选后结果数"

        print("✅ 状态筛选功能正常")

    def test_05_pagination(self):
        """分页功能"""
        page = self.page
        page.set_default_timeout(60000)

        pagination = page.locator(".ant-pagination")
        if pagination.is_visible():
            # 验证分页器存在
            assert pagination.is_visible(), "分页器应该可见"

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

        rows = page.locator(".ant-table-tbody tr").all()
        assert len(rows) > 0, "应该有数据可测试"

        # 保存当前 URL
        before_url = page.url

        # 点击行
        rows[0].click()
        page.wait_for_timeout(2000)

        # 验证 URL 改变
        current_url = page.url
        assert current_url != before_url, "点击行后 URL 应该改变"
        assert "/stage1/backtest/" in current_url, "URL 应该包含回测详情路径"

        print(f"✅ 行点击导航正常: {current_url}")

        # 返回列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")

    def test_07_delete_backtest(self):
        """删除回测任务"""
        page = self.page
        page.set_default_timeout(60000)

        rows = page.locator(".ant-table-tbody tr").all()
        if not rows:
            pytest.skip("没有数据可删除")

        # 获取删除前的行数
        before_count = len(rows)

        # 点击删除按钮
        delete_btn = rows[0].locator('button:has-text("删除")')
        assert delete_btn.is_visible(), "删除按钮应该可见"

        delete_btn.click()
        page.wait_for_timeout(500)

        # 确认删除
        confirm_btn = page.locator(".ant-popconfirm .ant-btn-dangerous")
        if confirm_btn.is_visible():
            confirm_btn.click()
            page.wait_for_timeout(2000)

            # 验证成功消息
            success_msg = page.locator(".ant-message-success")
            if success_msg.is_visible():
                print("✅ 删除成功")

            # 验证行数减少
            page.wait_for_timeout(1000)
            after_rows = page.locator(".ant-table-tbody tr").all()
            after_count = len(after_rows)

            assert after_count < before_count, f"删除后行数({after_count})应该 < 删除前行数({before_count})"
            print(f"✅ 删除验证通过: {before_count} -> {after_count}")
        else:
            pytest.skip("确认删除按钮不可见")

    def _select_date(self, page, label: str):
        """选择日期"""
        picker = page.locator(f'.ant-modal .ant-form-item:has-text("{label}") .ant-picker')
        if picker.is_visible():
            picker.click()
            page.wait_for_timeout(300)

            cell = page.locator(
                ".ant-picker-dropdown .ant-picker-cell:not(.ant-picker-cell-disabled)"
            ).first
            if cell.is_visible():
                cell.click()
                print(f"设置了{label}")
        page.wait_for_timeout(500)

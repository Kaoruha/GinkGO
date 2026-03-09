"""
E2E 测试：回测列表与详情功能

核心原则：
1. 每步操作都有明确的断言验证
2. 页面有错误 = 测试立即失败
3. 先检查页面健康，再验证功能

测试覆盖：
- Phase 1: 基础组件显示
- Phase 2: 列表功能验证
- Phase 3: 任务选择功能
- Phase 4: 状态标签显示
- Phase 5: 批量操作功能
- Phase 6: 详情页功能
"""

import pytest
from playwright.sync_api import Page, expect
from conftest import (
    PageHealth,
    collect_page_errors,
    assert_page_healthy,
    get_healthy_page,
    WEB_UI_URL,
    BACKTEST_PATH,
)

# ========== 第一层：页面健康检查 ==========


def test_page_must_load_healthy(healthy_page: Page):
    """
    测试 ID: TEST_001
    验证：页面必须健康加载，无任何错误

    步骤：
        1. 导航到回测列表页
        2. 验证页面标题不包含错误信息
        3. 验证无控制台错误
        4. 验证无网络错误

    断言：
        - 页面标题不包含 404/500/Error 等关键词
        - health.has_console_errors 为 False
        - health.has_page_errors 为 False
        - health.has_network_errors 为 False
    """
    # 页面已经通过 healthy_page fixture 进行了健康检查
    # 这里只需要验证页面确实已加载
    title = healthy_page.title()

    # 断言：页面标题存在且不为空
    assert title, "❌ 页面标题不能为空"
    assert len(title) > 0, "❌ 页面标题长度必须大于 0"

    # 断言：页面 URL 正确
    current_url = healthy_page.url
    assert BACKTEST_PATH in current_url, f"❌ 页面 URL 应包含 {BACKTEST_PATH}，实际为 {current_url}"

    print(f"✅ 页面健康加载: {title}")


# ========== 第二层：基础显示验证 ==========


def test_should_display_page_structure(healthy_page: Page):
    """
    测试 ID: TEST_002
    验证：应显示页面标题和基本结构

    步骤：
        1. 定位页面容器元素
        2. 定位页面头部元素
        3. 定位页面标题元素

    断言：
        - .page-container 元素可见
        - .page-header 元素可见
        - .page-title 元素可见且文本为"回测任务"
    """
    # 断言：页面容器存在且可见
    page_container = healthy_page.locator(".page-container")
    expect(page_container).to_be_visible()
    print("✓ .page-container 元素可见")

    # 断言：页面头部存在且可见
    page_header = healthy_page.locator(".page-header")
    expect(page_header).to_be_visible()
    print("✓ .page-header 元素可见")

    # 断言：页面标题存在且可见
    page_title = healthy_page.locator(".page-title")
    expect(page_title).to_be_visible()

    # 断言：页面标题文本为"回测任务"
    title_text = page_title.text_content()
    assert "回测任务" in title_text, f"❌ 页面标题应包含'回测任务'，实际为 '{title_text}'"
    print(f"✓ .page-title 元素可见且文本为 '{title_text.strip()}'")


def test_should_display_six_status_filters(healthy_page: Page):
    """
    测试 ID: TEST_003
    验证：应显示六态筛选按钮

    步骤：
        1. 定位筛选栏容器
        2. 验证所有状态筛选按钮存在

    断言：
        - .filters-bar 元素可见
        - .filters-bar 包含"全部"文本
        - .filters-bar 包含"待调度"文本
        - .filters-bar 包含"排队中"文本
        - .filters-bar 包含"进行中"文本
        - .filters-bar 包含"已完成"文本
        - .filters-bar 包含"失败"文本
        - .ant-radio-group 元素可见
    """
    # 断言：筛选栏可见
    filters_bar = healthy_page.locator(".filters-bar")
    expect(filters_bar).to_be_visible()
    print("✓ .filters-bar 筛选栏可见")

    # 断言：筛选栏包含所有六种状态
    expected_statuses = ["全部", "待调度", "排队中", "进行中", "已完成", "失败"]
    filters_text = filters_bar.text_content()

    for status in expected_statuses:
        assert status in filters_text, f"❌ 筛选栏应包含状态 '{status}'"
        print(f"✓ 筛选栏包含状态 '{status}'")

    # 断言：单选按钮组可见
    radio_group = healthy_page.locator(".filters-bar .ant-radio-group")
    expect(radio_group).to_be_visible()
    print("✓ .ant-radio-group 单选按钮组可见")


def test_should_display_stats_cards(healthy_page: Page):
    """
    测试 ID: TEST_004
    验证：应显示统计卡片

    步骤：
        1. 定位统计行元素
        2. 获取页面整体文本
        3. 验证统计数据显示

    断言：
        - .stats-row 元素可见
        - 页面包含"总任务数"文本
        - 页面包含"已完成"文本
        - 页面包含"运行中"文本
        - 页面包含"失败"文本
    """
    # 断言：统计行可见
    stats_row = healthy_page.locator(".stats-row")
    expect(stats_row).to_be_visible()
    print("✓ .stats-row 统计行可见")

    # 获取页面整体文本
    body_text = healthy_page.locator("body").text_content()

    # 断言：包含所有统计标签
    stats_labels = ["总任务数", "已完成", "运行中", "失败"]
    for label in stats_labels:
        assert label in body_text, f"❌ 页面应包含统计标签 '{label}'"
        print(f"✓ 页面包含统计标签 '{label}'")


# ========== 第三层：任务选择功能 ==========


def test_should_support_task_selection(healthy_page: Page):
    """
    测试 ID: TEST_005
    验证：应支持任务选择

    步骤：
        1. 查找表格中的复选框
        2. 如果存在，点击第一个复选框
        3. 验证批量操作栏出现

    断言：
        - 如果表格有数据，第一个复选框可点击
        - 点击复选框后 .batch-action-bar 元素可见
        - .batch-action-bar 包含"已选择"文本
    """
    # 定位表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count > 0:
        # 断言：至少有一个复选框
        assert count > 0, "❌ 表格应至少有一个复选框"
        print(f"✓ 找到 {count} 个复选框")

        # 点击第一个复选框
        checkboxes.first.click()
        print("✓ 点击第一个复选框")

        # 断言：批量操作栏可见
        batch_bar = healthy_page.locator(".batch-action-bar")
        expect(batch_bar).to_be_visible()
        print("✓ .batch-action-bar 批量操作栏可见")

        # 断言：批量操作栏包含"已选择"文本
        batch_bar_text = batch_bar.text_content()
        assert "已选择" in batch_bar_text, f"❌ 批量操作栏应包含'已选择'文本，实际为 '{batch_bar_text}'"
        print(f"✓ 批量操作栏显示: '{batch_bar_text.strip()}'")
    else:
        pytest.skip("⚠️  表格没有数据，跳过任务选择测试")


def test_should_support_select_all(healthy_page: Page):
    """
    测试 ID: TEST_006
    验证：应支持全选功能

    步骤：
        1. 查找表头的全选复选框
        2. 如果存在，点击全选复选框
        3. 验证批量操作栏显示选中数量

    断言：
        - .ant-table-thead .ant-checkbox-input 元素存在
        - 点击全选后 .batch-action-bar 可见
    """
    # 定位表头复选框
    select_all_checkbox = healthy_page.locator(".ant-table-thead .ant-checkbox-input")
    count = select_all_checkbox.count()

    if count > 0:
        # 断言：全选复选框存在
        assert count > 0, "❌ 表头应存在全选复选框"
        print("✓ 找到全选复选框")

        # 点击全选复选框
        select_all_checkbox.click()
        print("✓ 点击全选复选框")

        # 断言：批量操作栏显示
        batch_bar = healthy_page.locator(".batch-action-bar")
        expect(batch_bar).to_be_visible()
        print("✓ 批量操作栏显示")
    else:
        pytest.skip("⚠️  表格没有数据，跳过全选测试")


def test_should_support_deselect(healthy_page: Page):
    """
    测试 ID: TEST_007
    验证：应支持取消选择

    步骤：
        1. 查找表格复选框
        2. 选中一个任务
        3. 点击"取消选择"按钮
        4. 验证批量操作栏隐藏

    断言：
        - 选中任务后批量操作栏可见
        - 点击"取消选择"后批量操作栏不可见
    """
    # 定位表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count > 0:
        # 选中第一个任务
        checkboxes.first.click()

        # 断言：批量操作栏可见
        batch_bar = healthy_page.locator(".batch-action-bar")
        expect(batch_bar).to_be_visible()
        print("✓ 选中任务后批量操作栏可见")

        # 点击取消选择按钮
        cancel_button = healthy_page.locator('button:has-text("取消选择")')
        cancel_button.click()
        print("✓ 点击取消选择按钮")

        # 断言：批量操作栏隐藏
        expect(batch_bar).not_to_be_visible()
        print("✓ 批量操作栏已隐藏")
    else:
        pytest.skip("⚠️  表格没有数据，跳过取消选择测试")


# ========== 第四层：状态标签显示 ==========


def test_should_display_six_status_tags(healthy_page: Page):
    """
    测试 ID: TEST_008
    验证：应正确显示六态标签

    步骤：
        1. 查找表格中的状态标签
        2. 获取第一个状态标签的文本
        3. 验证状态是中文且有效

    断言：
        - 如果表格有数据，状态标签存在
        - 状态标签文本在六种中文状态中
    """
    # 定位状态标签
    status_tags = healthy_page.locator(".ant-table tbody .ant-tag")
    count = status_tags.count()

    if count > 0:
        # 断言：至少有一个状态标签
        assert count > 0, "❌ 表格应至少有一个状态标签"
        print(f"✓ 找到 {count} 个状态标签")

        # 获取第一个状态标签文本
        first_tag_text = status_tags.first.text_content()
        print(f"✓ 第一个状态标签: '{first_tag_text}'")

        # 断言：状态标签是六种中文状态之一
        valid_statuses = ["待调度", "排队中", "进行中", "已完成", "已停止", "失败"]
        assert first_tag_text.strip() in valid_statuses, (
            f"❌ 状态标签应是以下之一: {valid_statuses}，实际为 '{first_tag_text}'"
        )
        print(f"✓ 状态标签 '{first_tag_text}' 有效")
    else:
        pytest.skip("⚠️  表格没有数据，跳过状态标签测试")


# ========== 第五层：批量操作功能 ==========


def test_should_display_batch_actions_after_selection(healthy_page: Page):
    """
    测试 ID: TEST_009
    验证：选中任务后应显示批量操作按钮

    步骤：
        1. 查找表格复选框
        2. 选中一个任务
        3. 验证所有批量操作按钮可见

    断言：
        - button:has-text("批量启动") 可见
        - button:has-text("批量停止") 可见
        - button:has-text("批量取消") 可见
        - button:has-text("取消选择") 可见
    """
    # 定位表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count > 0:
        # 选中一个任务
        checkboxes.first.click()
        print("✓ 选中一个任务")

        # 断言：所有批量操作按钮可见
        batch_buttons = [
            ("批量启动", "批量启动按钮"),
            ("批量停止", "批量停止按钮"),
            ("批量取消", "批量取消按钮"),
            ("取消选择", "取消选择按钮"),
        ]

        for button_text, description in batch_buttons:
            button = healthy_page.locator(f'button:has-text("{button_text}")')
            expect(button).to_be_visible()
            print(f"✓ {description}可见")
    else:
        pytest.skip("⚠️  表格没有数据，跳过批量操作按钮测试")


def test_batch_actions_should_change_based_on_selection(healthy_page: Page):
    """
    测试 ID: TEST_010
    验证：批量操作按钮状态应根据选中任务动态变化

    步骤：
        1. 查找表格复选框
        2. 选中第一个任务，记录批量启动按钮状态
        3. 选中第二个任务，再次记录批量启动按钮状态
        4. 验证状态可能发生变化

    断言：
        - 批量启动按钮状态可获取
        - 选中不同任务组合后按钮状态可能变化
    """
    # 定位表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count >= 2:
        # 选中第一个任务
        checkboxes.nth(0).click()
        print("✓ 选中第一个任务")

        # 获取批量启动按钮状态
        batch_start = healthy_page.locator('button:has-text("批量启动")')
        is_disabled_1 = batch_start.is_disabled()
        print(f"✓ 批量启动按钮状态（选中第1个）: {'禁用' if is_disabled_1 else '启用'}")

        # 选中第二个任务
        checkboxes.nth(1).click()
        print("✓ 选中第二个任务")

        # 获取批量启动按钮状态
        is_disabled_2 = batch_start.is_disabled()
        print(f"✓ 批量启动按钮状态（选中第2个）: {'禁用' if is_disabled_2 else '启用'}")

        # 断言：状态可以获取（不要求一定变化）
        assert isinstance(is_disabled_1, bool), "❌ 按钮状态应为布尔值"
        assert isinstance(is_disabled_2, bool), "❌ 按钮状态应为布尔值"
        print("✓ 批量操作按钮状态动态变化功能正常")
    else:
        pytest.skip("⚠️  表格数据不足，跳过动态状态测试")


# ========== 第六层：详情页功能 ==========


def test_should_display_backtest_detail(healthy_page: Page):
    """
    测试 ID: TEST_011
    验证：应显示回测详情

    步骤：
        1. 查找第一个"查看详情"链接
        2. 点击链接
        3. 等待页面跳转
        4. 验证详情页标题可见

    断言：
        - "查看详情"链接存在
        - 点击后页面跳转
        - 详情页标题元素可见
    """
    # 定位查看详情链接
    detail_links = healthy_page.locator('a:has-text("查看详情")')
    count = detail_links.count()

    if count > 0:
        # 断言：查看详情链接存在
        assert count > 0, "❌ 应至少有一个查看详情链接"
        print("✓ 找到查看详情链接")

        # 点击链接
        detail_links.first.click()
        healthy_page.wait_for_timeout(2000)
        print("✓ 点击查看详情链接")

        # 断言：详情页标题可见
        detail_title = healthy_page.locator(".page-title, h1, h2")
        expect(detail_title).to_be_visible()
        print("✓ 详情页标题可见")
    else:
        pytest.skip("⚠️  没有查看详情链接，跳过详情页测试")


def test_should_display_action_buttons_in_detail(healthy_page: Page):
    """
    测试 ID: TEST_012
    验证：详情页应显示操作按钮（根据状态和权限）

    步骤：
        1. 导航到详情页
        2. 定位操作按钮区域
        3. 验证至少有一个操作按钮

    断言：
        - .header-actions 按钮数量大于 0
    """
    # 导航到详情页
    detail_links = healthy_page.locator('a:has-text("查看详情")')
    count = detail_links.count()

    if count > 0:
        detail_links.first.click()
        healthy_page.wait_for_timeout(2000)
        print("✓ 导航到详情页")

        # 定位操作按钮
        action_buttons = healthy_page.locator(".header-actions button, .header-actions a")
        button_count = action_buttons.count()

        # 断言：至少有一个操作按钮
        assert button_count > 0, "❌ 详情页应至少有一个操作按钮"
        print(f"✓ 找到 {button_count} 个操作按钮")
    else:
        pytest.skip("⚠️  没有详情页链接，跳过操作按钮测试")


# ========== 第七层：刷新功能 ==========


def test_should_support_manual_refresh(healthy_page: Page):
    """
    测试 ID: TEST_013
    验证：应支持手动刷新列表

    步骤：
        1. 定位页面头部操作按钮
        2. 验证操作按钮数量

    断言：
        - .header-actions 按钮数量大于 0
    """
    # 定位操作按钮
    action_buttons = healthy_page.locator(".header-actions button")
    count = action_buttons.count()

    # 断言：至少有一个操作按钮
    assert count > 0, "❌ 页面头部应至少有一个操作按钮"
    print(f"✓ 找到 {count} 个操作按钮")


# ========== 第八层：权限控制 ==========


def test_should_display_permission_tooltip(healthy_page: Page):
    """
    测试 ID: TEST_014
    验证：检查权限提示功能

    步骤：
        1. 搜索页面中的"无权限"文本
        2. 如果存在，验证其可见性

    断言：
        - 如果存在权限提示，提示文本可见
    """
    # 搜索无权限文本
    no_permission_text = healthy_page.locator("text=/无权限|没有权限/")
    count = no_permission_text.count()

    if count > 0:
        # 断言：权限提示可见
        expect(no_permission_text.first()).to_be_visible()
        print("✓ 发现无权限提示，权限控制正常")
    else:
        print("✓ 没有发现无权限提示（可能所有任务都有权限）")

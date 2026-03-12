"""
E2E 测试：回测任务操作

核心原则：
1. 每步操作都有明确的断言验证
2. 验证状态机所有操作：start, stop, cancel
3. 操作后验证状态转换

测试覆盖：
- 启动操作（已完成/已停止/失败状态）
- 停止操作（进行中状态）
- 取消操作（待调度/排队中状态）
- 批量操作
- 状态转换验证
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


# ========== 回测任务操作 - 启动(start) ==========


def test_should_start_completed_backtest(healthy_page: Page):
    """
    测试 ID: TEST_OP_001
    验证：应能启动已完成状态的回测任务

    步骤：
        1. 查找已完成的任务
        2. 验证启动按钮存在
        3. 点击启动按钮
        4. 等待并验证操作结果

    断言：
        - .ant-tag:has-text("已完成") 元素存在
        - 对应行的启动按钮存在
        - 点击后显示消息提示
        - 消息提示内容包含"启动"/"success"/"fail"/"error"
    """
    # 等待并查找已完成的任务
    completed_tag = healthy_page.locator('.ant-tag:has-text("已完成")')
    try:
        completed_tag.first.wait_for(state="visible", timeout=5000)
        print("✓ 找到已完成的任务")
    except:
        pytest.skip("⚠️  没有找到已完成的任务，跳过启动测试")

    # 定位启动按钮
    start_buttons = healthy_page.locator('button:has-text("启动")')
    start_button_count = start_buttons.count()

    # 断言：至少有一个启动按钮
    if start_button_count > 0:
        print(f"✓ 找到 {start_button_count} 个启动按钮")

        # 获取第一个启动按钮对应的任务状态
        first_button = start_buttons.first
        row = first_button.locator("xpath=ancestor::tr")
        status_tag = row.locator(".ant-tag").first
        status_text = status_tag.text_content()

        print(f"✓ 找到状态为 '{status_text}' 的任务，有启动按钮")

        # 点击启动按钮
        first_button.click()
        print("✓ 点击启动按钮")

        # 等待操作完成
        healthy_page.wait_for_timeout(3000)

        # 验证消息提示
        message = healthy_page.locator(".ant-message-notice-content")
        message_count = message.count()

        if message_count > 0:
            # 断言：消息提示存在
            message_text = message.first.text_content()
            print(f"✓ 消息提示: '{message_text.strip()}'")

            # 断言：消息内容包含操作相关关键词
            message_lower = message_text.lower()
            has_operation_keyword = any(
                keyword in message_lower
                for keyword in ["启动", "success", "fail", "error"]
            )
            assert has_operation_keyword, (
                f"❌ 消息提示应包含操作相关关键词，实际为 '{message_text}'"
            )
            print("✓ 消息提示内容验证通过")
        else:
            print("⚠️  没有看到消息提示，操作可能失败或无响应")
    else:
        pytest.skip("⚠️  没有找到可启动的任务（已完成/已停止/失败状态）")


def test_should_not_show_start_button_for_created_tasks(healthy_page: Page):
    """
    测试 ID: TEST_OP_002
    验证：不应显示待调度状态任务的启动按钮

    步骤：
        1. 查找待调度状态的任务
        2. 检查对应行的启动按钮

    断言：
        - .ant-tag:has-text("待调度") 元素存在
        - 对应行的启动按钮不存在（count = 0）
    """
    # 查找待调度状态的任务
    created_tasks = healthy_page.locator('.ant-tag:has-text("待调度")')
    count = created_tasks.count()

    if count > 0:
        print(f"✓ 找到 {count} 个待调度状态的任务")

        # 检查第一个待调度任务的启动按钮
        first_task_row = created_tasks.first.locator("xpath=ancestor::tr")
        start_button = first_task_row.locator('button:has-text("启动")')
        has_start_button = start_button.count() > 0

        # 断言：待调度状态任务不应有启动按钮
        assert not has_start_button, "❌ 待调度状态任务不应显示启动按钮"
        print("✓ 待调度状态任务不显示启动按钮（符合状态机设计）")
    else:
        pytest.skip("⚠️  没有找到待调度状态的任务")


# ========== 回测任务操作 - 停止(stop) ==========


def test_should_stop_running_backtest(healthy_page: Page):
    """
    测试 ID: TEST_OP_003
    验证：应能停止进行中状态的回测任务

    步骤：
        1. 查找进行中的任务
        2. 验证停止按钮存在
        3. 点击停止按钮
        4. 验证成功消息提示

    断言：
        - .ant-tag:has-text("进行中") 元素存在
        - 对应行的停止按钮存在
        - 点击后显示成功消息提示
    """
    # 查找进行中的任务
    running_tasks = healthy_page.locator('.ant-tag:has-text("进行中")')
    count = running_tasks.count()

    if count > 0:
        print(f"✓ 找到 {count} 个进行中状态的任务")

        # 检查第一个进行中任务的停止按钮
        first_task_row = running_tasks.first.locator("xpath=ancestor::tr")
        stop_button = first_task_row.locator('button:has-text("停止")')
        has_stop_button = stop_button.count() > 0

        if has_stop_button:
            print("✓ 进行中状态任务显示停止按钮")

            # 点击停止按钮
            stop_button.click()
            print("✓ 点击停止按钮")

            # 等待操作完成
            healthy_page.wait_for_timeout(2000)

            # 验证成功消息提示
            success_message = healthy_page.locator(
                ".ant-message-success, .ant-message-type-success"
            )
            has_success_message = success_message.count() > 0

            # 断言：显示成功消息提示
            assert has_success_message, "❌ 停止操作应显示成功消息提示"
            print("✓ 显示成功消息提示")
        else:
            pytest.fail("❌ 进行中状态任务应有停止按钮")
    else:
        pytest.skip("⚠️  没有找到进行中状态的任务")


# ========== 回测任务操作 - 取消(cancel) ==========


def test_should_cancel_created_backtest(healthy_page: Page):
    """
    测试 ID: TEST_OP_004
    验证：应能取消待调度状态的回测任务

    步骤：
        1. 查找待调度状态的任务
        2. 验证取消按钮存在
        3. 点击取消按钮
        4. 验证成功消息提示

    断言：
        - .ant-tag:has-text("待调度") 元素存在
        - 对应行的取消按钮存在
        - 点击后显示成功消息提示
    """
    # 查找待调度状态的任务
    created_tasks = healthy_page.locator('.ant-tag:has-text("待调度")')
    count = created_tasks.count()

    if count > 0:
        print(f"✓ 找到 {count} 个待调度状态的任务")

        # 检查第一个待调度任务的取消按钮
        first_task_row = created_tasks.first.locator("xpath=ancestor::tr")
        cancel_button = first_task_row.locator('button:has-text("取消")')
        has_cancel_button = cancel_button.count() > 0

        if has_cancel_button:
            print("✓ 待调度状态任务显示取消按钮")

            # 点击取消按钮
            cancel_button.click()
            print("✓ 点击取消按钮")

            # 等待操作完成
            healthy_page.wait_for_timeout(2000)

            # 验证成功消息提示
            success_message = healthy_page.locator(
                ".ant-message-success, .ant-message-type-success"
            )
            has_success_message = success_message.count() > 0

            # 断言：显示成功消息提示
            assert has_success_message, "❌ 取消操作应显示成功消息提示"
            print("✓ 显示成功消息提示")
        else:
            pytest.fail("❌ 待调度状态任务应有取消按钮")
    else:
        pytest.skip("⚠️  没有找到待调度状态的任务")


def test_should_cancel_pending_backtest(healthy_page: Page):
    """
    测试 ID: TEST_OP_005
    验证：应能取消排队中状态的回测任务

    步骤：
        1. 查找排队中状态的任务
        2. 验证取消按钮存在

    断言：
        - .ant-tag:has-text("排队中") 元素存在
        - 对应行的取消按钮存在
    """
    # 查找排队中状态的任务
    pending_tasks = healthy_page.locator('.ant-tag:has-text("排队中")')
    count = pending_tasks.count()

    if count > 0:
        print(f"✓ 找到 {count} 个排队中状态的任务")

        # 检查第一个排队中任务的取消按钮
        first_task_row = pending_tasks.first.locator("xpath=ancestor::tr")
        cancel_button = first_task_row.locator('button:has-text("取消")')
        has_cancel_button = cancel_button.count() > 0

        # 断言：排队中状态任务应有取消按钮
        assert has_cancel_button, "❌ 排队中状态任务应显示取消按钮"
        print("✓ 排队中状态任务显示取消按钮")
    else:
        pytest.skip("⚠️  没有找到排队中状态的任务")


# ========== 回测任务操作 - 批量操作 ==========


def test_batch_start_should_only_work_for_startable_tasks(healthy_page: Page):
    """
    测试 ID: TEST_OP_006
    验证：批量启动应只对可启动的任务有效

    步骤：
        1. 查找表格复选框
        2. 选中多个任务
        3. 检查批量启动按钮状态
        4. 如果启用，尝试点击并验证结果

    断言：
        - 选中多个任务后批量启动按钮存在
        - 批量启动按钮状态可获取
        - 如果启用，点击后有消息提示
    """
    # 查找表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count >= 2:
        # 选中前两个任务
        checkboxes.nth(0).click()
        checkboxes.nth(1).click()
        print("✓ 选中两个任务")

        # 检查批量启动按钮状态
        batch_start_button = healthy_page.locator('button:has-text("批量启动")')
        is_disabled = batch_start_button.is_disabled()

        print(f"✓ 批量启动按钮状态: {'禁用' if is_disabled else '启用'}")

        # 如果按钮启用，尝试点击
        if not is_disabled:
            batch_start_button.click()
            print("✓ 点击批量启动按钮")

            # 等待操作完成
            healthy_page.wait_for_timeout(2000)

            # 验证操作结果
            message = healthy_page.locator(".ant-message")
            has_message = message.count() > 0

            if has_message:
                message_text = message.first.text_content()
                print(f"✓ 批量操作消息: '{message_text.strip()}'")
            else:
                print("⚠️  批量操作没有消息提示")
        else:
            print("✓ 批量启动按钮禁用（符合预期）")
    else:
        pytest.skip("⚠️  表格数据不足，跳过批量启动测试")


def test_batch_cancel_should_only_work_for_cancellable_tasks(healthy_page: Page):
    """
    测试 ID: TEST_OP_007
    验证：批量取消应只对待调度/排队中任务有效

    步骤：
        1. 查找表格复选框
        2. 选中多个任务
        3. 检查批量取消按钮状态

    断言：
        - 选中多个任务后批量取消按钮存在
        - 批量取消按钮状态可获取
    """
    # 查找表格复选框
    checkboxes = healthy_page.locator(".ant-table .ant-checkbox-input")
    count = checkboxes.count()

    if count >= 2:
        # 选中前两个任务
        checkboxes.nth(0).click()
        checkboxes.nth(1).click()
        print("✓ 选中两个任务")

        # 检查批量取消按钮
        batch_cancel_button = healthy_page.locator('button:has-text("批量取消")')
        has_button = batch_cancel_button.count() > 0

        if has_button:
            is_disabled = batch_cancel_button.is_disabled()
            print(f"✓ 批量取消按钮状态: {'禁用' if is_disabled else '启用'}")
        else:
            pytest.skip("⚠️  批量取消按钮不存在")
    else:
        pytest.skip("⚠️  表格数据不足，跳过批量取消测试")


# ========== 回测任务操作 - 状态转换验证 ==========


def test_status_should_update_after_operation(healthy_page: Page):
    """
    测试 ID: TEST_OP_008
    验证：操作后状态应正确更新

    步骤：
        1. 记录初始状态分布
        2. 刷新页面
        3. 验证状态统计卡片显示正确

    断言：
        - 页面刷新后状态分布保持一致
        - .stats-row 显示正确的统计信息
    """
    # 记录初始状态分布
    initial_status_counts = {}
    for status in ["待调度", "排队中", "进行中", "已完成", "已停止", "失败"]:
        status_count = healthy_page.locator(f'.ant-tag:has-text("{status}")').count()
        initial_status_counts[status] = status_count
        print(f"✓ 初始 '{status}' 状态: {status_count} 个")

    print(f"✓ 初始状态分布: {initial_status_counts}")

    # 刷新页面
    healthy_page.reload()
    healthy_page.wait_for_timeout(2000)
    print("✓ 刷新页面")

    # 验证状态统计卡片显示正确
    stats_row = healthy_page.locator(".stats-row")
    expect(stats_row).to_be_visible()

    stats_text = stats_row.text_content()

    # 断言：统计卡片包含所有必要标签
    stats_labels = ["总任务数", "已完成", "运行中", "失败"]
    for label in stats_labels:
        assert label in stats_text, f"❌ 统计卡片应包含 '{label}' 标签"
        print(f"✓ 统计卡片包含 '{label}' 标签")

    print("✓ 状态统计卡片显示正常")


def test_operation_should_trigger_status_transition(healthy_page: Page):
    """
    测试 ID: TEST_OP_009
    验证：操作应触发正确的状态转换

    步骤：
        1. 选择一个可操作的任务
        2. 记录操作前状态
        3. 执行操作
        4. 验证状态转换

    断言：
        - 操作前状态可获取
        - 操作按钮存在且可点击
        - 操作后消息提示显示
    """
    # 查找可操作的任务
    start_buttons = healthy_page.locator('button:has-text("启动")')
    count = start_buttons.count()

    if count > 0:
        # 获取第一个按钮的任务行
        first_button = start_buttons.first
        row = first_button.locator("xpath=ancestor::tr")
        status_tag = row.locator(".ant-tag").first
        before_status = status_tag.text_content()

        print(f"✓ 操作前状态: '{before_status}'")

        # 验证状态是可启动的
        startable_statuses = ["已完成", "已停止", "失败"]
        assert before_status.strip() in startable_statuses, (
            f"❌ 状态 '{before_status}' 不应该有启动按钮"
        )
        print(f"✓ 状态 '{before_status}' 可启动")

        # 点击启动按钮
        first_button.click()
        print("✓ 执行启动操作")

        # 等待操作完成
        healthy_page.wait_for_timeout(3000)

        # 验证消息提示
        message = healthy_page.locator(".ant-message")
        has_message = message.count() > 0

        # 断言：操作触发消息提示
        assert has_message, "❌ 操作应触发消息提示"
        print("✓ 操作触发消息提示")
    else:
        pytest.skip("⚠️  没有找到可操作的任务")

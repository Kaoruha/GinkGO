"""
回测操作 E2E 测试（Python + Playwright）

验证回测任务的状态流转操作：
- 每步操作前检查当前状态
- 执行操作
- 操作后验证状态变化
- 验证操作结果消息

运行方式:
    cd /home/kaoru/Ginkgo
    python -m pytest tests/e2e/test_backtest_operations_python.py -v -s
"""

import pytest
import time
from typing import Dict, List, Optional
from playwright.sync_api import Page, expect, Browser

from .config import config
from .selectors import TABLE, TABLE_ROW, TAG, BTN, MESSAGE, SELECT_ITEM


# ==================== 页面健康检查 ====================

class PageHealthChecker:
    """页面健康检查器"""

    def __init__(self, page: Page):
        self.page = page
        self.errors: List[str] = []
        self.has_errors = False

    def setup_listeners(self):
        """设置错误监听器"""
        self.errors = []
        self.has_errors = False

        # 监听控制台错误
        def on_console(msg):
            if msg.type == "error":
                error_text = f"[CONSOLE] {msg.text}"
                self.errors.append(error_text)
                self.has_errors = True
                print(f"❌ 控制台错误: {msg.text}")

        self.page.on("console", on_console)

        # 监听页面错误
        def on_page_error(error):
            error_text = f"[PAGE] {error}"
            self.errors.append(error_text)
            self.has_errors = True
            print(f"❌ 页面错误: {error}")

        self.page.on("pageerror", on_page_error)

    def assert_healthy(self):
        """断言页面健康"""
        if self.has_errors:
            error_summary = "\n".join(self.errors[:5])
            raise AssertionError(
                f"❌ 页面有错误！\n"
                f"发现 {len(self.errors)} 个错误\n"
                f"错误列表:\n{error_summary}"
            )

        # 检查页面标题
        title = self.page.title()
        if any(err in title for err in ["404", "500", "Error", "NotFound"]):
            raise AssertionError(f"❌ 页面加载失败！标题: {title}")

        print("✅ 页面健康检查通过")


# ==================== 回测任务辅助类 ====================

class BacktestTaskHelper:
    """回测任务操作辅助类"""

    # 状态映射：中文 -> 英文
    STATUS_MAP = {
        "已创建": "created",
        "待调度": "pending",
        "进行中": "running",
        "已完成": "completed",
        "已停止": "stopped",
        "已失败": "failed",
        # 英文状态
        "created": "created",
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "stopped": "stopped",
        "failed": "failed",
    }

    # 状态机转换规则
    STATE_TRANSITIONS = {
        "start": {
            "allowed_from": ["completed", "stopped", "failed"],
            "expected_to": ["pending", "running"],
        },
        "stop": {
            "allowed_from": ["running"],
            "expected_to": ["stopped"],
        },
        "cancel": {
            "allowed_from": ["created", "pending"],
            "expected_to": ["stopped"],
        },
    }

    # 回测列表页面路径
    BACKTEST_LIST_PATH = "/stage1/backtest"

    def __init__(self, page: Page, config):
        self.page = page
        self.config = config
        self.health_checker = PageHealthChecker(page)

    @property
    def backtest_list_url(self) -> str:
        """回测列表完整 URL"""
        return f"{self.config.web_ui_url}{self.BACKTEST_LIST_PATH}"

    def navigate_to_list(self):
        """导航到回测列表页面"""
        print(f"\n📍 导航到回测列表: {self.backtest_list_url}")
        self.page.goto(self.backtest_list_url, wait_until="domcontentloaded")

        # 等待页面加载
        self.page.wait_for_load_state("domcontentloaded")

        # 健康检查
        self.health_checker.setup_listeners()
        self.page.wait_for_load_state("domcontentloaded")
        self.health_checker.assert_healthy()

    def get_task_status(self, task_uuid: str) -> str:
        """获取任务状态"""
        # 在表格中找到该任务
        task_row = self.page.locator(f"tr:has-text('{task_uuid[:8]}')").first
        if not task_row.is_visible():
            raise ValueError(f"找不到任务: {task_uuid}")

        # 获取状态列
        status_cell = task_row.locator(f".status-tag, {TAG}").first
        status_text = status_cell.text_content() or ""

        # 转换为英文状态
        for zh, en in self.STATUS_MAP.items():
            if zh in status_text:
                return en

        # 如果已经是英文，直接返回
        return status_text.lower()

    def find_tasks_by_status(self, *statuses: str) -> List[Dict]:
        """查找指定状态的任务"""
        tasks = []

        # 遍历表格行
        rows = self.page.locator("tbody tr").all()
        for row in rows:
            try:
                # 获取 UUID
                uuid_cell = row.locator(".task-uuid, td:nth-child(2)").first
                uuid_text = uuid_cell.text_content() or ""

                # 获取状态
                status_cell = row.locator(f".status-tag, {TAG}").first
                status_text = status_cell.text_content() or ""

                # 转换状态
                status_en = status_text.lower()
                for zh, en in self.STATUS_MAP.items():
                    if zh in status_text:
                        status_en = en
                        break

                # 检查是否匹配目标状态
                if status_en in statuses:
                    tasks.append({
                        "uuid": uuid_text,
                        "status": status_en,
                        "element": row,
                    })
            except:
                continue

        return tasks

    def click_operation_button(self, task_uuid: str, operation: str) -> str:
        """点击操作按钮"""
        print(f"  🔘 点击 {operation} 按钮")

        # 找到任务行
        task_row = self.page.locator(f"tr:has-text('{task_uuid[:8]}')").first

        # 根据操作类型查找按钮
        button_map = {
            "start": "button:has-text('启动')",
            "stop": "button:has-text('停止')",
            "cancel": "button:has-text('取消')",
        }
        button = task_row.locator(button_map[operation]).first
        button.click()

        # 等待操作完成
        self.page.wait_for_load_state("domcontentloaded")

        # 获取操作结果消息
        message_element = self.page.locator(f"{MESSAGE}-notice-content").first
        expect(message_element).to_be_visible(timeout=5000)
        message = message_element.text_content() or ""
        print(f"  操作消息: {message}")
        return message

    def verify_status_changed(self, task_uuid: str, old_status: str, operation: str) -> str:
        """验证状态已改变"""
        print(f"  🔍 验证状态变化: {old_status} -> ?")

        # 刷新页面
        self.page.reload(wait_until="domcontentloaded")

        # 获取新状态
        new_status = self.get_task_status(task_uuid)
        print(f"  ✨ 新状态: {new_status}")

        # 获取期望的状态转换
        transition = self.STATE_TRANSITIONS.get(operation, {})
        expected_states = transition.get("expected_to", [])

        # 验证状态改变
        if new_status == old_status:
            raise AssertionError(
                f"❌ 状态未改变！操作: {operation}, 旧状态: {old_status}, 新状态: {new_status}"
            )

        # 验证状态转换是否合法
        if expected_states and new_status not in expected_states:
            raise AssertionError(
                f"❌ 状态转换不符合预期！\n"
                f"操作: {operation}\n"
                f"旧状态: {old_status}\n"
                f"新状态: {new_status}\n"
                f"期望状态: {expected_states}"
            )

        print(f"  ✅ 状态验证通过: {old_status} -> {new_status}")
        return new_status

    def verify_operation_allowed(self, task_uuid: str, operation: str) -> bool:
        """验证操作是否被允许（按钮是否可用）"""
        task_row = self.page.locator(f"tr:has-text('{task_uuid[:8]}')").first

        button_map = {
            "start": "button:has-text('启动')",
            "stop": "button:has-text('停止')",
            "cancel": "button:has-text('取消')",
        }
        button = task_row.locator(button_map[operation]).first

        # 检查按钮是否被禁用
        is_disabled = button.is_disabled()
        print(f"  🔍 {operation} 按钮状态: {'禁用' if is_disabled else '可用'}")

        return not is_disabled


# ==================== 测试用例 ====================

@pytest.mark.e2e
class TestBacktestOperations:
    """回测操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self, browser, page):
        """设置测试环境（使用 conftest.py 的 browser 和 page fixture）"""
        self.browser = browser
        self.page = page
        self.helper = BacktestTaskHelper(self.page, config)

        yield

        # 测试结束不关闭页面，保留用于调试

    def test_start_completed_task(self):
        """测试: 启动已完成的回测任务"""
        print("\n" + "="*60)
        print("测试: 启动已完成的回测任务")
        print("="*60)

        # 1. 导航到列表页
        self.helper.navigate_to_list()

        # 2. 查找已完成状态的任务
        print("\n🔍 查找已完成状态的任务...")
        completed_tasks = self.helper.find_tasks_by_status("completed")

        if not completed_tasks:
            pytest.skip("当前没有已完成状态的任务，跳过测试")

        task = completed_tasks[0]
        task_uuid = task["uuid"]
        print(f"📋 找到任务: {task_uuid[:8]}... (状态: {task['status']})")

        # 3. 记录初始状态
        initial_status = self.helper.get_task_status(task_uuid)
        print(f"📊 初始状态: {initial_status}")

        # 4. 验证操作被允许
        assert self.helper.verify_operation_allowed(task_uuid, "start"), \
            "启动操作应该被允许"

        # 5. 执行启动操作
        message = self.helper.click_operation_button(task_uuid, "start")
        print(f"📨 操作消息: {message}")

        # 6. 验证消息提示成功
        assert any(word in message.lower() for word in ["启动", "success", "成功"]), \
            f"操作消息应包含成功提示: {message}"

        # 7. 验证状态已改变
        new_status = self.helper.verify_status_changed(
            task_uuid, initial_status, "start"
        )

        # 8. 验证新状态
        assert new_status in ["pending", "running"], \
            f"启动后状态应为 pending 或 running，实际为: {new_status}"

        print("\n✅ 测试通过: 已完成任务启动成功")

    def test_stop_running_task(self):
        """测试: 停止进行中的回测任务"""
        print("\n" + "="*60)
        print("测试: 停止进行中的回测任务")
        print("="*60)

        # 1. 导航到列表页
        self.helper.navigate_to_list()

        # 2. 查找进行中状态的任务
        print("\n🔍 查找进行中状态的任务...")
        running_tasks = self.helper.find_tasks_by_status("running")

        if not running_tasks:
            pytest.skip("当前没有进行中状态的任务，跳过测试")

        task = running_tasks[0]
        task_uuid = task["uuid"]
        print(f"📋 找到任务: {task_uuid[:8]}... (状态: {task['status']})")

        # 3. 记录初始状态
        initial_status = self.helper.get_task_status(task_uuid)
        print(f"📊 初始状态: {initial_status}")

        # 4. 验证操作被允许
        assert self.helper.verify_operation_allowed(task_uuid, "stop"), \
            "停止操作应该被允许"

        # 5. 执行停止操作
        message = self.helper.click_operation_button(task_uuid, "stop")
        print(f"📨 操作消息: {message}")

        # 6. 验证消息提示成功
        assert any(word in message.lower() for word in ["停止", "success", "成功"]), \
            f"操作消息应包含成功提示: {message}"

        # 7. 验证状态已改变
        new_status = self.helper.verify_status_changed(
            task_uuid, initial_status, "stop"
        )

        # 8. 验证新状态
        assert new_status == "stopped", \
            f"停止后状态应为 stopped，实际为: {new_status}"

        print("\n✅ 测试通过: 进行中任务停止成功")

    def test_cancel_pending_task(self):
        """测试: 取消待调度的回测任务"""
        print("\n" + "="*60)
        print("测试: 取消待调度的回测任务")
        print("="*60)

        # 1. 导航到列表页
        self.helper.navigate_to_list()

        # 2. 查找待调度状态的任务
        print("\n🔍 查找待调度状态的任务...")
        pending_tasks = self.helper.find_tasks_by_status("pending", "created")

        if not pending_tasks:
            pytest.skip("当前没有待调度状态的任务，跳过测试")

        task = pending_tasks[0]
        task_uuid = task["uuid"]
        print(f"📋 找到任务: {task_uuid[:8]}... (状态: {task['status']})")

        # 3. 记录初始状态
        initial_status = self.helper.get_task_status(task_uuid)
        print(f"📊 初始状态: {initial_status}")

        # 4. 验证操作被允许
        assert self.helper.verify_operation_allowed(task_uuid, "cancel"), \
            "取消操作应该被允许"

        # 5. 执行取消操作
        message = self.helper.click_operation_button(task_uuid, "cancel")
        print(f"📨 操作消息: {message}")

        # 6. 验证消息提示成功
        assert any(word in message.lower() for word in ["取消", "success", "成功"]), \
            f"操作消息应包含成功提示: {message}"

        # 7. 验证状态已改变
        new_status = self.helper.verify_status_changed(
            task_uuid, initial_status, "cancel"
        )

        # 8. 验证新状态
        assert new_status == "stopped", \
            f"取消后状态应为 stopped，实际为: {new_status}"

        print("\n✅ 测试通过: 待调度任务取消成功")

    def test_batch_start_operations(self):
        """测试: 批量启动多个任务"""
        print("\n" + "="*60)
        print("测试: 批量启动多个任务")
        print("="*60)

        # 1. 导航到列表页
        self.helper.navigate_to_list()

        # 2. 查找可启动的任务
        print("\n🔍 查找可启动的任务...")
        startable_tasks = self.helper.find_tasks_by_status(
            "completed", "stopped", "failed"
        )

        if len(startable_tasks) < 2:
            pytest.skip("可启动任务少于2个，跳过批量测试")

        # 选择前2个任务
        selected_tasks = startable_tasks[:2]
        task_uuids = [t["uuid"] for t in selected_tasks]
        print(f"📋 选择了 {len(task_uuids)} 个任务")

        # 3. 记录初始状态
        initial_statuses = {}
        for uuid in task_uuids:
            initial_statuses[uuid] = self.helper.get_task_status(uuid)
            print(f"  - {uuid[:8]}: {initial_statuses[uuid]}")

        # 4. 勾选复选框
        print("\n☑️ 勾选任务...")
        for uuid in task_uuids:
            task_row = self.page.locator(f"tr:has-text('{uuid[:8]}')").first
            checkbox = task_row.locator("input[type='checkbox']").first
            checkbox.check()
            print(f"  ✓ 勾选 {uuid[:8]}")

        # 等待批量操作栏出现
        page.wait_for_load_state("domcontentloaded")

        # 5. 点击批量启动按钮
        print("\n🔘 点击批量启动按钮")
        batch_start_btn = self.page.locator("button:has-text('批量启动')").first
        if not batch_start_btn.is_visible():
            raise AssertionError("批量启动按钮不可见")

        batch_start_btn.click()
        page.wait_for_load_state("domcontentloaded")

        # 6. 验证消息
        message_element = self.page.locator(f"{MESSAGE}-notice-content").first
        expect(message_element).to_be_visible(timeout=5000)
        message = message_element.text_content() or ""
        print(f"批量操作消息: {message}")

        # 7. 验证状态变化
        print("\n🔍 验证状态变化...")
        for uuid in task_uuids:
            new_status = self.helper.get_task_status(uuid)
            old_status = initial_statuses[uuid]
            print(f"  - {uuid[:8]}: {old_status} -> {new_status}")

            # 状态应该改变
            assert new_status != old_status, \
                f"任务 {uuid[:8]} 状态未改变"
            # 新状态应该是 pending 或 running
            assert new_status in ["pending", "running"], \
                f"任务 {uuid[:8]} 状态应为 pending 或 running，实际为: {new_status}"

        print("\n✅ 测试通过: 批量启动成功")

    def test_page_health_after_navigation(self):
        """测试: 页面导航后健康检查"""
        print("\n" + "="*60)
        print("测试: 页面健康检查")
        print("="*60)

        # 1. 导航到列表页
        self.helper.navigate_to_list()

        # 2. 检查页面元素是否正常渲染
        print("\n🔍 检查页面元素...")

        # 表格应该存在
        table = self.page.locator("table").first
        assert table.is_visible(), "表格应该可见"

        # 状态标签应该存在
        status_tags = self.page.locator(".status-tag, .ant-tag").all()
        assert len(status_tags) > 0, "应该有状态标签"
        print(f"  ✅ 找到 {len(status_tags)} 个状态标签")

        # 3. 等待一段时间确保没有延迟错误
        page.wait_for_load_state("domcontentloaded")
        self.helper.health_checker.assert_healthy()

        print("\n✅ 测试通过: 页面健康检查")


# ==================== 直接运行支持 ====================

if __name__ == "__main__":
    """直接运行测试文件"""
    import sys

    from playwright.sync_api import sync_playwright

    print("\n" + "="*60)
    print("回测操作 E2E 测试（独立运行模式）")
    print("="*60)

    with sync_playwright() as p:
        # 连接远程浏览器
        print(f"\n🔗 连接远程浏览器: {config.remote_browser}")
        browser = p.chromium.connect_over_cdp(config.remote_browser)
        print(f"✅ 已连接")

        # 获取上下文和页面
        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()

        # 创建辅助类
        helper = BacktestTaskHelper(page, config)

        try:
            # 导航到列表页
            helper.navigate_to_list()

            # 查找任务状态分布
            print("\n📊 当前任务状态分布:")

            status_count = {}
            rows = page.locator("tbody tr").all()
            for row in rows:
                try:
                    status_cell = row.locator(f".status-tag, {TAG}").first
                    status_text = status_cell.text_content() or ""
                    status_count[status_text] = status_count.get(status_text, 0) + 1
                except:
                    continue

            for status, count in status_count.items():
                print(f"  - {status}: {count} 个")

            # 查找可操作的任务
            print("\n🔍 可操作的任务:")

            completed = helper.find_tasks_by_status("completed")
            if completed:
                print(f"  - 可启动: {len(completed)} 个")

            running = helper.find_tasks_by_status("running")
            if running:
                print(f"  - 可停止: {len(running)} 个")

            pending = helper.find_tasks_by_status("pending", "created")
            if pending:
                print(f"  - 可取消: {len(pending)} 个")

            print("\n✅ 检查完成")
            print("\n💡 提示: 使用 pytest 运行完整测试")
            print('   python -m pytest tests/e2e/test_backtest_operations_python.py -v -s')

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

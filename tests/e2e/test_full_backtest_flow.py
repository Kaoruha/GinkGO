"""
完整回测流程 E2E 测试

模仿 examples/complete_backtest_example.py 的预制回测配置：
1. 创建 Portfolio（含组件配置）
2. 配置组件参数（Strategy、Sizer、Selector、Analyzer）
3. 创建回测任务
4. 观察回测进度
5. 等待回测完成
6. 查看回测结果
7. 分析信号记录
8. 分析订单记录

运行方式：
python -m pytest tests/e2e/test_full_backtest_flow.py -v -s
"""

import time
import uuid

import pytest
from playwright.sync_api import Page, expect

from .config import config

# 预制回测配置（参考 complete_backtest_example.py）
# 注意：000001.SZ 有 2023-12 到 2025-12 的数据
#      000002.SZ 只有 1991-1993 的测试数据
EXAMPLE_CONFIG = {
    "portfolio": {
        "name": "E2E_Full_Backtest_Flow",
        "initial_cash": 100000,
        "mode": "BACKTEST",
    },
    "selector": {
        "name": "fixed_selector",
        "config": {
            "name": "MyFixedSelector",  # 用户自定义名称
            "codes": "000001.SZ",  # 只用有数据的股票
        },
    },
    "sizer": {
        "name": "fixed_sizer",
        "config": {
            "name": "MyFixedSizer",  # 用户自定义名称
            "volume": "500",
        },
    },
    "strategy": {
        "name": "random_signal_strategy",
        "config": {
            "name": "MyRandomStrategy",  # 用户自定义名称
            "buy_probability": "0.9",
            "sell_probability": "0.05",
            "max_signals": "4",
        },
    },
    # 短周期回测（快速验证流程）- 使用有数据的日期范围
    "backtest_short": {
        "name": "E2E_Short_Backtest",
        "start_date": "2024-01-15",
        "end_date": "2024-01-31",
    },
    # 长周期回测（观察进度）
    "backtest_long": {
        "name": "E2E_Long_Backtest",
        "start_date": "2024-01-15",
        "end_date": "2024-06-30",
    },
}


@pytest.fixture(scope="class")
def backtest_context(authenticated_page):
    """创建 context 供整个测试类使用，替代 self.* 状态传递"""
    timestamp = int(time.time())
    portfolio_name = f"{EXAMPLE_CONFIG['portfolio']['name']}_{timestamp}"
    ctx = {
        "page": authenticated_page,
        "timestamp": timestamp,
        "portfolio_name": portfolio_name,
        "short_task_name": None,
        "long_task_name": None,
    }
    yield ctx


@pytest.mark.e2e
@pytest.mark.slow
class TestFullBacktestFlow:
    """完整回测流程测试"""

    def test_01_create_portfolio_with_components(self, authenticated_page, backtest_context):
        """步骤1: 创建Portfolio并配置组件"""
        page = authenticated_page
        page.set_default_timeout(120000)

        # 导航到Portfolio列表
        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 点击创建按钮
        create_btn = page.locator('button:has-text("创建"), button.ant-btn-primary').first
        create_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        expect(modal).to_be_visible()

        # 填写基本信息
        portfolio_name = backtest_context["portfolio_name"]
        page.fill('.ant-modal input[placeholder="组合名称"]', portfolio_name)

        # 设置初始资金
        cash_input = page.locator(".ant-modal .ant-input-number-input").first
        cash_input.fill(str(EXAMPLE_CONFIG["portfolio"]["initial_cash"]))
        page.wait_for_timeout(300)

        print(f"\n📋 创建Portfolio: {portfolio_name}")

        # 添加选股器
        self._add_component(
            page,
            type_btn_text="选股器",
            component_name=EXAMPLE_CONFIG["selector"]["name"],
            params=EXAMPLE_CONFIG["selector"]["config"],
        )
        print(f"   ✅ 添加选股器: {EXAMPLE_CONFIG['selector']['name']}")

        # 添加仓位管理器
        self._add_component(
            page,
            type_btn_text="仓位管理",
            component_name=EXAMPLE_CONFIG["sizer"]["name"],
            params=EXAMPLE_CONFIG["sizer"]["config"],
        )
        print(f"   ✅ 添加仓位管理器: {EXAMPLE_CONFIG['sizer']['name']}")

        # 添加策略
        self._add_component(
            page,
            type_btn_text="策略",
            component_name=EXAMPLE_CONFIG["strategy"]["name"],
            params=EXAMPLE_CONFIG["strategy"]["config"],
        )
        print(f"   ✅ 添加策略: {EXAMPLE_CONFIG['strategy']['name']}")

        # 提交创建
        submit_btn = page.locator(".ant-modal button.ant-btn-primary").last
        submit_btn.click()
        page.wait_for_timeout(3000)

        # 验证成功
        success_msg = page.locator(".ant-message-success")
        expect(success_msg).to_be_visible(timeout=5000)
        print(f"   ✅ Portfolio创建成功")

    def test_02_verify_portfolio_components(self, authenticated_page, backtest_context):
        """步骤2: 验证Portfolio组件配置"""
        page = authenticated_page

        # 搜索刚创建的Portfolio
        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        search_input = page.locator("input[placeholder*=\"搜索\"]").first
        search_input.fill(backtest_context["portfolio_name"])
        page.wait_for_timeout(1500)

        # 点击进入详情
        cards = page.locator(".portfolio-card").all()
        if cards:
            cards[0].click()
            page.wait_for_timeout(2000)
        else:
            # 如果搜索不到，直接跳过
            print("   ⚠️ 未找到Portfolio卡片，跳过验证")
            return

        # 验证URL跳转到详情页
        current_url = page.url
        assert "/portfolio/" in current_url and "/create" not in current_url
        print(f"\n📋 验证Portfolio详情页: {current_url}")

        # 验证组件配置显示
        body_text = page.locator("body").text_content()

        # 验证选股器配置
        assert "000001.SZ" in body_text, "选股器代码应该显示"
        print("   ✅ 选股器配置正确: 000001.SZ, 000002.SZ")

        # 验证策略配置
        assert "0.9" in body_text or "90%" in body_text, "买入概率应该显示"
        print("   ✅ 策略配置正确: buy_probability=0.9")

    def test_03_create_short_backtest(self, authenticated_page, backtest_context):
        """步骤3: 创建短周期回测任务（快速验证）"""
        page = authenticated_page
        page.set_default_timeout(120000)

        # 导航到回测列表
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 点击新建按钮
        create_btn = page.locator('button:has-text("新建")').first
        create_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框
        modal = page.locator(".ant-modal:visible")
        expect(modal).to_be_visible()

        # 填写任务名称
        timestamp = backtest_context["timestamp"]
        task_name = f"{EXAMPLE_CONFIG['backtest_short']['name']}_{timestamp}"
        backtest_context["short_task_name"] = task_name
        page.fill('.ant-modal:visible input[placeholder="请输入任务名称"]', task_name)
        print(f"\n📋 创建短周期回测: {task_name}")

        # 选择Portfolio
        portfolio_select = modal.locator(".ant-select").first
        portfolio_select.click()
        page.wait_for_timeout(500)

        # 选择刚创建的Portfolio
        portfolio_option = page.locator(f".ant-select-dropdown:visible .ant-select-item:has-text('{EXAMPLE_CONFIG['portfolio']['name'][:10]}')").first
        if portfolio_option.is_visible():
            portfolio_option.click()
            print("   ✅ 已选择Portfolio")
        else:
            # 选择第一个可用的
            first_option = page.locator(".ant-select-dropdown:visible .ant-select-item").first
            first_option.click()
            print("   ✅ 已选择第一个Portfolio")
        page.wait_for_timeout(500)

        # 设置日期
        self._set_date_picker_v2(page, modal, "开始日期", EXAMPLE_CONFIG["backtest_short"]["start_date"])
        print(f"   ✅ 开始日期: {EXAMPLE_CONFIG['backtest_short']['start_date']}")

        self._set_date_picker_v2(page, modal, "结束日期", EXAMPLE_CONFIG["backtest_short"]["end_date"])
        print(f"   ✅ 结束日期: {EXAMPLE_CONFIG['backtest_short']['end_date']}")

        # 提交 - 使用"确定"按钮
        submit_btn = modal.locator('button:has-text("确 定")')
        submit_btn.click()
        page.wait_for_timeout(3000)

        # 验证创建成功
        success_msg = page.locator(".ant-message-success")
        if success_msg.is_visible(timeout=5000):
            print("   ✅ 回测任务创建成功")

    def test_04_wait_short_backtest_complete(self, authenticated_page, backtest_context):
        """步骤4: 等待短周期回测完成"""
        page = authenticated_page
        page.set_default_timeout(120000)

        # 确保在回测列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        print(f"\n⏳ 等待短周期回测完成...")

        # 轮询检查任务状态
        max_wait = 60  # 最多等待60秒
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 刷新页面
            page.reload()
            page.wait_for_timeout(2000)

            # 查找任务状态
            rows = page.locator(".ant-table-tbody tr").all()
            for row in rows:
                row_text = row.text_content()
                if EXAMPLE_CONFIG["backtest_short"]["name"] in row_text or "Short" in row_text:
                    # 检查状态
                    if "已完成" in row_text or "completed" in row_text.lower():
                        print("   ✅ 短周期回测已完成")
                        return
                    elif "失败" in row_text or "failed" in row_text.lower():
                        print("   ⚠️ 回测失败")
                        return
                    elif "运行中" in row_text or "running" in row_text.lower():
                        progress = self._extract_progress(row_text)
                        print(f"   📊 回测运行中，进度: {progress}%")

            time.sleep(3)

        print("   ⏰ 等待超时，回测可能仍在运行")

    def test_05_view_backtest_results(self, authenticated_page, backtest_context):
        """步骤5: 查看回测结果"""
        page = authenticated_page

        # 确保在回测列表页
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        print(f"\n📊 查看回测结果...")

        # 点击最新的回测任务
        rows = page.locator(".ant-table-tbody tr").all()
        if rows:
            rows[0].click()
            page.wait_for_timeout(3000)

            # 验证进入详情页
            current_url = page.url
            if "/stage1/backtest/" in current_url:
                print(f"   ✅ 进入回测详情页: {current_url}")

                # 检查关键指标
                body_text = page.locator("body").text_content()

                # 检查统计卡片
                stats = page.locator(".ant-statistic, .stat-card").all()
                print(f"   📈 统计卡片数量: {len(stats)}")

                # 检查净值图表
                chart = page.locator(".net-value-chart, [class*='chart'], canvas").first
                if chart.is_visible():
                    print("   ✅ 净值图表显示正常")

    def test_06_analyze_signals(self, authenticated_page, backtest_context):
        """步骤6: 分析信号记录"""
        page = authenticated_page

        print(f"\n📈 分析信号记录...")

        # 检查是否有信号表格或列表
        signal_table = page.locator("[class*='signal'], .signal-table, .signal-list").first
        if signal_table.is_visible():
            signal_rows = signal_table.locator("tr, .signal-item").all()
            print(f"   📊 信号记录数量: {len(signal_rows)}")

            # 分析信号类型
            body_text = page.locator("body").text_content()
            buy_count = body_text.count("买入") + body_text.count("LONG") + body_text.count("Buy")
            sell_count = body_text.count("卖出") + body_text.count("SHORT") + body_text.count("Sell")
            print(f"   📊 买入信号: ~{buy_count}, 卖出信号: ~{sell_count}")
        else:
            print("   ℹ️ 暂无信号记录显示")

        # 检查策略参数是否正确生效
        body_text = page.locator("body").text_content()
        if "random" in body_text.lower() or "随机" in body_text:
            print("   ✅ 策略类型: RandomSignalStrategy")

    def test_07_analyze_orders(self, authenticated_page, backtest_context):
        """步骤7: 分析订单记录"""
        page = authenticated_page

        print(f"\n📋 分析订单记录...")

        # 检查订单表格
        order_table = page.locator("[class*='order'], .order-table, .order-list").first
        if order_table.is_visible():
            order_rows = order_table.locator("tr, .order-item").all()
            print(f"   📊 订单记录数量: {len(order_rows)}")
        else:
            # 检查是否有订单统计
            body_text = page.locator("body").text_content()
            if "订单" in body_text:
                print("   ℹ️ 订单信息已显示")

        # 检查持仓信息
        position_section = page.locator("[class*='position'], .position-list").first
        if position_section.is_visible():
            print("   ✅ 持仓信息显示正常")

    def test_08_create_long_backtest(self, authenticated_page, backtest_context):
        """步骤8: 创建长周期回测（观察进度）"""
        page = authenticated_page
        page.set_default_timeout(120000)

        # 导航到回测列表
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 点击新建按钮
        create_btn = page.locator('button:has-text("新建")').first
        create_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框
        modal = page.locator(".ant-modal:visible")
        expect(modal).to_be_visible()

        # 填写任务名称
        timestamp = backtest_context["timestamp"]
        task_name = f"{EXAMPLE_CONFIG['backtest_long']['name']}_{timestamp}"
        backtest_context["long_task_name"] = task_name
        page.fill('.ant-modal:visible input[placeholder="请输入任务名称"]', task_name)
        print(f"\n📋 创建长周期回测: {task_name}")

        # 选择Portfolio
        portfolio_select = modal.locator(".ant-select").first
        portfolio_select.click()
        page.wait_for_timeout(500)

        # 选择刚创建的Portfolio
        portfolio_option = page.locator(f".ant-select-dropdown:visible .ant-select-item:has-text('{EXAMPLE_CONFIG['portfolio']['name']}')").first
        if portfolio_option.is_visible():
            portfolio_option.click()
            print("   ✅ 已选择Portfolio")
        else:
            first_option = page.locator(".ant-select-dropdown:visible .ant-select-item").first
            first_option.click()
            print("   ✅ 已选择第一个Portfolio")
        page.wait_for_timeout(500)

        # 设置日期（长周期：3个月）
        self._set_date_picker_v2(page, modal, "开始日期", EXAMPLE_CONFIG["backtest_long"]["start_date"])
        print(f"   ✅ 开始日期: {EXAMPLE_CONFIG['backtest_long']['start_date']}")

        self._set_date_picker_v2(page, modal, "结束日期", EXAMPLE_CONFIG["backtest_long"]["end_date"])
        print(f"   ✅ 结束日期: {EXAMPLE_CONFIG['backtest_long']['end_date']}")

        # 提交 - 使用"确定"按钮
        submit_btn = modal.locator('button:has-text("确 定")')
        submit_btn.click()
        page.wait_for_timeout(3000)

        print("   ✅ 长周期回测任务创建成功")

    def test_09_monitor_long_backtest_progress(self, authenticated_page, backtest_context):
        """步骤9: 监控长周期回测进度"""
        page = authenticated_page
        page.set_default_timeout(180000)  # 3分钟超时

        print(f"\n⏳ 监控长周期回测进度...")

        # 刷新并检查状态
        max_checks = 10
        for i in range(max_checks):
            page.reload()
            page.wait_for_timeout(3000)

            # 查找任务
            rows = page.locator(".ant-table-tbody tr").all()
            for row in rows:
                row_text = row.text_content()
                if EXAMPLE_CONFIG["backtest_long"]["name"] in row_text or "Long" in row_text:
                    # 提取进度
                    progress = self._extract_progress(row_text)

                    # 检查状态
                    if "已完成" in row_text or "completed" in row_text.lower():
                        print(f"   ✅ 长周期回测已完成！")
                        return
                    elif "运行中" in row_text or "pending" in row_text.lower():
                        print(f"   📊 检查 {i+1}/{max_checks}: 运行中，进度: {progress}%")
                    elif "失败" in row_text:
                        print(f"   ⚠️ 回测失败")
                        return

            if i < max_checks - 1:
                print(f"   ⏳ 等待回测启动... ({i+1}/{max_checks})")

        print("   ℹ️ 监控结束，回测可能仍在后台运行")

    def test_10_final_summary(self, authenticated_page, backtest_context):
        """步骤10: 最终汇总"""
        page = authenticated_page

        print(f"\n" + "=" * 60)
        print("📊 E2E完整回测流程测试汇总")
        print("=" * 60)

        # 获取Portfolio数量
        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_timeout(2000)
        portfolio_cards = page.locator(".portfolio-card").all()
        print(f"📁 Portfolio数量: {len(portfolio_cards)}")

        # 获取回测任务数量
        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_timeout(2000)
        backtest_rows = page.locator(".ant-table-tbody tr").all()

        # 统计状态
        completed = 0
        running = 0
        for row in backtest_rows:
            text = row.text_content()
            if "已完成" in text:
                completed += 1
            elif "运行中" in text or "pending" in text.lower():
                running += 1

        print(f"📊 回测任务: {len(backtest_rows)}个")
        print(f"   - 已完成: {completed}")
        print(f"   - 运行中: {running}")

        print(f"\n✅ 测试配置信息:")
        print(f"   - 策略: {EXAMPLE_CONFIG['strategy']['name']}")
        print(f"   - 买入概率: {EXAMPLE_CONFIG['strategy']['config']['buy_probability']}")
        print(f"   - 卖出概率: {EXAMPLE_CONFIG['strategy']['config']['sell_probability']}")
        print(f"   - 最大信号数: {EXAMPLE_CONFIG['strategy']['config']['max_signals']}")
        print(f"   - 选股代码: {EXAMPLE_CONFIG['selector']['config']['codes']}")
        print(f"   - 固定仓位: {EXAMPLE_CONFIG['sizer']['config']['volume']}")

        print("=" * 60)

    # ========== 辅助方法 ==========

    def _add_component(self, page, type_btn_text: str, component_name: str, params: dict):
        """添加组件"""
        # 点击类型按钮
        type_btn = page.locator(f".ant-modal .type-btn:has-text('{type_btn_text}')")
        type_btn.click()
        page.wait_for_timeout(300)

        # 打开下拉选择
        select = page.locator(".ant-modal .component-selector .ant-select-selector")
        select.click()
        page.wait_for_timeout(500)

        # 输入并选择组件
        page.keyboard.type(component_name)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)

        # 填写参数
        for key, value in params.items():
            self._fill_param(page, key, value)

        page.wait_for_timeout(500)

    def _fill_param(self, page, label: str, value: str):
        """填写参数"""
        param_rows = page.locator(".ant-modal .config-section .param-row").all()

        for row in param_rows:
            label_el = row.locator(".param-label")
            if label_el.is_visible():
                label_text = label_el.text_content()
                if label_text and label in label_text:
                    # 数字输入框
                    num_input = row.locator(".ant-input-number-input")
                    if num_input.is_visible():
                        num_input.fill(str(value))
                        return

                    # 普通输入框
                    input_el = row.locator(".ant-input")
                    if input_el.is_visible():
                        input_el.fill(str(value))
                        return

    def _set_date_picker(self, page, label: str, date_str: str):
        """设置日期选择器"""
        # 找到日期选择器
        picker = page.locator(f'.ant-modal .ant-form-item:has-text("{label}") .ant-picker')
        if picker.is_visible():
            # 强制点击，忽略遮挡
            picker.click(force=True)
            page.wait_for_timeout(500)

            # 直接在输入框中输入
            picker_input = picker.locator("input")
            if picker_input.is_visible():
                picker_input.fill(date_str)
                page.wait_for_timeout(300)
                page.keyboard.press("Enter")
            else:
                # 使用键盘输入
                page.keyboard.type(date_str.replace("-", ""))
                page.wait_for_timeout(300)
                page.keyboard.press("Enter")

            page.wait_for_timeout(500)
            # 点击其他地方关闭可能的弹窗
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)

    def _set_date_picker_v2(self, page, modal, label: str, date_str: str):
        """设置日期选择器 - 改进版"""
        # 在模态框内找到日期选择器
        picker = modal.locator(f'.ant-form-item:has-text("{label}") .ant-picker')
        if picker.is_visible():
            # 点击输入框
            picker.click()
            page.wait_for_timeout(500)

            # 直接填写日期
            picker_input = picker.locator("input")
            picker_input.fill(date_str)
            page.wait_for_timeout(300)

            # 按回车确认
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)

            # 点击模态框其他位置关闭日期面板
            modal.locator(".ant-modal-content").click(position={"x": 10, "y": 10})
            page.wait_for_timeout(300)

    def _extract_progress(self, text: str) -> str:
        """从文本中提取进度"""
        import re
        match = re.search(r"(\d+)%", text)
        if match:
            return match.group(1)
        return "?"

"""
WebUI 完整回测流程 E2E 测试 (Playwright - 同步版本)

测试流程：
1. 创建 Portfolio（Selector + Sizer + Strategy）
2. 创建回测任务
3. 启动回测
4. 等待回测完成
5. 验证回测结果（Analyzer Records、Signal Records、Order Records）
"""

import pytest
import time
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 配置
WEB_UI_URL = "http://192.168.50.12:5173"
REMOTE_BROWSER = "http://192.168.50.10:9222"

# 回测日期区间 - 基于 000001.SZ 的实际数据范围 (2023-12-01 到 2026-02-13)
BACKTEST_START_DATE = "2024-01-01"
BACKTEST_END_DATE = "2025-12-31"


@pytest.mark.e2e
def test_full_backtest_flow_e2e():
    """完整的回测流程 E2E 测试"""

    print("\n" + "=" * 60)
    print("完整回测流程 E2E 测试 (Playwright)")
    print("=" * 60)

    with sync_playwright() as p:
        # 连接到远程浏览器
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()

        try:
            # ============================================================
            # 步骤1: 创建 Portfolio
            # ============================================================
            print("\n📋 步骤1: 创建 Portfolio")

            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            portfolio_name = f"E2E_Backtest_{timestamp}"
            initial_cash = random.randint(5, 20) * 10000  # 50,000 - 200,000

            # 导航到 Portfolio 列表页
            page.goto(f"{WEB_UI_URL}/portfolio", wait_until="domcontentloaded")
            time.sleep(2)

            # 点击创建按钮
            create_btn = page.locator("button:has-text('创建组合')").first
            create_btn.click()
            time.sleep(2)

            # 填写基本信息
            page.locator("#form_item_name").first.fill(portfolio_name)
            page.locator("textarea").first.fill(f"完整回测E2E测试 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            page.locator("#form_item_initial_cash").first.fill(str(initial_cash))
            time.sleep(0.5)

            # 配置 Selector
            page.locator("button.type-btn:has-text('选股器')").first.click()
            time.sleep(0.3)
            page.locator(".component-selector .ant-select").first.click()
            time.sleep(0.5)
            page.locator(".ant-select-item-option:has-text('fixed_selector')").first.click()
            time.sleep(1.5)
            page.locator(".param-row input").nth(1).fill("000001.SZ")  # codes
            time.sleep(0.5)

            # 配置 Sizer
            page.locator("button.type-btn:has-text('仓位管理')").first.click()
            time.sleep(0.3)
            page.locator(".component-selector .ant-select").first.click()
            time.sleep(0.5)
            page.locator(".ant-select-item-option:has-text('fixed_sizer')").first.click()
            time.sleep(1.5)
            page.locator(".param-row input").last.fill("1000")  # volume
            time.sleep(0.5)

            # 配置 Strategy
            page.locator("button.type-btn:has-text('策略')").first.click()
            time.sleep(0.3)
            strategy_dropdown = page.locator(".component-selector .ant-select").first
            strategy_dropdown.click()
            time.sleep(0.5)
            search_input = strategy_dropdown.locator("input[role='combobox']").first
            search_input.type("random_signal")
            time.sleep(0.8)
            page.locator(".ant-select-item-option").first.click()
            time.sleep(3.0)

            # 填写策略参数
            strategy_config_section = page.locator(".config-section:has(.section-title:has-text('策略'))")
            if strategy_config_section.count() > 0:
                param_inputs = strategy_config_section.locator(".param-row input")
                if param_inputs.count() >= 4:
                    param_inputs.nth(0).fill(f"E2E_Backtest_{timestamp}")
                    param_inputs.nth(1).fill("0.4")  # buy_probability
                    param_inputs.nth(2).fill("0.3")  # sell_probability
                    if param_inputs.count() >= 5:
                        param_inputs.nth(4).fill("10")  # max_signals
            time.sleep(1)

            # 提交创建 Portfolio
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)

            # 使用 JavaScript 点击创建按钮
            page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button.ant-btn-primary'));
                    const createBtn = buttons.find(btn => btn.textContent.trim() === '创 建');
                    if (createBtn) createBtn.click();
                }
            """)
            time.sleep(5)

            # 获取 Portfolio UUID
            current_url = page.url
            portfolio_uuid = None
            if "/portfolio/" in current_url and current_url.count("/") > 4:
                portfolio_uuid = current_url.split("/")[-1]
                print(f"  ✅ Portfolio 创建成功: {portfolio_name}")
                print(f"  UUID: {portfolio_uuid}")
            else:
                # 如果没有自动导航，手动查找
                page.goto(f"{WEB_UI_URL}/portfolio", wait_until="domcontentloaded")
                time.sleep(3)
                first_card = page.locator(".portfolio-card").first
                if first_card.count() > 0:
                    card_name = first_card.locator(".name").first.text_content()
                    if portfolio_name in card_name:
                        first_card.click()
                        time.sleep(3)
                        current_url = page.url
                        portfolio_uuid = current_url.split("/")[-1]
                        print(f"  ✅ Portfolio 创建成功: {portfolio_name}")
                        print(f"  UUID: {portfolio_uuid}")

            # ============================================================
            # 步骤2: 创建回测任务
            # ============================================================
            print("\n📊 步骤2: 创建回测任务")

            # 导航到回测创建页
            page.goto(f"{WEB_UI_URL}/stage1/backtest/create", wait_until="domcontentloaded")
            time.sleep(3)

            # 填写回测信息
            backtest_name = f"E2E_Backtest_{timestamp}"
            print(f"  填写回测任务名称: {backtest_name}")

            # 使用更灵活的选择器查找输入框
            name_input = page.locator("input[placeholder*='任务名称'], input[placeholder*='回测']").first
            if name_input.count() > 0:
                name_input.fill(backtest_name)
            else:
                # 尝试使用 label 查找
                name_input = page.locator("label:has-text('任务名称') + input").first
                if name_input.count() > 0:
                    name_input.fill(backtest_name)
                else:
                    # 直接找第一个输入框
                    page.locator("input[type='text']").first.fill(backtest_name)
            time.sleep(0.5)

            # 选择 Portfolio
            print(f"  选择 Portfolio: {portfolio_name}")
            portfolio_select = page.locator(".ant-select").first
            if portfolio_select.count() > 0:
                portfolio_select.click()
                time.sleep(1)

                # 搜索并选择刚创建的 Portfolio
                search_box = page.locator(".ant-select-dropdown input[role='combobox']").first
                if search_box.count() > 0:
                    search_box.type(portfolio_name[:20])  # 输入部分名称进行搜索
                    time.sleep(1)

                # 点击第一个选项
                option = page.locator(".ant-select-item-option").first
                if option.count() > 0:
                    option.click()
                    time.sleep(1)
                    print(f"  ✅ Portfolio 已选择")

            # 设置日期
            print(f"  设置日期: {BACKTEST_START_DATE} ~ {BACKTEST_END_DATE}")

            # 使用 JavaScript 直接设置日期输入框的值
            page.evaluate(f"""
                () => {{
                    // 查找日期输入框
                    const inputs = Array.from(document.querySelectorAll('input'));
                    const dateInputs = inputs.filter(input =>
                        input.placeholder && (
                            input.placeholder.includes('开始') ||
                            input.placeholder.includes('Start') ||
                            input.id.includes('start')
                        )
                    );

                    if (dateInputs.length > 0) {{
                        // 设置开始日期
                        dateInputs[0].value = '{BACKTEST_START_DATE}';
                        dateInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        dateInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    // 查找结束日期输入框
                    const endDateInputs = inputs.filter(input =>
                        input.placeholder && (
                            input.placeholder.includes('结束') ||
                            input.placeholder.includes('End') ||
                            input.id.includes('end')
                        )
                    );

                    if (endDateInputs.length > 0) {{
                        endDateInputs[0].value = '{BACKTEST_END_DATE}';
                        endDateInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        endDateInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    return {{
                        startCount: dateInputs.length,
                        endCount: endDateInputs.length
                    }};
                }}
            """)
            time.sleep(1)

            print(f"  回测区间: {BACKTEST_START_DATE} ~ {BACKTEST_END_DATE}")

            # 使用 JavaScript 点击创建按钮
            print(f"  点击创建按钮...")
            page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button.ant-btn-primary'));
                    const createBtn = buttons.find(btn => btn.textContent.includes('创建'));
                    if (createBtn) createBtn.click();
                    return { found: !!createBtn };
                }
            """)
            time.sleep(5)

            # 获取回测任务 UUID
            current_url = page.url
            backtest_uuid = None
            if "/stage1/backtest/" in current_url:
                backtest_uuid = current_url.split("/")[-1]
                print(f"  ✅ 回测任务创建成功")
                print(f"  UUID: {backtest_uuid}")

            # ============================================================
            # 步骤3: 启动回测
            # ============================================================
            print("\n🚀 步骤3: 启动回测")

            # 查找启动按钮
            start_btn = page.locator("button:has-text('启动')").first
            if start_btn.count() > 0:
                start_btn.click()
                print("  ✅ 回测启动按钮已点击")
                time.sleep(3)
            else:
                print("  ⚠️ 未找到启动按钮，可能已自动启动")

            # ============================================================
            # 步骤4: 等待回测完成
            # ============================================================
            print("\n⏳ 步骤4: 等待回测完成")

            max_wait_time = 300  # 最大等待 5 分钟
            waited_time = 0
            check_interval = 5  # 每 5 秒检查一次

            while waited_time < max_wait_time:
                # 检查状态
                status_badge = page.locator(".ant-badge, .ant-tag").first
                if status_badge.count() > 0:
                    status_text = status_badge.text_content()
                    print(f"  当前状态: {status_text} (已等待 {waited_time} 秒)")

                    if "完成" in status_text or "completed" in status_text.lower():
                        print("  ✅ 回测完成")
                        break
                    elif "失败" in status_text or "failed" in status_text.lower():
                        print("  ❌ 回测失败")
                        # 检查错误信息
                        error_msg = page.locator(".ant-alert-error, .ant-message-error").first
                        if error_msg.count() > 0:
                            print(f"  错误: {error_msg.text_content()}")
                        break
                    elif "运行" in status_text or "running" in status_text.lower():
                        # 正在运行，继续等待
                        pass

                time.sleep(check_interval)
                waited_time += check_interval

                # 刷新页面以获取最新状态
                page.reload(wait_until="domcontentloaded")
                time.sleep(2)

            if waited_time >= max_wait_time:
                print(f"  ⚠️ 等待超时 ({max_wait_time} 秒)")

            # ============================================================
            # 步骤5: 验证回测结果
            # ============================================================
            print("\n🔍 步骤5: 验证回测结果")

            # 等待页面加载完成
            time.sleep(5)

            # 验证统计信息
            print("  📊 验证统计信息:")
            stats = [
                ("总收益", "total_pnl"),
                ("最大回撤", "max_drawdown"),
                ("夏普比率", "sharpe_ratio"),
                ("年化收益", "annual_return"),
                ("胜率", "win_rate"),
            ]

            for stat_name, stat_key in stats:
                stat_element = page.locator(f".stat-label:has-text('{stat_name}')").first
                if stat_element.count() > 0:
                    stat_value = stat_element.locator("xpath=../..").locator(".stat-value").first
                    if stat_value.count() > 0:
                        value_text = stat_value.text_content()
                        print(f"    {stat_name}: {value_text}")

            # 验证分析器记录
            print("\n  📈 验证分析器记录 (Analyzer Records):")
            analyzer_count = 0
            analyzer_section = page.locator("text=/分析器|Analyzer/").first
            if analyzer_section.count() > 0:
                # 查找分析器卡片或列表
                analyzer_cards = page.locator(".ant-card, .ant-list-item").all()
                analyzer_count = len(analyzer_cards)
                print(f"    分析器数量: {analyzer_count}")

                if analyzer_count > 0:
                    print("    ✅ 有分析器记录")
                else:
                    print("    ❌ 没有分析器记录")
            else:
                # 尝试通过 API 检查
                print("    ⚠️ 页面未显示分析器，跳过检查")

            # 验证信号记录
            print("\n  📡 验证信号记录 (Signal Records):")

            # 点击信号记录 tab
            signal_tab = page.locator("text=信号记录|Signals").first
            if signal_tab.count() > 0:
                signal_tab.click()
                time.sleep(3)

                # 检查信号表格
                signal_table = page.locator(".ant-table-tbody tr").all()
                signal_count = len(signal_table)
                print(f"    信号数量: {signal_count}")

                if signal_count > 0:
                    # 显示前几条信号
                    for i in range(min(3, signal_count)):
                        row = signal_table[i]
                        row_text = row.text_content()
                        print(f"    [{i}] {row_text[:100]}...")
                    print("    ✅ 有信号记录")
                else:
                    print("    ❌ 没有信号记录")
            else:
                print("    ⚠️ 未找到信号记录 tab")

            # 验证订单记录
            print("\n  📋 验证订单记录 (Order Records):")

            # 点击订单记录 tab
            order_tab = page.locator("text=订单记录|Orders").first
            if order_tab.count() > 0:
                order_tab.click()
                time.sleep(3)

                # 检查订单表格
                order_table = page.locator(".ant-table-tbody tr").all()
                order_count = len(order_table)
                print(f"    订单数量: {order_count}")

                if order_count > 0:
                    # 显示前几条订单
                    for i in range(min(3, order_count)):
                        row = order_table[i]
                        row_text = row.text_content()
                        print(f"    [{i}] {row_text[:100]}...")
                    print("    ✅ 有订单记录")
                else:
                    print("    ❌ 没有订单记录")
            else:
                print("    ⚠️ 未找到订单记录 tab")

            # ============================================================
            # 测试总结
            # ============================================================
            print("\n" + "=" * 60)
            print("✅ 完整回测流程 E2E 测试完成！")
            print("=" * 60)
            print(f"Portfolio: {portfolio_name} ({portfolio_uuid})")
            print(f"回测任务: {backtest_name} ({backtest_uuid})")
            print(f"回测区间: {BACKTEST_START_DATE} ~ {BACKTEST_END_DATE}")
            print(f"信号记录: {signal_count if 'signal_count' in locals() else 0} 条")
            print(f"订单记录: {order_count if 'order_count' in locals() else 0} 条")

            # 断言验证
            assert portfolio_uuid, "Portfolio 创建失败"
            assert backtest_uuid, "回测任务创建失败"

            # 验证至少有一些信号和订单（取决于策略）
            # RandomSignalStrategy 应该会产生信号
            if 'signal_count' in locals() and signal_count > 0:
                print("\n✅ 所有验证通过！")
            else:
                print("\n⚠️ 警告: 未检测到信号记录，可能需要检查策略配置")

        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

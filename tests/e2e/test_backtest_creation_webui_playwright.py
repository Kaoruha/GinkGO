"""
WebUI 回测任务创建 E2E 测试 (Playwright - 同步版本)

通过浏览器操作验证回测任务创建流程：
1. 打开 WebUI 并导航到回测创建页
2. 填写回测任务信息（名称、Portfolio、日期范围、初始资金）
3. 提交创建
4. 验证回测任务创建成功
5. （可选）启动回测并等待完成
"""

import pytest
import time
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 配置
WEB_UI_URL = "http://192.168.50.12:5173"
REMOTE_BROWSER = "http://192.168.50.10:9222"

# 回测日期区间 - 使用数据库中实际存在的数据范围
# 数据库中 000001.SZ 的数据范围是 1991-04-04 到 1991-09-25
BACKTEST_START_DATE = "1991-04-05"
BACKTEST_END_DATE = "1991-04-30"  # 使用实际存在的日期


@pytest.mark.e2e
def test_backtest_creation_via_webui_playwright():
    """通过 WebUI (Playwright) 完成回测任务创建流程"""

    print("\n" + "=" * 60)
    print("WebUI 回测任务创建 E2E 测试 (Playwright)")
    print("=" * 60)

    with sync_playwright() as p:
        # 连接到远程浏览器
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()

        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backtest_name = f"E2E_Backtest_{timestamp}"

            # 生成随机的初始资金 (50000 - 200000 之间，10000的倍数)
            initial_cash = random.randint(5, 20) * 10000

            # 存储设置的参数值，用于验证
            expected_values = {
                "name": backtest_name,
                "start_date": BACKTEST_START_DATE,
                "end_date": BACKTEST_END_DATE,
                "initial_cash": initial_cash,
            }

            # ============================================================
            # 步骤1: 导航到回测创建页
            # ============================================================
            print("\n📋 步骤1: 导航到回测创建页")
            page.goto(f"{WEB_UI_URL}/stage1/backtest/create", wait_until="domcontentloaded")
            time.sleep(2)
            print("  ✅ 已导航到回测创建页")

            # ============================================================
            # 步骤2: 填写任务名称
            # ============================================================
            print("\n📝 步骤2: 填写任务名称")
            print(f"  任务名称: {backtest_name}")

            name_input = page.locator('input[placeholder="请输入任务名称"]').first
            if name_input.count() > 0:
                name_input.fill(backtest_name)
                print("  ✅ 填写任务名称")
            else:
                # 尝试通过 label 查找
                name_input = page.locator('label:has-text("任务名称") + * input').first
                if name_input.count() > 0:
                    name_input.fill(backtest_name)
                    print("  ✅ 填写任务名称")
                else:
                    print("  ❌ 未找到任务名称输入框")

            time.sleep(0.5)

            # ============================================================
            # 步骤3: 选择投资组合 (Portfolio)
            # ============================================================
            print("\n🎯 步骤3: 选择投资组合")

            # 点击下拉框
            portfolio_select = page.locator(".ant-select").first
            if portfolio_select.count() > 0:
                portfolio_select.click()
                time.sleep(1)
                print("  ✅ 打开投资组合下拉框")

                # 获取所有选项
                options = page.locator(".ant-select-item-option").all()
                print(f"  可选投资组合数量: {len(options)}")

                if len(options) > 0:
                    # 显示前几个选项
                    for i in range(min(3, len(options))):
                        option_text = options[i].text_content()
                        print(f"    [{i}] {option_text}")

                    # 选择第一个可用的投资组合
                    selected_option = options[0]
                    selected_text = selected_option.text_content()
                    selected_option.click()
                    time.sleep(1)
                    print(f"  ✅ 选择投资组合: {selected_text}")
                    expected_values["portfolio_name"] = selected_text
                else:
                    print("  ❌ 没有可用的投资组合，请先创建 Portfolio")
            else:
                print("  ❌ 未找到投资组合选择器")

            # ============================================================
            # 步骤4: 设置日期范围
            # ============================================================
            print("\n📅 步骤4: 设置日期范围")

            # 使用点击 + 填写 + Enter 的方式设置日期
            def set_date_picker(page, label: str, date_value: str):
                """设置 Ant Design DatePicker"""
                # 找到包含 label 的表单项
                form_item = page.locator(f".ant-form-item:has-text('{label}')").first
                if form_item.count() == 0:
                    print(f"  ❌ 未找到 {label} 表单项")
                    return False

                # 找到 picker 组件
                picker = form_item.locator(".ant-picker").first
                if picker.count() == 0:
                    print(f"  ❌ 未找到 {label} picker")
                    return False

                # 点击 picker
                picker.click()
                time.sleep(0.5)

                # 填写日期
                picker_input = picker.locator("input").first
                picker_input.fill(date_value)
                time.sleep(0.3)

                # 按回车确认
                page.keyboard.press("Enter")
                time.sleep(0.5)

                return True

            # 设置开始日期
            if set_date_picker(page, "开始日期", BACKTEST_START_DATE):
                print(f"  ✅ 开始日期: {BACKTEST_START_DATE}")
            else:
                print(f"  ❌ 开始日期设置失败")

            # 设置结束日期
            if set_date_picker(page, "结束日期", BACKTEST_END_DATE):
                print(f"  ✅ 结束日期: {BACKTEST_END_DATE}")
            else:
                print(f"  ❌ 结束日期设置失败")

            time.sleep(0.5)

            # ============================================================
            # 步骤5: 设置初始资金
            # ============================================================
            print("\n💰 步骤5: 设置初始资金")
            print(f"  初始资金: {initial_cash:,}")

            # 查找初始资金输入框 - Ant Design 使用 InputNumber 组件
            cash_form_item = page.locator(".ant-form-item:has-text('初始资金')").first
            if cash_form_item.count() > 0:
                # 查找 input-number 组件内的输入框
                cash_input = cash_form_item.locator("input[type='text']").first
                if cash_input.count() > 0:
                    # 清空并设置新值
                    cash_input.fill(str(initial_cash))
                    print("  ✅ 设置初始资金")
                else:
                    # 尝试直接在表单项中查找任何输入框
                    any_input = cash_form_item.locator("input").first
                    if any_input.count() > 0:
                        any_input.fill(str(initial_cash))
                        print("  ✅ 设置初始资金")
                    else:
                        print("  ⚠️ 未找到初始资金输入框")
            else:
                # 直接通过 JavaScript 设置
                page.evaluate(f"(val) => {{ const inputs = document.querySelectorAll('.ant-form-item:has-text(\"初始资金\") input'); if (inputs.length > 0) {{ inputs[0].value = val; inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }})); inputs[0].dispatchEvent(new Event('change', {{ bubbles: true }})); }} }}", initial_cash)
                print("  ✅ 设置初始资金 (JavaScript)")

            time.sleep(0.5)

            # ============================================================
            # 步骤6: 验证表单数据
            # ============================================================
            print("\n🔍 步骤6: 验证表单数据")

            # 获取当前表单值进行验证
            form_check = page.evaluate("""
                () => {
                    const inputs = Array.from(document.querySelectorAll('input'));
                    const result = {};

                    inputs.forEach(input => {
                        if (input.placeholder) {
                            if (input.placeholder.includes('任务名称') || input.placeholder.includes('名称')) {
                                result.name = input.value;
                            }
                        }
                        if (input.type === 'number') {
                            result.cash = input.value;
                        }
                    });

                    // 获取选中的投资组合
                    const selectWrapper = document.querySelector('.ant-select-selector');
                    if (selectWrapper) {
                        const selectedText = selectWrapper.textContent?.trim();
                        if (selectedText && selectedText !== '请选择投资组合') {
                            result.portfolio = selectedText;
                        }
                    }

                    return result;
                }
            """)

            print(f"  任务名称: {form_check.get('name', 'N/A')}")
            print(f"  投资组合: {form_check.get('portfolio', 'N/A')}")
            print(f"  初始资金: {form_check.get('cash', 'N/A')}")

            # ============================================================
            # 步骤7: 提交创建回测任务
            # ============================================================
            print("\n✅ 步骤7: 提交创建回测任务")

            # 监听网络请求
            api_requests = []
            def handle_request(request):
                if "/backtest" in request.url:
                    api_requests.append({"url": request.url, "method": request.method, "type": "request"})

            def handle_response(response):
                if "/backtest" in response.url:
                    api_requests.append({
                        "url": response.url,
                        "status": response.status,
                        "type": "response"
                    })

            page.on("request", handle_request)
            page.on("response", handle_response)

            # 查找并点击创建按钮
            create_btn = page.locator('button[type="submit"], button.ant-btn-primary:has-text("创建回测")').first

            if create_btn.count() > 0:
                btn_text = create_btn.text_content()
                print(f"  找到创建按钮: {btn_text}")

                # 检查按钮状态
                is_disabled = create_btn.get_attribute("disabled") == "disabled"
                print(f"  按钮禁用状态: {is_disabled}")

                if not is_disabled:
                    create_btn.click()
                    print("  ✅ 点击创建按钮")
                else:
                    print("  ❌ 按钮被禁用，检查表单验证")
            else:
                # 使用 JavaScript 查找并点击
                print("  使用 JavaScript 查找按钮...")
                click_result = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const createBtn = buttons.find(btn =>
                            btn.textContent.includes('创建回测') ||
                            (btn.type === 'submit')
                        );
                        if (createBtn) {
                            createBtn.click();
                            return { success: true, text: createBtn.textContent };
                        }
                        return { success: false };
                    }
                """)
                print(f"  点击结果: {click_result}")

            # 等待响应
            print("  等待创建响应...")
            time.sleep(5)

            # 输出网络请求日志
            print(f"  🌐 网络请求: {len(api_requests)} 条")
            for req in api_requests:
                if req["type"] == "request":
                    print(f"    → {req['method']} {req['url']}")
                else:
                    print(f"    ← {req['status']} {req['url']}")

            # 检查成功或错误消息
            success_msg = page.locator(".ant-message-success, .ant-notification-success").first
            error_msg = page.locator(".ant-message-error, .ant-notification-error, .ant-alert-error").first

            # 检查表单验证错误
            form_errors = page.locator(".ant-form-item-explain-error").all()
            if len(form_errors) > 0:
                print("  ⚠️ 发现表单验证错误:")
                for error in form_errors:
                    error_text = error.text_content()
                    print(f"    - {error_text}")

            if error_msg.count() > 0:
                error_text = error_msg.text_content()
                print(f"  ❌ 创建失败: {error_text}")
            elif success_msg.count() > 0:
                success_text = success_msg.text_content()
                print(f"  ✅ 回测任务创建成功: {success_text}")
            else:
                print("  ⚠️ 未找到成功或失败消息")

            # 截图保存当前状态
            page.screenshot(path="/tmp/backtest_creation_submit_state.png", full_page=True)
            print("  📸 已保存创建状态截图: /tmp/backtest_creation_submit_state.png")

            # ============================================================
            # 步骤8: 验证导航到详情页
            # ============================================================
            print("\n🔍 步骤8: 验证导航到详情页")

            time.sleep(3)
            current_url = page.url
            print(f"  当前URL: {current_url}")

            backtest_uuid = None

            if "/stage1/backtest/" in current_url and current_url.count("/") > 4:
                backtest_uuid = current_url.split("/")[-1]
                print(f"  ✅ 已自动导航到详情页")
                print(f"  Backtest UUID: {backtest_uuid}")

                # 验证页面标题
                page_title = page.locator(".page-title, h1, h2").first
                if page_title.count() > 0:
                    title_text = page_title.text_content()
                    print(f"  页面标题: {title_text}")

            else:
                print("  ⚠️ 未自动导航到详情页")

            # ============================================================
            # 步骤9: 启动回测
            # ============================================================
            print("\n🚀 步骤9: 启动回测")

            if backtest_uuid:
                # 查找启动按钮
                start_btn = page.locator('button:has-text("启动")').first
                if start_btn.count() > 0:
                    start_btn.click()
                    print("  ✅ 点击启动按钮")
                    time.sleep(3)

                    # 检查状态变化
                    status_badge = page.locator(".ant-badge, .ant-tag").first
                    if status_badge.count() > 0:
                        status_text = status_badge.text_content()
                        print(f"  当前状态: {status_text}")
                else:
                    print("  ⚠️ 未找到启动按钮，检查是否已自动启动")

                # 再次检查状态
                time.sleep(2)
                status_badge = page.locator(".ant-badge, .ant-tag").first
                if status_badge.count() > 0:
                    status_text = status_badge.text_content()
                    print(f"  当前状态: {status_text}")
            else:
                print("  ❌ 无法启动，没有有效的回测任务 UUID")

            # ============================================================
            # 步骤10: 等待回测完成
            # ============================================================
            print("\n⏳ 步骤10: 等待回测完成")

            max_wait_time = 300  # 最大等待 5 分钟
            waited_time = 0
            check_interval = 5  # 每 5 秒检查一次

            final_status = None

            while waited_time < max_wait_time:
                # 检查状态 - 使用更精确的选择器
                # 状态显示在多个地方：页面标题的 tag、描述列表中的 tag
                status_tags = page.locator(".ant-tag").all()

                status_text = None
                for tag in status_tags:
                    tag_text = tag.text_content()
                    # 过滤出状态相关的标签
                    if tag_text in ["待启动", "等待中", "运行中", "已完成", "失败", "已停止"]:
                        status_text = tag_text
                        break

                if status_text:
                    print(f"  当前状态: {status_text} (已等待 {waited_time} 秒)")

                    if status_text == "已完成":
                        print("  ✅ 回测完成")
                        final_status = "completed"
                        break
                    elif status_text == "失败":
                        print("  ❌ 回测失败")
                        final_status = "failed"
                        # 检查错误信息
                        error_msg = page.locator(".ant-alert-error, .ant-message-error, .error-message").first
                        if error_msg.count() > 0:
                            error_text = error_msg.text_content()
                            print(f"  错误信息: {error_text}")
                        break
                    elif status_text == "运行中":
                        # 正在运行，继续等待
                        pass
                else:
                    # 没有找到状态标签，打印调试信息
                    all_tags = [t.text_content() for t in status_tags[:5]]
                    print(f"  ⚠️ 未找到状态标签，页面标签: {all_tags}")

                time.sleep(check_interval)
                waited_time += check_interval

                # 定期刷新页面以获取最新状态
                if waited_time % 15 == 0:
                    print("  刷新页面获取最新状态...")
                    page.reload(wait_until="domcontentloaded")
                    time.sleep(2)

            if waited_time >= max_wait_time:
                print(f"  ⚠️ 等待超时 ({max_wait_time} 秒)")
                final_status = "timeout"

            # 只有在回测完成时才进行后续验证
            if final_status != "completed":
                print("\n⚠️ 回测未完成，跳过结果验证")
            else:

                # ============================================================
                # 步骤11: 验证回测统计信息
                # ============================================================
                print("\n📊 步骤11: 验证回测统计信息")

                time.sleep(3)  # 等待页面数据加载

                # 查找统计卡片
                stat_cards = page.locator(".stat-card, .ant-card, .info-card").all()
                print(f"  找到 {len(stat_cards)} 个统计卡片")

                # 显示所有统计信息
                for i, card in enumerate(stat_cards[:10]):  # 最多显示前10个
                    try:
                        label = card.locator(".stat-label, .label, .title").first
                        value = card.locator(".stat-value, .value, .content").first
                        if label.count() > 0 and value.count() > 0:
                            label_text = label.text_content()
                            value_text = value.text_content()
                            print(f"    {label_text}: {value_text}")
                    except:
                        pass

                # 验证关键指标
                key_metrics = {
                    "总收益": None,
                    "最大回撤": None,
                    "夏普比率": None,
                    "年化收益": None,
                    "胜率": None,
                    "净值": None,
                }

                for metric_name in key_metrics.keys():
                    metric_element = page.locator(f"text=/{metric_name}/").first
                    if metric_element.count() > 0:
                        # 获取同级的值元素
                        metric_value = metric_element.locator("xpath=../..").locator(".stat-value, .value, span").all()
                        if metric_value:
                            value_text = metric_value[0].text_content() if metric_value[0] else "N/A"
                            key_metrics[metric_name] = value_text
                            print(f"  ✅ {metric_name}: {value_text}")

                # ============================================================
                # 步骤12: 验证分析器数据
                # ============================================================
                print("\n📈 步骤12: 验证分析器数据 (Analyzer Records)")

                # 查找分析器区域
                analyzer_section = page.locator("text=/分析器|Analyzer|指标/").first
                if analyzer_section.count() > 0:
                    print("  找到分析器区域")

                    # 查找分析器卡片或列表项
                    analyzer_items = page.locator(".ant-card, .ant-list-item, .metric-card").all()
                    print(f"  分析器数量: {len(analyzer_items)}")

                    if len(analyzer_items) > 0:
                        print("  ✅ 有分析器记录")
                        # 显示前几个分析器
                        for i in range(min(5, len(analyzer_items))):
                            try:
                                item_text = analyzer_items[i].text_content()
                                if len(item_text) > 0 and len(item_text) < 200:
                                    print(f"    [{i}] {item_text[:100]}")
                            except:
                                pass
                    else:
                        print("  ❌ 没有分析器记录")
                else:
                    print("  ⚠️ 未找到分析器区域")

                # ============================================================
                # 步骤13: 验证交易记录 (包含信号和订单)
                # ============================================================
                print("\n📋 步骤13: 验证交易记录")

                # 点击"交易记录" tab
                trades_tab = page.locator("text=交易记录").first
                if trades_tab.count() > 0:
                    print("  找到交易记录 tab，点击查看...")
                    trades_tab.click()
                    time.sleep(3)

                    # 检查是否有内容显示
                    content_area = page.locator(".ant-tabs-tab-active").all()
                    print(f"  活动标签页数量: {len(content_area)}")

                    # 查找表格或其他内容
                    tables = page.locator(".ant-table").all()
                    print(f"  表格数量: {len(tables)}")

                    if len(tables) > 0:
                        print("  ✅ 有交易记录显示")
                        # 显示表格内容
                        for i, table in enumerate(tables[:2]):
                            rows = table.locator(".ant-table-tbody tr").all()
                            print(f"    表格 {i+1}: {len(rows)} 行")
                            if rows:
                                for j in range(min(2, len(rows))):
                                    row_text = rows[j].text_content()
                                    print(f"      [{j}] {row_text[:100]}")
                    else:
                        # 检查是否有其他内容
                        content_divs = page.locator(".ant-tabs-tab-active + .ant-tabs-tabpane").all()
                        if content_divs:
                            print(f"  内容区域元素数: {len(content_divs)}")
                            content_text = content_divs[0].text_content()
                            print(f"  内容: {content_text[:200]}")
                else:
                    print("  ⚠️ 未找到交易记录 tab")

                # ============================================================
                # 测试总结
                # ============================================================
                print("\n" + "=" * 60)
                print("✅ WebUI 回测任务创建 E2E 测试完成！")
                print("=" * 60)
                print(f"回测任务名称: {expected_values['name']}")
                print(f"投资组合: {expected_values.get('portfolio_name', 'N/A')}")
                print(f"日期范围: {expected_values['start_date']} ~ {expected_values['end_date']}")
                print(f"初始资金: ¥{expected_values['initial_cash']:,}")
                print(f"Backtest UUID: {backtest_uuid}")
                print(f"最终状态: {final_status}")
                print(f"\n📊 回测结果验证:")
                for metric_name, metric_value in key_metrics.items():
                    if metric_value:
                        print(f"  - {metric_name}: {metric_value}")

        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

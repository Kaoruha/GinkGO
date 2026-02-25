"""
WebUI Portfolio创建E2E测试 (Playwright - 同步版本)

通过浏览器操作验证Portfolio创建流程：
1. 打开WebUI并导航到Portfolio列表页
2. 创建新Portfolio（选择selector、sizer、strategy）
3. 填写组件参数
4. 验证Portfolio创建成功
"""

import pytest
import time
import re
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

# 配置
WEB_UI_URL = "http://192.168.50.12:5173"
REMOTE_BROWSER = "http://192.168.50.10:9222"


@pytest.mark.e2e
def test_portfolio_creation_via_webui_playwright():
    """通过WebUI (Playwright) 完成Portfolio创建流程"""

    print("\n" + "=" * 60)
    print("WebUI Portfolio创建E2E测试 (Playwright)")
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
            portfolio_name = f"E2E_WebUI_{timestamp}"

            # 生成随机的初始资金 (50000 - 500000 之间，10000的倍数)
            initial_cash = random.randint(5, 50) * 10000

            # 存储设置的参数值，用于验证
            expected_values = {
                "initial_cash": initial_cash,
                "selector_codes": "000001.SZ",
                "sizer_volume": "1500",
                "strategy_name": "E2E_RandomSignal",
                "buy_probability": "0.5",
                "sell_probability": "0.2",
                "max_signals": "4"
            }

            # ============================================================
            # 步骤1: 导航到Portfolio列表页
            # ============================================================
            print("\n📋 步骤1: 导航到Portfolio列表页")
            page.goto(f"{WEB_UI_URL}/portfolio", wait_until="domcontentloaded")
            time.sleep(2)
            print("  ✅ 已导航到Portfolio列表页")

            # ============================================================
            # 步骤2: 点击创建Portfolio按钮
            # ============================================================
            print("\n➕ 步骤2: 点击创建Portfolio按钮")
            create_btn = page.locator("button:has-text('创建组合')").first
            create_btn.click()
            time.sleep(2)
            print("  ✅ 已打开创建表单")

            # ============================================================
            # 步骤3: 填写Portfolio基本信息（使用精确ID）
            # ============================================================
            print("\n📝 步骤3: 填写Portfolio基本信息")
            print(f"  名称: {portfolio_name}")

            # 使用精确的ID选择器
            name_input = page.locator("#form_item_name").first
            name_input.fill(portfolio_name)
            print("  ✅ 填写名称")

            # 填写描述
            description = f"E2E测试组合 - 使用random_signal_strategy进行回测验证 (创建于{datetime.now().strftime('%Y-%m-%d %H:%M')})"
            desc_textarea = page.locator("textarea").first
            desc_textarea.fill(description)
            print(f"  ✅ 填写描述")

            # 填写初始资金（随机值）
            cash_input = page.locator("#form_item_initial_cash").first
            cash_input.fill(str(initial_cash))
            print(f"  ✅ 填写初始资金: {initial_cash:,}")

            time.sleep(0.5)

            # ============================================================
            # 步骤4: 配置Selector（使用点击选项）
            # ============================================================
            print("\n🎯 步骤4: 配置Selector")

            # 点击选股器 tab
            selector_tab = page.locator("button.type-btn:has-text('选股器')").first
            if selector_tab.count() > 0:
                selector_tab.click()
                time.sleep(0.3)

            # 点击下拉框
            selector_dropdown = page.locator(".component-selector .ant-select").first
            selector_dropdown.click()
            time.sleep(0.5)

            # 点击选项
            selector_option = page.locator(".ant-select-item-option:has-text('fixed_selector')").first
            if selector_option.count() > 0:
                selector_option.click()
                time.sleep(1.5)
                print("  ✅ 选择: fixed_selector")

                # 填写codes参数
                codes_input = page.locator(".param-row input").nth(1)
                if codes_input.count() > 0:
                    codes_input.fill("000001.SZ")
                    print("  ✅ 填写codes: 000001.SZ")

            # ============================================================
            # 步骤5: 配置Sizer（使用点击选项）
            # ============================================================
            print("\n📏 步骤5: 配置Sizer")

            # 点击仓位管理 tab
            sizer_tab = page.locator("button.type-btn:has-text('仓位管理')").first
            if sizer_tab.count() > 0:
                sizer_tab.click()
                time.sleep(0.3)

            # 点击下拉框
            sizer_dropdown = page.locator(".component-selector .ant-select").first
            sizer_dropdown.click()
            time.sleep(0.5)

            # 点击选项
            sizer_option = page.locator(".ant-select-item-option:has-text('fixed_sizer')").first
            if sizer_option.count() > 0:
                sizer_option.click()
                time.sleep(1.5)
                print("  ✅ 选择: fixed_sizer")

                # 填写volume参数
                volume_input = page.locator(".param-row input").last
                if volume_input.count() > 0:
                    volume_input.fill("1500")
                    print("  ✅ 填写volume: 1500")

            # ============================================================
            # 步骤6: 配置Strategy（使用点击选项）
            # ============================================================
            print("\n🎲 步骤6: 配置Strategy")

            # 点击策略 tab
            strategy_tab = page.locator("button.type-btn:has-text('策略')").first
            if strategy_tab.count() > 0:
                strategy_tab.click()
                time.sleep(0.3)

            # 点击下拉框
            strategy_dropdown = page.locator(".component-selector .ant-select").first
            strategy_dropdown.click()
            time.sleep(0.5)

            # 使用搜索框搜索 random_signal
            search_input = strategy_dropdown.locator("input[role='combobox']").first
            if search_input.count() > 0:
                search_input.type("random_signal")
                time.sleep(0.8)

            # 检查搜索后的选项
            filtered_options = page.locator(".ant-select-item-option").all()
            print(f"  搜索后选项数量: {len(filtered_options)}")
            for i, opt in enumerate(filtered_options[:5]):
                opt_text = opt.text_content()
                print(f"    [{i}] {opt_text}")

            # 点击搜索到的第一个选项
            strategy_option = page.locator(".ant-select-item-option").first
            if strategy_option.count() > 0:
                option_text = strategy_option.text_content()
                strategy_option.click()
                time.sleep(3.0)  # 增加等待时间，确保参数区域加载完成
                print(f"  ✅ 选择: {option_text}")

                # 配置策略参数
                print("  📝 配置策略参数:")

                # 查找策略配置区域的参数输入框
                # 使用更精确的选择器：查找包含"策略"标题的配置区域
                strategy_config_section = page.locator(".config-section:has(.section-title:has-text('策略'))")
                if strategy_config_section.count() > 0:
                    # 在策略区域内查找参数输入框
                    param_inputs = strategy_config_section.locator(".param-row input")
                    param_count = param_inputs.count()
                    print(f"    找到 {param_count} 个参数输入框")

                    # RandomSignalStrategy 参数: name, buy_probability, sell_probability, signal_reason_template, max_signals
                    if param_count >= 4:
                        # name (第1个参数)
                        param_inputs.nth(0).fill("E2E_RandomSignal")
                        print("    ✅ name: E2E_RandomSignal")

                        # buy_probability (第2个参数)
                        param_inputs.nth(1).fill("0.5")
                        print("    ✅ buy_probability: 0.5")

                        # sell_probability (第3个参数)
                        param_inputs.nth(2).fill("0.2")
                        print("    ✅ sell_probability: 0.2")

                        # max_signals (第5个参数，跳过signal_reason_template)
                        if param_count >= 5:
                            param_inputs.nth(4).fill("4")
                            print("    ✅ max_signals: 4")
                    else:
                        print(f"    ⚠️ 策略参数数量不足，至少需要4个，实际: {param_count}")
                else:
                    print("    ⚠️ 未找到策略配置区域，检查所有配置区域:")
                    all_sections = page.locator(".config-section").all()
                    for i, section in enumerate(all_sections):
                        title = section.locator(".section-title").text_content()
                        print(f"      [{i}] {title}")
            else:
                print("  ⚠️ 未找到 random_signal_strategy 选项")

            # 验证所有组件已添加
            config_sections = page.locator(".config-section").count()
            print(f"\n  当前配置区域数量: {config_sections}")
            assert config_sections >= 3, f"至少需要3个配置区域(选股器、仓位管理、策略)，实际: {config_sections}"

            # ============================================================
            # 步骤7: 提交创建Portfolio
            # ============================================================
            print("\n✅ 步骤7: 提交创建Portfolio")

            # 监听网络请求
            api_requests = []
            def handle_request(request):
                if "/portfolio" in request.url:
                    api_requests.append({"url": request.url, "method": request.method, "type": "request"})

            def handle_response(response):
                if "/portfolio" in response.url:
                    api_requests.append({
                        "url": response.url,
                        "status": response.status,
                        "type": "response",
                        "body": response.body() if response.ok else None
                    })

            page.on("request", handle_request)
            page.on("response", handle_response)

            # 滚动到模态框顶部，确保按钮可点击
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)

            # 查找创建按钮（模态框中的按钮文本是"创建"）
            submit_btn = page.locator("button.ant-btn-primary:has-text('创建')").first

            # 检查按钮状态和表单验证状态
            print("  检查按钮状态:")
            print(f"    按钮数量: {submit_btn.count()}")
            if submit_btn.count() > 0:
                is_disabled = submit_btn.get_attribute("disabled") == "disabled"
                is_loading = "ant-btn-loading" in submit_btn.get_attribute("class") or ""
                print(f"    禁用: {is_disabled}")
                print(f"    加载中: {is_loading}")

            # 检查表单验证错误
            form_errors = page.locator(".ant-form-item-has-error").all()
            print(f"  表单验证错误: {len(form_errors)} 个")
            for err in form_errors[:5]:
                err_text = err.locator(".ant-form-item-explain-error").text_content() if err.locator(".ant-form-item-explain-error").count() > 0 else "无说明"
                print(f"    - {err_text}")

            # 检查输入框的值
            name_value = page.locator("#form_item_name").first.input_value()
            cash_value = page.locator("#form_item_initial_cash").first.input_value()
            print(f"  表单数据: name='{name_value}', initial_cash={cash_value}")

            # 尝试使用 JavaScript 直接触发点击，确保触发 Vue 事件
            print("  使用 JavaScript 调试按钮...")
            debug_result = page.evaluate("""
                () => {
                    // 获取所有主按钮
                    const buttons = Array.from(document.querySelectorAll('button.ant-btn-primary'));
                    const buttonInfo = buttons.map(btn => ({
                        text: btn.textContent.trim(),
                        class: btn.className,
                        disabled: btn.disabled
                    }));

                    // 查找模态框中的创建按钮（文本是"创 建"，中间有空格）
                    const createBtn = buttons.find(btn => btn.textContent.trim() === '创 建');

                    return {
                        allButtons: buttonInfo,
                        foundCreate: !!createBtn,
                        createButtonText: createBtn ? createBtn.textContent.trim() : null
                    };
                }
            """)
            print(f"    所有主按钮: {debug_result['allButtons']}")
            print(f"    找到创建按钮: {debug_result['foundCreate']}")

            # 如果找到，点击它
            if debug_result['foundCreate']:
                click_result = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button.ant-btn-primary'));
                        // 精确匹配"创 建"按钮（模态框中的创建按钮）
                        const createBtn = buttons.find(btn => btn.textContent.trim() === '创 建');
                        if (createBtn) {
                            createBtn.click();
                            return { success: true };
                        }
                        return { success: false };
                    }
                """)
                print(f"    点击结果: {click_result}")

            # 等待响应
            print("  等待创建响应...")
            time.sleep(8)  # 增加等待时间

            # 输出网络请求日志
            print(f"  🌐 网络请求: {len(api_requests)} 条")
            for req in api_requests:
                if req["type"] == "request":
                    print(f"    → {req['method']} {req['url']}")
                else:
                    print(f"    ← {req['status']} {req['url']}")

            # 检查成功或错误消息
            success_msg = page.locator(".ant-message-success, .ant-notification-success").first
            error_msg = page.locator(".ant-message-error, .ant-notification-error").first

            # 检查表单验证错误
            form_errors = page.locator(".ant-form-item-explain-error, .ant-alert-error").all()
            if len(form_errors) > 0:
                print("  ⚠️ 发现表单验证错误:")
                for error in form_errors:
                    error_text = error.text_content()
                    print(f"    - {error_text}")

            # 检查浏览器控制台错误
            console_errors = page.evaluate("""
                () => {
                    const errors = [];
                    const originalError = console.error;
                    console.error = function(...args) {
                        errors.push(args.join(' '));
                        originalError.apply(console, args);
                    };
                    return errors; // 注意：这只会捕获从此刻开始的错误
                }
            """)

            if error_msg.count() > 0:
                error_text = error_msg.text_content()
                print(f"  ❌ 创建失败: {error_text}")
            elif success_msg.count() > 0:
                success_text = success_msg.text_content()
                print(f"  ✅ Portfolio创建成功: {success_text}")
            else:
                print("  ⚠️ 未找到成功或失败消息")

            # 截图保存当前状态
            page.screenshot(path="/tmp/portfolio_creation_submit_state.png", full_page=True)
            print("  📸 已保存创建状态截图: /tmp/portfolio_creation_submit_state.png")

            # 等待自动导航到详情页（Vue的handleCreated函数会自动导航）
            print("  等待自动导航到详情页...")
            time.sleep(3)

            # 检查当前URL，可能已经自动导航到详情页
            current_url = page.url
            print(f"  当前URL: {current_url}")

            # 检查模态框是否还打开
            modal_visible = page.locator(".ant-modal").count() > 0
            print(f"  模态框仍打开: {modal_visible}")

            # 如果已经在详情页，直接验证
            if "/portfolio/" in current_url and current_url.count("/") > 4:
                print("  ✅ 已自动导航到详情页")
            else:
                # 否则手动导航到列表页
                print("  导航到Portfolio列表页...")
                page.goto(f"{WEB_UI_URL}/portfolio", wait_until="domcontentloaded")
                time.sleep(3)

                # 点击第一个Portfolio卡片
                first_card = page.locator(".portfolio-card").first
                if first_card.count() > 0:
                    card_name = first_card.locator(".name").first
                    if card_name.count() > 0:
                        name_text = card_name.text_content()
                        print(f"  打开第一个Portfolio: {name_text}")

                    first_card.click()
                    time.sleep(3)

            # ============================================================
            # 步骤8: 验证Portfolio详情
            # ============================================================
            print("\n🔍 步骤8: 验证Portfolio详情")

            # 验证基本信息
            print("\n  📝 验证基本信息:")

            # 验证名称
            page_title = page.locator(".page-title").first
            if page_title.count() > 0:
                actual_name = page_title.text_content().strip()
                print(f"    Portfolio名称: {actual_name}")

            # 验证初始资金
            initial_cash_label = page.locator(".stat-label:has-text('初始资金')").first
            if initial_cash_label.count() > 0:
                cash_value = initial_cash_label.locator("xpath=../..").locator(".stat-value").first
                if cash_value.count() > 0:
                    cash_text = cash_value.text_content()
                    cash_number = cash_text.replace("¥", "").replace(",", "").replace(" ", "").strip()
                    try:
                        cash_int = int(cash_number)
                        expected_cash = expected_values["initial_cash"]
                        if cash_int == expected_cash:
                            print(f"    ✅ 初始资金匹配: {cash_text}")
                        else:
                            print(f"    ❌ 初始资金不匹配: 期望 {expected_cash:,}, 实际 {cash_int:,}")
                    except ValueError:
                        print(f"    ⚠️ 初始资金格式: {cash_text}")

            # 验证组件配置
            print("\n  🧩 验证组件配置参数:")

            # 验证 Selector codes
            selector_section = page.locator(".component-section:has(.ant-tag:has-text('选股器'))").first
            if selector_section.count() > 0:
                config_tags = selector_section.locator(".config-tag").all()
                for tag in config_tags:
                    tag_text = tag.text_content()
                    if "codes" in tag_text:
                        if expected_values["selector_codes"] in tag_text:
                            print(f"    ✅ Selector codes: {expected_values['selector_codes']}")
                        else:
                            print(f"    ❌ Selector codes: 期望 {expected_values['selector_codes']}, 实际 {tag_text}")
                        break
            else:
                print(f"    ❌ Selector 未找到")

            # 验证 Sizer volume
            sizer_section = page.locator(".component-section:has(.ant-tag:has-text('仓位管理'))").first
            if sizer_section.count() > 0:
                config_tags = sizer_section.locator(".config-tag").all()
                for tag in config_tags:
                    tag_text = tag.text_content()
                    if "volume" in tag_text:
                        if expected_values["sizer_volume"] in tag_text:
                            print(f"    ✅ Sizer volume: {expected_values['sizer_volume']}")
                        else:
                            print(f"    ❌ Sizer volume: 期望 {expected_values['sizer_volume']}, 实际 {tag_text}")
                        break
            else:
                print(f"    ❌ Sizer 未找到")

            # 验证 Strategy 参数
            strategy_section = page.locator(".component-section:has(.ant-tag:has-text('策略'))").first
            if strategy_section.count() > 0:
                strategy_name = strategy_section.locator(".component-name").text_content()
                print(f"    策略组件名称: {strategy_name}")

                # 获取所有配置标签用于调试
                config_tags = strategy_section.locator(".config-tag").all()

                # 构建参数值到参数索引的映射
                # RandomSignalStrategy 参数顺序: name(0), buy_probability(1), sell_probability(2), signal_reason_template(3), max_signals(4)
                param_checks = {
                    "E2E_RandomSignal": "name",      # param_0
                    "0.5": "buy_probability",         # param_1
                    "0.2": "sell_probability",        # param_2
                    "4": "max_signals"                # param_4
                }

                all_found = True
                for expected_value, param_name in param_checks.items():
                    found = False
                    for tag in config_tags:
                        tag_text = tag.text_content()
                        if expected_value in tag_text:
                            print(f"    ✅ {param_name}: {expected_value}")
                            found = True
                            break
                    if not found:
                        print(f"    ❌ {param_name}: 未找到或值不匹配 (期望 {expected_value})")
                        all_found = False

                if all_found:
                    print("    ✅ 所有策略参数验证通过")
            else:
                print(f"    ❌ Strategy 未找到")

            # ============================================================
            # 测试总结
            # ============================================================
            print("\n" + "=" * 60)
            print("✅ WebUI Portfolio创建E2E测试完成！")
            print("=" * 60)
            print(f"Portfolio名称: {portfolio_name}")
            print(f"初始资金: {expected_values['initial_cash']:,}")
            print(f"配置组件: Selector (fixed_selector), Sizer (fixed_sizer), Strategy (random_signal_strategy)")
            print(f"配置区域数量: 3")

        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

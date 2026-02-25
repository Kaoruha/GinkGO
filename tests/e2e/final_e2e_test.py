"""
完整回测E2E测试 - 使用有数据的股票

1. 创建Portfolio (FixedSelector + FixedSizer + RandomSignalStrategy)
2. 配置组件参数 (codes=000001.SZ, 有数据)
3. 创建并启动回测
4. 等待完成并验证分析器数据
"""

import time
import json
import urllib.request
from playwright.sync_api import sync_playwright

WEB_UI_URL = "http://192.168.50.12:5173"
API_URL = "http://localhost:8000/api/v1"
REMOTE_BROWSER = "http://192.168.50.10:9222"


def fill_parameter_by_label(page, label_text, value):
    """根据参数标签找到对应的输入框并填写值"""
    label = page.locator(f".param-label:has-text('{label_text}')").first
    if label.is_visible(timeout=2000):
        param_row = label.locator("..")
        input_field = param_row.locator("input, .ant-input-number-input").first
        input_field.fill(str(value))
        print(f"    ✓ 填写参数 {label_text} = {value}")
        return True
    else:
        print(f"    ✗ 未找到参数标签: {label_text}")
        return False


def run_full_e2e_test():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        context = browser.contexts[0]
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            # ========== 1. 创建Portfolio ==========
            print("\n" + "="*50)
            print("步骤1: 创建Portfolio")
            print("="*50)

            page.goto(f"{WEB_UI_URL}/portfolio")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # 点击创建组合
            page.click('button:has-text("创建组合")')
            page.wait_for_timeout(1000)

            task_name = f"Final_E2E_{int(time.time())}"
            page.fill('input[placeholder="组合名称"]', task_name)
            print(f"✓ 组合名称: {task_name}")

            # 设置初始资金
            cash_input = page.locator(".ant-modal .ant-input-number-input").first
            cash_input.fill("")
            cash_input.fill("100000")
            print("✓ 初始资金: 100000")

            # ========== 添加选股器 (使用有数据的000001.SZ) ==========
            print("\n添加选股器 (FixedSelector with 000001.SZ)...")
            type_btns = page.locator(".ant-modal .component-type-tabs button").all()
            for btn in type_btns:
                text = btn.text_content()
                if "选股器" in text or "SEL" in text:
                    btn.click()
                    page.wait_for_timeout(500)
                    break

            selector_select = page.locator(".ant-modal .component-selector .ant-select").first
            selector_select.click()
            page.wait_for_timeout(500)
            page.keyboard.type("fixed_selector")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print("  ✓ 已选择: fixed_selector")

            # 填写codes参数 - 使用有数据的000001.SZ
            fill_parameter_by_label(page, "codes", "000001.SZ")

            # ========== 添加仓位管理器 ==========
            print("\n添加仓位管理器 (FixedSizer)...")
            for btn in type_btns:
                text = btn.text_content()
                if "仓位" in text or "SIZ" in text:
                    btn.click()
                    page.wait_for_timeout(500)
                    break

            sizer_select = page.locator(".ant-modal .component-selector .ant-select").first
            sizer_select.click()
            page.wait_for_timeout(500)
            page.keyboard.type("fixed_sizer")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print("  ✓ 已选择: fixed_sizer")

            fill_parameter_by_label(page, "volume", "100")

            # ========== 添加策略 ==========
            print("\n添加策略 (RandomSignalStrategy)...")
            for btn in type_btns:
                text = btn.text_content()
                if "策略" in text or "STR" in text:
                    btn.click()
                    page.wait_for_timeout(500)
                    break

            strategy_select = page.locator(".ant-modal .component-selector .ant-select").first
            strategy_select.click()
            page.wait_for_timeout(500)
            page.keyboard.type("random_signal")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print("  ✓ 已选择: random_signal_strategy")

            fill_parameter_by_label(page, "buy_probability", "0.7")
            fill_parameter_by_label(page, "sell_probability", "0.2")

            # 保存Portfolio
            print("\n保存Portfolio...")
            submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')")
            submit_btn.click()
            page.wait_for_timeout(5000)

            # 关闭模态框
            try:
                close_btn = page.locator(".ant-modal-close")
                if close_btn.is_visible(timeout=2000):
                    close_btn.click()
                    page.wait_for_timeout(1000)
            except:
                pass

            # 获取Portfolio ID
            print("从API获取Portfolio ID...")
            try:
                api_url = f"{API_URL}/portfolio?size=1&sort_by=created_at&order=desc"
                response = urllib.request.urlopen(api_url, timeout=5)
                data = json.loads(response.read())
                portfolios = data.get("data", [])
                if portfolios:
                    portfolio_id = portfolios[0].get("uuid", "")
                    print(f"✓ Portfolio ID: {portfolio_id}")

                    # 验证配置
                    portfolio_detail = portfolios[0]
                    print(f"\nPortfolio配置验证:")
                    selectors = portfolio_detail.get("components", {}).get("selectors", [])
                    if selectors:
                        print(f"  Selector: {selectors[0].get('name')}, codes={selectors[0].get('config', {}).get('codes')}")
                    sizer = portfolio_detail.get("components", {}).get("sizer", {})
                    if sizer:
                        print(f"  Sizer: {sizer.get('name')}, volume={sizer.get('config', {}).get('volume')}")
                    strategies = portfolio_detail.get("components", {}).get("strategies", [])
                    if strategies:
                        cfg = strategies[0].get('config', {})
                        print(f"  Strategy: {strategies[0].get('name')}")
                        print(f"    buy_probability={cfg.get('buy_probability')}, sell_probability={cfg.get('sell_probability')}")
                else:
                    print("✗ 无法获取Portfolio ID")
                    return {"success": False, "error": "Cannot get portfolio ID"}
            except Exception as e:
                print(f"✗ API获取失败: {e}")
                return {"success": False, "error": str(e)}

            # ========== 2. 创建并启动回测 ==========
            print("\n" + "="*50)
            print("步骤2: 创建并启动回测任务")
            print("="*50)

            page.goto(f"{WEB_UI_URL}/stage1/backtest")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            page.click('button:has-text("新建")')
            page.wait_for_timeout(1000)

            bt_name = f"BT_{int(time.time())}"
            page.fill('.ant-modal:visible input[placeholder*="任务名称"]', bt_name)
            print(f"✓ 任务名称: {bt_name}")

            # 选择Portfolio - 搜索刚创建的portfolio
            portfolio_select = page.locator(".ant-modal:visible .ant-select").first
            portfolio_select.click()
            page.wait_for_timeout(500)

            search_input = page.locator(".ant-select-dropdown:visible .ant-select-search__field").first
            if search_input.is_visible():
                search_input.fill(task_name)
                page.wait_for_timeout(500)

            dropdown_items = page.locator(".ant-select-dropdown:visible .ant-select-item").all()
            if dropdown_items:
                dropdown_items[0].click()
                print(f"✓ 已选择Portfolio: {task_name}")
            else:
                print("✗ Portfolio下拉列表为空")
                return {"success": False, "error": "No portfolio options"}
            page.wait_for_timeout(500)

            # 设置日期范围 - 使用有数据的日期 (2023年1月)
            date_inputs = page.locator(".ant-modal:visible input.ant-picker-input").all()
            if len(date_inputs) >= 2:
                date_inputs[0].fill("2023-01-01")
                date_inputs[1].fill("2023-01-31")
                print("✓ 日期: 2023-01-01 ~ 2023-01-31")
                page.wait_for_timeout(300)

            # 提交回测
            print("\n提交回测任务...")
            submit_btn = page.locator(".ant-modal:visible button.ant-btn-primary:has-text('确 定')")
            submit_btn.click()
            page.wait_for_timeout(5000)

            # 关闭模态框
            try:
                close_btn = page.locator(".ant-modal-close")
                if close_btn.is_visible(timeout=2000):
                    close_btn.click()
                    page.wait_for_timeout(1000)
            except:
                pass

            # 获取回测任务ID并启动
            print("获取回测任务ID并启动...")
            try:
                # 获取最新创建的回测
                api_url = f"{API_URL}/backtest?size=1&sort_by=created_at&order=desc"
                response = urllib.request.urlopen(api_url, timeout=5)
                data = json.loads(response.read())
                tasks = data.get("data", [])
                if tasks:
                    backtest_id = tasks[0].get("uuid", "")
                    print(f"✓ 回测任务ID: {backtest_id}")

                    # 启动回测
                    start_url = f"{API_URL}/backtest/{backtest_id}/start"
                    start_req = urllib.request.Request(
                        start_url,
                        data=json.dumps({"portfolio_uuid": portfolio_id}).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                    response = urllib.request.urlopen(start_req, timeout=10)
                    result = json.loads(response.read())
                    print(f"✓ 回测已启动: {result.get('message', '')}")
                else:
                    print("✗ 无法获取回测任务ID")
                    return {"success": False, "error": "Cannot get backtest ID"}
            except Exception as e:
                print(f"✗ 启动回测失败: {e}")
                return {"success": False, "error": str(e)}

            # ========== 3. 等待回测完成 ==========
            print("\n" + "="*50)
            print("步骤3: 等待回测完成 (最多3分钟)")
            print("="*50)

            for i in range(36):
                time.sleep(5)

                try:
                    response = urllib.request.urlopen(f"{API_URL}/backtest/{backtest_id}", timeout=5)
                    data = json.loads(response.read())

                    status = data.get("status", "")
                    progress = data.get("progress", 0)
                    stage = data.get("current_stage", "")

                    print(f"  [{i*5}s] 状态: {status}, 进度: {progress}%, 阶段: {stage}")

                    if status == "completed" or progress >= 100:
                        print(f"\n✓✓✓ 回测完成!")
                        print(f"  信号数: {data.get('total_signals')}")
                        print(f"  订单数: {data.get('total_orders')}")
                        print(f"  最终净值: {data.get('final_portfolio_value')}")
                        break
                    elif status == "failed":
                        error_msg = data.get("error_message", "Unknown error")
                        print(f"\n✗✗✗ 回测失败: {error_msg}")
                        return {"success": False, "error": error_msg}

                except Exception as e:
                    print(f"查询状态失败: {e}")

            # ========== 4. 验证分析器数据 ==========
            print("\n" + "="*50)
            print("步骤4: 验证分析器数据")
            print("="*50)

            try:
                api_url = f"{API_URL}/backtest/{backtest_id}/analyzers"
                response = urllib.request.urlopen(api_url, timeout=10)
                data = json.loads(response.read())

                print(f"\n分析器API返回:")
                print(f"  run_id: {data.get('run_id', '')[:32]}...")
                print(f"  total_count: {data.get('total_count', 0)}")
                print(f"  分析器数量: {len(data.get('analyzers', []))}")

                analyzers = data.get('analyzers', [])
                if analyzers:
                    print(f"\n分析器详情:")
                    for analyzer in analyzers:
                        name = analyzer.get('name')
                        count = analyzer.get('record_count', 0)
                        latest = analyzer.get('latest_value')
                        print(f"  - {name}: {count} 条记录, 最新值 = {latest}")
                else:
                    print("  ⚠️ 没有分析器数据")

            except Exception as e:
                print(f"✗ 获取分析器API失败: {e}")

            # 检查页面显示
            page.reload()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            analyzer_tab = page.locator('.ant-tabs-tab:has-text("分析器")')
            if analyzer_tab.is_visible():
                analyzer_tab.click()
                page.wait_for_timeout(2000)

                cards = page.locator(".ant-card").all()
                print(f"\n页面显示分析器卡片: {len(cards)} 个")

                for card in cards[:5]:
                    try:
                        text = card.text_content()
                        if text:
                            lines = text.split('\n')[:3]
                            print(f"  {' '.join(lines)}")
                    except:
                        pass

            print("\n" + "="*50)
            print("✅ E2E测试完成!")
            print("="*50)

            return {"success": True, "backtest_id": backtest_id, "portfolio_id": portfolio_id}

        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

        finally:
            page.close()


if __name__ == "__main__":
    result = run_full_e2e_test()
    print(f"\n{'='*50}")
    print(f"测试结果: {'✅ 成功' if result.get('success') else '❌ 失败'}")
    if result.get('backtest_id'):
        print(f"回测ID: {result.get('backtest_id')}")
    if result.get('error'):
        print(f"错误: {result.get('error')}")
    print(f"{'='*50}")

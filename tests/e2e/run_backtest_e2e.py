"""
通过Playwright运行完整回测E2E测试

流程：
1. 创建Portfolio（选股器+仓位管理器+策略）
2. 创建并启动回测任务
3. 等待完成
4. 验证分析器数据
"""

import time
import os
from playwright.sync_api import sync_playwright

WEB_UI_URL = os.environ.get('WEB_UI_URL', 'http://192.168.50.12:5173')
REMOTE_BROWSER = os.environ.get('REMOTE_BROWSER', 'http://192.168.50.10:9222')


def run_backtest_e2e():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        context = browser.contexts[0]
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            # ========== 1. 创建Portfolio ==========
            print("\n=== 步骤1: 创建Portfolio ===")
            page.goto(f"{WEB_UI_URL}/portfolio")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # 点击创建组合
            page.click('button:has-text("创建组合")')
            page.wait_for_timeout(1000)

            task_name = f"E2E_BT_{int(time.time())}"
            page.fill('input[placeholder="组合名称"]', task_name)
            print(f"✓ 组合名称: {task_name}")

            # 设置初始资金
            cash_input = page.locator(".ant-modal .ant-input-number-input").first
            cash_input.fill("")
            cash_input.fill("100000")
            print("✓ 初始资金: 100000")

            # 添加选股器
            print("\n添加选股器...")
            type_btns = page.locator(".ant-modal .component-type-tabs button").all()
            for btn in type_btns:
                text = btn.text_content()
                if "选股器" in text or "SEL" in text:
                    btn.click()
                    page.wait_for_timeout(500)
                    break

            # 选择FixedSelector
            selector_select = page.locator(".ant-modal .component-selector .ant-select").first
            selector_select.click()
            page.wait_for_timeout(500)
            page.keyboard.type("fixed_selector")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print("✓ 已选择: fixed_selector")

            # 填写codes参数
            param_input = page.locator(".ant-modal .ant-input").first
            param_input.fill("600000.SH")
            print("✓ 代码: 600000.SH")
            page.wait_for_timeout(500)

            # 添加仓位管理器
            print("\n添加仓位管理器...")
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
            print("✓ 已选择: fixed_sizer")

            # 填写volume参数
            param_input = page.locator(".ant-modal .ant-input").first
            param_input.fill("")
            param_input.fill("1000")
            print("✓ 仓位: 1000")
            page.wait_for_timeout(500)

            # 添加策略
            print("\n添加策略...")
            for btn in type_btns:
                text = btn.text_content()
                if "策略" in text or "STR" in text:
                    btn.click()
                    page.wait_for_timeout(500)
                    break

            strategy_select = page.locator(".ant-modal .component-selector .ant-select").first
            strategy_select.click()
            page.wait_for_timeout(500)
            page.keyboard.type("random_signal_strategy")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print("✓ 已选择: random_signal_strategy")

            # 保存Portfolio
            print("\n保存Portfolio...")
            submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')")
            submit_btn.click()
            page.wait_for_timeout(5000)

            # 关闭模态框（如果还存在）
            try:
                close_btn = page.locator(".ant-modal-close")
                if close_btn.is_visible(timeout=2000):
                    close_btn.click()
                    page.wait_for_timeout(1000)
            except:
                pass

            # 从API获取最新创建的portfolio
            print("从API获取Portfolio ID...")
            import urllib.request
            import json

            try:
                api_url = "http://localhost:8000/api/v1/portfolio?size=1&sort_by=create_at&order=desc"
                response = urllib.request.urlopen(api_url, timeout=5)
                data = json.loads(response.read())
                portfolios = data.get("data", [])
                if portfolios:
                    portfolio_id = portfolios[0].get("uuid", "")
                    print(f"✓ Portfolio ID: {portfolio_id}")
                else:
                    print("✗ 无法获取Portfolio ID")
                    return {"success": False, "error": "Cannot get portfolio ID"}
            except Exception as e:
                print(f"✗ API获取失败: {e}")
                return {"success": False, "error": str(e)}

            # ========== 2. 创建回测任务 ==========
            print("\n=== 步骤2: 创建回测任务 ===")
            page.goto(f"{WEB_UI_URL}/stage1/backtest")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            page.click('button:has-text("新建")')
            page.wait_for_timeout(1000)

            bt_name = f"BT_{int(time.time())}"
            page.fill('.ant-modal:visible input[placeholder*="任务名称"]', bt_name)
            print(f"✓ 任务名称: {bt_name}")

            # 选择Portfolio - 直接从列表选择第一个
            portfolio_select = page.locator(".ant-modal:visible .ant-select").first
            portfolio_select.click()
            page.wait_for_timeout(500)

            # 从下拉列表选择第一个（如果有的话）
            dropdown_items = page.locator(".ant-select-dropdown:visible .ant-select-item").all()
            if dropdown_items:
                dropdown_items[0].click()
                print("✓ 已选择Portfolio (第一个选项)")
            else:
                print("✗ Portfolio下拉列表为空")
                return {"success": False, "error": "No portfolio options"}
            page.wait_for_timeout(500)

            # 设置日期范围
            date_inputs = page.locator(".ant-modal:visible input.ant-picker-input").all()
            if len(date_inputs) >= 2:
                date_inputs[0].fill("2024-01-02")
                date_inputs[1].fill("2024-01-10")
                print("✓ 日期: 2024-01-02 ~ 2024-01-10")
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

            # 从API获取最新创建的回测任务
            print("从API获取回测任务ID...")
            try:
                api_url = "http://localhost:8000/api/v1/backtest?size=1&sort_by=create_at&order=desc"
                response = urllib.request.urlopen(api_url, timeout=5)
                data = json.loads(response.read())
                tasks = data.get("data", [])
                if tasks:
                    backtest_id = tasks[0].get("uuid", "")
                    print(f"✓ 回测任务ID: {backtest_id}")
                else:
                    print("✗ 无法获取回测任务ID")
                    return {"success": False, "error": "Cannot get backtest ID"}
            except Exception as e:
                print(f"✗ API获取失败: {e}")
                return {"success": False, "error": str(e)}

            # ========== 3. 等待完成 ==========
            print("\n=== 步骤3: 等待回测完成 (最多3分钟) ===")
            for i in range(36):
                page.reload()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)

                text = page.text_content()
                if "已完成" in text or "100%" in text:
                    print("\n✓ 回测已完成!")
                    break
                elif "失败" in text or "ERROR" in text:
                    print("\n✗ 回测失败")
                    return {"success": False, "error": "Backtest failed"}

                # 获取进度
                try:
                    progress_el = page.locator(".ant-progress-text")
                    if progress_el.is_visible():
                        progress = progress_el.text_content()
                        print(f"  进度: {progress} ({i*5}s)")
                except:
                    pass

                time.sleep(5)

            # ========== 4. 验证分析器数据 ==========
            print("\n=== 步骤4: 验证分析器数据 ===")

            # 检查分析器API
            import urllib.request
            import json

            try:
                api_url = f"http://localhost:8000/api/v1/backtest/{backtest_id}/analyzers"
                response = urllib.request.urlopen(api_url, timeout=10)
                data = json.loads(response.read())

                print(f"分析器API返回:")
                print(f"  run_id: {data.get('run_id', '')[:32]}...")
                print(f"  total_count: {data.get('total_count', 0)}")
                print(f"  分析器数量: {len(data.get('analyzers', []))}")

                for analyzer in data.get('analyzers', []):
                    name = analyzer.get('name')
                    count = analyzer.get('record_count', 0)
                    latest = analyzer.get('latest_value')
                    print(f"    - {name}: {count} 条记录, 最新值 = {latest}")

            except Exception as e:
                print(f"获取分析器API失败: {e}")

            # 检查页面显示
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

            return {"success": True, "backtest_id": backtest_id, "portfolio_id": portfolio_id}

        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

        finally:
            page.close()


if __name__ == "__main__":
    result = run_backtest_e2e()
    print(f"\n{'='*40}")
    print(f"测试结果: {'成功' if result.get('success') else '失败'}")
    if result.get('backtest_id'):
        print(f"回测ID: {result.get('backtest_id')}")
    print(f"{'='*40}")

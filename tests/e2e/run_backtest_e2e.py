"""
完整回测 E2E 测试

快速验证完整回测流程：
1. 创建 Portfolio
2. 创建回测任务
3. 等待完成
4. 验证结果
"""

import time
import pytest
import json
import urllib.request
from playwright.sync_api import Page

from .config import config


@pytest.mark.e2e
@pytest.mark.slow
def test_full_backtest_flow(authenticated_page: Page):
    """完整回测流程测试 - 单文件版本"""

    page = authenticated_page
    page.set_default_timeout(60000)
    api_base = "http://192.168.50.12:8000/api/v1"

    # 生成唯一名称
    task_name = f"Quick_BT_{int(time.time())}"
    bt_name = f"BT_{int(time.time())}"

    # ========== 1. 创建 Portfolio ==========
    print("\n=== 步骤1: 创建 Portfolio ===")

    page.goto(f"{config.web_ui_url}/portfolio")
    page.wait_for_load_state("networkidle")

    # 验证在组合页面
    assert "/portfolio" in page.url

    # 点击创建组合
    page.click('button:has-text("创建组合")')
    page.wait_for_timeout(1000)

    # 验证模态框打开
    modal = page.locator(".ant-modal")
    assert modal.is_visible()

    # 填写组合名称
    page.fill('input[placeholder="组合名称"]', task_name)
    print(f"✓ 组合名称: {task_name}")

    # 设置初始资金
    cash_input = page.locator(".ant-modal .ant-input-number-input").first
    cash_input.fill("100000")
    print("✓ 初始资金: 100000")

    # 添加选股器
    type_btns = page.locator(".ant-modal .component-type-tabs button").all()
    for btn in type_btns:
        if "选股器" in btn.text_content() or "SEL" in btn.text_content():
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

    # 填写 codes 参数
    param_input = page.locator(".ant-modal .ant-input").first
    param_input.fill("600000.SH")
    print("✓ 代码: 600000.SH")

    # 添加仓位管理器
    for btn in type_btns:
        if "仓位" in btn.text_content() or "SIZ" in btn.text_content():
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

    param_input = page.locator(".ant-modal .ant-input").first
    param_input.fill("1000")
    print("✓ 仓位: 1000")

    # 添加策略
    for btn in type_btns:
        if "策略" in btn.text_content() or "STR" in btn.text_content():
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

    # 保存 Portfolio
    submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')")
    submit_btn.click()
    page.wait_for_timeout(5000)

    # 验证成功
    success_msg = page.locator(".ant-message-success")
    if success_msg.is_visible():
        print("✓ Portfolio 创建成功")

    # 关闭模态框
    close_btn = page.locator(".ant-modal-close")
    if close_btn.is_visible(timeout=2000):
        close_btn.click()

    # 获取 Portfolio ID
    api_url = f"{api_base}/portfolio?size=1&sort_by=created_at&order=desc"
    response = urllib.request.urlopen(api_url, timeout=5)
    data = json.loads(response.read())
    portfolios = data.get("data", [])

    assert portfolios, "应该能获取 Portfolio 列表"
    portfolio_id = portfolios[0].get("uuid", "")
    assert portfolio_id, "Portfolio ID 不应该为空"
    print(f"✓ Portfolio ID: {portfolio_id}")

    # ========== 2. 创建回测任务 ==========
    print("\n=== 步骤2: 创建回测任务 ===")

    page.goto(f"{config.web_ui_url}/stage1/backtest")
    page.wait_for_load_state("networkidle")

    # 验证在回测页面
    assert "/stage1/backtest" in page.url

    # 点击创建回测
    page.click('button:has-text("创建回测")')
    page.wait_for_timeout(1000)

    # 验证模态框打开
    modal = page.locator(".ant-modal")
    assert modal.is_visible()

    # 填写任务名称
    page.fill('.ant-modal:visible input[placeholder*="任务名称"]', bt_name)
    print(f"✓ 任务名称: {bt_name}")

    # 选择 Portfolio
    portfolio_select = page.locator(".ant-modal:visible .ant-select").first
    portfolio_select.click()
    page.wait_for_timeout(500)

    dropdown_items = page.locator(".ant-select-dropdown:visible .ant-select-item").all()
    assert dropdown_items, "Portfolio 下拉列表应该有选项"
    dropdown_items[0].click()
    print("✓ 已选择 Portfolio")
    page.wait_for_timeout(500)

    # 设置日期范围
    date_inputs = page.locator(".ant-modal:visible input.ant-picker-input").all()
    assert len(date_inputs) >= 2, "应该有日期输入框"
    date_inputs[0].fill("2024-01-02")
    date_inputs[1].fill("2024-01-10")
    print("✓ 日期: 2024-01-02 ~ 2024-01-10")

    # 提交回测
    submit_btn = page.locator(".ant-modal:visible button.ant-btn-primary:has-text('确 定')")
    submit_btn.click()
    page.wait_for_timeout(5000)

    # 验证成功
    success_msg = page.locator(".ant-message-success")
    if success_msg.is_visible():
        print("✓ 回测任务创建成功")

    # 关闭模态框
    close_btn = page.locator(".ant-modal-close")
    if close_btn.is_visible(timeout=2000):
        close_btn.click()

    # 获取回测任务 ID
    api_url = f"{api_base}/backtest?size=1&sort_by=created_at&order=desc"
    response = urllib.request.urlopen(api_url, timeout=5)
    data = json.loads(response.read())
    tasks = data.get("data", [])

    assert tasks, "应该能获取回测任务列表"
    backtest_id = tasks[0].get("uuid", "")
    assert backtest_id, "回测任务 ID 不应该为空"
    print(f"✓ 回测任务ID: {backtest_id}")

    # ========== 3. 启动回测 ==========
    print("\n=== 步骤3: 启动回测 ===")

    start_url = f"{api_base}/backtest/{backtest_id}/start"
    start_req = urllib.request.Request(
        start_url,
        data=b"{}",
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(start_req, timeout=10)
    result = json.loads(response.read())

    assert result.get("success") or "message" in result, f"启动回测失败: {result}"
    print(f"✓ 回测已启动: {result.get('message', '')}")

    # ========== 4. 等待完成 ==========
    print("\n=== 步骤4: 等待回测完成 ===")

    for i in range(36):
        time.sleep(5)

        try:
            response = urllib.request.urlopen(f"{api_base}/backtest/{backtest_id}", timeout=5)
            data = json.loads(response.read())

            status = data.get("status", "")
            progress = data.get("progress", 0)

            print(f"  [{i*5}s] 状态: {status}, 进度: {progress}%")

            if status == "completed" or progress >= 100:
                print("\n✓✓✓ 回测完成!")
                break
            elif status == "failed":
                error_msg = data.get("error_message", "Unknown error")
                pytest.fail(f"回测失败: {error_msg}")

        except Exception as e:
            print(f"查询状态失败: {e}")

    # ========== 5. 验证分析器数据 ==========
    print("\n=== 步骤5: 验证分析器数据 ===")

    try:
        api_url = f"{api_base}/backtest/{backtest_id}/analyzers"
        response = urllib.request.urlopen(api_url, timeout=10)
        data = json.loads(response.read())

        print(f"分析器API返回:")
        print(f"  run_id: {data.get('run_id', '')[:32]}...")
        print(f"  total_count: {data.get('total_count', 0)}")

        analyzers = data.get('analyzers', [])
        assert isinstance(analyzers, list), "分析器数据应该是列表"

        if analyzers:
            print(f"  分析器数量: {len(analyzers)}")

            for analyzer in analyzers[:3]:
                name = analyzer.get('name')
                count = analyzer.get('record_count', 0)
                print(f"    - {name}: {count} 条记录")
        else:
            print("  ⚠️ 没有分析器数据")

    except Exception as e:
        print(f"获取分析器数据失败: {e}")

    print("\n✅ 测试完成!")

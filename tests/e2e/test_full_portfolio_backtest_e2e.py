"""
完整的Portfolio创建和回测E2E测试

验证完整流程：
1. 创建完整的Portfolio（包含selector、sizer、strategy）
2. 验证Portfolio组件配置正确
3. 创建回测任务
4. 等待回测完成
5. 验证BacktestTask记录
6. 验证AnalyzerRecord记录
7. 验证信号和订单记录
"""

import pytest
import requests
import time
from datetime import datetime

# API配置
API_BASE = "http://192.168.50.12:8000"


@pytest.fixture(scope="module")
def api_client():
    """API客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


@pytest.fixture(scope="module")
def cleanup_portfolio(api_client):
    """测试后清理创建的Portfolio和BacktestTask"""
    created_portfolio_ids = []
    created_backtest_ids = []

    yield created_portfolio_ids, created_backtest_ids

    # 清理回测任务
    for task_id in created_backtest_ids:
        try:
            api_client.delete(f"{API_BASE}/api/v1/backtest/{task_id}")
        except:
            pass

    # 清理Portfolio
    for portfolio_id in created_portfolio_ids:
        try:
            api_client.delete(f"{API_BASE}/api/v1/portfolio/{portfolio_id}")
        except:
            pass


@pytest.mark.e2e
def test_full_portfolio_to_backtest_flow(api_client, cleanup_portfolio):
    """测试从Portfolio创建到回测完成的完整流程"""

    created_portfolio_ids, created_backtest_ids = cleanup_portfolio

    print("\n" + "=" * 60)
    print("完整Portfolio创建和回测E2E测试")
    print("=" * 60)

    # ============================================================
    # 步骤1: 获取组件UUID
    # ============================================================
    print("\n📋 步骤1: 获取组件UUID")

    # 获取selectors
    selectors_resp = api_client.get(f"{API_BASE}/api/v1/components/selectors")
    assert selectors_resp.status_code == 200
    selectors = selectors_resp.json().get("data", [])
    fixed_selector = next((s for s in selectors if "fixed" in s["name"].lower()), None)
    assert fixed_selector is not None, "未找到FixedSelector"
    print(f"  Selector: {fixed_selector['name']} ({fixed_selector['uuid'][:16]}...)")

    # 获取sizers
    sizers_resp = api_client.get(f"{API_BASE}/api/v1/components/sizers")
    assert sizers_resp.status_code == 200
    sizers = sizers_resp.json().get("data", [])
    fixed_sizer = next((s for s in sizers if "fixed" in s["name"].lower()), None)
    assert fixed_sizer is not None, "未找到FixedSizer"
    print(f"  Sizer: {fixed_sizer['name']} ({fixed_sizer['uuid'][:16]}...)")

    # 获取strategies
    strategies_resp = api_client.get(f"{API_BASE}/api/v1/components/strategies")
    assert strategies_resp.status_code == 200
    strategies = strategies_resp.json().get("data", [])

    # 优先使用my_custom_strategy，如果没有则使用第一个有参数的策略
    target_strategy = next(
        (s for s in strategies if "my_custom" in s["name"].lower()),
        next((s for s in strategies if s.get("params")), None)
    )
    assert target_strategy is not None, "未找到有效的Strategy"
    print(f"  Strategy: {target_strategy['name']} ({target_strategy['uuid'][:16]}...)")

    # 打印参数定义
    print(f"\n  Strategy参数定义:")
    for p in target_strategy.get("params", []):
        print(f"    [{p.get('index', '?')}] {p['name']}: {p.get('type')} (默认: {p.get('default', 'N/A')})")

    # ============================================================
    # 步骤2: 创建Portfolio
    # ============================================================
    print("\n📝 步骤2: 创建Portfolio")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    portfolio_name = f"E2E_Full_{timestamp}"

    portfolio_payload = {
        "name": portfolio_name,
        "initial_cash": 100000.0,
        "mode": "BACKTEST",
        "description": "E2E完整测试Portfolio",
        "selectors": [
            {
                "component_uuid": fixed_selector["uuid"],
                "config": {
                    "name": "FixedSelector",
                    "codes": "000001.SZ"
                }
            }
        ],
        "sizer_uuid": fixed_sizer["uuid"],
        "sizer_config": {
            "name": "FixedSizer",
            "volume": 1500
        },
        "strategies": [
            {
                "component_uuid": target_strategy["uuid"],
                "weight": 1.0,
                "config": {
                    # 根据策略参数定义填充
                    "name": "MyCustomMA",
                    "short_window": 5,
                    "long_window": 20
                }
            }
        ]
    }

    response = api_client.post(f"{API_BASE}/api/v1/portfolio", json=portfolio_payload)
    assert response.status_code == 200, f"创建Portfolio失败: {response.text}"

    portfolio_result = response.json()
    portfolio_id = portfolio_result["uuid"]
    created_portfolio_ids.append(portfolio_id)

    print(f"  Portfolio创建成功: {portfolio_id[:16]}...")
    print(f"  名称: {portfolio_name}")

    # ============================================================
    # 步骤3: 验证Portfolio配置
    # ============================================================
    print("\n🔍 步骤3: 验证Portfolio配置")

    response = api_client.get(f"{API_BASE}/api/v1/portfolio/{portfolio_id}")
    assert response.status_code == 200

    portfolio = response.json()
    components = portfolio.get("components", {})

    # 验证selector
    assert components.get("selectors"), "缺少Selector"
    selector = components["selectors"][0]
    print(f"  ✅ Selector: {selector['name']}")
    print(f"     Config: {selector.get('config', {})}")

    # 验证sizer
    assert components.get("sizer"), "缺少Sizer"
    sizer = components["sizer"]
    print(f"  ✅ Sizer: {sizer['name']}")
    print(f"     Config: {sizer.get('config', {})}")

    # 验证strategy
    assert components.get("strategies"), "缺少Strategy"
    strategy = components["strategies"][0]
    print(f"  ✅ Strategy: {strategy['name']}")
    print(f"     Config: {strategy.get('config', {})}")

    # ============================================================
    # 步骤4: 创建回测任务
    # ============================================================
    print("\n🚀 步骤4: 创建回测任务")

    backtest_payload = {
        "name": f"{portfolio_name}_Backtest",
        "portfolio_id": portfolio_id,
        "start_date": "2023-12-01",  # 数据起始日期
        "end_date": "2023-12-31",    # 使用更长的日期范围以获得更多交易机会
        "config_snapshot": {
            "initial_cash": 100000.0,
            "commission_rate": 0.0003,
        }
    }

    response = api_client.post(f"{API_BASE}/api/v1/backtest", json=backtest_payload)
    assert response.status_code == 200, f"创建回测任务失败: {response.text}"

    backtest_result = response.json()
    backtest_id = backtest_result["uuid"]
    created_backtest_ids.append(backtest_id)

    print(f"  回测任务创建成功: {backtest_id[:16]}...")
    print(f"  任务名称: {backtest_payload['name']}")
    print(f"  日期范围: {backtest_payload['start_date']} ~ {backtest_payload['end_date']}")

    # ============================================================
    # 步骤5: 等待回测完成
    # ============================================================
    print("\n⏳ 步骤5: 等待回测完成")

    max_wait = 180  # 最多等待3分钟
    start_time = time.time()
    final_status = None

    while time.time() - start_time < max_wait:
        response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}")
        assert response.status_code == 200

        task_status = response.json()
        status = task_status.get("status")
        progress = task_status.get("progress", 0)

        if status == "completed":
            final_status = task_status
            print(f"  ✅ 回测完成 (进度: {progress}%)")
            break
        elif status == "failed":
            error_msg = task_status.get("error_message", "Unknown error")
            pytest.fail(f"回测失败: {error_msg}")
        elif status in ["created", "pending", "running"]:
            current_stage = task_status.get("current_stage", "UNKNOWN")
            current_date = task_status.get("current_date", "")
            print(f"  状态: {status}, 阶段: {current_stage}, 日期: {current_date}, 进度: {progress}%")
            time.sleep(3)
        else:
            print(f"  状态: {status}, 进度: {progress}%")
            time.sleep(2)
    else:
        pytest.fail("回测超时")

    # ============================================================
    # 步骤6: 验证BacktestTask记录
    # ============================================================
    print("\n📊 步骤6: 验证BacktestTask记录")

    response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}")
    assert response.status_code == 200

    backtest_task = response.json()

    # 验证基本信息
    assert backtest_task["uuid"] == backtest_id
    assert backtest_task["status"] == "completed"
    assert backtest_task["portfolio_id"] == portfolio_id

    print(f"  ✅ BacktestTask基本信息验证通过")
    print(f"     UUID: {backtest_task['uuid'][:16]}...")
    print(f"     Portfolio: {backtest_task['portfolio_id'][:16]}...")
    print(f"     状态: {backtest_task['status']}")

    # 验证财务数据
    final_value = float(backtest_task.get("final_portfolio_value", 0))
    total_pnl = float(backtest_task.get("total_pnl", 0))

    print(f"     最终价值: ¥{final_value:,.2f}")
    print(f"     总盈亏: ¥{total_pnl:,.2f}")

    # ============================================================
    # 步骤7: 验证AnalyzerRecord记录
    # ============================================================
    print("\n📈 步骤7: 验证AnalyzerRecord记录")

    response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}/analyzers")
    assert response.status_code == 200

    analyzers_result = response.json()
    analyzers = analyzers_result.get("analyzers", [])

    assert len(analyzers) > 0, "没有分析器记录"

    print(f"  ✅ AnalyzerRecord验证通过")
    print(f"     分析器数量: {len(analyzers)}")

    # 打印关键指标
    key_metrics = ["net_value", "annualized_return", "max_drawdown", "sharpe_ratio", "volatility", "win_rate"]
    for analyzer in analyzers:
        if analyzer["name"] in key_metrics:
            print(f"     - {analyzer['name']}: {analyzer.get('latest_value', 'N/A')}")

    # ============================================================
    # 步骤8: 验证净值曲线
    # ============================================================
    print("\n📊 步骤8: 验证净值曲线")

    response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}/netvalue")
    assert response.status_code == 200

    netvalue = response.json()

    assert "strategy" in netvalue, "净值数据缺少strategy字段"
    assert len(netvalue["strategy"]) > 0, "净值数据为空"

    print(f"  ✅ 净值曲线验证通过")
    print(f"     数据点数量: {len(netvalue['strategy'])}")

    # ============================================================
    # 步骤9: 验证信号记录
    # ============================================================
    print("\n📡 步骤9: 验证信号记录")

    response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}/signals")
    assert response.status_code == 200

    signals_result = response.json()
    signals = signals_result.get("data", [])

    print(f"  ✅ 信号记录验证通过")
    print(f"     信号数量: {len(signals)}")

    if signals:
        print(f"     信号示例:")
        for signal in signals[:3]:
            print(f"       - {signal['timestamp']}: {signal['direction']} {signal['code']} ({signal.get('reason', 'N/A')})")

    # ============================================================
    # 步骤10: 验证订单记录
    # ============================================================
    print("\n📋 步骤10: 验证订单记录")

    response = api_client.get(f"{API_BASE}/api/v1/backtest/{backtest_id}/orders")
    assert response.status_code == 200

    orders_result = response.json()
    orders = orders_result.get("data", [])

    print(f"  ✅ 订单记录验证通过")
    print(f"     订单数量: {len(orders)}")

    if orders:
        print(f"     订单示例:")
        for order in orders[:3]:
            status_map = {"1": "NEW", "2": "SUBMITTED", "3": "PARTIAL_FILLED", "4": "FILLED"}
            status = status_map.get(str(order.get("status")), f"STATUS_{order.get('status')}")
            print(f"       - {order['timestamp']}: {order['code']} 数量:{order['volume']} 状态:{status}")

        # 统计订单状态
        filled_count = sum(1 for o in orders if float(o.get("transaction_volume", 0)) > 0)
        print(f"     成交订单: {filled_count}/{len(orders)}")

    # ============================================================
    # 测试总结
    # ============================================================
    print("\n" + "=" * 60)
    print("✅ 完整Portfolio创建和回测E2E测试全部通过！")
    print("=" * 60)
    print(f"Portfolio: {portfolio_id[:16]}...")
    print(f"Backtest: {backtest_id[:16]}...")
    print(f"信号数: {len(signals)}, 订单数: {len(orders)}, 分析器数: {len(analyzers)}")
    print(f"最终净值: ¥{final_value:,.2f}, 总盈亏: ¥{total_pnl:,.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

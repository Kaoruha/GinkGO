"""
E2E回测测试

验证完整的回测流程：
1. 通过API创建回测任务
2. 等待回测完成
3. 验证BacktestTask记录
4. 验证AnalyzerRecord记录
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
def test_portfolio_id(api_client):
    """获取测试用的Portfolio ID - 使用预配置的完整Portfolio"""
    # 使用预创建的完整Portfolio (包含selector, sizer, strategy)
    portfolio_id = "df40070a2ec54f3a83a9cd9d20889090"

    # 验证Portfolio存在
    response = api_client.get(f"{API_BASE}/api/v1/portfolio/{portfolio_id}")
    assert response.status_code == 200

    portfolio = response.json()
    print(f"使用Portfolio: {portfolio['name']} ({portfolio_id[:16]}...)")
    print(f"  - Selector: {portfolio['components']['selectors'][0]['name'] if portfolio['components']['selectors'] else 'None'}")
    print(f"  - Sizer: {portfolio['components']['sizer']['name'] if portfolio['components']['sizer'] else 'None'}")
    print(f"  - Strategies: {len(portfolio['components']['strategies'])}")

    return portfolio_id


@pytest.mark.e2e
def test_backtest_full_flow(api_client, test_portfolio_id):
    """测试完整回测流程"""

    # 1. 创建回测任务
    print("\n📝 步骤1: 创建回测任务")
    # 使用有数据的日期范围（000001.SZ数据范围: 2023-12-01 ~ 2026-02-13）
    payload = {
        "name": f"E2E测试_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "portfolio_id": test_portfolio_id,
        "start_date": "2023-12-01",  # 数据起始日期
        "end_date": "2023-12-10",    # 数据结束日期
        "config_snapshot": {
            "initial_cash": 100000.0,
            "commission_rate": 0.0003,
        }
    }

    response = api_client.post(f"{API_BASE}/api/v1/backtest", json=payload)
    assert response.status_code == 200

    task = response.json()
    task_id = task["uuid"]  # uuid == run_id，会话实体的主键

    print(f"  任务创建成功: task_id={task_id[:16]}...")

    # 2. 等待回测完成
    print("\n⏳ 步骤2: 等待回测完成")
    max_wait = 120  # 最多等待2分钟
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = api_client.get(f"{API_BASE}/api/v1/backtest/{task_id}")
        assert response.status_code == 200

        task_status = response.json()
        status = task_status["status"]

        if status == "completed":
            print(f"  ✅ 回测完成")
            break
        elif status == "failed":
            pytest.fail(f"回测失败: {task_status.get('error_message', 'Unknown error')}")
        elif status in ["created", "pending", "running"]:
            progress = task_status.get("progress", 0)
            print(f"  状态: {status}, 进度: {progress}%")
            time.sleep(2)
        else:
            pytest.fail(f"未知状态: {status}")
    else:
        pytest.fail("回测超时")

    # 3. 验证BacktestTask
    print("\n📊 步骤3: 验证BacktestTask记录")
    response = api_client.get(f"{API_BASE}/api/v1/backtest/{task_id}")
    assert response.status_code == 200

    task = response.json()
    assert task["uuid"] == task_id  # uuid == run_id
    assert task["status"] == "completed"
    assert float(task["final_portfolio_value"]) > 0

    print(f"  ✅ BacktestTask验证通过")
    print(f"     最终价值: ¥{float(task['final_portfolio_value']):,.2f}")
    print(f"     总盈亏: ¥{float(task['total_pnl']):,.2f}")

    # 4. 验证AnalyzerRecord
    print("\n📈 步骤4: 验证AnalyzerRecord记录")
    response = api_client.get(f"{API_BASE}/api/v1/backtest/{task_id}/analyzers")
    assert response.status_code == 200

    result = response.json()
    analyzers = result.get("analyzers", [])
    print(f"  分析器原始响应: {result}")

    print(f"  ✅ AnalyzerRecord验证通过")
    print(f"     分析器数量: {len(analyzers)}")

    for analyzer in list(analyzers)[:3]:  # 只显示前3个
        print(f"     - {analyzer['name']}: {analyzer.get('latest_value', 'N/A')}")

    # 5. 验证净值数据
    print("\n📊 步骤5: 验证净值曲线")
    response = api_client.get(f"{API_BASE}/api/v1/backtest/{task_id}/netvalue")
    assert response.status_code == 200

    netvalue = response.json()
    assert "strategy" in netvalue
    assert len(netvalue["strategy"]) > 0

    print(f"  ✅ 净值数据验证通过")
    print(f"     数据点数量: {len(netvalue['strategy'])}")

    print("\n✅ E2E测试全部通过！")


if __name__ == "__main__":
    # 直接运行测试
    import sys
    pytest.main([__file__, "-v", "-s", "--tb=short"])

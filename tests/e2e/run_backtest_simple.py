"""
简化的回测E2E测试 - 创建Portfolio并运行回测

通过API直接操作，减少对页面交互的依赖
"""

import time
import json
import urllib.request

WEB_UI_URL = "http://192.168.50.12:5173"
API_URL = "http://localhost:8000/api/v1"

def create_portfolio():
    """通过API创建Portfolio"""
    print("\n=== 创建Portfolio ===")

    # 先获取组件UUID
    print("获取组件UUID...")
    try:
        # 获取选股器
        resp = urllib.request.urlopen(f"{API_URL}/components/selectors?size=10", timeout=5)
        selectors = json.loads(resp.read())["data"]
        selector_uuid = selectors[0]["uuid"]
        print(f"  选股器: {selectors[0]['name']} ({selector_uuid})")

        # 获取仓位管理器
        resp = urllib.request.urlopen(f"{API_URL}/components/sizers?size=10", timeout=5)
        sizers = json.loads(resp.read())["data"]
        sizer_uuid = sizers[0]["uuid"]
        print(f"  仓位管理器: {sizers[0]['name']} ({sizer_uuid})")

        # 获取策略
        resp = urllib.request.urlopen(f"{API_URL}/components/strategies?size=10", timeout=5)
        strategies = json.loads(resp.read())["data"]
        strategy_uuid = strategies[0]["uuid"]
        print(f"  策略: {strategies[0]['name']} ({strategy_uuid})")
    except Exception as e:
        print(f"  ✗ 获取组件失败: {e}")
        return None

    # 创建Portfolio
    task_name = f"E2E_BT_{int(time.time())}"
    portfolio_data = {
        "name": task_name,
        "initial_cash": 100000,
        "mode": "BACKTEST",
        "description": "E2E自动化测试",
        "selectors": [{"component_uuid": selector_uuid, "config": {"codes": "600000.SH"}}],
        "sizers": [{"component_uuid": sizer_uuid, "config": {"volume": "1000"}}],
        "strategies": [{"component_uuid": strategy_uuid, "config": {"buy_probability": "0.8", "sell_probability": "0.1"}}],
    }

    print(f"\n创建Portfolio: {task_name}")
    try:
        req = urllib.request.Request(
            f"{API_URL}/portfolio",
            data=json.dumps(portfolio_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        portfolio_id = result.get("uuid", "")
        print(f"✓ Portfolio创建成功: {portfolio_id}")
        return portfolio_id
    except Exception as e:
        print(f"✗ 创建Portfolio失败: {e}")
        return None


def create_backtest(portfolio_id):
    """通过API创建回测任务"""
    print(f"\n=== 创建回测任务 (Portfolio: {portfolio_id[:20]}...) ===")

    task_data = {
        "name": f"BT_{int(time.time())}",
        "portfolio_id": portfolio_id,
        "start_date": "2024-01-02",
        "end_date": "2024-01-05",
        "initial_cash": 100000,
    }

    print(f"任务配置: {task_data['name']}")
    print(f"  日期: {task_data['start_date']} ~ {task_data['end_date']}")

    try:
        # 创建任务
        req = urllib.request.Request(
            f"{API_URL}/backtest",
            data=json.dumps(task_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        backtest_id = result.get("uuid", "")
        print(f"✓ 回测任务创建成功: {backtest_id}")

        # 启动任务
        print("\n启动回测任务...")
        req = urllib.request.Request(
            f"{API_URL}/backtest/{backtest_id}/start",
            data=json.dumps({"portfolio_uuid": portfolio_id}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        print(f"✓ 回测任务已启动")

        return backtest_id
    except Exception as e:
        print(f"✗ 创建/启动回测失败: {e}")
        return None


def wait_for_completion(backtest_id, max_wait=180):
    """等待回测完成"""
    print(f"\n=== 等待回测完成 (最多{max_wait}秒) ===")

    for i in range(max_wait // 5):
        time.sleep(5)

        try:
            resp = urllib.request.urlopen(f"{API_URL}/backtest/{backtest_id}", timeout=5)
            data = json.loads(resp.read())

            status = data.get("status", "")
            progress = data.get("progress", 0)

            print(f"  状态: {status}, 进度: {progress}% ({i*5}/{max_wait}s)", end='\r')

            if status == "completed" or progress >= 100:
                print(f"\n✓ 回测完成!")
                return True
            elif status == "failed":
                print(f"\n✗ 回测失败")
                return False

        except Exception as e:
            print(f"\n查询失败: {e}")

    print(f"\n✗ 回测超时")
    return False


def check_analyzers(backtest_id):
    """检查分析器数据"""
    print(f"\n=== 检查分析器数据 ===")

    try:
        resp = urllib.request.urlopen(f"{API_URL}/backtest/{backtest_id}/analyzers", timeout=5)
        data = json.loads(resp.read())

        print(f"run_id: {data.get('run_id', '')[:32]}...")
        print(f"分析器数量: {len(data.get('analyzers', []))}")

        for analyzer in data.get('analyzers', []):
            name = analyzer.get('name', '?')
            count = analyzer.get('record_count', 0)
            latest = analyzer.get('latest_value')
            print(f"  - {name}: {count} 条记录, 最新值 = {latest}")

        return len(data.get('analyzers', [])) > 0
    except Exception as e:
        print(f"✗ 获取分析器失败: {e}")
        return False


def main():
    print("="*50)
    print("        回测E2E测试 - 通过API")
    print("="*50)

    # 1. 创建Portfolio
    portfolio_id = create_portfolio()
    if not portfolio_id:
        print("\n✗ Portfolio创建失败，终止测试")
        return False

    # 2. 创建并启动回测
    backtest_id = create_backtest(portfolio_id)
    if not backtest_id:
        print("\n✗ 回测创建失败，终止测试")
        return False

    # 3. 等待完成
    success = wait_for_completion(backtest_id)
    if not success:
        print("\n✗ 回测未完成")
        return False

    # 4. 检查分析器
    has_analyzers = check_analyzers(backtest_id)

    print("\n" + "="*50)
    if has_analyzers:
        print("✓✓✓ 测试通过！有分析器数据")
    else:
        print("✗✗✗ 测试失败！无分析器数据")
    print("="*50)

    return has_analyzers


if __name__ == "__main__":
    main()

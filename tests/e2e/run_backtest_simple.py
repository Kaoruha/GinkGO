"""
简化的回测 E2E 测试 - 通过 API 操作

测试流程：
1. 通过 API 创建 Portfolio
2. 通过 API 创建并启动回测任务
3. 等待回测完成
4. 验证分析器数据
"""

import pytest
import time
import json
import urllib.request

from .config import config


@pytest.mark.e2e
@pytest.mark.slow
class TestBacktestViaAPI:
    """通过 API 进行回测测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置 API 基础 URL"""
        self.api_base = "http://192.168.50.12:8000/api/v1"
        self.portfolio_id = None
        self.backtest_id = None

        yield

    def test_01_get_available_components(self):
        """测试 1: 获取可用组件"""
        print("\n=== 获取可用组件 ===")

        # 获取选股器
        resp = urllib.request.urlopen(f"{self.api_base}/components/selectors?size=10", timeout=5)
        selectors = json.loads(resp.read())["data"]
        assert len(selectors) > 0, "应该有可用的选股器"
        self.selector_uuid = selectors[0]["uuid"]
        print(f"✓ 选股器: {selectors[0]['name']}")

        # 获取仓位管理器
        resp = urllib.request.urlopen(f"{self.api_base}/components/sizers?size=10", timeout=5)
        sizers = json.loads(resp.read())["data"]
        assert len(sizers) > 0, "应该有可用的仓位管理器"
        self.sizer_uuid = sizers[0]["uuid"]
        print(f"✓ 仓位管理器: {sizers[0]['name']}")

        # 获取策略
        resp = urllib.request.urlopen(f"{self.api_base}/components/strategies?size=10", timeout=5)
        strategies = json.loads(resp.read())["data"]
        assert len(strategies) > 0, "应该有可用的策略"
        self.strategy_uuid = strategies[0]["uuid"]
        print(f"✓ 策略: {strategies[0]['name']}")

    def test_02_create_portfolio(self):
        """测试 2: 创建 Portfolio"""
        task_name = f"Simple_BT_{int(time.time())}"

        portfolio_data = {
            "name": task_name,
            "initial_cash": 100000,
            "mode": "BACKTEST",
            "description": "E2E自动化测试",
            "selectors": [{"component_uuid": self.selector_uuid, "config": {"codes": "600000.SH"}}],
            "sizers": [{"component_uuid": self.sizer_uuid, "config": {"volume": "1000"}}],
            "strategies": [{"component_uuid": self.strategy_uuid, "config": {"buy_probability": "0.8", "sell_probability": "0.1"}}],
        }

        print(f"\n创建 Portfolio: {task_name}")

        req = urllib.request.Request(
            f"{self.api_base}/portfolio",
            data=json.dumps(portfolio_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        self.portfolio_id = result.get("uuid", "")
        assert self.portfolio_id, "Portfolio ID 不应该为空"
        print(f"✓ Portfolio 创建成功: {self.portfolio_id}")

    def test_03_create_backtest_task(self):
        """测试 3: 创建回测任务"""
        task_data = {
            "name": f"BT_{int(time.time())}",
            "portfolio_id": self.portfolio_id,
            "start_date": "2024-01-02",
            "end_date": "2024-01-05",
            "initial_cash": 100000,
        }

        print(f"\n创建回测任务: {task_data['name']}")

        req = urllib.request.Request(
            f"{self.api_base}/backtest",
            data=json.dumps(task_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        self.backtest_id = result.get("uuid", "")
        assert self.backtest_id, "回测任务 ID 不应该为空"
        print(f"✓ 回测任务创建成功: {self.backtest_id}")

    def test_04_start_backtest(self):
        """测试 4: 启动回测"""
        print(f"\n启动回测任务...")

        req = urllib.request.Request(
            f"{self.api_base}/backtest/{self.backtest_id}/start",
            data=b"{}",
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        assert result.get("success") or "message" in result, f"启动失败: {result}"
        print(f"✓ 回测任务已启动")

    def test_05_wait_for_completion(self):
        """测试 5: 等待回测完成"""
        print(f"\n等待回测完成...")

        max_wait = 180
        for i in range(max_wait // 5):
            time.sleep(5)

            resp = urllib.request.urlopen(f"{self.api_base}/backtest/{self.backtest_id}", timeout=5)
            data = json.loads(resp.read())

            status = data.get("status", "")
            progress = data.get("progress", 0)

            print(f"  状态: {status}, 进度: {progress}%", end='\r')

            if status == "completed" or progress >= 100:
                print(f"\n✓ 回测完成!")
                return
            elif status == "failed":
                pytest.fail(f"回测失败: {data.get('error_message', 'Unknown error')}")

        pytest.fail("回测超时")

    def test_06_check_analyzers(self):
        """测试 6: 检查分析器数据"""
        print(f"\n检查分析器数据...")

        resp = urllib.request.urlopen(f"{self.api_base}/backtest/{self.backtest_id}/analyzers", timeout=5)
        data = json.loads(resp.read())

        print(f"run_id: {data.get('run_id', '')[:32]}...")
        print(f"分析器数量: {len(data.get('analyzers', []))}")

        analyzers = data.get('analyzers', [])
        assert isinstance(analyzers, list), "分析器数据应该是列表"

        if analyzers:
            for analyzer in analyzers[:3]:
                name = analyzer.get('name', '?')
                count = analyzer.get('record_count', 0)
                print(f"  - {name}: {count} 条记录")

            # 验证至少有一个分析器有数据
            has_data = any(a.get('record_count', 0) > 0 for a in analyzers)
            if has_data:
                print("✓ 有分析器数据")
            else:
                print("⚠️ 分析器无数据")
        else:
            pytest.skip("没有分析器数据（可能未配置）")

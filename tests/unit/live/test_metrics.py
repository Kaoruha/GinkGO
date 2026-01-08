"""
监控指标单元测试 (T069)

验证ExecutionNode和Portfolio的监控指标收集功能：
- PortfolioState缓存到Redis
- ExecutionNode状态缓存到Redis
- MetricsCollector功能验证
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ginkgo.workers.execution_node.metrics import MetricsCollector
from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES


@pytest.mark.unit
@pytest.mark.live
class TestMetricsCollector:
    """MetricsCollector单元测试"""

    @pytest.fixture
    def redis_client(self):
        """模拟Redis客户端"""
        return Mock()

    @pytest.fixture
    def metrics_collector(self, redis_client):
        """创建MetricsCollector实例"""
        return MetricsCollector(
            node_id="test_node_001",
            redis_client=redis_client
        )

    def test_collect_metrics_raises_not_implemented(self, metrics_collector):
        """测试collect_metrics()方法抛出NotImplementedError"""
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            metrics_collector.collect_metrics()

    def test_update_portfolio_state_success(self, metrics_collector, redis_client):
        """测试成功更新Portfolio状态到Redis"""
        portfolio_id = "test_portfolio_001"
        state = {
            "status": "RUNNING",
            "queue_size": "100",
            "buffer_size": "5",
            "position_count": "3"
        }

        result = metrics_collector.update_portfolio_state(portfolio_id, state)

        # 验证返回True
        assert result is True

        # 验证Redis hset被调用
        redis_client.hset.assert_called_once()

        # 验证调用参数
        call_args = redis_client.hset.call_args
        assert "portfolio:test_portfolio_001:state" in str(call_args)

    def test_update_portfolio_state_adds_timestamp(self, metrics_collector, redis_client):
        """测试更新Portfolio状态时自动添加时间戳"""
        portfolio_id = "test_portfolio_002"
        state = {"status": "RUNNING"}

        metrics_collector.update_portfolio_state(portfolio_id, state)

        # 获取调用参数中的mapping
        call_args = redis_client.hset.call_args
        mapping = call_args.kwargs.get('mapping') or call_args[1].get('mapping', {})

        # 验证包含last_update字段
        assert 'last_update' in mapping

    def test_update_portfolio_state_failure(self, metrics_collector, redis_client):
        """测试更新Portfolio状态失败处理"""
        portfolio_id = "test_portfolio_003"
        state = {"status": "RUNNING"}

        # 模拟Redis抛出异常
        redis_client.hset.side_effect = Exception("Redis connection error")

        result = metrics_collector.update_portfolio_state(portfolio_id, state)

        # 验证返回False
        assert result is False

    def test_update_node_state_success(self, metrics_collector, redis_client):
        """测试成功更新Node状态到Redis"""
        state = {
            "status": "RUNNING",
            "portfolio_count": "3",
            "queue_usage_70pct": "False"
        }

        result = metrics_collector.update_node_state(state)

        # 验证返回True
        assert result is True

        # 验证Redis hset被调用
        redis_client.hset.assert_called_once()

        # 验证调用参数
        call_args = redis_client.hset.call_args
        assert "execution_node:test_node_001:info" in str(call_args)

    def test_get_portfolio_state_exists(self, metrics_collector, redis_client):
        """测试读取存在的Portfolio状态"""
        portfolio_id = "test_portfolio_004"

        # 模拟Redis返回数据
        redis_client.hgetall.return_value = {
            b"status": b"RUNNING",
            b"queue_size": b"100",
            b"buffer_size": b"0"
        }

        state = metrics_collector.get_portfolio_state(portfolio_id)

        # 验证返回状态字典
        assert state is not None
        assert state["status"] == "RUNNING"
        assert state["queue_size"] == "100"

        # 验证bytes被转换为str
        assert all(isinstance(k, str) for k in state.keys())
        assert all(isinstance(v, str) for v in state.values())

    def test_get_portfolio_state_not_exists(self, metrics_collector, redis_client):
        """测试读取不存在的Portfolio状态"""
        portfolio_id = "test_portfolio_nonexistent"

        # 模拟Redis返回空数据
        redis_client.hgetall.return_value = {}

        state = metrics_collector.get_portfolio_state(portfolio_id)

        # 验证返回None
        assert state is None

    def test_get_node_state_exists(self, metrics_collector, redis_client):
        """测试读取存在的Node状态"""
        # 模拟Redis返回数据
        redis_client.hgetall.return_value = {
            b"status": b"RUNNING",
            b"portfolio_count": b"5",
            b"uptime_seconds": b"3600"
        }

        state = metrics_collector.get_node_state()

        # 验证返回状态字典
        assert state is not None
        assert state["status"] == "RUNNING"
        assert state["portfolio_count"] == "5"

    def test_get_node_state_not_exists(self, metrics_collector, redis_client):
        """测试读取不存在的Node状态"""
        # 模拟Redis返回空数据
        redis_client.hgetall.return_value = {}

        state = metrics_collector.get_node_state()

        # 验证返回None
        assert state is None


@pytest.mark.unit
@pytest.mark.live
class TestExecutionNodeMetrics:
    """ExecutionNode监控功能单元测试"""

    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        return Mock()

    @pytest.fixture
    def execution_node(self, mock_redis):
        """创建ExecutionNode实例（不启动）"""
        node = ExecutionNode(node_id="test_node_metrics")
        # 模拟Redis客户端
        node._get_redis_client = Mock(return_value=mock_redis)
        return node

    def test_update_portfolio_state_updates_redis(self, execution_node, mock_redis):
        """测试_update_portfolio_state()更新Redis"""
        # 创建模拟Portfolio
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.get_status.return_value = PORTFOLIO_RUNSTATE_TYPES.RUNNING
        mock_portfolio.positions = {}

        # 添加到ExecutionNode
        execution_node._portfolio_instances["test_port"] = mock_portfolio
        execution_node.input_queues["test_port"] = Mock()
        execution_node.input_queues["test_port"].qsize.return_value = 150

        # 调用方法
        execution_node._update_portfolio_state("test_port")

        # 验证Redis hset被调用
        mock_redis.hset.assert_called_once()

        # 验证键名正确
        call_args = mock_redis.hset.call_args
        key = call_args[0][0] if call_args[0] else call_args.kwargs.get('key', '')
        assert "portfolio:test_port:state" in key

    def test_update_portfolio_state_missing_portfolio(self, execution_node, mock_redis):
        """测试更新不存在的Portfolio状态"""
        # 调用方法（Portfolio不存在）
        execution_node._update_portfolio_state("nonexistent_port")

        # 验证Redis hset未被调用
        mock_redis.hset.assert_not_called()

    def test_update_all_portfolios_state(self, execution_node, mock_redis):
        """测试_update_all_portfolios_state()批量更新"""
        # 创建多个模拟Portfolio
        for i in range(3):
            portfolio_id = f"test_port_{i}"
            mock_portfolio = Mock(spec=PortfolioLive)
            mock_portfolio.get_status.return_value = PORTFOLIO_RUNSTATE_TYPES.RUNNING
            mock_portfolio.positions = {}

            execution_node._portfolio_instances[portfolio_id] = mock_portfolio
            execution_node.input_queues[portfolio_id] = Mock()
            execution_node.input_queues[portfolio_id].qsize.return_value = i * 100

        # 调用方法
        execution_node._update_all_portfolios_state()

        # 验证Redis hset被调用3次
        assert mock_redis.hset.call_count == 3

    def test_update_node_state_calculates_metrics(self, execution_node, mock_redis):
        """测试_update_node_state()计算正确指标"""
        # 设置ExecutionNode状态
        execution_node.is_running = True
        execution_node.is_paused = False
        execution_node.started_at = datetime.now().isoformat()
        execution_node.portfolios = {"p1": Mock(), "p2": Mock()}

        # 模拟队列大小
        execution_node.input_queues = {
            "p1": Mock(), "p2": Mock()
        }
        execution_node.input_queues["p1"].qsize.return_value = 500
        execution_node.input_queues["p2"].qsize.return_value = 600

        # 调用方法
        execution_node._update_node_state()

        # 验证Redis hset被调用
        mock_redis.hset.assert_called_once()

        # 验证状态字典内容
        call_args = mock_redis.hset.call_args
        mapping = call_args.kwargs.get('mapping') or call_args[1].get('mapping', {})

        assert mapping["status"] == "RUNNING"
        assert int(mapping["portfolio_count"]) == 2
        # 平均队列大小550，不大于700或950
        assert mapping["queue_usage_70pct"] == "False"
        assert mapping["queue_usage_95pct"] == "False"

    def test_update_node_state_stopped(self, execution_node, mock_redis):
        """测试停止状态的Node状态更新"""
        # 设置为停止状态
        execution_node.is_running = False

        # 调用方法
        execution_node._update_node_state()

        # 验证状态为STOPPED
        call_args = mock_redis.hset.call_args
        mapping = call_args.kwargs.get('mapping') or call_args[1].get('mapping', {})

        assert mapping["status"] == "STOPPED"

    def test_update_node_state_paused(self, execution_node, mock_redis):
        """测试暂停状态的Node状态更新"""
        # 设置为暂停状态
        execution_node.is_running = True
        execution_node.is_paused = True

        # 调用方法
        execution_node._update_node_state()

        # 验证状态为PAUSED
        call_args = mock_redis.hset.call_args
        mapping = call_args.kwargs.get('mapping') or call_args[1].get('mapping', {})

        assert mapping["status"] == "PAUSED"


@pytest.mark.unit
@pytest.mark.live
class TestPrometheusIntegration:
    """Prometheus集成预留接口测试"""

    def test_setup_prometheus_exporter_raises_not_implemented(self):
        """测试setup_prometheus_exporter()抛出NotImplementedError"""
        with pytest.raises(NotImplementedError, match="Prometheus"):
            from ginkgo.workers.execution_node.metrics import setup_prometheus_exporter
            setup_prometheus_exporter(port=8000)

    def test_create_prometheus_metrics_raises_not_implemented(self):
        """测试create_prometheus_metrics()抛出NotImplementedError"""
        with pytest.raises(NotImplementedError, match="Prometheus"):
            from ginkgo.workers.execution_node.metrics import create_prometheus_metrics
            create_prometheus_metrics()

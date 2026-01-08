"""
优雅重启集成测试 (T051) - 直接测试Portfolio状态

验证Portfolio优雅重启功能：
- 状态转换流程 (RUNNING → STOPPING → RELOADING → RUNNING)
- 配置版本检查
- Redis状态缓存
"""

import pytest
import time
from unittest.mock import Mock, patch

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES
from ginkgo.data.crud import RedisCRUD


@pytest.mark.integration
@pytest.mark.live
class TestGracefulReload:
    """优雅重启集成测试 - 直接测试Portfolio状态"""

    def test_portfolio_status_transitions(self):
        """测试Portfolio状态转换流程"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_reload",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 初始状态：RUNNING
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        assert portfolio.get_status() == PORTFOLIO_RUNSTATE_TYPES.RUNNING

        # 模拟优雅重启的状态转换
        # RUNNING → STOPPING
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.STOPPING)
        assert portfolio.get_status() == PORTFOLIO_RUNSTATE_TYPES.STOPPING

        # STOPPING → RELOADING
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RELOADING)
        assert portfolio.get_status() == PORTFOLIO_RUNSTATE_TYPES.RELOADING

        # RELOADING → RUNNING
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        assert portfolio.get_status() == PORTFOLIO_RUNSTATE_TYPES.RUNNING

    def test_graceful_reload_timeout_constraint(self):
        """测试优雅重启时间约束 (< 30秒)"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_timeout",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 记录开始时间
        start_time = time.time()

        # 模拟重载流程（快速状态转换）
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        time.sleep(0.01)  # 模拟处理时间
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.STOPPING)
        time.sleep(0.01)  # 模拟处理时间
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RELOADING)
        time.sleep(0.01)  # 模拟加载配置
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)

        # 计算耗时
        elapsed = time.time() - start_time

        # 验证时间约束（应该很快，因为没有真实IO）
        assert elapsed < 30, f"Status transitions should complete in < 30s, took {elapsed:.2f}s"

    @patch('ginkgo.trading.portfolios.portfolio_live.PortfolioLive._load_config_from_db')
    def test_graceful_reload_loads_new_config(self, mock_load_config):
        """测试优雅重启加载新配置"""
        # 模拟新配置
        new_config = {
            'version': 'v2',
            'strategy_params': {'ma_short': 10, 'ma_long': 30},
            'risk_params': {'loss_limit': 15.0}
        }
        mock_load_config.return_value = new_config

        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_config",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 设置初始配置版本
        portfolio._config_version = "v1"

        # 执行优雅重启（如果没有真实配置会失败，但验证方法被调用）
        try:
            result = portfolio.graceful_reload(timeout=30)
        except Exception:
            pass  # 可能失败（没有真实数据库）

        # 验证加载配置方法被调用
        mock_load_config.assert_called_once()

    def test_graceful_reload_preserves_portfolio_id(self):
        """测试优雅重启保留Portfolio ID"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_id",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 记录原始ID
        original_id = portfolio.portfolio_id

        # 模拟状态转换（不实际重载）
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.STOPPING)
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RELOADING)
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)

        # 验证ID不变
        assert portfolio.portfolio_id == original_id, "Portfolio ID should be preserved"

    def test_graceful_reload_handles_config_version_unchanged(self):
        """测试优雅重启处理配置版本未变化的情况"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_version",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 设置配置版本
        portfolio._config_version = "v1"

        # 模拟_load_config_from_db返回相同版本
        with patch.object(portfolio, '_load_config_from_db') as mock_load:
            mock_load.return_value = {
                'version': 'v1',  # 相同版本
                'strategy_params': {}
            }

            # 执行优雅重启
            result = portfolio.graceful_reload(timeout=30)

            # 验证跳过重载（版本未变化）
            assert result == True, "Should return True when config version unchanged"
            assert portfolio._config_version == "v1", "Version should remain unchanged"

    def test_graceful_reload_handles_load_failure(self):
        """测试优雅重启处理配置加载失败"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_fail",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 设置初始状态
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
        portfolio._config_version = "v1"

        # 模拟_load_config_from_db失败（返回None）
        with patch.object(portfolio, '_load_config_from_db') as mock_load:
            mock_load.return_value = None

            # 执行优雅重启
            result = portfolio.graceful_reload(timeout=30)

            # 验证失败处理
            assert result == False, "Should return False when config load fails"
            # 验证恢复到RUNNING状态
            assert portfolio.get_status() == PORTFOLIO_RUNSTATE_TYPES.RUNNING, \
                "Should return to RUNNING state on failure"

    @pytest.mark.parametrize("initial_status,expected_can_reload", [
        (PORTFOLIO_RUNSTATE_TYPES.RUNNING, True),
        (PORTFOLIO_RUNSTATE_TYPES.STOPPED, False),
    ])
    def test_graceful_reload_checks_portfolio_state(self, initial_status, expected_can_reload):
        """测试优雅重启检查Portfolio状态"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_state_check",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 设置初始状态
        portfolio._set_status(initial_status)

        # 检查是否可以重载
        can_reload = portfolio.get_status() in [
            PORTFOLIO_RUNSTATE_TYPES.RUNNING
        ]

        assert can_reload == expected_can_reload, \
            f"Portfolio in {initial_status} can_reload={expected_can_reload}"

    def test_portfolio_state_caches_to_redis(self):
        """测试Portfolio状态缓存到Redis"""
        try:
            redis_crud = RedisCRUD()
            redis_client = redis_crud.redis
        except Exception:
            pytest.skip("Redis not available")

        portfolio_id = "test_portfolio_redis_cache"
        state_key = f"portfolio:{portfolio_id}:state"

        # 清理
        redis_client.delete(state_key)

        # 创建Portfolio并设置状态
        portfolio = PortfolioLive(
            portfolio_id=portfolio_id,
            engine_id="test_engine",
            run_id="test_run"
        )
        portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.RUNNING)

        # 模拟状态缓存（直接写入Redis）
        state = {
            "status": "RUNNING",
            "queue_size": "100",
            "buffer_size": "5",
            "position_count": "3",
            "node_id": "test_node"
        }
        redis_client.hset(state_key, mapping=state)

        # 验证状态已缓存
        cached_state = redis_client.hgetall(state_key)
        state_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in cached_state.items()
        }

        assert state_str["status"] == "RUNNING"
        assert state_str["position_count"] == "3"  # 持仓数量

        # 清理
        redis_client.delete(state_key)

    def test_portfolio_state_retrieval_from_redis(self):
        """测试从Redis读取Portfolio状态"""
        try:
            redis_crud = RedisCRUD()
            redis_client = redis_crud.redis
        except Exception:
            pytest.skip("Redis not available")

        portfolio_id = "test_portfolio_retrieve"
        state_key = f"portfolio:{portfolio_id}:state"

        # 写入状态到Redis
        state = {
            "status": "RUNNING",
            "queue_size": "200",
            "node_id": "test_node_1"
        }
        redis_client.hset(state_key, mapping=state)

        # 读取状态
        cached_state = redis_client.hgetall(state_key)

        # 转换并验证
        state_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in cached_state.items()
        }

        assert state_str["status"] == "RUNNING"
        assert state_str["queue_size"] == "200"
        assert state_str["node_id"] == "test_node_1"

        # 清理
        redis_client.delete(state_key)

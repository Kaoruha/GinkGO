"""#6489: TaskEngineBuilder._load_portfolio_from_task 必须用直调路径获取 portfolio_service。

DynamicContainer 没有 .services 中间层，services.data.services.portfolio_service() 会抛
AttributeError 被 retry 循环吞掉，导致回测/模拟盘引擎装配静默失败。正确路径是
services.data.portfolio_service()（service provider 直接注册在容器顶层）。
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def builder():
    from ginkgo.trading.services._assembly.task_engine_builder import TaskEngineBuilder
    with patch("ginkgo.trading.services._assembly.task_engine_builder.GLOG"):
        return TaskEngineBuilder()


class TestLoadPortfolioServicePath:
    """#6489: service 获取路径回归。"""

    def test_uses_direct_service_path(self, builder):
        """_load_portfolio_from_task 必须走 services.data.portfolio_service() 直调。

        buggy 写法 services.data.services.portfolio_service() 在真实 DynamicContainer
        上抛 AttributeError；本测试只配置直调路径的 mock，断言直调被命中。
        """
        mock_portfolio_service = MagicMock()
        mock_portfolio_service.build_position_writer.return_value = MagicMock()
        mock_portfolio_service.build_redis_writer.return_value = MagicMock()

        mock_assembly = MagicMock()
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        # 非 PortfolioLive 实例 → 走 `return result.data` 分支，避开 _convert 路径
        mock_result.data = "loaded_portfolio"
        mock_assembly.assemble_live_portfolio.return_value = mock_result

        mock_task = MagicMock()
        mock_task.portfolio_uuid = "12345678-aaaa-bbbb-cccc-dddddddddddd"

        with patch("ginkgo.services") as mock_services, \
             patch("ginkgo.trading.services.engine_assembly_service.EngineAssemblyService") as mock_asm_cls:
            # 只配置直调路径
            mock_services.data.portfolio_service.return_value = mock_portfolio_service
            mock_asm_cls.return_value = mock_assembly

            result = builder._load_portfolio_from_task(mock_task)

        # 直调路径必须被命中（buggy code 走 .data.services.portfolio_service 不命中此处）
        mock_services.data.portfolio_service.assert_called_once()
        assert result == "loaded_portfolio"

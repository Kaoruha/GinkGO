"""
TDD tests for BrokerManager.start_broker error path (#5552).

Behavior under test: when the broker CRUD lookup raises, start_broker must
return False gracefully instead of masking the original exception with
UnboundLocalError (``broker`` referenced in the except block before any
assignment in the try block).
"""
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.trading.brokers.broker_manager import BrokerManager


@pytest.fixture
def broker_manager():
    """直接构造 BrokerManager——__init__ 仅初始化空状态，无外部依赖。"""
    return BrokerManager()


class TestStartBrokerErrorPath:
    """#5552: broker CRUD 失败路径不得抛 UnboundLocalError。"""

    @patch("ginkgo.trading.brokers.broker_manager.container.broker_instance_crud")
    def test_no_unbound_local_noise_when_broker_lookup_raises(
        self, mock_broker_crud_factory, broker_manager, monkeypatch
    ):
        """CRUD 查询 broker 抛异常时，错误路径不得泄漏 UnboundLocalError 噪音。

        #5552：``get_broker_by_portfolio`` 抛异常 → ``broker`` 未绑定 →
        except 块访问 ``broker.uuid`` 触发 UnboundLocalError。该异常当前被
        内层 except 吞掉，污染诊断日志（原始 CRUD 异常被 UnboundLocalError 掩盖）。
        修复后应前置 ``broker = None`` 并以 ``if broker is not None`` 守卫，使
        原始异常被干净记录。
        """
        errors = []
        monkeypatch.setattr(
            "ginkgo.trading.brokers.broker_manager.GLOG.ERROR",
            lambda msg, *a, **k: errors.append(str(msg)),
        )

        mock_broker_crud = mock_broker_crud_factory.return_value
        mock_broker_crud.get_broker_by_portfolio.side_effect = RuntimeError("DB connection lost")

        result = broker_manager.start_broker("portfolio-uuid")

        # 仍优雅返回 False
        assert result is False
        # 原始 CRUD 异常必须被记录（诊断可见）
        assert any("DB connection lost" in e for e in errors), errors
        # 不得泄漏 UnboundLocalError（修复前会在此记录二次异常）。
        # 跨 Python 版本鲁棒：3.13+ 消息为 "cannot access local variable 'broker'
        # where it is not associated with a value"，旧版为 "local variable 'broker'
        # referenced before assignment"——共同锚点是 "local variable" + 变量名。
        leaked = [
            e for e in errors
            if "local variable" in e and "broker" in e
        ]
        assert not leaked, f"错误路径泄漏 UnboundLocalError 噪音: {leaked}"

    @patch("ginkgo.trading.brokers.broker_manager.container.broker_instance_crud")
    def test_updates_status_when_broker_found_but_later_step_raises(
        self, mock_broker_crud_factory, broker_manager
    ):
        """broker 查询成功但后续步骤抛异常时，仍应以正确 uuid 更新状态为 error。

        回归锁（#5552 守卫的对称面）：``if broker is not None`` 守卫不得误伤
        正常错误路径——broker 已绑定时，状态更新必须仍以正确 uuid 触发。
        若有人把守卫误写成 ``if broker is None``，本测试会捕获退化。
        """
        mock_broker_crud = mock_broker_crud_factory.return_value
        broker = MagicMock()
        broker.uuid = "broker-uuid-123"
        mock_broker_crud.get_broker_by_portfolio.return_value = broker

        # broker 已在内存注册表（通过 L262 ``broker.uuid in self._brokers`` 检查）
        broker_obj = MagicMock()
        broker_obj.connect.side_effect = RuntimeError("exchange down")
        broker_manager._brokers["broker-uuid-123"] = broker_obj

        result = broker_manager.start_broker("portfolio-uuid")

        assert result is False
        # 外层 except 内：broker 已绑定 → update 仍被调用，uuid 正确
        mock_broker_crud.update_broker_instance_status.assert_any_call(
            "broker-uuid-123", "error", error_message="exchange down"
        )

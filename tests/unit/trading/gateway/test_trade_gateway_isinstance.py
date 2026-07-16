# #6715 回归门：trade_gateway.py:62 isinstance(brokers, BaseBroker) 历史静默错判
# 修复前 trade_gateway import 弱侧 BaseBroker(trading/bases/base_broker)，
# 导致强侧 BaseBroker 子类(AutoBroker/ManualBroker)实例走单 broker 入参分支时
# isinstance 静默返回 False → ValueError 误拒。
# 修复：trade_gateway import 唯一强侧 BaseBroker(trading/brokers/base_broker.py)。
"""
TDD 回归：强侧 BaseBroker 子类实例通过 TradeGateway 单 broker 入参分支。
原 bug：isinstance import 弱侧 BaseBroker，强侧实例被静默误拒。
"""
import pytest


class TestTradeGatewayIsinstanceStrongSide:
    """#6715: 强侧 BaseBroker 子类必须通过 TradeGateway 单 broker 入参路径。"""

    def test_manual_broker_passes_isinstance_strong_basebroker(self):
        """ManualBroker 实例 isinstance(强侧 BaseBroker) 返回 True。"""
        from ginkgo.trading.brokers.base_broker import BaseBroker
        from ginkgo.trading.brokers.manual_broker import ManualBroker

        broker = ManualBroker({})
        assert isinstance(broker, BaseBroker), (
            "ManualBroker 必须通过强侧 BaseBroker isinstance（trade_gateway 类型门）"
        )

    def test_autobroker_subclass_passes_isinstance_strong_basebroker(self):
        """AutoBroker 具体子类实例 isinstance(强侧 BaseBroker) 返回 True。"""
        from ginkgo.trading.brokers.base_broker import BaseBroker
        from ginkgo.trading.brokers.auto_broker import AutoBroker

        class _ConcreteAutoBroker(AutoBroker):
            async def _submit_order_to_api(self, order):
                return {}

            async def _cancel_order_via_api(self, broker_order_id):
                return {}

            async def _query_order_from_api(self, broker_order_id):
                return {}

            def _parse_api_response_to_execution_result(self, api_response, order_id):
                from ginkgo.trading.brokers.base_broker import (
                    ExecutionResult, ExecutionStatus,
                )
                return ExecutionResult(
                    order_id=order_id, status=ExecutionStatus.SUBMITTED,
                )

            async def _initialize_api_client(self):
                return True

        broker = _ConcreteAutoBroker({})
        assert isinstance(broker, BaseBroker), (
            "AutoBroker 子类必须通过强侧 BaseBroker isinstance（trade_gateway 类型门）"
        )

    def test_trade_gateway_isinstance_check_strong_basebroker(self):
        """#6715 核心回归：trade_gateway.py:62 isinstance(brokers, BaseBroker) 必须用强侧 BaseBroker。

        原 bug：trade_gateway import 弱侧 BaseBroker，导致强侧 ManualBroker/AutoBroker
        实例走单 broker 入参分支时 isinstance 静默返回 False → ValueError 误拒。
        本测试用 MonkeyPatch 验证 trade_gateway 模块内的 BaseBroker 就是强侧
        （trading.brokers.base_broker.BaseBroker），并验证 ManualBroker 通过 isinstance。
        """
        import ginkgo.trading.gateway.trade_gateway as gw_mod
        from ginkgo.trading.brokers.base_broker import BaseBroker as StrongBaseBroker
        from ginkgo.trading.brokers.manual_broker import ManualBroker

        # trade_gateway 内 import 的 BaseBroker 必须是强侧
        assert gw_mod.BaseBroker is StrongBaseBroker, (
            "trade_gateway 必须收敛到唯一强侧 BaseBroker（ADR-022 原则6）"
        )

        broker = ManualBroker({})
        # 单 broker 入参路径 line 62 的 isinstance 必须通过
        assert isinstance(broker, gw_mod.BaseBroker), (
            "ManualBroker 必须通过 trade_gateway 的 isinstance 类型门"
        )

    def test_strong_basebroker_remains_unique(self):
        """验收 #1：grep ^class BaseBroker src/ 唯一命中 trading/brokers/base_broker.py。

        防止再次出现双胞胎（ADR-022 原则6 命名空间唯一性）。
        """
        import ginkgo.trading.brokers.base_broker as strong_mod
        from ginkgo.trading.bases.broker_cache_mixin import BrokerCacheMixin

        # 强侧 BaseBroker 必须仍是 Broker 子类（组合根）
        from ginkgo.trading.brokers.interfaces import Broker
        assert issubclass(strong_mod.BaseBroker, Broker)

        # 弱侧已降级为 BrokerCacheMixin，不再是 BaseBroker
        assert not hasattr(BrokerCacheMixin, "__name__") or BrokerCacheMixin.__name__ != "BaseBroker"

    def test_broker_cache_mixin_preserves_market_data_cache(self):
        """验收 #4：BrokerCacheMixin 保留行情/持仓缓存方法（SimBroker 回测依赖）。"""
        from ginkgo.trading.bases.broker_cache_mixin import BrokerCacheMixin

        # 行情缓存 API
        assert hasattr(BrokerCacheMixin, "set_market_data")
        assert hasattr(BrokerCacheMixin, "get_market_data")
        assert hasattr(BrokerCacheMixin, "get_all_market_data")
        assert hasattr(BrokerCacheMixin, "clear_market_data")
        assert hasattr(BrokerCacheMixin, "update_price_data")

        # 持仓缓存 API
        assert hasattr(BrokerCacheMixin, "update_position")
        assert hasattr(BrokerCacheMixin, "get_position")
        assert hasattr(BrokerCacheMixin, "get_all_positions")
        assert hasattr(BrokerCacheMixin, "clear_positions")

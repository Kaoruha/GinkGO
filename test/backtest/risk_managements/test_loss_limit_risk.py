import unittest
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from ginkgo.backtest.risk_managements.loss_limit_risk import LossLimitRisk
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.entities.position import Position
from ginkgo.backtest.execution.events import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class TestLossLimitRisk(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.loss_limit_risk = LossLimitRisk(name="TestLossLimit", loss_limit=15.0)  # 15%止损阈值

        # 模拟投资组合信息
        self.portfolio_info = {
            "uuid": "test_portfolio_id",
            "engine_id": "test_engine_id",
            "now": datetime.now(),
            "cash": 100000,
            "positions": {},
        }

        # 创建测试用的持仓
        self.test_position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,  # 成本价10元
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        # 创建价格更新事件
        self.price_update_event = EventPriceUpdate(
            code="000001.SZ",
            open=8.5,
            high=9.0,
            low=8.0,
            close=8.5,  # 当前价8.5元，亏损15%
            volume=10000,
            timestamp=datetime.now(),
        )

    def test_init(self):
        """测试初始化"""
        risk = LossLimitRisk(loss_limit=20.0)
        self.assertEqual(risk.loss_limit, 20.0)
        self.assertEqual(risk.name, "LossLimitRisk_20.0%")

    def test_cal_order_passthrough(self):
        """测试订单处理方法（应该直接通过）"""
        order = Order()
        order.set(
            "000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
        )

        result = self.loss_limit_risk.cal(self.portfolio_info, order)
        self.assertEqual(result, order)  # 应该原样返回订单

    def test_generate_signals_no_position(self):
        """测试当没有持仓时不生成信号"""
        # 空的持仓字典
        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"] = {}

        signals = self.loss_limit_risk.generate_signals(portfolio_info, self.price_update_event)
        self.assertEqual(len(signals), 0)

    def test_generate_signals_zero_volume_position(self):
        """测试当持仓量为0时不生成信号"""
        # 持仓量为0的持仓
        zero_position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=0,  # 持仓量为0
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = zero_position

        signals = self.loss_limit_risk.generate_signals(portfolio_info, self.price_update_event)
        self.assertEqual(len(signals), 0)

    def test_generate_signals_loss_below_limit(self):
        """测试当亏损未达到阈值时不生成信号"""
        # 创建亏损10%的情况（低于15%阈值）
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        # 价格9元，亏损10%
        event = EventPriceUpdate(
            code="000001.SZ", open=9.0, high=9.2, low=8.8, close=9.0, volume=10000, timestamp=datetime.now()  # 亏损10%
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = self.loss_limit_risk.generate_signals(portfolio_info, event)
        self.assertEqual(len(signals), 0)

    def test_generate_signals_loss_above_limit(self):
        """测试当亏损超过阈值时生成平仓信号"""
        # 持仓成本10元，当前价格8.4元，亏损16%（超过15%阈值）
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        event = EventPriceUpdate(
            code="000001.SZ", open=8.5, high=8.6, low=8.2, close=8.4, volume=10000, timestamp=datetime.now()  # 亏损16%
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = self.loss_limit_risk.generate_signals(portfolio_info, event)

        # 应该生成一个平仓信号
        self.assertEqual(len(signals), 1)

        signal = signals[0]
        self.assertEqual(signal.code, "000001.SZ")
        self.assertEqual(signal.direction, DIRECTION_TYPES.SHORT)  # 平仓
        self.assertEqual(signal.portfolio_id, "test_portfolio_id")
        self.assertEqual(signal.engine_id, "test_engine_id")
        self.assertEqual(signal.source, SOURCE_TYPES.STRATEGY)
        self.assertIn("Loss Limit", signal.reason)
        self.assertIn("16.00%", signal.reason)

    def test_generate_signals_profit_position(self):
        """测试当持仓盈利时不生成止损信号"""
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        # 价格11元，盈利10%
        event = EventPriceUpdate(
            code="000001.SZ",
            open=11.0,
            high=11.2,
            low=10.8,
            close=11.0,  # 盈利10%
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = self.loss_limit_risk.generate_signals(portfolio_info, event)
        self.assertEqual(len(signals), 0)

    def test_generate_signals_invalid_price_data(self):
        """测试价格数据无效时不生成信号"""
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        # 创建没有close价格的事件
        event = EventPriceUpdate(
            code="000001.SZ",
            open=8.5,
            high=9.0,
            low=8.0,
            close=None,  # 无效价格
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        with patch.object(self.loss_limit_risk, "log") as mock_log:
            signals = self.loss_limit_risk.generate_signals(portfolio_info, event)
            self.assertEqual(len(signals), 0)
            mock_log.assert_called_with("WARN", "LossLimitRisk: Invalid price data for 000001.SZ")

    def test_generate_signals_invalid_cost(self):
        """测试成本价无效时不生成信号"""
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=0.0,  # 无效成本
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        with patch.object(self.loss_limit_risk, "log") as mock_log:
            signals = self.loss_limit_risk.generate_signals(portfolio_info, self.price_update_event)
            self.assertEqual(len(signals), 0)
            mock_log.assert_called_with("WARN", "LossLimitRisk: Invalid price data for 000001.SZ")

    def test_generate_signals_non_price_event(self):
        """测试非价格更新事件时不生成信号"""
        # 创建一个非价格更新事件
        non_price_event = Mock()
        non_price_event.event_type = EVENT_TYPES.SIGNALGENERATION
        non_price_event.code = "000001.SZ"

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=10.0,
            volume=1000,
            price=10.0,
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = self.loss_limit_risk.generate_signals(portfolio_info, non_price_event)
        self.assertEqual(len(signals), 0)

    def test_loss_ratio_calculation(self):
        """测试亏损比例计算的准确性"""
        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=100.0,  # 成本价100元
            volume=100,
            price=100.0,
            uuid=uuid.uuid4().hex,
        )

        # 测试各种亏损情况
        test_cases = [
            (90.0, 10.0),  # 90元，亏损10%
            (80.0, 20.0),  # 80元，亏损20%
            (50.0, 50.0),  # 50元，亏损50%
            (30.0, 70.0),  # 30元，亏损70%
        ]

        portfolio_info = self.portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        for current_price, expected_loss_ratio in test_cases:
            event = EventPriceUpdate(
                code="000001.SZ",
                open=current_price,
                high=current_price,
                low=current_price,
                close=current_price,
                volume=10000,
                timestamp=datetime.now(),
            )

            # 使用较高的阈值确保不会触发信号生成，只测试计算
            high_limit_risk = LossLimitRisk(loss_limit=200.0)

            with patch.object(high_limit_risk, "log") as mock_log:
                signals = high_limit_risk.generate_signals(portfolio_info, event)

                # 检查DEBUG日志中的亏损比例计算
                debug_calls = [call for call in mock_log.call_args_list if call[0][0] == "DEBUG"]
                if debug_calls:
                    debug_message = debug_calls[0][0][1]
                    self.assertIn(f"{expected_loss_ratio:.2f}%", debug_message)

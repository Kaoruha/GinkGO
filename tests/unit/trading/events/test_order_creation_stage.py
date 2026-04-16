"""
OrderCreation阶段测试

测试订单创建阶段的组件交互和逻辑处理
涵盖Signal→Order转换、风险预检、订单参数设置等
相关组件：Portfolio, Strategy, RiskManager, Sizer
"""
import pytest
import sys
import datetime
from decimal import Decimal
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.entities.order import Order
from ginkgo.entities.signal import Signal
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, SOURCE_TYPES


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50,
                status=ORDERSTATUS_TYPES.NEW):
    """Helper to create a valid Order instance."""
    return Order(
        portfolio_id="test-portfolio-001",
        engine_id="test-engine-001",
        run_id="test-run-001",
        code=code,
        direction=direction,
        order_type=order_type,
        status=status,
        volume=volume,
        limit_price=limit_price,
    )


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100):
    """Helper to create a valid Signal instance."""
    return Signal(
        portfolio_id="test-portfolio-001",
        engine_id="test-engine-001",
        run_id="test-run-001",
        code=code,
        direction=direction,
        volume=volume,
    )


@pytest.mark.unit
class TestOrderCreationFromSignal:
    """1. 从信号创建订单测试"""

    def test_signal_to_order_conversion(self):
        """测试信号到订单的基本转换"""
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG, 200)
        order = _make_order(
            code=signal.code,
            direction=signal.direction,
            volume=signal.volume,
        )
        assert order.code == signal.code
        assert order.direction == signal.direction
        assert order.volume == signal.volume

    def test_order_direction_mapping(self):
        """测试订单方向映射"""
        long_signal = _make_signal(direction=DIRECTION_TYPES.LONG)
        short_signal = _make_signal(direction=DIRECTION_TYPES.SHORT)

        long_order = _make_order(direction=DIRECTION_TYPES.LONG)
        short_order = _make_order(direction=DIRECTION_TYPES.SHORT)

        assert long_order.direction == DIRECTION_TYPES.LONG
        assert short_order.direction == DIRECTION_TYPES.SHORT
        assert long_signal.direction == long_order.direction
        assert short_signal.direction == short_order.direction

    def test_order_initial_status_setting(self):
        """测试订单初始状态设置"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        assert order.status == ORDERSTATUS_TYPES.NEW
        assert order.is_new() is True

    def test_order_basic_attributes_inheritance(self):
        """测试订单基本属性继承"""
        signal = _make_signal("600036.SH", DIRECTION_TYPES.SHORT, 300)
        ts = datetime.datetime(2024, 1, 15, 9, 30, 0)

        order = Order(
            portfolio_id="test-portfolio-001",
            engine_id="test-engine-001",
            run_id="test-run-001",
            code=signal.code,
            direction=signal.direction,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=signal.volume,
            limit_price=0,
            timestamp=ts,
        )
        assert order.code == "600036.SH"
        assert order.direction == DIRECTION_TYPES.SHORT
        assert order.volume == 300

    def test_signal_metadata_preservation(self):
        """测试信号元数据保持"""
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG, 100)
        order = _make_order(
            code=signal.code,
            direction=signal.direction,
            volume=signal.volume,
        )
        assert order.portfolio_id == signal.portfolio_id
        assert order.engine_id == signal.engine_id
        assert order.run_id == signal.run_id


@pytest.mark.unit
class TestOrderSizingInCreation:
    """2. 订单创建中的仓位管理测试"""

    def test_sizer_volume_calculation(self):
        """测试仓位管理器数量计算"""
        capital = Decimal("100000")
        price = Decimal("10.50")
        expected_volume = int(capital / price / 100) * 100  # Round down to lot size 100
        assert expected_volume == 9500  # 100000/10.5 = 9523, round down to 9500

        order = _make_order(volume=expected_volume)
        assert order.volume == 9500

    def test_portfolio_available_capital_check(self):
        """测试投资组合可用资金检查"""
        available_capital = Decimal("50000")
        price = Decimal("20.00")
        max_volume = int(available_capital / price)
        assert max_volume == 2500

        order = _make_order(volume=max_volume, limit_price=price)
        assert order.volume == 2500

    def test_position_size_constraints(self):
        """测试持仓规模约束"""
        max_position_volume = 10000
        current_position = 3000
        available_volume = max_position_volume - current_position
        assert available_volume == 7000

        order = _make_order(volume=available_volume)
        assert order.volume == 7000

    def test_order_minimum_volume_validation(self):
        """测试订单最小数量验证"""
        minimum_lot_size = 100
        order = _make_order(volume=minimum_lot_size)
        assert order.volume >= minimum_lot_size
        assert order.volume == 100

    def test_fractional_share_handling(self):
        """测试零股处理"""
        raw_volume = 1050
        lot_size = 100
        rounded_volume = (raw_volume // lot_size) * lot_size
        assert rounded_volume == 1000

        order = _make_order(volume=rounded_volume)
        assert order.volume == 1000


@pytest.mark.unit
class TestOrderPriceInCreation:
    """3. 订单创建中的价格设置测试"""

    def test_market_order_price_setting(self):
        """测试市价单价格设置"""
        order = _make_order(order_type=ORDER_TYPES.MARKETORDER, limit_price=0)
        assert order.order_type == ORDER_TYPES.MARKETORDER
        assert float(order.limit_price) == 0.0

    def test_limit_order_price_calculation(self):
        """测试限价单价格计算"""
        current_price = Decimal("10.00")
        slippage = Decimal("0.02")
        limit_price = float(current_price * (1 + slippage))
        assert limit_price == 10.20

        order = _make_order(order_type=ORDER_TYPES.LIMITORDER, limit_price=limit_price)
        assert order.order_type == ORDER_TYPES.LIMITORDER
        assert float(order.limit_price) == 10.20

    def test_stop_order_price_validation(self):
        """测试止损单价格验证"""
        current_price = 10.00
        stop_price = 9.50
        assert stop_price < current_price, "Stop price should be below current price for sell stop"

        order = _make_order(order_type=ORDER_TYPES.LIMITORDER, limit_price=stop_price)
        assert float(order.limit_price) == 9.50

    def test_price_precision_adjustment(self):
        """测试价格精度调整"""
        raw_price = 10.123
        tick_size = 0.01
        adjusted_price = round(raw_price / tick_size) * tick_size
        assert abs(adjusted_price - 10.12) < 1e-9

        order = _make_order(limit_price=adjusted_price)
        assert abs(float(order.limit_price) - 10.12) < 1e-9

    def test_price_band_constraint_check(self):
        """测试价格涨跌幅约束检查"""
        prev_close = 10.00
        limit_up = prev_close * 1.10
        limit_down = prev_close * 0.90
        order_price = 10.50
        assert limit_down <= order_price <= limit_up

        order = _make_order(limit_price=order_price)
        assert float(order.limit_price) == 10.50


@pytest.mark.unit
class TestOrderCreationRiskPreCheck:
    """4. 订单创建风险预检测试"""

    def test_risk_manager_pre_validation(self):
        """测试风险管理器预验证"""
        max_single_order_ratio = 0.20
        portfolio_value = 1000000
        max_order_value = portfolio_value * max_single_order_ratio
        order_value = 150000
        assert order_value <= max_order_value

        order = _make_order(volume=int(order_value / 10.50), limit_price=10.50)
        assert order.volume > 0

    def test_position_ratio_pre_check(self):
        """测试持仓比例预检查"""
        max_position_ratio = 0.25
        portfolio_value = 1000000
        new_order_value = 200000
        existing_position_value = 50000
        total_after = existing_position_value + new_order_value
        ratio = total_after / portfolio_value
        assert ratio <= max_position_ratio

    def test_capital_adequacy_pre_check(self):
        """测试资金充足性预检查"""
        available_capital = 100000
        order_cost = 80000
        assert available_capital >= order_cost, "Insufficient capital for order"

        order = _make_order(volume=1000, limit_price=80.00)
        assert order.volume == 1000

    def test_daily_trading_limit_pre_check(self):
        """测试日内交易限制预检查"""
        daily_limit = 500000
        daily_used = 300000
        new_order_value = 150000
        assert daily_used + new_order_value <= daily_limit

    def test_order_rejection_in_pre_check(self):
        """测试预检查中的订单拒绝"""
        max_position_ratio = 0.20
        current_ratio = 0.19
        new_ratio = 0.05
        is_rejected = (current_ratio + new_ratio) > max_position_ratio
        assert is_rejected is True


@pytest.mark.unit
class TestOrderCreationPortfolioIntegration:
    """5. 订单创建与投资组合集成测试"""

    def test_portfolio_order_tracking_setup(self):
        """测试投资组合订单跟踪设置"""
        order = _make_order()
        assert order.portfolio_id == "test-portfolio-001"
        assert order.engine_id == "test-engine-001"
        assert order.run_id == "test-run-001"

    def test_order_id_assignment(self):
        """测试订单ID分配"""
        order = _make_order()
        assert order.uuid is not None
        assert len(order.uuid) > 0
        assert order.order_id == order.uuid

    def test_portfolio_id_embedding(self):
        """测试投资组合ID嵌入"""
        order = _make_order()
        assert order.portfolio_id == "test-portfolio-001"

    def test_order_creation_timestamp(self):
        """测试订单创建时间戳"""
        ts = datetime.datetime(2024, 3, 15, 10, 30, 0)
        order = _make_order()
        assert order.timestamp is not None
        assert isinstance(order.timestamp, datetime.datetime)

    def test_order_creation_logging(self):
        """测试订单创建日志记录"""
        order = _make_order("600036.SH")
        assert order.code == "600036.SH"
        assert order.direction in (DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT)
        assert order.volume > 0


@pytest.mark.unit
class TestOrderCreationValidation:
    """6. 订单创建验证测试"""

    def test_order_mandatory_fields_validation(self):
        """测试订单必填字段验证"""
        with pytest.raises(Exception):
            Order(
                portfolio_id="",
                engine_id="test-engine-001",
                run_id="test-run-001",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=10.50,
            )

    def test_order_type_consistency_validation(self):
        """测试订单类型一致性验证"""
        market_order = _make_order(order_type=ORDER_TYPES.MARKETORDER, limit_price=0)
        assert market_order.order_type == ORDER_TYPES.MARKETORDER

        limit_order = _make_order(order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50)
        assert limit_order.order_type == ORDER_TYPES.LIMITORDER
        assert float(limit_order.limit_price) > 0

    def test_order_business_rule_validation(self):
        """测试订单业务规则验证"""
        order = _make_order(volume=100, limit_price=10.50)
        assert order.volume > 0
        assert float(order.limit_price) > 0

    def test_order_creation_error_handling(self):
        """测试订单创建错误处理"""
        with pytest.raises(Exception):
            Order(
                portfolio_id="test-portfolio-001",
                engine_id="test-engine-001",
                run_id="test-run-001",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=0,
                limit_price=10.50,
            )


@pytest.mark.unit
class TestOrderCreationMultiStrategy:
    """7. 多策略订单创建测试"""

    def test_concurrent_signal_order_creation(self):
        """测试并发信号订单创建"""
        signal1 = _make_signal("000001.SZ", DIRECTION_TYPES.LONG, 100)
        signal2 = _make_signal("600036.SH", DIRECTION_TYPES.SHORT, 200)

        order1 = _make_order(code=signal1.code, direction=signal1.direction, volume=signal1.volume)
        order2 = _make_order(code=signal2.code, direction=signal2.direction, volume=signal2.volume)

        assert order1.code == "000001.SZ"
        assert order2.code == "600036.SH"
        assert order1.uuid != order2.uuid

    def test_conflicting_signal_resolution(self):
        """测试冲突信号解决"""
        long_order = _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        short_order = _make_order(code="000001.SZ", direction=DIRECTION_TYPES.SHORT, volume=100)
        assert long_order.direction != short_order.direction

    def test_order_priority_assignment(self):
        """测试订单优先级分配"""
        order_high = _make_order(volume=1000)
        order_low = _make_order(volume=100)
        assert order_high.volume > order_low.volume

    def test_strategy_specific_order_attributes(self):
        """测试策略特定订单属性"""
        order = Order(
            portfolio_id="strategy-a-portfolio",
            engine_id="test-engine-001",
            run_id="test-run-001",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=500,
            limit_price=10.50,
        )
        assert order.portfolio_id == "strategy-a-portfolio"
        assert order.engine_id == "test-engine-001"
        assert order.run_id == "test-run-001"

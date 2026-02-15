"""
交易对象工厂 - TDD测试数据生成

提供标准化的测试对象创建，减少测试中的样板代码：
1. 实体对象工厂（订单、持仓、信号）
2. 事件对象工厂（价格更新、交易确认）
3. 投资组合场景工厂（不同市场状况）
4. Protocol接口测试工具
5. Mixin功能测试工具

设计原则：
- 提供合理的默认值
- 支持参数覆盖
- 保证数据一致性
- 简化TDD测试编写

Author: TDD Framework
Created: 2024-01-15
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, Callable
import uuid
import random
from unittest.mock import Mock

# 核心导入
try:
    from ginkgo.trading.entities.order import Order
    from ginkgo.trading.entities.position import Position
    from ginkgo.trading.entities.signal import Signal
    from ginkgo.trading.events.price_update import EventPriceUpdate
    from ginkgo.enums import (
        DIRECTION_TYPES,
        ORDER_TYPES,
        ORDERSTATUS_TYPES,
        SOURCE_TYPES,
        EVENT_TYPES
    )
    GINKGO_AVAILABLE = True
except ImportError:
    GINKGO_AVAILABLE = False


# ===== 辅助函数 =====

def generate_test_uuid(prefix: str = "TEST") -> str:
    """生成带有前缀的测试UUID"""
    return f"{prefix}_{uuid.uuid4()}"


# ===== 实体工厂类 =====

class OrderFactory:
    """订单对象工厂"""

    @staticmethod
    def create_market_order(
        code: str = "000001.SZ",
        direction: DIRECTION_TYPES = DIRECTION_TYPES.LONG,
        volume: int = 1000,
        **overrides
    ) -> Order:
        """创建市价订单"""
        if not GINKGO_AVAILABLE:
            return None

        order = Order(
            portfolio_id=overrides.get("portfolio_id", "test_portfolio"),
            engine_id=overrides.get("engine_id", "test_engine"),
            run_id=overrides.get("run_id", "test_run"),
            code=code,
            direction=direction,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=volume,
            limit_price=overrides.get("limit_price", 0.0),
            timestamp=overrides.get("timestamp", datetime.now())
        )

        used_keys = {"portfolio_id", "engine_id", "run_id", "limit_price", "timestamp"}
        for key, value in overrides.items():
            if key not in used_keys and hasattr(order, key):
                setattr(order, key, value)

        return order

    @staticmethod
    def create_limit_order(
        code: str = "000001.SZ",
        direction: DIRECTION_TYPES = DIRECTION_TYPES.LONG,
        volume: int = 1000,
        limit_price: Decimal = Decimal('10.50'),
        **overrides
    ) -> Order:
        """创建限价订单"""
        if not GINKGO_AVAILABLE:
            return None

        frozen_money = 0.0
        frozen_volume = 0
        if direction == DIRECTION_TYPES.LONG:
            frozen_money = float(limit_price * volume)
        else:
            frozen_volume = volume

        order = Order(
            portfolio_id=overrides.get("portfolio_id", "test_portfolio"),
            engine_id=overrides.get("engine_id", "test_engine"),
            run_id=overrides.get("run_id", "test_run"),
            code=code,
            direction=direction,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=volume,
            limit_price=float(limit_price),
            frozen_money=overrides.get("frozen_money", frozen_money),
            frozen_volume=overrides.get("frozen_volume", frozen_volume),
            timestamp=overrides.get("timestamp", datetime.now())
        )

        used_keys = {"portfolio_id", "engine_id", "run_id", "frozen_money", "frozen_volume", "timestamp"}
        for key, value in overrides.items():
            if key not in used_keys and hasattr(order, key):
                setattr(order, key, value)

        return order

    @staticmethod
    def create_filled_order(
        code: str = "000001.SZ",
        direction: DIRECTION_TYPES = DIRECTION_TYPES.LONG,
        volume: int = 1000,
        transaction_price: Decimal = Decimal('10.50'),
        **overrides
    ) -> Order:
        """创建已成交订单"""
        order = OrderFactory.create_limit_order(
            code=code,
            direction=direction,
            volume=volume,
            limit_price=transaction_price
        )

        if order:
            order.status = ORDERSTATUS_TYPES.FILLED
            order.transaction_volume = volume
            order.transaction_price = transaction_price
            order.fee = transaction_price * volume * Decimal('0.0003')

        for key, value in overrides.items():
            if hasattr(order, key):
                setattr(order, key, value)

        return order


class PositionFactory:
    """持仓对象工厂"""

    @staticmethod
    def create_long_position(
        code: str = "000001.SZ",
        volume: int = 1000,
        average_cost: Decimal = Decimal('10.0'),
        current_price: Decimal = Decimal('10.5'),
        **overrides
    ) -> Position:
        """创建多头持仓"""
        if not GINKGO_AVAILABLE:
            return None

        position = Position()
        position.code = code
        position.volume = volume
        position.average_cost = average_cost
        position.current_price = current_price
        position.market_value = current_price * volume
        position.profit_loss = (current_price - average_cost) * volume
        position.profit_loss_ratio = float((current_price - average_cost) / average_cost)

        for key, value in overrides.items():
            if hasattr(position, key):
                setattr(position, key, value)

        return position

    @staticmethod
    def create_losing_position(
        code: str = "000001.SZ",
        volume: int = 1000,
        loss_ratio: float = 0.15,
        **overrides
    ) -> Position:
        """创建亏损持仓"""
        cost = Decimal('10.0')
        current_price = cost * (1 - Decimal(str(loss_ratio)))

        return PositionFactory.create_long_position(
            code=code,
            volume=volume,
            average_cost=cost,
            current_price=current_price,
            **overrides
        )

    @staticmethod
    def create_profitable_position(
        code: str = "000001.SZ",
        volume: int = 1000,
        profit_ratio: float = 0.25,
        **overrides
    ) -> Position:
        """创建盈利持仓"""
        cost = Decimal('10.0')
        current_price = cost * (1 + Decimal(str(profit_ratio)))

        return PositionFactory.create_long_position(
            code=code,
            volume=volume,
            average_cost=cost,
            current_price=current_price,
            **overrides
        )


class SignalFactory:
    """信号对象工厂"""

    @staticmethod
    def create_buy_signal(
        code: str = "000001.SZ",
        strength: float = 0.8,
        reason: str = "技术指标买入信号",
        **overrides
    ) -> Signal:
        """创建买入信号"""
        if not GINKGO_AVAILABLE:
            return None

        signal = Signal()
        signal.code = code
        signal.direction = DIRECTION_TYPES.LONG
        signal.strength = strength
        signal.reason = reason
        signal.timestamp = datetime.now()
        signal.signal_id = f"buy_signal_{uuid.uuid4().hex[:8]}"

        for key, value in overrides.items():
            if hasattr(signal, key):
                setattr(signal, key, value)

        return signal

    @staticmethod
    def create_sell_signal(
        code: str = "000001.SZ",
        strength: float = 0.8,
        reason: str = "技术指标卖出信号",
        **overrides
    ) -> Signal:
        """创建卖出信号"""
        signal = SignalFactory.create_buy_signal(
            code=code,
            strength=strength,
            reason=reason,
            **overrides
        )

        if signal:
            signal.direction = DIRECTION_TYPES.SHORT

        return signal

    @staticmethod
    def create_risk_signal(
        code: str = "000001.SZ",
        risk_type: str = "stop_loss",
        **overrides
    ) -> Signal:
        """创建风控信号"""
        reason_map = {
            "stop_loss": "止损风控信号",
            "take_profit": "止盈风控信号",
            "position_limit": "仓位限制风控信号"
        }

        return SignalFactory.create_sell_signal(
            code=code,
            strength=1.0,
            reason=reason_map.get(risk_type, f"{risk_type}风控信号"),
            **overrides
        )


class EventFactory:
    """事件对象工厂"""

    @staticmethod
    def create_price_update_event(
        code: str = "000001.SZ",
        open_price: Decimal = Decimal('10.0'),
        high_price: Decimal = Decimal('10.8'),
        low_price: Decimal = Decimal('9.8'),
        close_price: Decimal = Decimal('10.5'),
        volume: int = 100000,
        **overrides
    ) -> EventPriceUpdate:
        """创建价格更新事件"""
        if not GINKGO_AVAILABLE:
            return None

        event = EventPriceUpdate()
        event.code = code
        event.open = open_price
        event.high = high_price
        event.low = low_price
        event.close = close_price
        event.volume = volume
        event.timestamp = datetime.now()

        for key, value in overrides.items():
            if hasattr(event, key):
                setattr(event, key, value)

        return event

    @staticmethod
    def create_price_drop_event(
        code: str = "000001.SZ",
        drop_ratio: float = 0.10,
        base_price: Decimal = Decimal('10.0'),
        **overrides
    ) -> EventPriceUpdate:
        """创建价格下跌事件"""
        new_price = base_price * (1 - Decimal(str(drop_ratio)))

        return EventFactory.create_price_update_event(
            code=code,
            open_price=base_price,
            high_price=base_price,
            low_price=new_price * Decimal('0.98'),
            close_price=new_price,
            **overrides
        )

    @staticmethod
    def create_price_rise_event(
        code: str = "000001.SZ",
        rise_ratio: float = 0.10,
        base_price: Decimal = Decimal('10.0'),
        **overrides
    ) -> EventPriceUpdate:
        """创建价格上涨事件"""
        new_price = base_price * (1 + Decimal(str(rise_ratio)))

        return EventFactory.create_price_update_event(
            code=code,
            open_price=base_price,
            high_price=new_price * Decimal('1.02'),
            low_price=base_price,
            close_price=new_price,
            **overrides
        )


class PortfolioFactory:
    """投资组合工厂"""

    @staticmethod
    def create_basic_portfolio(
        total_value: Decimal = Decimal('100000.0'),
        cash_ratio: float = 0.5,
        positions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """创建基础投资组合"""
        cash = total_value * Decimal(str(cash_ratio))

        if positions is None:
            position_value = total_value * Decimal('0.2')
            positions = [{
                "code": "000001.SZ",
                "volume": 1000,
                "cost": Decimal('20.0'),
                "current_price": Decimal('20.0'),
                "market_value": position_value
            }]

        portfolio = {
            "uuid": f"portfolio_{uuid.uuid4().hex[:8]}",
            "cash": cash,
            "total_value": total_value,
            "positions": {}
        }

        for pos_data in positions:
            code = pos_data["code"]
            portfolio["positions"][code] = {
                "code": code,
                "volume": pos_data["volume"],
                "cost": pos_data["cost"],
                "current_price": pos_data["current_price"],
                "market_value": pos_data["market_value"],
                "profit_loss": (pos_data["current_price"] - pos_data["cost"]) * pos_data["volume"],
                "profit_loss_ratio": float((pos_data["current_price"] - pos_data["cost"]) / pos_data["cost"])
            }

        return portfolio

    @staticmethod
    def create_high_risk_portfolio() -> Dict[str, Any]:
        """创建高风险投资组合"""
        return PortfolioFactory.create_basic_portfolio(
            cash_ratio=0.1,
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 3000,
                    "cost": Decimal('15.0'),
                    "current_price": Decimal('15.0'),
                    "market_value": Decimal('45000.0')
                },
                {
                    "code": "000002.SZ",
                    "volume": 2000,
                    "cost": Decimal('20.0'),
                    "current_price": Decimal('22.5'),
                    "market_value": Decimal('45000.0')
                }
            ]
        )

    @staticmethod
    def create_conservative_portfolio() -> Dict[str, Any]:
        """创建保守投资组合"""
        return PortfolioFactory.create_basic_portfolio(
            cash_ratio=0.8,
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 500,
                    "cost": Decimal('20.0'),
                    "current_price": Decimal('20.0'),
                    "market_value": Decimal('10000.0')
                }
            ]
        )


class MarketScenarioFactory:
    """市场场景工厂"""

    @staticmethod
    def create_bull_market_scenario(days: int = 30) -> List[EventPriceUpdate]:
        """创建牛市场景"""
        events = []
        base_price = Decimal('10.0')
        current_price = base_price

        for i in range(days):
            daily_return = random.uniform(0.01, 0.03)
            current_price *= (1 + Decimal(str(daily_return)))

            event = EventFactory.create_price_update_event(
                open_price=current_price * Decimal('0.99'),
                high_price=current_price * Decimal('1.02'),
                low_price=current_price * Decimal('0.98'),
                close_price=current_price,
                volume=random.randint(80000, 120000)
            )
            events.append(event)

        return events

    @staticmethod
    def create_bear_market_scenario(days: int = 30) -> List[EventPriceUpdate]:
        """创建熊市场景"""
        events = []
        base_price = Decimal('10.0')
        current_price = base_price

        for i in range(days):
            daily_return = random.uniform(-0.04, -0.01)
            current_price *= (1 + Decimal(str(daily_return)))

            event = EventFactory.create_price_update_event(
                open_price=current_price * Decimal('1.01'),
                high_price=current_price * Decimal('1.02'),
                low_price=current_price * Decimal('0.97'),
                close_price=current_price,
                volume=random.randint(100000, 150000)
            )
            events.append(event)

        return events

    @staticmethod
    def create_volatile_market_scenario(days: int = 30) -> List[EventPriceUpdate]:
        """创建震荡市场景"""
        events = []
        base_price = Decimal('10.0')
        current_price = base_price

        for i in range(days):
            daily_return = random.uniform(-0.05, 0.05)
            current_price *= (1 + Decimal(str(daily_return)))

            if current_price > base_price * Decimal('1.2'):
                current_price = base_price * Decimal('1.2')
            elif current_price < base_price * Decimal('0.8'):
                current_price = base_price * Decimal('0.8')

            event = EventFactory.create_price_update_event(
                close_price=current_price,
                volume=random.randint(60000, 140000)
            )
            events.append(event)

        return events


# ===== 增强框架工厂 =====

class EnhancedEventFactory:
    """增强事件工厂 - 支持事件上下文和追踪"""

    @staticmethod
    def create_enhanced_price_update_event(
        code: str = "000001.SZ",
        close_price: Decimal = Decimal('10.5'),
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        engine_id: str = "test_engine",
        run_id: str = "test_run",
        sequence_number: int = 1,
        **overrides
    ) -> EventPriceUpdate:
        """创建增强的价格更新事件"""
        event = EventFactory.create_price_update_event(
            code=code,
            close_price=close_price,
            **overrides
        )

        if event:
            event.correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:8]}"
            event.causation_id = causation_id
            event.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
            event.engine_id = engine_id
            event.run_id = run_id
            event.sequence_number = sequence_number
            event.event_type = "price_update"

        return event

    @staticmethod
    def create_event_chain(
        code: str = "000001.SZ",
        start_price: Decimal = Decimal('10.0'),
        price_changes: List[float] = None,
        **kwargs
    ) -> List[EventPriceUpdate]:
        """创建事件链条"""
        if price_changes is None:
            price_changes = [0.01, 0.02, -0.01, 0.03]

        events = []
        current_price = start_price
        correlation_id = kwargs.get('correlation_id', f"chain_{uuid.uuid4().hex[:8]}")

        for i, change in enumerate(price_changes):
            current_price *= (1 + Decimal(str(change)))
            event = EnhancedEventFactory.create_enhanced_price_update_event(
                code=code,
                close_price=current_price,
                correlation_id=correlation_id,
                causation_id=events[-1].correlation_id if events else None,
                sequence_number=i + 1,
                **kwargs
            )
            events.append(event)

        return events


class ProtocolTestFactory:
    """Protocol接口测试工厂"""

    @staticmethod
    def create_strategy_implementation(
        strategy_name: str = "TestStrategy",
        implementation_type: str = "basic"
    ):
        """创建策略实现用于Protocol测试"""
        if implementation_type == "basic":
            class TestStrategy:
                def __init__(self):
                    self.name = strategy_name

                def cal(self, portfolio_info, event):
                    return []

                def get_strategy_info(self):
                    return {"name": self.name, "type": "basic"}

                def validate_parameters(self, params):
                    return True

                def initialize(self, context):
                    pass

                def finalize(self):
                    return {}

            return TestStrategy()

        elif implementation_type == "advanced":
            class AdvancedTestStrategy:
                def __init__(self):
                    self.name = strategy_name
                    self.signals_generated = []

                def cal(self, portfolio_info, event):
                    if hasattr(event, 'code') and hasattr(event, 'close_price'):
                        if float(event.close_price) > 10.0:
                            signal = SignalFactory.create_buy_signal(code=event.code)
                            self.signals_generated.append(signal)
                            return [signal]
                    return []

                def get_strategy_info(self):
                    return {
                        "name": self.name,
                        "type": "advanced",
                        "signals_count": len(self.signals_generated)
                    }

                def validate_parameters(self, params):
                    required_params = ['threshold', 'max_position']
                    return all(param in params for param in required_params)

                def initialize(self, context):
                    self.context = context

                def finalize(self):
                    return {
                        "total_signals": len(self.signals_generated),
                        "context": getattr(self, 'context', {})
                    }

            return AdvancedTestStrategy()

    @staticmethod
    def create_risk_manager_implementation(
        manager_name: str = "TestRiskManager",
        risk_type: str = "position_ratio"
    ):
        """创建风控管理器实现用于Protocol测试"""
        if risk_type == "position_ratio":
            class TestPositionRatioRiskManager:
                def __init__(self):
                    self.name = manager_name
                    self.max_position_ratio = 0.2
                    self.max_total_position_ratio = 0.8

                def validate_order(self, portfolio_info, order):
                    total_value = portfolio_info.get('total_value', 100000)
                    order_value = getattr(order, 'volume', 0) * getattr(order, 'limit_price', 0)
                    max_allowed = total_value * self.max_position_ratio

                    if order_value > max_allowed:
                        adjusted_quantity = int(max_allowed / (getattr(order, 'limit_price', 1) or 1))
                        if hasattr(order, 'volume'):
                            order.volume = max(adjusted_quantity, 0)

                    return order

                def generate_risk_signals(self, portfolio_info, event):
                    return []

                def check_risk_limits(self, portfolio_info):
                    return []

                def update_risk_parameters(self, parameters):
                    self.max_position_ratio = parameters.get('max_position_ratio', 0.2)

                def get_risk_metrics(self, portfolio_info):
                    return {"max_position_ratio": self.max_position_ratio}

            return TestPositionRatioRiskManager()

        elif risk_type == "stop_loss":
            class TestStopLossRiskManager:
                def __init__(self):
                    self.name = manager_name
                    self.loss_limit = 0.1

                def validate_order(self, portfolio_info, order):
                    return order

                def generate_risk_signals(self, portfolio_info, event):
                    signals = []
                    positions = portfolio_info.get('positions', {})

                    for code, position in positions.items():
                        if position.get('profit_loss_ratio', 0) < -self.loss_limit:
                            signal = SignalFactory.create_sell_signal(
                                code=code,
                                reason=f"止损: 亏损超过{self.loss_limit:.1%}"
                            )
                            signals.append(signal)

                    return signals

                def check_risk_limits(self, portfolio_info):
                    return []

                def update_risk_parameters(self, parameters):
                    self.loss_limit = parameters.get('loss_limit', 0.1)

                def get_risk_metrics(self, portfolio_info):
                    return {"loss_limit": self.loss_limit}

            return TestStopLossRiskManager()

        # 默认返回一个基本的Mock对象
        risk_manager = Mock()
        risk_manager.name = manager_name
        risk_manager.validate_order = Mock(return_value=None)
        risk_manager.generate_risk_signals = Mock(return_value=[])
        risk_manager.check_risk_limits = Mock(return_value=[])
        risk_manager.update_risk_parameters = Mock()
        risk_manager.get_risk_metrics = Mock(return_value={})
        return risk_manager


class MixinTestFactory:
    """Mixin功能测试工厂"""

    @staticmethod
    def create_strategy_with_mixin(base_class=None, mixin_classes=None):
        """创建带有Mixin的策略类"""
        if base_class is None:
            class BaseStrategy:
                def __init__(self):
                    self.name = "BaseStrategy"

                def cal(self, portfolio_info, event):
                    return []

            base_class = BaseStrategy

        if mixin_classes is None:
            mixin_classes = []

        class EnhancedStrategy(base_class, *mixin_classes):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for mixin_class in mixin_classes:
                    if hasattr(mixin_class, '__init__'):
                        mixin_class.__init__(self)

        return EnhancedStrategy

    @staticmethod
    def create_portfolio_with_enhancement(
        portfolio_class=None,
        enhancement_features=None
    ):
        """创建增强功能的投资组合"""
        if portfolio_class is None:
            class BasePortfolio:
                def __init__(self):
                    self.name = "BasePortfolio"
                    self.positions = {}
                    self.cash = Decimal('100000')

                def get_portfolio_info(self):
                    return {
                        "name": self.name,
                        "positions": self.positions,
                        "cash": self.cash
                    }

            portfolio_class = BasePortfolio

        if enhancement_features is None:
            enhancement_features = ['event_enhancement', 'time_provider']

        class EnhancedPortfolio(portfolio_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.enhancement_features = enhancement_features
                self.event_history = []

            def process_enhanced_event(self, event):
                if 'event_enhancement' in self.enhancement_features:
                    self.event_history.append({
                        'event': event,
                        'timestamp': datetime.now()
                    })

                return None

        return EnhancedPortfolio


# ===== test_utils.py 需要的额外工厂类 =====

class TradingDataFactory:
    """量化交易数据工厂"""

    def __init__(self, config=None):
        """初始化工厂"""
        self.config = config or MockDataConfig()
        self._order_counter = 0
        self._position_counter = 0
        self._signal_counter = 0

    def create_orders(self, portfolio_id: str = "test_portfolio", count: int = None) -> List[Order]:
        """创建订单数据"""
        if count is None:
            count = self.config.count

        orders = []
        for i in range(count):
            self._order_counter += 1
            symbol = self.config.symbols[i % len(self.config.symbols)]
            order = OrderFactory.create_limit_order(
                code=symbol,
                volume=random.randint(100, 1000),
                limit_price=self.config.initial_price * (1 + Decimal(str(random.uniform(-0.1, 0.1)))),
                portfolio_id=portfolio_id
            )
            orders.append(order)

        return orders

    def create_positions(self, count: int = None) -> List[Position]:
        """创建持仓数据"""
        if count is None:
            count = self.config.count

        positions = []
        for i in range(count):
            self._position_counter += 1
            symbol = self.config.symbols[i % len(self.config.symbols)]
            position = PositionFactory.create_long_position(
                code=symbol,
                volume=random.randint(100, 1000),
                average_cost=self.config.initial_price,
                current_price=self.config.initial_price * (1 + Decimal(str(random.uniform(-0.2, 0.2))))
            )
            positions.append(position)

        return positions

    def create_signals(self, count: int = None) -> List[Signal]:
        """创建信号数据"""
        if count is None:
            count = self.config.count

        signals = []
        for i in range(count):
            self._signal_counter += 1
            symbol = self.config.symbols[i % len(self.config.symbols)]
            if random.random() > 0.5:
                signal = SignalFactory.create_buy_signal(code=symbol)
            else:
                signal = SignalFactory.create_sell_signal(code=symbol)
            signals.append(signal)

        return signals

    def create_portfolio_info(self) -> Dict[str, Any]:
        """创建投资组合信息"""
        return {
            "uuid": generate_test_uuid("portfolio"),
            "cash": Decimal('50000.0'),
            "total_value": Decimal('100000.0'),
            "positions": {},
            "risk_metrics": {
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0
            }
        }


class MockDataConfig:
    """模拟数据配置"""

    def __init__(
        self,
        count: int = 10,
        start_date: datetime = None,
        end_date: datetime = None,
        symbols: List[str] = None,
        initial_price: Decimal = Decimal("10.0"),
        volatility: Decimal = Decimal("0.02")
    ):
        self.count = count
        self.start_date = start_date or datetime(2024, 1, 1)
        self.end_date = end_date or datetime(2024, 12, 31)
        self.symbols = symbols or ["000001.SZ", "000002.SZ"]
        self.initial_price = initial_price
        self.volatility = volatility


class ProtocolTestHelper:
    """Protocol接口测试辅助类"""

    def create_mock_strategy(self):
        """创建模拟策略"""
        strategy = Mock()
        strategy.name = "MockStrategy"
        strategy.cal = Mock(return_value=[])
        strategy.validate_parameters = Mock(return_value=True)
        strategy.get_strategy_info = Mock(return_value={"name": "MockStrategy", "type": "mock"})
        return strategy

    def create_mock_risk_manager(self):
        """创建模拟风控管理器"""
        risk_manager = Mock()
        risk_manager.name = "MockRiskManager"
        risk_manager.validate_order = Mock(return_value=None)
        risk_manager.generate_risk_signals = Mock(return_value=[])
        risk_manager.check_risk_limits = Mock(return_value=[])
        return risk_manager

    def create_mock_portfolio(self):
        """创建模拟投资组合"""
        portfolio = Mock()
        portfolio.name = "MockPortfolio"
        portfolio.add_strategy = Mock(return_value=None)
        portfolio.get_portfolio_info = Mock(return_value={"total_value": 100000.0})
        return portfolio

    def create_mock_engine(self):
        """创建模拟引擎"""
        engine = Mock()
        engine.name = "MockEngine"
        engine.start = Mock(return_value=True)
        engine.run = Mock(return_value={"status": "completed"})
        return engine


class MixinTestHelper:
    """Mixin功能测试辅助类"""

    def create_test_class_with_mixin(self, base_class, mixin_class):
        """创建包含Mixin的测试类"""
        class_name = f"{base_class.__name__}_With_{mixin_class.__name__}"

        class CombinedClass(base_class, mixin_class):
            pass

        CombinedClass.__name__ = class_name
        return CombinedClass

    def validate_mixin_integration(self, instance, mixin_class, base_class):
        """验证Mixin集成"""
        errors = []

        # 检查是否是基类实例
        if not isinstance(instance, base_class):
            errors.append(f"实例不是{base_class.__name__}的实例")

        # 检查Mixin方法是否存在
        for attr_name in dir(mixin_class):
            if not attr_name.startswith('_') and callable(getattr(mixin_class, attr_name, None)):
                if not hasattr(instance, attr_name):
                    errors.append(f"缺少Mixin方法: {attr_name}")

        return len(errors) == 0, errors


class TypeSafetyValidator:
    """类型安全验证器"""

    def validate_method_signatures(self, instance, expected_methods: Dict[str, Any]) -> tuple:
        """验证方法签名"""
        import inspect
        errors = []

        for method_name, expected_sig in expected_methods.items():
            if not hasattr(instance, method_name):
                errors.append(f"缺少方法: {method_name}")
                continue

            actual_sig = inspect.signature(getattr(instance, method_name))
            # 简化验证，只检查参数数量
            if len(actual_sig.parameters) != len(expected_sig.parameters):
                errors.append(f"方法{method_name}签名不匹配")

        return len(errors) == 0, errors

    def validate_return_types(self, instance, method_name: str, expected_type: Type) -> bool:
        """验证返回类型"""
        method = getattr(instance, method_name, None)
        if method is None:
            return False

        try:
            result = method()
            return isinstance(result, expected_type)
        except Exception:
            return False


class TestScenarioBuilder:
    """测试场景构建器"""

    def build_strategy_test_scenario(self, scenario_type: str = "basic") -> Dict[str, Any]:
        """构建策略测试场景"""
        return {
            "portfolio_info": PortfolioFactory.create_basic_portfolio(),
            "market_event": EventFactory.create_price_update_event(),
            "expected_signals": [],
            "scenario_type": scenario_type
        }

    def build_risk_test_scenario(self, risk_type: str = "position_limit") -> Dict[str, Any]:
        """构建风控测试场景"""
        return {
            "portfolio_info": PortfolioFactory.create_basic_portfolio(),
            "order": OrderFactory.create_limit_order(),
            "risk_type": risk_type
        }

    def build_portfolio_test_scenario(self, state: str = "normal") -> Dict[str, Any]:
        """构建投资组合测试场景"""
        return {
            "portfolio_info": PortfolioFactory.create_basic_portfolio(),
            "signals": [],
            "state": state
        }


class AssertionHelper:
    """断言辅助类"""

    def assert_financial_precision(self, actual: Decimal, expected: Decimal, places: int = 4):
        """断言金融精度"""
        tolerance = Decimal(10) ** -places
        if abs(actual - expected) > tolerance:
            raise AssertionError(f"金融精度不匹配: {actual} != {expected} (容差: {tolerance})")

    def assert_list_not_empty(self, items: List):
        """断言列表非空"""
        if not items:
            raise AssertionError("列表为空")

    def assert_dict_contains_keys(self, data: Dict, keys: List[str]):
        """断言字典包含指定键"""
        missing = [k for k in keys if k not in data]
        if missing:
            raise AssertionError(f"缺少键: {missing}")

    def assert_datetime_range(self, dt: datetime, start: datetime, end: datetime):
        """断言时间在范围内"""
        if not (start <= dt <= end):
            raise AssertionError(f"时间{dt}不在范围[{start}, {end}]内")


# ===== 导出列表 =====

__all__ = [
    # 辅助函数
    'generate_test_uuid',

    # 实体工厂
    'OrderFactory',
    'PositionFactory',
    'SignalFactory',
    'EventFactory',
    'PortfolioFactory',
    'MarketScenarioFactory',

    # 增强工厂
    'EnhancedEventFactory',
    'ProtocolTestFactory',
    'MixinTestFactory',

    # 测试工具类
    'TradingDataFactory',
    'MockDataConfig',
    'ProtocolTestHelper',
    'MixinTestHelper',
    'TypeSafetyValidator',
    'TestScenarioBuilder',
    'AssertionHelper',
]

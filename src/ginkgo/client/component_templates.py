# Upstream: component_cli.py（_generate_component_code调用）
# Downstream: 无（纯模板代码生成，不依赖其他业务模块）
# Role: 组件代码模板生成，为各种交易组件类型提供标准化的Python代码模板


"""
Ginkgo Component Templates - 组件代码模板生成函数
为策略、风控、选股器、仓位管理器、分析器等组件提供代码模板
"""


def _get_basic_strategy_template(name: str, class_name: str) -> str:
    """基础策略模板"""
    return f'''"""
{name} Strategy
基础策略模板
"""

import datetime
from ginkgo.backtest.execution.events import EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {class_name}(BaseStrategy):
    """
    {name} 策略
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        # 初始化策略参数
        self._window = 20

    def cal(self, portfolio_info, event, *args, **kwargs):
        """策略计算逻辑"""
        super({class_name}, self).cal(portfolio_info, event)

        # 获取历史数据
        date_start = self.now + datetime.timedelta(days=-self._window - 5)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end)

        if len(df) < self._window:
            return []  # 数据不足

        # 策略逻辑示例
        current_price = df['close'].iloc[-1]
        ma = df['close'].rolling(window=self._window).mean().iloc[-1]

        signals = []
        if current_price > ma:
            signal = Signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=current_price,
                weight=1.0,
                reason="Price > Moving Average"
            )
            signals.append(signal)

        return signals

    def reset_state(self):
        """重置策略状态"""
        super().reset_state()
        # 重置自定义状态变量
        pass
'''


def _get_ma_strategy_template(name: str, class_name: str) -> str:
    """移动平均策略模板"""
    return f'''"""
{name} Moving Average Strategy
移动平均交叉策略模板
"""

import datetime
from ginkgo.backtest.execution.events import EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {class_name}(BaseStrategy):
    """
    {name} 移动平均策略
    当短期均线上穿长期均线时买入，下穿时卖出
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", short_window: int = 5, long_window: int = 20, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self._short_window = short_window
        self._long_window = long_window
        self._prev_short_ma = None
        self._prev_long_ma = None

    def cal(self, portfolio_info, event, *args, **kwargs):
        """策略计算逻辑"""
        super({class_name}, self).__init__(portfolio_info, event)

        date_start = self.now + datetime.timedelta(days=-self._long_window - 5)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end)

        if len(df) < self._long_window:
            return []

        # 计算移动平均线
        df['ma_short'] = df['close'].rolling(window=self._short_window).mean()
        df['ma_long'] = df['close'].rolling(window=self._long_window).mean()

        current_short_ma = df['ma_short'].iloc[-1]
        current_long_ma = df['ma_long'].iloc[-1]

        signals = []

        # 金叉：短期均线上穿长期均线（买入）
        if (self._prev_short_ma is not None and self._prev_long_ma is not None and
            self._prev_short_ma <= self._prev_long_ma and current_short_ma > current_long_ma):

            signal = Signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                weight=1.0,
                reason=f"Golden Cross: MA({current_short_ma:.2f}) > MA({current_long_ma:.2f})"
            )
            signals.append(signal)

        # 死叉：短期均线下穿长期均线（卖出）
        elif (self._prev_short_ma is not None and self._prev_long_ma is not None and
              self._prev_short_ma >= self._prev_long_ma and current_short_ma < current_long_ma):

            signal = Signal(
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                weight=1.0,
                reason=f"Death Cross: MA({current_short_ma:.2f}) < MA({current_long_ma:.2f})"
            )
            signals.append(signal)

        # 更新历史值
        self._prev_short_ma = current_short_ma
        self._prev_long_ma = current_long_ma

        return signals

    def reset_state(self):
        """重置策略状态"""
        super().reset_state()
        self._prev_short_ma = None
        self._prev_long_ma = None
'''


def _get_basic_risk_template(name: str, class_name: str) -> str:
    """基础风控模板"""
    return f'''"""
{name} Risk Manager
基础风控管理器模板
"""

from ginkgo.backtest.strategy.risk_managements.base_risk_management import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class {class_name}(BaseRiskManagement):
    """
    {name} 风控管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", max_position_ratio: float = 0.2, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.max_position_ratio = max_position_ratio

    def cal(self, portfolio_info: dict, order: Order) -> Order:
        """订单拦截和修改"""
        if order.volume == 0:
            return order

        # 计算允许的最大仓位
        total_value = portfolio_info.get('total_value', 0)
        max_volume = int(total_value * self.max_position_ratio / order.price)

        # 限制订单数量
        if order.volume > max_volume:
            order.volume = max_volume

        return order

    def generate_signals(self, portfolio_info: dict, event) -> list:
        """生成风控信号"""
        signals = []
        # 实现具体的风控逻辑
        return signals

    def reset_state(self):
        """重置风控状态"""
        super().reset_state()
        pass
'''


def _get_stoploss_risk_template(name: str, class_name: str) -> str:
    """止损风控模板"""
    return f'''"""
{name} Stop Loss Risk Manager
动态止损风控管理器模板
"""

import datetime
from ginkgo.backtest.strategy.risk_managements.base_risk_management import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {class_name}(BaseRiskManagement):
    """
    {name} 止损风控管理器
    基于ATR的动态止损策略
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", atr_period: int = 14,
                 stop_loss_multiplier: float = 2.0, max_drawdown: float = 0.05, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.atr_period = atr_period
        self.stop_loss_multiplier = stop_loss_multiplier
        self.max_drawdown = max_drawdown
        self._position_entries = {{}}
        self._highest_prices = {{}}

    def cal(self, portfolio_info: dict, order: Order) -> Order:
        """订单拦截和修改"""
        # 仓位限制
        max_position_ratio = portfolio_info.get('max_position_ratio', 0.2)
        if order.volume > 1000:  # 简单的仓位限制
            order.volume = 1000
        return order

    def generate_signals(self, portfolio_info: dict, event) -> list:
        """生成止损信号"""
        signals = []
        code = event.code
        current_price = event.price
        current_position = portfolio_info.get('positions', {{}}).get(code, 0)

        if current_position == 0:
            self._position_entries.pop(code, None)
            self._highest_prices.pop(code, None)
            return signals

        # 初始化持仓信息
        if code not in self._position_entries:
            entry_price = portfolio_info.get('avg_prices', {{}}).get(code, current_price)
            self._position_entries[code] = {{
                'entry_price': entry_price,
                'stop_loss': entry_price - (self._calculate_atr(code) * self.stop_loss_multiplier),
                'position': current_position
            }}
            self._highest_prices[code] = entry_price
            return signals

        position_info = self._position_entries[code]
        stop_loss_price = position_info['stop_loss']

        # 更新最高价（用于追踪止损）
        if current_position > 0:  # 多头
            if current_price > self._highest_prices[code]:
                self._highest_prices[code] = current_price
                # 更新追踪止损
                new_stop_loss = self._highest_prices[code] - (self._calculate_atr(code) * self.stop_loss_multiplier)
                if new_stop_loss > position_info['stop_loss']:
                    position_info['stop_loss'] = new_stop_loss

            # 检查止损触发
            if current_price <= position_info['stop_loss']:
                signals.append(Signal(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,  # 平仓
                    source=SOURCE_TYPES.RISK,
                    datetime=datetime.datetime.now(),
                    price=current_price,
                    volume=abs(current_position),
                    reason=f"Stop Loss: Price({{current_price:.2f}}) <= Stop({{position_info['stop_loss']:.2f}})"
                ))

        return signals

    def _calculate_atr(self, code: str) -> float:
        """计算ATR"""
        try:
            date_start = datetime.datetime.now() - datetime.timedelta(days=self.atr_period * 2)
            date_end = datetime.datetime.now()
            df = get_bars(code, date_start, date_end)

            if len(df) < self.atr_period:
                return 0.0

            df['tr'] = df[['high-low', 'high-close', 'low-close']].max(axis=1)
            return df['tr'].rolling(window=self.atr_period).mean().iloc[-1]
        except Exception as e:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"计算ATR失败: {e}")
            return 0.0

    def reset_state(self):
        """重置风控状态"""
        super().reset_state()
        self._position_entries.clear()
        self._highest_prices.clear()
'''


def _get_basic_selector_template(name: str, class_name: str) -> str:
    """基础选股器模板"""
    return f'''"""
{name} Selector
基础选股器模板
"""

from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector
from ginkgo.data import get_stockinfos


class {class_name}(BaseSelector):
    """
    {name} 选股器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)

    def select(self, universe: list, *args, **kwargs) -> list:
        """选股逻辑"""
        # 简单示例：返回所有股票
        return universe

    def reset_state(self):
        """重置选股器状态"""
        super().reset_state()
        pass
'''


def _get_basic_sizer_template(name: str, class_name: str) -> str:
    """基础仓位管理器模板"""
    return f'''"""
{name} Sizer
基础仓位管理器模板
"""

from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer
from ginkgo.backtest.entities.order import Order


class {class_name}(BaseSizer):
    """
    {name} 仓位管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", fixed_size: int = 100, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.fixed_size = fixed_size

    def size(self, order: Order) -> int:
        """计算仓位大小"""
        return self.fixed_size

    def reset_state(self):
        """重置仓位管理器状态"""
        super().reset_state()
        pass
'''


def _get_basic_analyzer_template(name: str, class_name: str) -> str:
    """基础分析器模板"""
    return f'''"""
{name} Analyzer
基础分析器模板
"""

from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer


class {class_name}(BaseAnalyzer):
    """
    {name} 分析器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)

    def _do_activate(self):
        """激活分析器"""
        # 实现分析逻辑
        pass

    def _do_record(self, event, *args, **kwargs):
        """记录事件"""
        # 实现数据记录
        pass

    def _do_deactivate(self):
        """停用分析器"""
        # 实现清理逻辑
        pass

    def reset_state(self):
        """重置分析器状态"""
        super().reset_state()
        pass
'''


def _get_rsi_strategy_template(name: str, class_name: str) -> str:
    """RSI策略模板"""
    return f'''"""
{name} RSI Strategy
RSI超买超卖策略模板
"""

import datetime
from ginkgo.backtest.execution.events import EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {class_name}(BaseStrategy):
    """
    {name} RSI策略
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", rsi_period: int = 14, oversold: float = 30, overbought: float = 70, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def cal(self, portfolio_info, event, *args, **kwargs):
        """策略计算逻辑"""
        super({class_name}, self).__init__(portfolio_info, event)

        date_start = self.now + datetime.timedelta(days=-self.rsi_period * 2)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end)

        if len(df) < self.rsi_period:
            return []

        # 计算RSI
        df['change'] = df['close'].diff()
        df['gain'] = df['change'].where(df['change'] > 0, 0)
        df['loss'] = -df['change'].where(df['change'] < 0, 0)
        df['avg_gain'] = df['gain'].rolling(window=self.rsi_period).mean()
        df['avg_loss'] = df['loss'].rolling(window=self.rsi_period).mean()
        df['rs'] = 100 - (100 / (1 + df['avg_gain'] / df['avg_loss']))
        current_rsi = df['rs'].iloc[-1]

        signals = []
        if current_rsi < self.oversold:
            signals.append(Signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                reason=f"RSI Oversold: {{current_rsi:.2f}} < {{self.oversold}}"
            ))
        elif current_rsi > self.overbought:
            signals.append(Signal(
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                reason=f"RSI Overbought: {{current_rsi:.2f}} > {{self.overbought}}"
            ))

        return signals

    def reset_state(self):
        """重置策略状态"""
        super().reset_state()
        pass
'''


def _get_momentum_strategy_template(name: str, class_name: str) -> str:
    """动量策略模板"""
    return f'''"""
{name} Momentum Strategy
动量策略模板
"""

import datetime
from ginkgo.backtest.execution.events import EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {class_name}(BaseStrategy):
    """
    {name} 动量策略
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", lookback_period: int = 20, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.lookback_period = lookback_period

    def cal(self, portfolio_info, event, *args, **kwargs):
        """策略计算逻辑"""
        super({class_name}, self).__init__(portfolio_info, event)

        date_start = self.now + datetime.timedelta(days=-self.lookback_period)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end)

        if len(df) < self.lookback_period:
            return []

        # 计算动量
        df['returns'] = df['close'].pct_change()
        momentum = df['returns'].sum()  # 简单的动量计算

        signals = []
        if momentum > 0:
            signals.append(Signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                weight=abs(momentum),
                reason=f"Positive Momentum: {{momentum:.4f}}"
            ))
        elif momentum < 0:
            signals.append(Signal(
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=df['close'].iloc[-1],
                weight=abs(momentum),
                reason=f"Negative Momentum: {{momentum:.4f}}"
            ))

        return signals

    def reset_state(self):
        """重置策略状态"""
        super().reset_state()
        pass
'''


def _get_position_risk_template(name: str, class_name: str) -> str:
    """仓位风控模板"""
    return f'''"""
{name} Position Risk Manager
仓位风控管理器模板
"""

from ginkgo.backtest.strategy.risk_managements.base_risk_management import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class {class_name}(BaseRiskManagement):
    """
    {name} 仓位风控管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", max_position_ratio: float = 0.1, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.max_position_ratio = max_position_ratio

    def cal(self, portfolio_info: dict, order: Order) -> Order:
        """订单拦截和修改"""
        if order.volume == 0:
            return order

        total_value = portfolio_info.get('total_value', 0)
        current_position = portfolio_info.get('positions', {{}}).get(order.code, 0)
        allowed_volume = int(total_value * self.max_position_ratio / order.price)

        if current_position + order.volume > allowed_volume:
            order.volume = max(0, allowed_volume - current_position)

        return order

    def generate_signals(self, portfolio_info: dict, event) -> list:
        """生成风控信号"""
        signals = []
        # 实现仓位管理逻辑
        return signals

    def reset_state(self):
        """重置风控状态"""
        super().reset_state()
        pass
'''


def _get_profitlimit_risk_template(name: str, class_name: str) -> str:
    """止盈风控模板"""
    return f'''"""
{name} Profit Limit Risk Manager
止盈风控管理器模板
"""

import datetime
from ginkgo.backtest.strategy.risk_managements.base_risk_management import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class {class_name}(BaseRiskManagement):
    """
    {name} 止盈风控管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", profit_target: float = 0.2, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.profit_target = profit_target
        self._position_entries = {{}}

    def cal(self, portfolio_info: dict, order: Order) -> Order:
        """订单拦截和修改"""
        return order

    def generate_signals(self, portfolio_info: dict, event) -> list:
        """生成止盈信号"""
        signals = []
        code = event.code
        current_price = event.price
        current_position = portfolio_info.get('positions', {{}}).get(code, 0)

        if current_position == 0:
            self._position_entries.pop(code, None)
            return signals

        if code not in self._position_entries:
            entry_price = portfolio_info.get('avg_prices', {{}}).get(code, current_price)
            self._position_entries[code] = entry_price
            return signals

        entry_price = self._position_entries[code]
        current_return = (current_price - entry_price) / entry_price

        # 检查止盈条件
        if current_return >= self.profit_target:
            signals.append(Signal(
                code=code,
                direction=DIRECTION_TYPES.SHORT if current_position > 0 else DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.RISK,
                datetime=datetime.datetime.now(),
                price=current_price,
                volume=abs(current_position),
                reason=f"Profit Target Reached: {{current_return:.2%}} >= {{self.profit_target:.2%}}"
            ))

        return signals

    def reset_state(self):
        """重置风控状态"""
        super().reset_state()
        self._position_entries.clear()
'''


def _get_fixed_selector_template(name: str, class_name: str) -> str:
    """固定选股器模板"""
    return f'''"""
{name} Fixed Selector
固定选股器模板
"""

from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector
from ginkgo.data import get_stockinfos


class {class_name}(BaseSelector):
    """
    {name} 固定选股器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", stock_list: list = None, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.stock_list = stock_list or []

    def select(self, universe: list, *args, **kwargs) -> list:
        """选股逻辑"""
        if self.stock_list:
            return [stock for stock in universe if stock in self.stock_list]
        return universe

    def reset_state(self):
        """重置选股器状态"""
        super().reset_state()
        pass
'''


def _get_fixed_sizer_template(name: str, class_name: str) -> str:
    """固定仓位管理器模板"""
    return f'''"""
{name} Fixed Sizer
固定仓位管理器模板
"""

from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer
from ginkgo.backtest.entities.order import Order


class {class_name}(BaseSizer):
    """
    {name} 固定仓位管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", fixed_size: int = 100, *args, **kwargs):
        super({class_name}, self).__init__(name, *args, **kwargs)
        self.fixed_size = fixed_size

    def size(self, order: Order) -> int:
        """计算仓位大小"""
        return self.fixed_size

    def reset_state(self):
        """重置仓位管理器状态"""
        super().reset_state()
        pass
'''

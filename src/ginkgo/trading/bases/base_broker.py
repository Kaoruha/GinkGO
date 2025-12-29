# Upstream: SimBroker/ManualBroker/LiveBroker (Broker子类继承)、Portfolio (使用Broker执行订单)
# Downstream: TimeMixin (继承提供时间戳管理)、ContextMixin (继承提供上下文管理)、LoggableMixin (继承提供日志记录)
# Role: BaseBroker经纪商基础抽象基类通过Mixin组装时间戳管理/上下文管理/日志记录等基础功能定义订单执行和成交处理的核心方法






"""
BaseBroker基础类

通过Mixin组装，提供Broker的基础功能。
组装TimeMixin、ContextMixin、LoggableMixin等基础功能。
不包含OrderManagementMixin，因为不同类型的Broker有不同的订单管理需求。
"""

from typing import Optional, Dict, Any

from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.trading.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES


class BaseBroker(TimeMixin, ContextMixin, LoggableMixin):
    """
    Broker基础类

    通过Mixin组装提供Broker的基础功能：
    - TimeMixin: 时间管理和业务时间戳处理
    - ContextMixin: 引擎上下文管理
    - LoggableMixin: 统一日志记录

    子类继承后只需要专注于具体的执行逻辑和业务规则。
    不包含OrderManagementMixin，因为：
    - SimBroker: 立即执行，不需要订单队列管理
    - ManualBroker: 需要人工确认的队列管理，直接在类中实现
    - LiveBroker: SDK管理订单状态，不需要本地队列
    """

    def __init__(self, name: str = "BaseBroker"):
        """
        初始化Broker基础功能

        Args:
            name: Broker名称
        """
        # 按照Mixin依赖顺序初始化
        TimeMixin.__init__(self)
        ContextMixin.__init__(self)
        LoggableMixin.__init__(self)

        # 设置名称
        self._broker_name = name

        # 市场数据缓存（主要用于回测）
        self._current_market_data: Dict[str, Any] = {}

        # 持仓信息（内存中的当前持仓）
        self._current_positions: Dict[str, Position] = {}

        # 异步结果回调函数
        self._result_callback = None

        # 记录初始化完成
        self.log("INFO", f"{self._broker_name} initialized")

    @property
    def name(self) -> str:
        """
        获取Broker名称

        Returns:
            str: Broker名称
        """
        return self._broker_name

    def get_broker_info(self) -> dict:
        """
        获取Broker信息摘要

        Returns:
            dict: Broker信息
        """
        return {
            'name': self._broker_name,
            'market_data_count': len(self._current_market_data),
            'position_count': len(self._current_positions),
            'has_result_callback': self._result_callback is not None,
            'has_engine_binding': hasattr(self, 'bound_engine') and self.bound_engine is not None,
        }

    def set_result_callback(self, callback):
        """
        设置异步结果回调函数

        Args:
            callback: 回调函数，用于处理异步执行结果
        """
        self._result_callback = callback
        self.log("DEBUG", f"Result callback set for {self._broker_name}")

    # 市场数据管理方法（主要用于回测）
    def set_market_data(self, code: str, data: Any) -> None:
        """
        设置市场数据

        Args:
            code: 股票代码
            data: 市场数据
        """
        self._current_market_data[code] = data
        # 可以添加数据验证逻辑
        if hasattr(self, 'log'):
            self.log("DEBUG", f"Market data updated for {code}")

    def get_market_data(self, code: str) -> Optional[Any]:
        """
        获取市场数据

        Args:
            code: 股票代码

        Returns:
            Optional[Any]: 市场数据，如果不存在返回None
        """
        return self._current_market_data.get(code)

    def get_all_market_data(self) -> Dict[str, Any]:
        """
        获取所有市场数据

        Returns:
            Dict[str, Any]: 所有市场数据的副本
        """
        return dict(self._current_market_data)

    def clear_market_data(self) -> None:
        """清空市场数据缓存"""
        self._current_market_data.clear()
        if hasattr(self, 'log'):
            self.log("DEBUG", "Market data cache cleared")

    def update_price_data(self, price_data) -> None:
        """
        更新价格数据（兼容接口）

        Args:
            price_data: 价格数据对象
        """
        if hasattr(price_data, 'code'):
            self.set_market_data(price_data.code, price_data)

    # 持仓管理方法
    def update_position(self, code: str, volume_change: int, price: float = 0.0) -> None:
        """
        更新持仓信息

        Args:
            code: 股票代码
            volume_change: 数量变化（正数为买入，负数为卖出）
            price: 价格（用于计算市值）
        """
        if code not in self._current_positions:
            # 创建Position时需要portfolio_id, engine_id, run_id
            # portfolio_id从事件中获取，engine_id和run_id也从事件中获取
            portfolio_id = self._current_event.portfolio_id
            engine_id = self._current_event.engine_id
            run_id = self._current_event.run_id

            self._current_positions[code] = Position(
                code=code,
                volume=0,
                price=price,
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                run_id=run_id
            )

        position = self._current_positions[code]
        position.volume += volume_change
        position.price = price  # 更新最新价格

        # 如果持仓为0，移除该持仓
        if position.volume == 0:
            del self._current_positions[code]

        if hasattr(self, 'log'):
            self.log("DEBUG", f"Position updated: {code} volume={position.volume}")

    def get_position(self, code: str) -> Optional[Position]:
        """
        获取持仓信息

        Args:
            code: 股票代码

        Returns:
            Optional[Position]: 持仓信息，如果不存在返回None
        """
        return self._current_positions.get(code)

    def get_all_positions(self) -> Dict[str, Position]:
        """
        获取所有持仓信息

        Returns:
            Dict[str, Position]: 所有持仓信息的副本
        """
        return dict(self._current_positions)

    def clear_positions(self) -> None:
        """清空所有持仓"""
        self._current_positions.clear()
        if hasattr(self, 'log'):
            self.log("DEBUG", "All positions cleared")

    # 通用辅助方法
    def _notify_result(self, result):
        """
        通知异步执行结果

        Args:
            result: 执行结果
        """
        if self._result_callback:
            self._result_callback(result)
        else:
            if hasattr(self, 'log'):
                self.log("WARN", "No result callback set, cannot notify result")
# Upstream: Portfolio Manager (创建订单)、Backtest Engines (执行订单并更新状态)、Risk Management (cal()方法拦截并调整订单)
# Downstream: Base/TimeMixin (继承提供uuid/component_type和时间能力)、DIRECTION_TYPES/ORDER_TYPES/ORDERSTATUS_TYPES/SOURCE_TYPES (枚举)
# Role: Order订单实体继承Base定义订单属性和交易相关信息支持订单管理支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import datetime
import uuid
from typing import Optional
from decimal import Decimal
from functools import singledispatchmethod

from ginkgo.libs import base_repr, datetime_normalize, GLOG, to_decimal, Number
from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    COMPONENT_TYPES,
)


class Order(Base, TimeMixin):
    """
    Order Class
    """

    def __init__(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: Number,
        frozen_money: Number = 0,
        frozen_volume: int = 0,
        transaction_price: Number = 0,
        transaction_volume: int = 0,
        remain: Number = 0,
        fee: Number = 0,
        timestamp: any = None,
        uuid: str = "",
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the Order instance with strict validation.

        Design Philosophy: All core parameters must be explicitly provided.
        No default values for business-critical fields to ensure intentional construction.

        Args:
            portfolio_id (str): Portfolio ID (required, no default)
            engine_id (str): Engine ID (required, no default)
            run_id (str): Run ID (required, no default)
            code (str): Order code (required, no default)
            direction (DIRECTION_TYPES): Trading direction (required, no default)
            order_type (ORDER_TYPES): Order type (required, no default)
            status (ORDERSTATUS_TYPES): Order status (required, no default)
            volume (int): Order volume (required, must be positive)
            limit_price (Number): Limit price (required, no default)
            frozen_money (Number): Frozen money amount (optional, default=0)
            frozen_volume (int): Frozen stock volume (optional, default=0)
            transaction_price (Number): Transaction price (optional, default=0)
            transaction_volume (int): Transaction volume (optional, default=0)
            remain (Number): Remaining amount (optional, default=0)
            fee (Number): Transaction fee (optional, default=0)
            timestamp (any): Order timestamp (optional, auto-generated if None)
            uuid (str): UUID (optional, auto-generated if empty)
        """
        # 初始化多重继承的父类
        Base.__init__(self, uuid=uuid, component_type=COMPONENT_TYPES.ORDER, *args, **kwargs)
        TimeMixin.__init__(self, timestamp=timestamp, *args, **kwargs)

        try:
            self.set(portfolio_id, engine_id, run_id, code, direction, order_type, status,
                    volume, limit_price, frozen_money, frozen_volume, transaction_price, transaction_volume,
                    remain, fee, timestamp)
        except Exception as e:
            GLOG.ERROR(f"Error initializing Order: {e}")
            raise Exception(f"Error initializing Order: {e}")

        self.set_source(SOURCE_TYPES.OTHER)

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        """
        Support set from params or dataframe.
            1. From parmas
            2. From dataframe
            code,direction,type,volume,limit_price,frozen_money,frozen_volume,transaction_price,remain,timestamp,uuid
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: Number,
        frozen_money: Number = 0,
        frozen_volume: int = 0,
        transaction_price: Number = 0,
        transaction_volume: int = 0,
        remain: Number = 0,
        fee: Number = 0,
        timestamp: any = None,
        *args,
        **kwargs,
    ):
        # 对所有核心业务字段进行严格的类型和值验证

        # portfolio_id类型和值验证
        if not isinstance(portfolio_id, str):
            raise TypeError(f"portfolio_id must be str, got {type(portfolio_id).__name__}")
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty.")

        # engine_id类型和值验证
        if not isinstance(engine_id, str):
            raise TypeError(f"engine_id must be str, got {type(engine_id).__name__}")
        if not engine_id:
            raise ValueError("engine_id cannot be empty.")

        # run_id类型和值验证
        if not isinstance(run_id, str):
            raise TypeError(f"run_id must be str, got {type(run_id).__name__}")
        if not run_id:
            raise ValueError("run_id cannot be empty.")

        # code类型和值验证
        if not isinstance(code, str):
            raise TypeError(f"code must be str, got {type(code).__name__}")
        if not code:
            raise ValueError("code cannot be empty.")

        # direction类型验证
        if direction is None:
            raise ValueError("direction cannot be None.")
        if not isinstance(direction, (DIRECTION_TYPES, int)):
            raise TypeError(f"direction must be DIRECTION_TYPES or int, got {type(direction).__name__}")

        # order_type类型验证
        if order_type is None:
            raise ValueError("order_type cannot be None.")
        if not isinstance(order_type, (ORDER_TYPES, int)):
            raise TypeError(f"order_type must be ORDER_TYPES or int, got {type(order_type).__name__}")

        # status类型验证
        if status is None:
            raise ValueError("status cannot be None.")
        if not isinstance(status, (ORDERSTATUS_TYPES, int)):
            raise TypeError(f"status must be ORDERSTATUS_TYPES or int, got {type(status).__name__}")

        # volume类型和值验证（支持pandas/numpy整数类型）
        try:
            volume = int(volume)
        except (ValueError, TypeError):
            raise TypeError(f"volume must be convertible to int, got {type(volume).__name__}")

        if volume <= 0:
            raise ValueError("volume must be positive.")

        # limit_price类型验证 - 支持Number类型（float, int, Decimal）
        if not isinstance(limit_price, (int, float, Decimal)):
            raise TypeError(f"limit_price must be Number (int, float, Decimal), got {type(limit_price).__name__}")
        # 注意：允许负价格，以支持期货等衍生品交易（如2020年原油期货负价格）

        # timestamp验证和设置（委托给TimeRelated）
        if timestamp is None:
            timestamp = datetime.datetime.now()
        self.timestamp = timestamp  # 使用TimeRelated的timestamp属性

        # 赋值所有验证通过的字段
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code = code
        self._volume = volume
        self._limit_price = to_decimal(limit_price)
        self._frozen_money = to_decimal(frozen_money)
        self._frozen_volume = int(frozen_volume)
        self._transaction_price = to_decimal(transaction_price)
        self._transaction_volume = int(transaction_volume)
        self._remain = to_decimal(remain)
        self._fee = to_decimal(fee)

        # 支持枚举类型转换
        if isinstance(direction, int):
            self._direction = DIRECTION_TYPES(direction)
        else:
            self._direction = direction

        if isinstance(order_type, int):
            self._order_type = ORDER_TYPES(order_type)
        else:
            self._order_type = order_type

        if isinstance(status, int):
            self._status = ORDERSTATUS_TYPES(status)
        else:
            self._status = status

        # 订单ID统一使用UUID（Base类自动生成）
        self._order_id = self.uuid

    @set.register
    def _(self, series: pd.Series, *args, **kwargs):
        """
        Set from pandas Series with validation
        """
        required_fields = {"portfolio_id", "engine_id", "run_id", "code", "direction", "order_type", "status"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(series.index):
            missing_fields = required_fields - set(series.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        # 直接调用位置参数的set方法
        self.set(
            series['portfolio_id'],
            series['engine_id'],
            series.get('run_id', ''),
            series['code'],
            DIRECTION_TYPES(series['direction']),
            ORDER_TYPES(series['order_type']),
            ORDERSTATUS_TYPES(series['status']),
            series.get('volume', 0),
            series.get('limit_price', 0.0),
            series.get('frozen_money', 0.0),
            series.get('frozen_volume', 0),
            series.get('transaction_price', 0.0),
            series.get('transaction_volume', 0),
            series.get('remain', 0.0),
            series.get('fee', 0.0),
            series.get('timestamp', None)
        )

        if "source" in series.index:
            self.set_source(SOURCE_TYPES(series['source']))

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        """
        Set from pandas DataFrame (uses first row)
        """
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_fields = {"portfolio_id", "engine_id", "run_id", "code", "direction", "order_type", "status"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 使用第一行数据设置
        row = df.iloc[0]
        self.set(row)

    @property
    def code(self) -> str:
        """
        Get the code of the order.

        Returns:
            str: The code.
        """
        return self._code

    @code.setter
    def code(self, value) -> None:
        """
        Set the code of the order.

        Args:
            value (str): The code to set.
        """
        self._code = value


    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @direction.setter
    def direction(self, value) -> None:
        self._direction = value

    @property
    def order_type(self) -> ORDER_TYPES:
        return self._order_type

    @order_type.setter
    def order_type(self, value) -> None:
        self._order_type = value

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value

    @property
    def status(self) -> ORDERSTATUS_TYPES:
        return self._status

    @property
    def limit_price(self) -> Decimal:
        return self._limit_price

    @limit_price.setter
    def limit_price(self, value) -> None:
        self._limit_price = value

    @property
    def frozen_money(self) -> Decimal:
        """冻结资金金额（买单使用）"""
        return self._frozen_money

    @frozen_money.setter
    def frozen_money(self, value) -> None:
        """支持多种输入类型但内部存储为Decimal"""
        self._frozen_money = to_decimal(value)

    @property
    def frozen_volume(self) -> int:
        """冻结股票数量（卖单使用）"""
        return self._frozen_volume

    @frozen_volume.setter
    def frozen_volume(self, value) -> None:
        """支持多种输入类型但内部存储为int"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"frozen_volume must be int or float, got {type(value).__name__}")
        if value < 0:
            raise ValueError("frozen_volume cannot be negative")
        self._frozen_volume = int(value)

    @property
    def transaction_price(self) -> Decimal:
        return self._transaction_price

    @transaction_price.setter
    def transaction_price(self, value) -> None:
        self._transaction_price = value

    @property
    def transaction_volume(self) -> float:
        return self._transaction_volume

    @transaction_volume.setter
    def transaction_volume(self, value) -> None:
        self._transaction_volume = value

    @property
    def remain(self) -> Decimal:
        return self._remain

    @remain.setter
    def remain(self, value) -> None:
        self._remain = value

    @property
    def fee(self) -> Decimal:
        return self._fee

    @fee.setter
    def fee(self, value) -> None:
        self._fee = value

    @property
    def order_id(self) -> str:
        return self._uuid

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def run_id(self) -> str:
        return self._run_id

    @run_id.setter
    def run_id(self, value) -> None:
        self._run_id = value

    def _validate_status_transition(self, from_status: ORDERSTATUS_TYPES, to_status: ORDERSTATUS_TYPES) -> None:
        """
        验证订单状态转换的合法性

        Args:
            from_status: 当前状态
            to_status: 目标状态

        Raises:
            ValueError: 如果状态转换不合法
        """
        # 定义合法的状态转换规则
        valid_transitions = {
            ORDERSTATUS_TYPES.NEW: [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.CANCELED],
            ORDERSTATUS_TYPES.SUBMITTED: [ORDERSTATUS_TYPES.PARTIAL_FILLED, ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.CANCELED],
            ORDERSTATUS_TYPES.PARTIAL_FILLED: [ORDERSTATUS_TYPES.PARTIAL_FILLED, ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.CANCELED],
            ORDERSTATUS_TYPES.FILLED: [],  # 已成交订单不能再转换状态
            ORDERSTATUS_TYPES.CANCELED: []  # 已取消订单不能再转换状态
        }

        if to_status not in valid_transitions.get(from_status, []):
            raise ValueError(f"Invalid status transition from {from_status.name} to {to_status.name}")

    def submit(self) -> None:
        """
        提交订单

        Raises:
            ValueError: 如果当前状态不允许提交
        """
        self._validate_status_transition(self._status, ORDERSTATUS_TYPES.SUBMITTED)
        self._status = ORDERSTATUS_TYPES.SUBMITTED

    def fill(self, price: float = None, fee: float = 0.0) -> None:
        """
        完全成交订单（成交剩余全部数量）

        Args:
            price (float): 成交价格，市价单必须提供此参数
            fee (float): 交易费用

        Raises:
            ValueError: 如果当前状态不允许成交或参数无效
        """
        # 验证状态转换
        if self._status not in [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]:
            raise ValueError(f"Cannot fill order with status {self._status.name}")

        remaining_volume = self._volume - self._transaction_volume
        if remaining_volume > 0:
            # 确定成交价格
            if price is not None:
                fill_price = price
            elif self._order_type == ORDER_TYPES.LIMITORDER and self._limit_price != 0:
                fill_price = float(self._limit_price)
            else:
                raise ValueError("Market orders must specify price parameter")

            self.partial_fill(remaining_volume, fill_price, fee)
        else:
            # 已经完全成交，只更新状态
            self._validate_status_transition(self._status, ORDERSTATUS_TYPES.FILLED)
            self._status = ORDERSTATUS_TYPES.FILLED

    def cancel(self) -> None:
        """
        取消订单

        Raises:
            ValueError: 如果当前状态不允许取消
        """
        self._validate_status_transition(self._status, ORDERSTATUS_TYPES.CANCELED)
        self._status = ORDERSTATUS_TYPES.CANCELED

    def partial_fill(self, executed_volume: int, executed_price: float, fee: float = 0.0) -> None:
        """
        处理部分成交

        Args:
            executed_volume (int): 本次成交数量
            executed_price (float): 成交价格
            fee (float): 本次成交费用

        Raises:
            ValueError: 如果当前状态不允许成交或参数无效
        """
        # 验证状态是否允许部分成交
        if self._status not in [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]:
            raise ValueError(f"Cannot partially fill order with status {self._status.name}")

        # 验证成交量参数
        if not isinstance(executed_volume, int):
            raise TypeError(f"executed_volume must be int, got {type(executed_volume).__name__}")
        if executed_volume <= 0:
            raise ValueError("executed_volume must be positive")

        # 验证成交价格参数
        if not isinstance(executed_price, (int, float)):
            raise TypeError(f"executed_price must be int or float, got {type(executed_price).__name__}")

        # 验证费用参数（费用本身不能为负，但总成交金额可以为负因为价格可以为负）
        if not isinstance(fee, (int, float)):
            raise TypeError(f"fee must be int or float, got {type(fee).__name__}")
        if fee < 0:
            raise ValueError("fee cannot be negative")

        # 防止超额成交
        if self._transaction_volume + executed_volume > self._volume:
            raise ValueError(f"Overfill detected: trying to fill {executed_volume}, "
                           f"but only {self._volume - self._transaction_volume} remaining")

        # 转换为Decimal进行精确计算
        executed_price_decimal = to_decimal(executed_price)
        fee_decimal = to_decimal(fee)

        # 更新累积成交量
        self._transaction_volume += executed_volume

        # 更新加权平均成交价格
        if self._transaction_volume > executed_volume:
            # 已有之前的成交，计算加权平均
            prev_volume = self._transaction_volume - executed_volume
            total_amount = self._transaction_price * to_decimal(prev_volume)
            new_amount = executed_price_decimal * to_decimal(executed_volume)
            self._transaction_price = (total_amount + new_amount) / to_decimal(self._transaction_volume)
        else:
            # 第一次成交
            self._transaction_price = executed_price_decimal

        # 更新费用
        self._fee += fee_decimal

        # 更新状态
        if self._transaction_volume >= self._volume:
            self._status = ORDERSTATUS_TYPES.FILLED
        else:
            self._status = ORDERSTATUS_TYPES.PARTIAL_FILLED

        # 更新剩余金额（简化计算：剩余数量 * 限价）
        remaining_volume = self._volume - self._transaction_volume
        if remaining_volume > 0 and self._limit_price > 0:
            self._remain = to_decimal(remaining_volume) * self._limit_price
        else:
            self._remain = to_decimal(0)

    def is_new(self) -> bool:
        """检查订单是否为新建状态"""
        return self._status == ORDERSTATUS_TYPES.NEW

    def is_submitted(self) -> bool:
        """检查订单是否已提交"""
        return self._status == ORDERSTATUS_TYPES.SUBMITTED

    def is_partially_filled(self) -> bool:
        """检查订单是否部分成交"""
        return self._status == ORDERSTATUS_TYPES.PARTIAL_FILLED

    def is_filled(self) -> bool:
        """检查订单是否完全成交"""
        return self._status == ORDERSTATUS_TYPES.FILLED

    def is_canceled(self) -> bool:
        """检查订单是否已取消"""
        return self._status == ORDERSTATUS_TYPES.CANCELED

    def is_active(self) -> bool:
        """检查订单是否处于活跃状态（可以成交）"""
        return self._status in [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]

    def is_final(self) -> bool:
        """检查订单是否处于最终状态（已完成或取消）"""
        return self._status in [ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.CANCELED]

    def get_remaining_volume(self) -> int:
        """获取剩余未成交数量"""
        return self._volume - self._transaction_volume

    def get_fill_ratio(self) -> float:
        """获取成交比例"""
        if self._volume == 0:
            return 0.0
        return float(self._transaction_volume) / float(self._volume)

    def to_model(self):
        """
        转换为数据库模型
        
        Returns:
            MOrder: 数据库模型实例
        """
        from ginkgo.data.models import MOrder
        
        model = MOrder()
        model.update(
            portfolio_id=getattr(self, '_portfolio_id', ''),
            engine_id=getattr(self, '_engine_id', ''),
            run_id=getattr(self, '_run_id', ''),  # 新增run_id传递
            uuid=self.uuid,
            code=self._code,
            direction=self._direction,
            order_type=self._order_type,
            status=self._status,
            volume=self._volume,
            limit_price=self._limit_price,
            frozen_money=self._frozen_money,
            frozen_volume=self._frozen_volume,
            transaction_price=self._transaction_price,
            transaction_volume=self._transaction_volume,
            remain=self._remain,
            fee=self._fee,
            timestamp=self._timestamp,
            source=self._source
        )
        return model
    
    @classmethod
    def from_model(cls, model) -> 'Order':
        """
        从数据库模型创建实体

        Args:
            model (MOrder): 数据库模型实例

        Returns:
            Order: 订单实体实例

        Raises:
            TypeError: If model is not an MOrder instance
        """
        from ginkgo.data.models.model_order import MOrder

        # Validate model type
        if not isinstance(model, MOrder):
            raise TypeError(f"Expected MOrder instance, got {type(model).__name__}")

        return cls(
            code=model.code,
            direction=DIRECTION_TYPES(model.direction),
            order_type=ORDER_TYPES(model.order_type),
            status=ORDERSTATUS_TYPES(model.status),
            volume=model.volume,
            limit_price=model.limit_price,  # 保持Decimal类型
            frozen_money=model.frozen_money,  # 保持Decimal类型
            frozen_volume=model.frozen_volume,  # 保持int类型
            transaction_price=model.transaction_price,  # 保持Decimal类型
            transaction_volume=model.transaction_volume,
            remain=model.remain,  # 保持Decimal类型
            fee=model.fee,  # 保持Decimal类型
            timestamp=model.timestamp,
            order_id=model.uuid,
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            run_id=model.run_id,  # 新增run_id读取
        )

    def __repr__(self) -> str:
        return base_repr(self, Order.__name__, 20, 60)

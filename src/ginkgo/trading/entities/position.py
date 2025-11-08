import pandas as pd
import numpy
import datetime
from typing import List, Optional, Union
from functools import singledispatchmethod
from decimal import Decimal
from ginkgo.libs import base_repr, Number, to_decimal, GLOG, datetime_normalize
from ginkgo.enums import DIRECTION_TYPES, COMPONENT_TYPES
from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin


class Position(Base, TimeMixin):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        engine_id: str = "",
        run_id: str = "",
        code: str = "",
        cost: Number = 0.0,
        volume: int = 0,
        frozen_volume: int = 0,
        settlement_frozen_volume: int = 0,
        settlement_days: int = 0,
        frozen_money: Number = 0,
        price: Number = 0.0,
        fee: Number = 0.0,
        uuid: str = "",
        timestamp: Optional[datetime.datetime] = None,
        init_time: Optional[datetime.datetime] = None,
        last_update: Optional[datetime.datetime] = None,
        realized_pnl: Number = 0.0,
        *args,
        **kwargs,
    ):
        # 初始化多重继承的父类
        Base.__init__(self, uuid=uuid, component_type=COMPONENT_TYPES.POSITION, *args, **kwargs)
        TimeMixin.__init__(self, timestamp=timestamp, init_time=init_time, *args, **kwargs)

        # 初始化日志系统
        self.loggers = []  # 先初始化空列表

        # 严格验证核心业务参数（与Signal保持一致）
        if not isinstance(portfolio_id, str) or not portfolio_id:
            raise ValueError("portfolio_id cannot be empty.")

        if not isinstance(engine_id, str) or not engine_id:
            raise ValueError("engine_id cannot be empty.")

        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id cannot be empty.")

        if not isinstance(code, str) or not code:
            raise ValueError("code cannot be empty.")

        # 初始化状态属性
        self.frozen = False

        # 如果外部指定了last_update，覆盖TimeRelated的默认值
        if last_update is not None:
            self.last_update = last_update

        # 初始化已实现盈亏
        self._realized_pnl = to_decimal(realized_pnl)

        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code = code
        self._cost = to_decimal(cost)
        self.volume = volume  # 使用setter进行类型转换
        self._frozen_volume = frozen_volume
        self._settlement_frozen_volume = settlement_frozen_volume  # 从参数初始化
        self._frozen_money = to_decimal(frozen_money)
        self._price = to_decimal(price)
        self._fee = to_decimal(fee)

        # 交易制度配置：T+N结算机制
        self._settlement_days = settlement_days  # 从参数初始化
        self._settlement_queue = []  # 结算队列：存储待结算的持仓批次
        # UUID已由Base类处理，无需额外逻辑
        self._profit = 0
        self._worth = 0
        self.update_worth()
        self.update_total_pnl()

        self.add_logger(GLOG)

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        code: str,
        cost: Optional[Number] = None,
        volume: Optional[int] = None,
        frozen_volume: Optional[int] = None,
        settlement_frozen_volume: Optional[int] = None,
        settlement_days: Optional[int] = None,
        frozen_money: Optional[Number] = None,
        price: Optional[Number] = None,
        fee: Optional[Number] = None,
        uuid: Optional[str] = None,
        init_time: Optional[datetime.datetime] = None,
        last_update: Optional[datetime.datetime] = None,
        realized_pnl: Optional[Number] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Data reset.
        return: none
        """
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code = code

        # 记录是否需要重新计算和是否明确指定了last_update
        need_recalculate = False
        last_update_explicitly_set = last_update is not None

        if cost is not None:
            self._cost = to_decimal(cost)
            need_recalculate = True
        if volume is not None:
            self._volume = int(volume)
            need_recalculate = True
        if frozen_volume is not None:
            self._frozen_volume = int(frozen_volume)
            need_recalculate = True
        if settlement_frozen_volume is not None:
            self._settlement_frozen_volume = int(settlement_frozen_volume)
            need_recalculate = True
        if settlement_days is not None:
            self.settlement_days = settlement_days  # 使用setter进行验证
        if frozen_money is not None:
            self._frozen_money = to_decimal(frozen_money)
        if price is not None:
            self._price = to_decimal(price)
            need_recalculate = True
        if fee is not None:
            self._fee = to_decimal(fee)
            need_recalculate = True
        if uuid is not None:
            self._uuid = uuid

        # 处理新增的属性
        if init_time is not None:
            self._init_time = init_time
        if last_update is not None:
            self._last_update = last_update
        if realized_pnl is not None:
            self._realized_pnl = to_decimal(realized_pnl)

        # 在所有参数设置完成后统一重新计算
        if need_recalculate:
            self.update_total_pnl()
            self.update_worth()

        # 如果没有明确指定last_update，才自动更新时间戳
        if not last_update_explicitly_set:
            self._update_last_update()

    @set.register
    def _(self, df: pd.Series, *args, **kwargs):
        """
        Set from pandas Series
        """
        required_fields = {"portfolio_id", "engine_id", "run_id", "code"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        self._portfolio_id = df["portfolio_id"]
        self._engine_id = df["engine_id"]
        self._run_id = df.get("run_id", "")
        self._code = df["code"]
        self._cost = to_decimal(df.get("cost", 0))
        self._volume = int(df.get("volume", 0))
        self._frozen_volume = int(df.get("frozen_volume", 0))
        self._frozen_money = to_decimal(df.get("frozen_money", 0))
        self._price = to_decimal(df.get("price", 0))
        self._fee = to_decimal(df.get("fee", 0))
        if "uuid" in df.index:
            self._uuid = df["uuid"]

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        """
        Set from pandas DataFrame (uses first row)
        """
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_fields = {"portfolio_id", "engine_id", "run_id", "code"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 使用第一行数据设置
        row = df.iloc[0]
        self.set(row)

    @property
    def portfolio_id(self, *args, **kwargs) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def run_id(self, *args, **kwargs) -> str:
        return self._run_id

    @run_id.setter
    def run_id(self, value) -> None:
        self._run_id = value

    @property
    def volume(self, *args, **kwargs) -> int:
        """
        可用持仓数量：未冻结的持仓数量，可以用于新的交易操作

        注意：总持仓 = volume(可用持仓) + frozen_volume(冻结持仓) + settlement_frozen_volume(结算冻结)
        """
        if self._volume < 0:
            self.log("CRITICAL", f"Volume is less than 0: {self._volume}")
            return 0
        if not isinstance(self._volume, (int, numpy.int64)):
            self.log("CRITICAL", f"Volume is not a int: {self._volume}")
            return 0
        return self._volume

    @volume.setter
    def volume(self, value) -> None:
        self._volume = int(value)

    @property
    def frozen_money(self, *args, **kwargs) -> Decimal:
        if self._frozen_money < 0:
            self.log("CRITICAL", f"Frozen money is less than 0: {self._frozen_money}")
            return 0
        return self._frozen_money

    @property
    def worth(self, *args, **kwargs) -> float:
        """
        The worth of Position.
        """
        return self._worth


    def update_worth(self, *args, **kwargs) -> None:
        w = (self.volume + self.frozen_volume) * self.price
        self._worth = round(w, 2)
        self._last_update = self.get_current_time()

    @property
    def code(self) -> str:
        """
        Position Code.
        """
        return self._code

    @property
    def price(self, *args, **kwargs) -> Decimal:
        """
        Current Price.
        """
        if self._price < 0:
            self.log("CRITICAL", f"Price is less than 0: {self._price}")
        if not isinstance(self._price, Decimal):
            self.log("CRITICAL", f"Price is not a DECIMAL: {self._price}")
            return Decimal('0')
        return self._price

    @property
    def cost(self, *args, **kwargs) -> Decimal:
        """
        Average Cost.
        """
        return self._cost

    @property
    def frozen_volume(self, *args, **kwargs) -> float:
        """
        冻结持仓数量：已预留用于交易但尚未成交的持仓数量

        注意：总持仓 = volume(可用持仓) + frozen_volume(冻结持仓) + settlement_frozen_volume(结算冻结)
        """
        if self._frozen_volume < 0:
            self.log("CRITICAL", f"Frozen is less than 0: {self._frozen_volume}")
        if not isinstance(self._frozen_volume, (int, numpy.int64)):
            self.log("CRITICAL", f"Frozen is not a int: {self._frozen_volume}")
            return 0
        return self._frozen_volume

    @property
    def settlement_frozen_volume(self, *args, **kwargs) -> int:
        """
        结算冻结持仓数量：因T+N交易制度而冻结的持仓数量

        在T+N市场中，当日买入的股票需要经过N个交易日后才能卖出
        这部分持仓在结算期间保存在settlement_frozen_volume中，无法用于交易
        """
        if self._settlement_frozen_volume < 0:
            self.log("CRITICAL", f"Settlement frozen volume is less than 0: {self._settlement_frozen_volume}")
            return 0
        return self._settlement_frozen_volume

    @property
    def settlement_days(self, *args, **kwargs) -> int:
        """
        结算天数配置：0=T+0(当日可卖), 1=T+1(次日可卖), 2=T+2等

        注意：此属性为只读，只能在构造函数中设置。在持仓创建后不应修改。
        """
        return self._settlement_days

    @property
    def total_position(self, *args, **kwargs) -> int:
        """
        总持仓数量：包括可用、冻结和结算冻结的所有持仓
        计算公式：volume + frozen_volume + settlement_frozen_volume
        """
        return self.volume + self.frozen_volume + self.settlement_frozen_volume

    def freeze(self, volume: int, *args, **kwargs) -> bool:
        """
        Freeze Position.
        Args:
            volume (int): Amount to freeze.
        Returns:
            bool: Success or failure.
        """
        if volume <= 0:
            self.log("CRITICAL", f"Invalid freeze volume: {volume}")
            return False
        volume = int(volume)
        if volume > self.volume:
            self.log("CRITICAL", f"Insufficient volume to freeze: {volume}, available: {self.volume}")
            return False

        self._volume -= volume
        self._frozen_volume += volume
        self.log("INFO", f"Freezed {volume} units. Remaining: {self.volume}, Frozen: {self.frozen_volume}")
        return True

    def unfreeze(self, volume: int, *args, **kwargs) -> bool:
        """
        Unfreeze Position.

        Args:
            volume (int): 要解冻的数量

        Returns:
            bool: 操作是否成功
        """
        try:
            volume = int(volume)
            if volume <= 0:
                self.log("ERROR", f"Invalid unfreeze volume: {volume}")
                return False

            if volume > self.frozen_volume:
                self.log("CRITICAL", f"POS {self.code} just freezed {self.frozen_volume} cant afford {volume}.")
                return False

            self._frozen_volume -= volume
            self._volume += volume  # 将冻结持仓恢复为可用持仓
            self.log(
                "INFO",
                f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen_volume: {self.frozen_volume}",
            )
            return True

        except Exception as e:
            self.log("ERROR", f"Error during unfreeze operation: {e}")
            return False

    @property
    def fee(self, *args, **kwargs) -> Decimal:
        """
        Sum of fee.
        """
        if self._fee < 0:
            self.log("CRITICAL", f"Fee is less than 0: {self._fee}")
        if not isinstance(self._fee, Decimal):
            self.log("CRITICAL", f"Fee is not a DECIMAL: {self._fee}")
            return to_decimal("0")
        return self._fee

    def add_fee(self, fee: float, *args, **kwargs) -> bool:
        """
        添加手续费

        Args:
            fee (float): 要添加的手续费金额

        Returns:
            bool: 操作是否成功
        """
        try:
            if fee < 0:
                self.log("CRITICAL", f"Can not add fee less than 0.")
                return False

            self._fee += to_decimal(fee)
            return True

        except Exception as e:
            self.log("ERROR", f"Error adding fee: {e}")
            return False

    @property
    def total_pnl(self, *args, **kwargs) -> float:
        """
        总盈亏：当前持仓的总盈亏（包括冻结持仓和结算冻结持仓）
        计算公式：(volume + frozen_volume + settlement_frozen_volume) * (price - cost) - fee
        """
        return self._profit

    def update_total_pnl(self, *args, **kwargs) -> None:
        """
        更新总盈亏：基于总持仓量（含冻结和结算冻结）计算
        """
        self._profit = self.total_position * (self.price - self.cost) - self.fee
        self._last_update = self.get_current_time()

    def _bought(self, price: Number, volume: int, *args, **kwargs) -> bool:
        """
        Handle a long trade.

        Args:
            price (Number): The price at which the position is bought.
            volume (int): The volume of the position to be added.

        Returns:
            bool: Whether the operation was successful.
        """
        try:
            volume = int(volume)
            price = to_decimal(price)
            if price <= 0 or volume <= 0:
                raise ValueError(f"Invalid price: {price} or volume: {volume}")
        except Exception as e:
            self.log("ERROR", f"Invalid input - price: {price}, volume: {volume}, error: {e}")
            return False
        finally:
            pass

        try:
            prev_price = self.cost
            prev_total_volume = self.total_position  # 使用总持仓计算成本

            # T+N逻辑：根据settlement_days决定新购股票的归属
            if self._settlement_days == 0:
                # T+0市场：直接可用
                self._volume += volume
                self.log("DEBUG", f"T+0 mode: added {volume} to available volume")
            else:
                # T+N市场：进入结算冻结，待日终结算
                self._settlement_frozen_volume += volume
                # 添加到结算队列，记录结算日期
                current_time = self.get_current_time()
                settlement_date = current_time + datetime.timedelta(days=self._settlement_days)
                self._settlement_queue.append({
                    'volume': volume,
                    'settlement_date': settlement_date,
                    'buy_date': current_time
                })
                self.log("DEBUG", f"T+{self._settlement_days} mode: added {volume} to settlement frozen, settle on {settlement_date.date()}")

            # 重新计算平均成本（基于总持仓）
            new_total_volume = self.total_position
            self._cost = (prev_price * prev_total_volume + price * volume) / new_total_volume
            self.on_price_update(price)

            # Check cost
            if self._cost < 0:
                self.log("CRITICAL", f"Cost is less than 0: {self._cost}")
                return False
            if not isinstance(self._cost, Decimal):
                self.log("CRITICAL", f"Cost is not a DECIMAL: {self._cost}")
                return False

            self.log("DEBUG", f"POS {self.code} bought {volume} at ${price}. New cost: ${self._cost}")
            self.log("DEBUG", f"Available: {self.volume}, Frozen: {self.frozen_volume}, Settlement: {self.settlement_frozen_volume}")
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            pass

    def _sold(self, price: float, volume: int, *args, **kwargs) -> bool:
        """
        Handle a short trade.

        Args:
            price (float): The price at which the position is sold.
            volume (int): The volume of the position to be reduced.

        Returns:
            bool: Whether the operation was successful.
        """
        # 参数校验
        try:
            volume = int(volume)
            price = float(price)
            if price <= 0 or volume <= 0:
                raise ValueError(f"Invalid price: {price} or volume: {volume}")
        except Exception as e:
            self.log("ERROR", f"Invalid input - price: {price}, volume: {volume}, error: {e}")
            return False
        finally:
            pass

        if volume > self.frozen_volume:
            self.log(
                "CRITICAL", f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code"
            )
            return False

        # 执行卖出逻辑
        try:
            # 计算并累积已实现盈亏
            sell_price = to_decimal(price)
            realized_gain = (sell_price - self._cost) * volume
            self._realized_pnl += realized_gain

            # 更新持仓：只减少冻结持仓（总持仓已在freeze时减少）
            self._frozen_volume -= volume  # 减少冻结持仓量
            self.on_price_update(price)

            # 日志记录
            self.log(
                "DEBUG",
                f"POS {self.code} sold {volume} at ${price}. "
                f"Realized PnL: {realized_gain}, Total realized: {self._realized_pnl}. "
                f"Final price: ${self._cost}, volume: {self.volume}, "
                f"cost: ${self.cost}, frozen: {self.frozen_volume}",
            )
            return True
        except Exception as e:
            import pdb

            pdb.set_trace()
            self.log("ERROR", f"Error during sell operation - price: {price}, volume: {volume}, error: {e}")
        finally:
            pass

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int, *args, **kwargs) -> bool:
        """
        Handles trade execution.

        Args:
            direction (DIRECTION_TYPES): Trade direction (LONG or SHORT).
            price (float): Execution price.
            volume (int): Execution volume.

        Returns:
            bool: Whether the trade was successful.

        Example:
            success = position.deal(DIRECTION_TYPES.LONG, 100.5, 50)
        """
        success = False

        if direction == DIRECTION_TYPES.LONG:
            success = self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            success = self._sold(price, volume)
        else:
            self.log("ERROR", f"Invalid direction: {direction}")
            return False

        # 只有交易成功时才更新状态
        if success:
            self.update_total_pnl()
            self.update_worth()
            self._update_last_update()

        return success

    def on_price_update(self, price: Union[float, int, Decimal], *args, **kwargs) -> bool:
        """
        价格更新并验证有效性

        Args:
            price: 新的价格

        Returns:
            bool: 更新是否成功
        """
        try:
            price_decimal = to_decimal(price)

            # 验证价格非负
            if price_decimal < 0:
                self.log("CRITICAL", f"Rejected negative price update: {price_decimal} for {self._code}")
                return False

            # 更新价格
            self._price = price_decimal
            self.update_total_pnl()
            self.update_worth()
            self._update_last_update()
            return True

        except Exception as e:
            self.log("ERROR", f"Error updating price: {e}")
            return False

    @property
    def market_value(self) -> Decimal:
        """
        市场价值：等同于worth，表示当前市场价值
        """
        return self.worth

    @property
    def unrealized_pnl(self) -> Decimal:
        """
        未实现盈亏：当前持仓按市价计算的潜在盈亏（不包括已实现部分）
        等同于total_pnl，使用更精确的财务术语
        计算公式：(当前价格 - 成本价格) × 总持仓数量 - 手续费
        """
        return to_decimal(self.total_pnl)

    @property
    def realized_pnl(self) -> Decimal:
        """
        已实现盈亏：通过交易操作累积的已确定盈亏
        """
        return self._realized_pnl

    @realized_pnl.setter
    def realized_pnl(self, value: Number) -> None:
        """
        设置已实现盈亏
        """
        if not isinstance(value, (int, float, Decimal)):
            raise TypeError(f"realized_pnl must be numeric, got {type(value).__name__}")
        self._realized_pnl = to_decimal(value)
        self._update_last_update()


    @property
    def available_volume(self) -> int:
        """
        实际可交易数量：可用持仓减去冻结持仓的剩余数量

        计算公式：available_volume = volume(可用持仓) - frozen_volume(冻结持仓)
        注意：这是当前可以发起新交易操作的最大数量
        """
        return max(0, self.volume - self.frozen_volume)

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)

    def _update_last_update(self) -> None:
        """
        更新最后更新时间戳
        """
        self._last_update = self.get_current_time()

    def _on_time_advance(self, new_time: datetime.datetime) -> None:
        """
        Handle position-specific time advancement logic.

        Processes settlement queue to transfer settlement_frozen_volume to available volume
        when settlement periods expire.

        Args:
            new_time(datetime.datetime): The new current time
        """
        settled_volume = 0
        remaining_queue = []

        # 检查结算队列中的每个批次
        for settlement_batch in self._settlement_queue:
            if new_time.date() >= settlement_batch['settlement_date'].date():
                # 到期结算：从settlement_frozen转移到可用volume
                batch_volume = settlement_batch['volume']
                self._settlement_frozen_volume -= batch_volume
                self._volume += batch_volume
                settled_volume += batch_volume

                self.log("DEBUG", f"Settled {batch_volume} shares bought on {settlement_batch['buy_date'].date()}")
            else:
                # 未到期，保留在队列中
                remaining_queue.append(settlement_batch)

        # 更新结算队列
        self._settlement_queue = remaining_queue

        if settled_volume > 0:
            self.log("INFO", f"Total settled volume: {settled_volume}, Available: {self.volume}, Settlement frozen: {self.settlement_frozen_volume}")

        # Update last_update timestamp after settlement processing (delegate to TimeRelated)
        self.last_update = new_time

    def process_settlement_queue(self, new_time: datetime.datetime) -> None:
        """
        公共接口：处理结算队列

        这是PortfolioT1Backtest调用的公共接口，内部委托给_on_time_advance方法。
        提供了一致的接口设计，便于外部组件调用结算处理逻辑。

        Args:
            new_time(datetime.datetime): 新的当前时间
        """
        self.log("DEBUG", f"Processing settlement queue for position {self.code} at time {new_time}")
        return self._on_time_advance(new_time)

    def add_realized_pnl(self, pnl: Number) -> bool:
        """
        累积已实现盈亏（用于部分平仓时）

        Args:
            pnl (Number): 要添加的已实现盈亏金额

        Returns:
            bool: 操作是否成功
        """
        try:
            if not isinstance(pnl, (int, float, Decimal)):
                self.log("ERROR", f"pnl must be numeric, got {type(pnl).__name__}")
                return False

            self._realized_pnl += to_decimal(pnl)
            self._update_last_update()

            self.log("INFO", f"Position {self._code} added realized PnL: {pnl}, total: {self._realized_pnl}")
            return True

        except Exception as e:
            self.log("ERROR", f"Error adding realized PnL: {e}")
            return False

    def log(self, level: str, msg: str, *args, **kwargs) -> None:
        level_up = level.upper()
        if level_up == "DEBUG":
            for i in self.loggers:
                i.DEBUG(msg)
        elif level_up == "INFO":
            for i in self.loggers:
                i.INFO(msg)
        elif level_up == "WARNING":
            for i in self.loggers:
                i.WARN(msg)
        elif level_up == "ERROR":
            for i in self.loggers:
                i.ERROR(msg)
        elif level_up == "CRITICAL":
            for i in self.loggers:
                i.CRITICAL(msg)
        else:
            pass


    def add_logger(self, logger) -> None:
        if logger in self.loggers:
            return
        self.loggers.append(logger)

    def reset_logger(self) -> None:
        self.loggers = []

    def to_model(self):
        """
        转换为数据库模型

        Returns:
            MPosition: 数据库模型实例
        """
        import json
        from ginkgo.data.models import MPosition

        # 序列化结算队列为JSON
        settlement_queue_json = json.dumps(self._settlement_queue, default=str)

        model = MPosition()
        model.update(
            self._portfolio_id,  # portfolio_id as first positional argument
            self._engine_id,     # engine_id as second positional argument
            self._run_id,        # run_id as third positional argument
            code=self._code,
            cost=self._cost,
            volume=self._volume,
            frozen_volume=self._frozen_volume,
            settlement_frozen_volume=self._settlement_frozen_volume,
            settlement_days=self._settlement_days,
            settlement_queue_json=settlement_queue_json,
            frozen_money=self._frozen_money,
            price=self._price,
            fee=self._fee
        )
        # 设置UUID
        model.uuid = self.uuid
        return model
    
    @classmethod
    def from_model(cls, model) -> 'Position':
        """
        从数据库模型创建实体

        Args:
            model (MPosition): 数据库模型实例

        Returns:
            Position: 持仓实体实例

        Raises:
            TypeError: If model is not an MPosition instance
        """
        import json
        import datetime
        from ginkgo.data.models.model_position import MPosition

        # Validate model type
        if not isinstance(model, MPosition):
            raise TypeError(f"Expected MPosition instance, got {type(model).__name__}")

        # 创建Position实例，只传递非None值以使用构造函数默认值
        position_kwargs = {
            'portfolio_id': model.portfolio_id,
            'engine_id': model.engine_id,
            'run_id': model.run_id,
            'code': model.code,
            'cost': model.cost,
            'volume': model.volume,
            'price': model.price,
            'uuid': model.uuid,
            'timestamp': '2023-01-01 10:00:00'
        }

        # 只添加非None的可选字段
        if model.frozen_volume is not None:
            position_kwargs['frozen_volume'] = model.frozen_volume
        if model.settlement_frozen_volume is not None:
            position_kwargs['settlement_frozen_volume'] = model.settlement_frozen_volume
        if model.settlement_days is not None:
            position_kwargs['settlement_days'] = model.settlement_days
        if model.frozen_money is not None:
            position_kwargs['frozen_money'] = model.frozen_money
        if model.fee is not None:
            position_kwargs['fee'] = model.fee

        position = cls(**position_kwargs)

        # 反序列化结算队列JSON
        try:
            settlement_queue_data = json.loads(model.settlement_queue_json or "[]")
            position._settlement_queue = []

            for batch_data in settlement_queue_data:
                # 转换日期字符串回datetime对象
                batch = {
                    'volume': batch_data['volume'],
                    'buy_date': datetime.datetime.fromisoformat(batch_data['buy_date']),
                    'settlement_date': datetime.datetime.fromisoformat(batch_data['settlement_date'])
                }
                position._settlement_queue.append(batch)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            position.log("ERROR", f"Failed to deserialize settlement_queue: {e}")
            position._settlement_queue = []

        return position

    # Corporate Actions Methods
    def stock_split(self, ratio: Number, *args, **kwargs) -> bool:
        """股票拆分"""
        try:
            ratio_decimal = to_decimal(ratio)
            if ratio_decimal <= 1:
                self.log("ERROR", f"Stock split ratio must be > 1, got {ratio}")
                return False

            self.set(
                self._portfolio_id, self._engine_id, self._run_id, self._code,
                cost=self._cost / ratio_decimal,
                volume=int(self._volume * float(ratio_decimal)),
                price=self._price / ratio_decimal
            )
            self.log("INFO", f"Stock split {ratio}:1 applied to {self._code}")
            return True
        except Exception as e:
            self.log("ERROR", f"Stock split failed: {e}")
            return False

    def stock_consolidation(self, ratio: Number, *args, **kwargs) -> bool:
        """股票合并"""
        try:
            ratio_decimal = to_decimal(ratio)
            if ratio_decimal <= 1:
                self.log("ERROR", f"Consolidation ratio must be > 1, got {ratio}")
                return False

            self.set(
                self._portfolio_id, self._engine_id, self._run_id, self._code,
                cost=self._cost * ratio_decimal,
                volume=int(self._volume / float(ratio_decimal)),
                price=self._price * ratio_decimal
            )
            self.log("INFO", f"Stock consolidation {ratio}:1 applied to {self._code}")
            return True
        except Exception as e:
            self.log("ERROR", f"Stock consolidation failed: {e}")
            return False

    def stock_dividend(self, ratio: Number, *args, **kwargs) -> bool:
        """送股"""
        try:
            ratio = float(ratio)
            if ratio <= 0:
                self.log("ERROR", f"Stock dividend ratio must be > 0, got {ratio}")
                return False

            old_volume = self._volume
            new_volume = int(old_volume * (1 + ratio))

            self.set(
                self._portfolio_id, self._engine_id, self._run_id, self._code,
                cost=self._cost * old_volume / new_volume,
                volume=new_volume,
                price=self._price * old_volume / new_volume
            )
            self.log("INFO", f"Stock dividend {ratio*100:.1f}% applied to {self._code}")
            return True
        except Exception as e:
            self.log("ERROR", f"Stock dividend failed: {e}")
            return False

    def cash_dividend(self, amount: Number, *args, **kwargs) -> bool:
        """现金分红"""
        try:
            amount = to_decimal(amount)
            if amount <= 0:
                self.log("ERROR", f"Dividend amount must be > 0, got {amount}")
                return False

            total_dividend = amount * self._volume
            self.set(
                self._portfolio_id, self._engine_id, self._run_id, self._code,
                price=self._price - amount,
                realized_pnl=getattr(self, '_realized_pnl', 0) + total_dividend
            )
            self.log("INFO", f"Cash dividend {amount}/share applied to {self._code}, total: {total_dividend}")
            return True
        except Exception as e:
            self.log("ERROR", f"Cash dividend failed: {e}")
            return False


    # def __repr__(self) -> str:
    #     return base_repr(self, self._code, 12, 60)

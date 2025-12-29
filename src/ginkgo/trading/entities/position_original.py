# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Position Original实体定义PositionOriginal原始持仓数据结构和属性支持相关功能






import pandas as pd
import numpy
from typing import List, Optional, Union
from functools import singledispatchmethod
from decimal import Decimal
from ginkgo.libs import base_repr, Number, to_decimal, GLOG, datetime_normalize
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.trading.core.base import Base


class Position(Base):
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
        frozen_money: Number = 0,
        price: Number = 0.0,
        fee: Number = 0.0,
        uuid: str = "",
        *args,
        **kwargs,
    ):
        # 使用新的Base类初始化，传入组件类型
        super(Position, self).__init__(component_type="position", *args, **kwargs)
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._run_id = run_id
        self._code = code
        self._cost = to_decimal(cost)
        self._volume = volume
        self._frozen_volume = frozen_volume
        self._frozen_money = to_decimal(frozen_money)
        self._price = to_decimal(price)
        self._fee = to_decimal(fee)
        # 只有提供了明确的uuid参数才覆盖Base类生成的UUID
        if uuid and len(uuid) > 0:
            self._uuid = uuid
        self._profit = 0
        self._worth = 0
        self.update_worth()
        self.update_profit()

        self.loggers = []
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
        frozen_money: Optional[Number] = None,
        price: Optional[Number] = None,
        fee: Optional[Number] = None,
        uuid: Optional[str] = None,
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
        if cost is not None:
            self._cost = to_decimal(cost)
        if volume is not None:
            self._volume = volume
        if frozen_volume is not None:
            self._frozen_volume = frozen_volume
        if frozen_money is not None:
            self._frozen_money = to_decimal(frozen_money)
        if price is not None:
            self._price = to_decimal(price)
            self.update_profit()
            self.update_worth()
        if fee is not None:
            self._fee = to_decimal(fee)
        if uuid is not None:
            self._uuid = uuid

    @set.register
    def _(self, df: pd.Series, *args, **kwargs):
        self._portfolio_id = df["portfolio_id"]
        self._engine_id = df["engine_id"]
        self._run_id = df.get("run_id", "")
        self._code = df["code"]
        self._cost = to_decimal(df["cost"])
        self._volume = int(df["volume"])
        self._frozen_volume = int(df["frozen_volume"])
        self._frozen_money = to_decimal(df["frozen_money"])
        self._price = to_decimal(df["price"])
        self._fee = to_decimal(df["fee"])
        self._uuid = df["uuid"]

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
        The Amount of position.
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

    @property
    def code(self) -> str:
        """
        Position Code.
        """
        return self._code

    @property
    def price(self, *args, **kwargs) -> float:
        """
        Current Price.
        """
        if self._price < 0:
            self.log("CRITICAL", f"Price is less than 0: {self._price}")
        if not isinstance(self._price, Decimal):
            self.log("CRITICAL", f"Price is not a DECIMAL: {self._price}")
            return 0
        return self._price

    @property
    def cost(self, *args, **kwargs) -> float:
        """
        Average Cost.
        """
        return self._cost

    @property
    def frozen_volume(self, *args, **kwargs) -> float:
        """
        Frozen amount of position.
        """
        if self._frozen_volume < 0:
            self.log("CRITICAL", f"Frozen is less than 0: {self._frozen_volume}")
        if not isinstance(self._frozen_volume, (int, numpy.int64)):
            self.log("CRITICAL", f"Frozen is not a int: {self._frozen_volume}")
            return 0
        return self._frozen_volume

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

    def unfreeze(self, volume: int, *args, **kwargs) -> int:
        """
        Unfreeze Position.
        """
        volume = int(volume)

        if volume > self.frozen_volume:
            self.log("CRITICAL", f"POS {self.code} just freezed {self.frozen} cant afford {volume}.")
            return

        self._frozen_volume -= volume
        self._volume += volume
        self.log(
            "INFO",
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen_volume: {self.frozen_volume}",
        )
        return self.volume

    @property
    def fee(self, *args, **kwargs) -> float:
        """
        Sum of fee.
        """
        if self._fee < 0:
            self.log("CRITICAL", f"Fee is less than 0: {self._fee}")
        if not isinstance(self._fee, Decimal):
            self.log("CRITICAL", f"Fee is not a DECIMAL: {self._fee}")
            return to_decimal("0")
        return self._fee

    def add_fee(self, fee: float, *args, **kwargs) -> float:
        if fee < 0:
            self.log("CRITICAL", f"Can not add fee less than 0.")
            return
        self._fee += fee
        return self.fee

    @property
    def profit(self, *args, **kwargs) -> float:
        """
        Current Profit of the position.
        """
        return self._profit

    def update_profit(self, *args, **kwargs) -> None:
        """
        Update Profit. Call after Trade Done or Price Update.
        """
        self._profit = (self.volume + self.frozen_volume) * (self.price - self.cost) - self.fee

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
            prev_volume = self.volume
            self._volume += volume
            self._cost = (prev_price * prev_volume + price * volume) / self.volume
            self.on_price_update(price)
            # Check cost
            if self._cost < 0:
                self.log("CRITICAL", f"Cost is less than 0: {self._cost}")
                return
            if not isinstance(self._cost, Decimal):
                self.log("CRITICAL", f"Cost is not a DECIMAL: {self._cost}")
                return
            self.log("DEBUG", f"POS {self.code} added {volume} at ${price}. Final price: ${self._cost}, ")
            self.log("DEBUG", f"volume: {self.volume}, cost: ${self.cost}, frozen: {self.frozen_volume}")
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
            self._frozen_volume -= volume
            self.on_price_update(price)
            # 日志记录
            self.log(
                "DEBUG",
                f"POS {self.code} sold {volume} at ${price}. "
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

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int, *args, **kwargs) -> None:
        """
        Handles successful trade execution.

        Args:
            direction (DIRECTION_TYPES): Trade direction (LONG or SHORT).
            price (float): Execution price.
            volume (int): Execution volume.

        Example:
            position.deal(DIRECTION_TYPES.LONG, 100.5, 50)
        """
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        self.update_profit()
        self.update_worth()

    def on_price_update(self, price: Union[float, int, Decimal], *args, **kwargs) -> Decimal:
        """
        Dealing with price update
        return: latest price of position
        """
        self._price = price if isinstance(price, Decimal) else Decimal(str(price))
        self.update_profit()
        self.update_worth()
        return self._price

    @property
    def market_value(self) -> Decimal:
        # TODO
        pass

    @property
    def unrealized_value(self) -> Decimal:
        # TODO
        pass

    @property
    def realized_pnl(self) -> Decimal:
        # TODO
        pass

    @property
    def last_update(self) -> Decimal:
        # TODO
        pass

    @property
    def init_time(self) -> Decimal:
        # TODO
        pass

    @property
    def available_volume(self) -> int:
        # TODO
        pass

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)

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

    def advance_time(self, time: any, *args, **kwargs) -> None:
        """
        Go next frame.
        Timestamp update. Just support from past to future.

        Args:
            time(any): new time
        Returns:
            None
        """
        # Should support Day or Min or other frame gap
        time = datetime_normalize(time)

        if time is None:
            self.log("ERROR", "Time format not support, can not update time")
            return

        if self._now is None:
            self._now = time
            self.log("DEBUG", f"{self.name} Time Init: None --> {self._now}")
            return

        if time < self.now:
            self.log("ERROR", "We can not go back such as a TIME TRAVALER.")
            return

        elif time == self.now:
            self.log("WARNING", "Time not goes on.")
            return

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            self.log("DEBUG", f"{type(self)} {self.name} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {self.name} Time Elapses: {old} --> {self.now}")

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
        from ginkgo.data.models import MPosition
        
        model = MPosition()
        model.update(
            portfolio_id=getattr(self, '_portfolio_id', ''),
            engine_id=getattr(self, '_engine_id', ''),
            run_id=getattr(self, '_run_id', ''),
            uuid=self.uuid,
            code=self._code,
            cost=float(self._cost),
            volume=self._volume,
            frozen_volume=self._frozen_volume,
            frozen_money=float(self._frozen_money),
            price=float(self._price),
            fee=float(self._fee)
        )
        return model
    
    @classmethod
    def from_model(cls, model) -> 'Position':
        """
        从数据库模型创建实体
        
        Args:
            model (MPosition): 数据库模型实例
            
        Returns:
            Position: 持仓实体实例
        """
        return cls(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            run_id=getattr(model, 'run_id', ''),
            code=model.code,
            cost=model.cost,
            volume=model.volume,
            frozen_volume=model.frozen_volume,
            frozen_money=model.frozen_money,
            price=model.price,
            fee=model.fee
        )

    # def __repr__(self) -> str:
    #     return base_repr(self, self._code, 12, 60)

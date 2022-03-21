"""
持仓类
"""
from src.libs.ginkgo_logger import ginkgo_logger as gl


class Position(object):
    """
    持仓类
    """

    # region Property
    @property
    def cost(self):
        """
        持仓成本
        """
        return self._cost

    @cost.setter
    def cost(self, value: float):
        self._cost = value

    @property
    def last_price(self):
        """
        持有标的的最新价格
        """
        return self._last_price

    @last_price.setter
    def last_price(self, value: float):
        self._last_price = value

    @property
    def volume(self):
        """
        持仓量
        """
        return self._volume

    @volume.setter
    def volume(self, value: int):
        self._volume = value

    @property
    def frozen_t1(self):
        """
        刚买入标的的冻结量
        """
        return self._frozen_t1

    @frozen_t1.setter
    def frozen_t1(self, value: int):
        self._frozen_t1 = value

    @property
    def avaliable_volume(self):
        """
        可用来沽出的量
        """
        return self._avaliable_volume

    @avaliable_volume.setter
    def avaliable_volume(self, value: int):
        self._avaliable_volume = value

    @property
    def frozen_sell(self):
        """
        当前冻结的量
        """
        return self._frozen_sell

    @frozen_sell.setter
    def frozen_sell(self, value: int):
        self._frozen_sell = value

    @property
    def market_value(self):
        """
        当前标的的市场价值
        """
        return self.last_price * self.volume

    @property
    def date(self):
        """
        当前日期
        """
        return self._date

    @date.setter
    def date(self, value: str):
        # TODO 加上日期的校验
        try:
            if value > self.date:
                self._date = value
                return self._date
            else:
                gl.error(f"当前日期{self.date} 预更新至 {value} 不满足回测要求，请检查代码")
                return
        except AttributeError as e:
            self._date = value

    @property
    def is_t1(self):
        """
        是否T+1，影响买入后是否冻结
        """
        return self._is_t1

    @is_t1.setter
    def is_t1(self, value: bool):
        if not isinstance(value, bool):
            gl.error(f"is_t1 只能传入bool值，当前传入类型不符 {type(value)},已默认开启T+1模式")
            self._is_t1 = True

        self._is_t1 = value

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, value):
        try:
            self._history.append(value)
        except AttributeError as e:
            self._history = []
            self._history.append(value)

    # endregion

    def __init__(
        self,
        is_t1=True,
        code="BaseCode",
        name="Hello:)",
        cost=0.0,
        volume=0,
        date="1999-09-09",
    ):
        self.is_t1 = is_t1
        self.code = code
        self.name = name
        self.cost = cost
        self.last_price = cost
        self.volume = volume  # 当前持有股票量
        self.frozen_sell = 0  # 总冻结股票
        self.frozen_t1 = volume if self.is_t1 else 0  # 当前T+1冻结股票数量
        self.avaliable_volume = 0 if self.is_t1 else volume  # 可用股票
        self.date = date  # 开仓日

    def __repr__(self):
        s = f"{self.date} {self.code} {self.name} 持仓，"
        s += f"成本价「{self.cost}」 持有量「{self.volume}」 "
        s += f"可用「{self.avaliable_volume}」 冻结「{self.frozen_sell + self.frozen_t1}」 "
        s += f"其中卖出预冻结 「{self.frozen_sell}」 T+1冻结「{self.frozen_t1}」"
        s += f"现价「{self.last_price}」 总价值「{self.market_value}」 "
        s += f"浮动盈亏「{self.market_value - self.volume * self.last_price}」"
        return s

    def pre_sell(self, volume: int, date: str):
        """
        持仓卖出的预处理

        卖出前冻结可用股票份额
        卖出交易发起前调用
        """
        if not isinstance(volume, int):
            gl.error(
                f"{self.code} {self.name} 打算减少持有份额，减少的份额应该是整型，({type(volume)}){volume}不是整数"
            )
            return

        if volume > self.avaliable_volume:
            gl.warning(
                f"{self.date} {self.code} 预沽量{volume}大于持仓{self.avaliable_volume}，已重新设置为持仓量，请检查代码"
            )
            volume = self.avaliable_volume

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if volume <= 0:
            gl.error(f"{self.date} {self.code} {self.name} 预沽量{volume}应该大于零，请检查代码")
            return

        self.date = date
        self.frozen_sell += volume
        self.avaliable_volume -= volume
        gl.info(f"{date} {self.code} 冻结仓位成功，冻结份额「{volume}」")
        gl.info(self)
        return self

    def buy(self, volume: int, cost: float, date: str):
        """
        增加持仓后Position的操作
        """
        if not isinstance(volume, int):
            gl.error(
                f"{self.code} {self.name} 打算增加持有份额，增加的份额应该是整数，({type(volume)}){volume}不是整数"
            )
            return

        if volume <= 0:
            gl.error(
                f"{self.code} {self.name} 打算增加持有份额，增加的份额应该大于0，({type(volume)}){volume}"
            )
            return

        if isinstance(cost, int):
            cost = float(cost)
        if not isinstance(cost, float):
            gl.error(f"{self.code} 打算增加持有份额，新增持的价格应该是浮点数，({type(cost)}){cost}不是浮点数")
            return

        if cost < 0:
            gl.error(f"{self.code} 打算增加持有份额，新增持的价格应该大于0，({type(cost)}){cost}")
            return

        gl.info(
            f"{date} {self.code} {self.name} 开设多仓成功，价格「{round(cost, 2)}」 份额「{volume}」"
        )

        self.cost = (self.cost * self.volume + volume * cost) / (self.volume + volume)
        if self.is_t1:
            self.frozen_t1 += volume
        else:
            self.avaliable_volume += volume
        self.volume += volume

        gl.info(self)
        return self

    def sell(self, volume: int, done: bool, date: str):
        """
        卖出后的处理

        :param volume: 卖出的股票数
        :param done: 卖出是否成功
        :param date: 卖出日期
        """
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        # 卖出交易成功后调用
        if not isinstance(volume, int):
            gl.error(
                f"{self.date} {self.code} {self.name} 打算增加持有份额，增加的份额应该是整数，({type(volume)}){volume}不是整数"
            )
            return

        if volume <= 0:
            gl.error(
                f"{self.date} {self.code} {self.name} 卖出失败，预计成交量{volume}应该大于0，请检查代码，当前回测有误"
            )
            return

        if volume > self.freeze:
            s = "成功" if done else "失败"
            gl.error(
                f"{self.date} {self.code} {self.name} 卖出{s}，成交量{volume}大于冻结量{self.freeze}，请检查代码，当前回测有误"
            )
            return self

        if not isinstance(done, bool):
            gl.error(
                f"{self.date} {self.code} {self.name} 卖出失败，done应该传入卖出成功与否，({type(done)}){done}不是布尔值"
            )
            return self

        if done:
            # 交易成功
            self.frozen_sell -= volume
            self.date = date
            gl.info(f"{self.date} {self.code} {self.name} 卖出成功，卖出{volume}份额")
        else:
            # 交易失败
            gl.info(f"{self.date} {self.code} {self.name} 卖出失败，解除冻结份额{volume}")
            self.volume += volume
            self.frozen_sell -= volume

        self.cal_total()
        gl.info(self)
        return self

    def unfreezeT1(self):
        """
        解除T+1冻结
        """
        if not self.is_t1 or self.frozen_t1 == 0:
            return
        if self.frozen_t1 < 0:
            gl.error(f"{self.date} 解除冻结失败，当前冻结额度小于0，请检查代码")
            return
        gl.info(f"{self.date} 解除冻结 {self.frozen_t1}")
        self.avaliable_volume += self.frozen_t1
        self.frozen_t1 = 0

    def update_last_price(self, price: float, date: str):
        """
        更新最新价格
        """
        if isinstance(price, int):
            price = float(price)
        if not isinstance(price, float):
            gl.error(
                f"{date} {self.code} {self.name} 打算更新最新价格，价格应该是浮点数，({type(price)}{price}不是整数"
            )
            return

        if price <= 0:
            gl.error(
                f"{date} {self.code} {self.name} 打算更新最新价格，({type(price)}{price}应该大于0"
            )
            return

        if self.update_date(date) is None:
            return
        self.last_price = price
        self.unfreezeT1()
        gl.info(self)
        return self.last_price

    def update_date(self, date: str):
        """
        更新日期，只能顺着时间流
        """
        # TODO 需要校验日期有效性，目前日期校验有Bug
        if date > self.date:
            self.date = date
            return self.date
        else:
            gl.error(f"当前日期{self.date} 预更新至 {date} 不满足回测要求，请检查代码")
            return

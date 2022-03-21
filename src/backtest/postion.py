"""
持仓类
"""
from src.libs.ginkgo_logger import ginkgo_logger as gl


class Position(object):
    """
    持仓类
    """

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
            if value < self.date:
                gl.error(f"当前日期{self.date} 预更新至 {value} 不满足回测要求，请检查代码")
                return
        except AttributeError as e:
            pass
        self._date = value

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

    def __init__(
        self,
        is_t1=True,
        code="BaseCode",
        name="Hello:)",
        cost=0.0,
        volume=0,
        date="1999-09-09",
    ):
        self.is_t1 = is_t1  # 是否T+1
        self.code = code  # 代码
        self.name = name  # 名称
        self.cost = cost  # 持仓成本
        self.last_price = cost  # 最新价格
        self.volume = volume  # 当前持有数量
        self.frozen_sell = 0  # 总冻结数量
        self.frozen_t1 = volume if self.is_t1 else 0  # T+1冻结股票数量
        self.avaliable_volume = 0 if self.is_t1 else volume  # 可用数量
        self.date = date  # 开仓日

    def __repr__(self):
        s = f"{self.date} {self.code} {self.name} 持仓，"
        s += f"成本价「{self.cost}」 持有量「{self.volume}」 "
        s += f"可用「{self.avaliable_volume}」 冻结「{self.frozen_sell + self.frozen_t1}」 "
        s += f"其中卖出预冻结 「{self.frozen_sell}」 T+1冻结「{self.frozen_t1}」"
        s += f"现价「{self.last_price}」 总价值「{self.market_value}」 "
        s += f"浮动盈亏「{self.market_value - self.volume * self.last_price}」"
        return s

    def buy(self, volume: int, cost: float, date: str):
        """
        增加持仓后Position的操作
        """
        if volume <= 0:
            gl.error(
                f"{self.code} {self.name} 打算增加持有份额，增加的份额应该大于0，({type(volume)}){volume}"
            )
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

    def pre_sell(self, volume: int, date: str):
        """
        持仓卖出的预处理

        卖出前冻结可用股票份额
        卖出交易发起前调用
        """
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
        if volume <= 0:
            gl.error(
                f"{self.date} {self.code} {self.name} 卖出失败，预计成交量{volume}应该大于0，请检查代码，当前回测有误"
            )
            return

        if volume > self.frozen_sell:
            s = "成功" if done else "失败"
            gl.error(
                f"{self.date} {self.code} {self.name} 卖出{s}，成交量{volume}大于冻结量{self.freeze}，请检查代码，当前回测有误"
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

        gl.info(self)
        return self

    def unfreeze_t1(self):
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

    def unfreeze_sell(self, volume: int):
        """
        解除卖出冻结
        """

    def update_last_price(self, price: float, date: str):
        """
        更新最新价格
        """
        if price <= 0:
            gl.error(
                f"{date} {self.code} {self.name} 打算更新最新价格，({type(price)}{price}应该大于0"
            )
            return

        self.date = date
        self.last_price = price
        self.unfreezeT1()
        gl.info(self)
        return self.last_price

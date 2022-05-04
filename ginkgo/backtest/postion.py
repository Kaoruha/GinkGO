"""
持仓类
"""
import datetime as dt
from ginkgo.libs import GINKGOLOGGER as gl


class Position(object):
    """
    持仓类
    """

    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, value):
        if isinstance(value, dt.datetime):
            self._datetime = value
        try:
            self._datetime = dt.datetime.strptime(value, "%Y-%m-%d")
        except Exception as e:
            gl.logger.error(e)
            try:
                self._datetime = dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except Exception as e2:
                gl.logger.error(e2)
                self._datetime = dt.datetime.strptime("9999-01-01", "%Y-%m-%d")

    @property
    def market_value(self):
        """
        当前标的的市场价值
        """
        return self.last_price * self.volume

    @property
    def frozen(self):
        return self.frozen_sell + self.frozen_t1

    @property
    def float_profit(self):
        return self.market_value - self.cost * self.volume

    def __init__(
        self,
        code: str = "BaseCode",
        name: str = "Hello:)",
        cost: float = 0.0,
        volume: int = 0,
        datetime: datetime = None,
    ):
        self.is_t1 = True
        self.code = code  # 代码
        self.name = name  # 名称
        self.cost = 0  # 持仓成本
        self.last_price = 0  # 最新价格
        self.volume = 0  # 当前持有数量
        self.frozen_sell = 0  # 总冻结数量
        self.frozen_t1 = 0  # T+1冻结股票数量
        self.avaliable_volume = 0  # 可用数量
        self.update_last_price(price=cost, datetime=datetime)
        self.buy(volume=volume, price=cost)

    def __repr__(self):
        s = f"{self.code} {self.name} 持仓，"
        s += f"成本价「{self.cost}」 持有量「{self.volume}」 "
        s += f"可用「{self.avaliable_volume}」 冻结「{self.frozen_sell + self.frozen_t1}」 "
        s += f"其中卖出预冻结 「{self.frozen_sell}」 T+1冻结「{self.frozen_t1}」"
        s += f"现价「{self.last_price}」 总价值「{self.market_value}」 "
        s += f"浮动盈亏「{self.market_value - self.volume * self.cost}」"
        return s

    def buy(self, volume: int, price: float):
        """
        增加持仓后Position的操作
        """
        if volume <= 0:
            gl.logger.error(f"{self.name} 打算增加持有份额，增加的份额应该大于0，({type(volume)}){volume}")
            return

        if price < 0:
            gl.logger.error(f"{self.code} 打算增加持有份额，新增持的价格应该大于0，({type(price)}){price}")
            return

        gl.logger.info(
            f"{self.code} {self.name} 开设多仓成功，价格「{round(price, 2)}」 份额「{volume}」"
        )

        self.cost = (self.cost * self.volume + volume * price) / (self.volume + volume)
        if self.is_t1:
            self.frozen_t1 += volume
        else:
            self.avaliable_volume += volume
        self.volume += volume

        gl.logger.info(self)
        # TODO 需要记录
        return self

    def freeze_sell(self, volume: int):
        """
        持仓卖出的预处理

        卖出前冻结可用股票份额
        卖出交易发起前调用
        """
        if volume > self.avaliable_volume:
            gl.logger.warning(
                f"{self.code} 预沽量{volume}大于持仓{self.avaliable_volume}，已重新设置为持仓量，请检查代码"
            )
            volume = self.avaliable_volume

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if volume <= 0:
            gl.logger.error(f"{self.code} {self.name} 预沽量{volume}应该大于零，请检查代码")
            return

        self.frozen_sell += volume
        self.avaliable_volume -= volume
        gl.logger.info(f"{self.code} 冻结仓位成功，冻结份额「{volume}」")
        gl.logger.info(self)
        return self

    def sell(self, volume: int):
        """
        卖出后的处理
        """
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        # 卖出交易成功后调用
        if volume <= 0:
            gl.logger.error(
                f"{self.code} {self.name} 卖出失败，预计成交量{volume}应该大于0，请检查代码，当前回测有误"
            )
            return

        if volume > self.frozen_sell:
            gl.logger.error(
                f"{self.code} {self.name} 卖出，成交量{volume}大于冻结量{self.freeze}，请检查代码，当前回测有误"
            )
            return self

            # 交易成功
        self.unfreeze_sell(volume=volume)
        self.volume -= volume
        gl.logger.info(f"{self.datetime} {self.code} {self.name} 卖出成功，卖出{volume}份额")
        gl.logger.info(self)
        return self

    def unfreeze_t1(self):
        """
        解除T+1冻结
        """
        if not self.is_t1 or self.frozen_t1 == 0:
            return
        if self.frozen_t1 < 0:
            gl.logger.error(f"{self.datetime} 解除冻结T+1失败，当前冻结额度小于0，请检查代码")
            return
        gl.logger.info(f"{self.datetime} 解除冻结T+1 {self.frozen_t1}")
        self.avaliable_volume += self.frozen_t1
        self.frozen_t1 = 0

    def unfreeze_sell(self, volume: int) -> int:
        """
        解除卖出冻结
        """
        if volume > self.frozen_sell:
            volume = self.frozen_sell
            gl.logger.error(f"解除冻结份额「{volume}」超过当前冻结份额「{self.frozen_sell}」，回测有误，请检查代码")
        self.frozen_sell -= volume
        return self.frozen_sell

    def update_last_price(self, price: float, datetime: dt.datetime):
        """
        更新最新价格
        """
        self.datetime = datetime
        if price <= 0:
            gl.logger.error(
                f"{self.code} {self.name} 打算更新最新价格，({type(price)}{price}应该大于0"
            )
            return

        self.last_price = price
        gl.logger.info(self)
        return self.last_price

    def update(self, volume: int, price: float, datetime: dt.datetime):
        self.datetime = datetime
        if volume > 0:
            self.buy(volume=volume, cost=price)
        else:
            self.sell(volume=volume)
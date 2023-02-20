import datetime as dt
from ginkgo.libs import GINKGOLOGGER as gl


class Position(object):
    """
    持仓类
    """

    @property
    def datetime(self):
        return self.__datetime

    @datetime.setter
    def datetime(self, value):
        if isinstance(value, dt.datetime):
            self.__datetime = value
        elif isinstance(value, str):
            self.__datetime = dt.datetime.strptime(value, "%Y-%m-%d")
        else:
            self.__datetime = dt.datetime.strptime("9999-01-01", "%Y-%m-%d")

    @property
    def market_value(self):
        """
        当前标的的市场价值
        """
        return self.latest_price * self.quantity

    @property
    def frozen(self):
        return self.frozen_sell + self.frozen_t1

    @property
    def float_profit(self):
        return self.market_value - self.cost * self.quantity

    @property
    def code(self):
        return self.__code

    @property
    def name(self):
        return self.__name

    def __init__(
        self,
        code: str = "BaseCode",
        name: str = "头寸",
        price: float = 0.0,
        quantity: int = 0,
        datetime: datetime = None,
    ):
        self.is_t1 = True
        self.__code = code  # 代码
        self.__name = name  # 名称
        self.cost = price  # 持仓成本
        self.latest_price = price  # 最新价格
        self.quantity = quantity  # 当前持有数量
        self.frozen_sell = 0  # sell冻结数量
        self.frozen_t1 = quantity if self.is_t1 else 0  # T+1冻结股票数量
        self.avaliable_quantity = 0 if self.is_t1 else quantity  # 可用数量
        self.datetime = datetime

        gl.logger.debug(f"初始化持仓 {self}")

    def __repr__(self):
        s = f"「{self.code} {self.name}」持仓实例，"
        s += f"成本价「{self.cost}」 持有量「{self.quantity}」 "
        s += f"可用「{self.avaliable_quantity}」 冻结「{self.frozen_sell + self.frozen_t1}」 "
        s += f"其中卖出预冻结 「{self.frozen_sell}」 T+1冻结「{self.frozen_t1}」"
        s += f"现价「{self.latest_price}」 总价值「{self.market_value}」 "
        s += f"浮动盈亏「{self.market_value - self.quantity * self.cost}」"
        return s

    def __buy(self, price: float, quantity: int, datetime: dt.datetime):
        """
        增加持仓后Position的操作
        """
        if quantity <= 0:
            gl.logger.error(
                f"「{self.name}」 打算增加持有份额，增加的份额应该大于0，({type(quantity)}){quantity}"
            )
            return

        if price < 0:
            gl.logger.error(f"{self.code} 打算增加持有份额，新增持的价格应该大于0，({type(price)}){price}")
            return

        gl.logger.info(
            f"{self.code} {self.name} 开设多仓成功，价格「{round(price, 2)}」 份额「{quantity}」"
        )

        # 更新成本
        self.cost = (self.cost * self.quantity + quantity * price) / (
            self.quantity + quantity
        )

        # 更新可用头寸
        if self.is_t1:
            self.frozen_t1 += quantity
        else:
            self.avaliable_quantity += quantity
        # 更新总头寸
        self.quantity += quantity
        # 更新价格
        self.update_latest_price(price=price, datetime=datetime)

        gl.logger.debug(self)
        # TODO 需要记录
        return self

    def freeze_position(self, quantity: int, datetime: str = "9999-01-01"):
        """
        持仓卖出的预处理

        卖出前冻结可用股票份额
        卖出交易发起前调用
        """
        if quantity > self.avaliable_quantity:
            gl.logger.warning(
                f"{self.code} 预沽量{quantity}大于持仓{self.avaliable_quantity}，已重新设置为持仓量，请检查代码"
            )
            quantity = self.avaliable_quantity

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if quantity <= 0:
            gl.logger.error(f"{self.code} {self.name} 预沽量{quantity}应该大于零，请检查代码")
            return

        self.frozen_sell += quantity
        self.avaliable_quantity -= quantity
        gl.logger.info(f"{self.code} 冻结仓位成功，冻结份额「{quantity}」")
        gl.logger.debug(self)
        return self

    def __sell(self, quantity: int, datetime: str = "9999-01-01", *kwarg, **kwargs):
        """
        卖出后的处理
        """
        # 卖出调整持仓
        # 卖出交易成功后调用
        if quantity <= 0:
            gl.logger.error(
                f"{self.code} {self.name} 卖出失败，预计成交量{quantity}应该大于0，请检查代码，当前回测有误"
            )
            return self

        if quantity > self.frozen_sell:
            gl.logger.error(
                f"{self.code} {self.name}卖出，成交量{quantity}大于冻结量{self.frozen_sell}，请检查代码，当前回测有误"
            )
            return self

        # 交易成功
        self.unfreeze_sell(quantity=quantity)
        self.quantity -= quantity
        gl.logger.info(f"「{self.datetime}」{self.code} {self.name} 卖出成功，卖出{quantity}份额")
        gl.logger.debug(self)
        return self

    def unfreeze_t1(self):
        """
        解除T+1冻结
        """
        if not self.is_t1 or self.frozen_t1 == 0:
            return
        if self.frozen_t1 < 0:
            gl.logger.error(f"「{self.datetime}」解除冻结T+1失败，当前冻结额度小于0，请检查代码")
            return
        self.avaliable_quantity += self.frozen_t1
        gl.logger.info(f"「{self.datetime}」解除冻结T+1 {self.frozen_t1}")
        self.frozen_t1 = 0
        gl.logger.debug(self)

    def unfreeze_sell(self, quantity: int) -> bool:
        """
        解除卖出冻结
        return: the result of this action
        """
        if quantity > self.frozen_sell:
            quantity = self.frozen_sell
            gl.logger.error(
                f"解除冻结份额「{quantity}」超过当前冻结份额「{self.frozen_sell}」，回测有误，请检查代码"
            )
            return False
        self.frozen_sell -= quantity
        gl.logger.info(f"「{self.datetime}」解除冻结卖出 {self.frozen_sell}")
        gl.logger.debug(self)
        return True

    def update_latest_price(self, price: float, datetime: dt.datetime):
        """
        更新最新价格
        """
        self.datetime = datetime
        if price <= 0:
            gl.logger.error(
                f"{self.code} {self.name} 打算更新最新价格，({type(price)}{price}应该大于0"
            )
            return

        price = float(price)
        if price == self.latest_price:
            gl.logger.info("Price has no change.")
            return

        old_price = self.latest_price
        self.latest_price = price
        gl.logger.info(
            f"「{self.datetime}」「{self.name} {self.code}」价格更新「{old_price}」->「{price}」持有量「{self.quantity}」浮盈「{self.float_profit}」"
        )
        return self.latest_price

    def update(
        self,
        datetime: dt.datetime,
        quantity: int,
        price: float = 0.0,
    ):
        """
        头寸更新
        """
        self.datetime = datetime
        if quantity > 0:
            self.__buy(quantity=quantity, price=price, datetime=datetime)
        else:
            self.__sell(quantity=-quantity, datetime=datetime)

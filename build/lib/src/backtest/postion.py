"""
持仓类
"""
from src.libs.ginkgo_logger import ginkgo_logger as gl


class Position(object):
    """
    持仓类
    """

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, value: str):
        # TODO Check the code
        self.__code = value

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value

    @property
    def cost(self):
        return self.__cost

    @cost.setter
    def cost(self, value: float):
        self.__cost = value

    @property
    def market_price(self):
        return self.__market_price

    @market_price.setter
    def market_price(self, value: float):
        self.__market_price = value

    @property
    def volume(self):
        return self.__volume

    @volume.setter
    def volume(self, value: int):
        self.__volume = value

    @property
    def t1frozen(self):
        return self.__t1frozen

    @t1frozen.setter
    def t1frozen(self, value:int):
        self.__t1frozen = value

    @property
    def avaliable_volume(self):
        return self.__avaliable_volume

    @avaliable_volume.setter
    def avaliable_volume(self, value:int):
        self.__avaliable_volume = value
    
    @property
    def frozen_volume(self):
        return self.__frozen_volume

    @frozen_volume.setter
    def frozen_volume(self, value: int):
        self.__frozen_volume = value

    @property
    def market_value(self):
        return self.__market_value

    @market_value.setter
    def market_value(self, value: float):
        self.__market_value = value


    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value: str):
        # TODO 加上日期的校验
        self._date = value

    def __init__(self, code='BaseCode', name='Hello:)', cost=0.0, volume=0, date='1999-09-09'):
        self.code = code
        self.name = name
        self.cost = cost
        self.market_price = cost
        self.last_price = cost
        self.volume = volume  # 当前持有股票量
        self.t1frozen = volume  # 当前T+1冻结股票数量
        self.avaliable_volume = 0  # 可用股票
        self.frozen_volume = 0  # 总冻结股票
        self.market_value = 0  # 持仓总价值
        self.date = date  # 开仓日

        self.cal_total()

    def __repr__(self):
        s = f"{self.date} {self.code} {self.name} 持仓，"
        s += f"成本价「{self.cost}」 持有量「{self.volume}」 "
        s += f"可用「{self.avaliable_volume}」 冻结「{self.frozen_volume}」 "
        s += f"现价「{self.market_price}」 总价值「{self.market_value}」"
        return s

    def pre_sell(self, volume: int, date: str):
        """
        持仓卖出的预处理

        卖出前冻结可用股票份额
        卖出交易发起前调用
        """
        if not isinstance(volume, int):
            gl.error(f'{self.code} {self.name} 打算减少持有份额，减少的份额应该是整型，({type(volume)}){volume}不是整数')
            return self

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if volume < 0:
            gl.error(f'{self.date} {self.code} {self.name} 预沽量{volume}应该大于零，请检查代码')
            return self

        if volume > self.avaliable_volume:
            gl.warning(f'{self.date} {self.code} 预沽量{volume}大于持仓{self.avaliable_volume}，已重新设置为持仓量，请检查代码')
            volume = self.avaliable_volume

        self.date = date
        self.frozen_volume += volume
        self.avaliable_volume -= volume
        gl.info(f'{date} {self.code} 冻结仓位成功，冻结份额「{volume}」')
        gl.info(self)
        return self

    def buy(self, volume: int, cost: float, date: str):
        """
        当前股票增加持仓
        """
        if not isinstance(volume, int):
            gl.error(f'{self.code} {self.name} 打算增加持有份额，增加的份额应该是整数，({type(volume)}){volume}不是整数')
            return self
        if volume <= 0:
            gl.error(f'{self.code} {self.name} 打算增加持有份额，增加的份额应该大于0，({type(volume)}){volume}')
            return self
        if isinstance(cost, int):
            cost = float(cost)
        if not isinstance(cost, float):
            gl.error(f'{self.code} 打算增加持有份额，新增持的价格应该是浮点数，({type(cost)}){cost}不是浮点数')
            return self
        if cost < 0:
            gl.error(f'{self.code} 打算增加持有份额，新增持的价格应该大于0，({type(cost)}){cost}')
            return self


        gl.info(f'{date} {self.code} {self.name} 开设多仓成功，价格「{round(cost, 2)}」 份额「{volume}」')
        self.cost = (self.cost * self.volume + volume * cost) / (self.volume + volume)
        self.t1frozen += volume
        self.volume += volume
        self.date = date  # TODO 日期校验
        # 用成交价更新最新价格
        self.update_market_price(price=cost, date=date)
        # 重新计算总价值
        self.cal_total()
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
            gl.error(f'{self.date} {self.code} {self.name} 打算增加持有份额，增加的份额应该是整数，({type(volume)}){volume}不是整数')
            return self

        if volume <= 0:
            gl.error(f"{self.date} {self.code} {self.name} 卖出失败，预计成交量{volume}应该大于0，请检查代码，当前回测有误")
            return self

        if volume > self.freeze:
            s = '成功' if done else '失败'
            gl.error(f"{self.date} {self.code} {self.name} 卖出{s}，成交量{volume}大于冻结量{self.freeze}，请检查代码，当前回测有误")
            return self

        if not isinstance(done, bool):
            gl.error(f'{self.date} {self.code} {self.name} 卖出失败，done应该传入卖出成功与否，({type(done)}){done}不是布尔值')
            return self

        if done:
            # 交易成功
            self.frozen_volume -= volume
            self.date = date
            gl.info(f'{self.date} {self.code} {self.name} 卖出成功，卖出{volume}份额')
        else:
            # 交易失败
            gl.info(f'{self.date} {self.code} {self.name} 卖出失败，解除冻结份额{volume}')
            self.volume += volume
            self.frozen_volume -= volume

        self.cal_total()
        gl.info(self)
        return self

    def cal_total(self):
        """
        计算持仓总价值
        """
        self.market_value = self.market_price * self.volume
        return self.market_value

    def unfreezeT1(self):
        """
        解除T+1冻结
        """
        self.avaliable_volume += self.t1frozen
        self.t1frozen = 0

    def update_market_price(self, price: float, date: str):
        """
        更新最新价格
        """
        if isinstance(price, int):
            price = float(price)
        if not isinstance(price, float):
            gl.error(f'{date} {self.code} {self.name} 打算更新最新价格，价格应该是浮点数，({type(price)}{price}不是整数')
            return self.market_price

        if price <= 0:
            gl.error(f'{date} {self.code} {self.name} 打算更新最新价格，({type(price)}{price}应该大于0')
            return self.market_price

        # TODO Date需要校验
        self.date = date
        self.market_price = price
        self.cal_total()
        gl.info(self)
        return self.market_price


p = Position()
print(p)
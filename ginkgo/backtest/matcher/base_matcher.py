import datetime
import queue
import abc
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.enums import Direction, OrderStatus, Source
from ginkgo.backtest.events import OrderEvent, FillEvent, Event
from ginkgo.libs import GINKGOLOGGER as gl


class BaseMatcher(abc.ABC):
    """
    撮合基类
    """
    # 买入时，会产生佣金、过户费两项费用，佣金为成交金额*佣金费率，单笔佣金不满最低佣金时，按最低佣金计算。
    # 卖出时，会产生佣金、过户费、印花税。印花税为成交金额*印花税费，

    # 1.从Broker接到订单，存入OrderList
    # 2.将OrderList中的订单，发送给券商/模拟撮合，状态改为已发送
    # 3.获取订单结果，存入ResultList
    #     - 3.1 实盘券商API，每次调用方法时会将所有已发送的订单抽出，查询结果
    #     - 3.2 模拟成交的话，需要手写一个模拟成交的规则，手动调用TryMatch方法，将模拟的结果存放在MatchList
    #           等待手动/自动触发GetResult，将模拟的结果存入ResultList，将对应Order状态修改为Complete，
    @property
    def order_history(self):
        return self.order_list


    def __init__(
        self,
        name="撮合基类",
        stamp_tax_rate=0.001,
        transfer_fee_rate=0.0002,
        commission_rate=0.0003,
        min_commission=5,
        *args,
        **kwargs,
    ):
        self.name = name
        self.stamp_tax_rate = stamp_tax_rate  # 设置印花税，默认千1
        self.transfer_fee_rate = transfer_fee_rate  # 设置过户费,默认万2
        self.commission_rate = commission_rate  # 交易佣金，按最高千3计算了，一般比这个低
        self.min_commission = min_commission  # 最低交易佣金，交易佣金的起步价
        self.order_list = {}  # 订单队列
        self.result_list = {}  # 结果队列
        self.engine: EventEngine = None  # 用来推送事件
        self.order_count = 0  # 订单计数器
        self.datetime: datetime = None

    def gen_fillevent(
        self, order: OrderEvent, is_complete: bool, price: float = 0, volume: int = 0
    ) -> FillEvent:
        """
        生成成交事件
        """
        # 根据传入的订单，是否成交，成交的价格和成交量返回成交事件

        fill = FillEvent(
            code=order.code,
            direction=order.direction,
            price=0,
            volume=0,
            fee=0,
            source=Source.SIMMATCHER,
            datetime=self.datetime,
        )
        if is_complete:
            fill.price = price
            fill.volume = volume
            fill.fee = self.fee_cal(
                direction=order.direction, price=price, volume=volume
            )

        return fill

    def fee_cal(self, direction: Direction, price: float, volume: int) -> float:
        """
        费率计算

        包含印花税，过户费，交易税，有最低税费
        """
        total = price * volume
        if total == 0:
            return 0
        stamp_tax = 0
        transfer = total * self.transfer_fee_rate
        commision = total * self.commission_rate
        if commision < self.min_commission:
            commision = self.min_commission
        if direction == direction.BEAR:
            stamp_tax = total * self.stamp_tax_rate
        return commision + stamp_tax + transfer

    def get_order(self, order: OrderEvent):
        """
        获取订单

        """
        # TODO 查重
        if order.status == OrderStatus.CREATED:
            if order.code not in self.order_list:
                self.order_list[order.code] = []
            self.order_list[order.code].append(order)

            gl.logger.info(
                    f"{self.name} 获取Order: {order.code} {order.uuid} {order.direction} {order.order_type}"
            )
        else:
            gl.logger.error(f"{order.code} 状态异常{order.status}，提交失败")
            order.status = OrderStatus.REJECTED
            if self.engine:
                self.engine.put(order)
            else:
                gl.logger.critical(f"{self.name} 引擎未注册")

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例
        """
        self._engine = engine
    
    def send_to_engine(self, event: Event):
        if self.engine:
            self.engine.put(event)
        else:
            gl.logger.critical(f"{self.name} 引擎未注册")

    @abc.abstractmethod
    def send_order(self, order):
        """
        发送订单，模拟回测的话直接将订单存至队列

        实盘的话向券商发送订单
        """
        raise NotImplementedError("Must implement send_order()")

    @abc.abstractmethod
    def get_result(self):
        """
        获取订单结果

        模拟回测的话向成交队列里查询结果
        实盘的话向券商发送API查询结果
        """
        raise NotImplementedError("Must implement get_result()")

    @abc.abstractmethod
    def clear(self):
        """
        跨日处理所有成交结果，未成交订单
        """
        raise NotImplementedError("Must implement Clear()")

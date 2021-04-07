import random
from .base_matcher import BaseMatcher
from ginkgo_server.backtest.events import OrderEvent, FillEvent
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.enums import DealType
from ginkgo_server.backtest.postion import Position


class SimulateMatcher(BaseMatcher):
    def __init__(
        self,
        stamp_tax_rate: float = 0.001,
        fee_rate: float = 0.0000687,
        slide: float = 0.002,
    ):
        BaseMatcher.__init__(self, stamp_tax_rate=stamp_tax_rate, fee_rate=fee_rate)
        self.slide = slide  # 滑点
        self.remain = 0  # 剩余资金
        self.source = ""

    def try_match(self, event: OrderEvent, position: Position):
        
        # 如果是实盘就直接发下单信号

    def get_result(self):
        # 查询结果，如果是实盘需要开启一个线程ping到有结果
        # 模拟盘就直接返回Fill了
        # 模拟成交,此处模拟按照开盘价购入
        # TODO 加入随机参数slider，让价格随机上下波动

        # 交易失败的情况

        # 交易成功的情况


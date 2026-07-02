# Upstream: PortfolioBase, ComponentFactoryService
# Downstream: BaseSizer, Signal, Order, DIRECTION_TYPES, pandas
# Role: ATR仓位管理器，基于平均真实波幅计算波动率自适应的订单仓位






from typing import Dict, Optional
from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Order
from ginkgo.entities import Signal
from ginkgo.entities.mixins import LotAlignableMixin
from ginkgo.libs import GLOG
from ginkgo.trading.computation.technical.average_true_range import AverageTrueRange as ATR  # #3958 restored import

import datetime
import pandas as pd


class ATRSizer(LotAlignableMixin, BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "ATRSizer",
        period: int = 14,
        risk: float = 0.01,
        risk_ratio: float = 2,
        min_atr_percent: float = 0.005,
        lot_size: int = 100,
        *args,
        **kwargs,
    ):
        super().__init__(name, *args, **kwargs)
        self.period = period
        self.risk = risk
        self.risk_ratio = risk_ratio
        # #5490: minimum ATR as a fraction of close. When ATR collapses near
        # zero (halt / limit board / stale quotes) the raw max_money/atr would
        # produce oversized positions; floor ATR before sizing.
        self.min_atr_percent = min_atr_percent
        # #6498: 最小交易单位（手），A 股默认 100；参数化以支持美股(1)/港股。
        # 仅作用于开仓(LONG)路径的 lot 对齐；平仓(SHORT)路径全量下单不受影响。
        self._lot_size = lot_size

    def set_risk(self, risk: float):
        self.risk = risk

    def cal(self, portfolio_info, signal: Signal) -> Optional[Order]:
        code = signal.code
        o = None
        if signal.direction == DIRECTION_TYPES.SHORT:
            # 获取持仓信息
            if code not in portfolio_info["positions"]:
                return None
            pos = portfolio_info["positions"][code]
            if pos is None:
                return None
            o = self.create_order(
                code=signal.code,
                direction=signal.direction,
                volume=pos.volume,
                limit_price=0,
                frozen_money=0,
                transaction_price=0,
                transaction_volume=0,
                remain=0,
                fee=0,
                timestamp=self.now,
            )
        if signal.direction == DIRECTION_TYPES.LONG:
            if self.now is None:
                GLOG.WARN("ATRSizer: now is None, passing the signal")
                return None
            # #4706: LONG 取数走注入的 _data_feeder.get_historical_data()，对齐
            # FixedSizer/RatioSizer 范式。原直查 container.bar_service() 是 sizer 中
            # 旁路 feeder 的数据层穿透孤例：回测下常 result.success=False 致静默丢信号，
            # 且绕过 feeder 的 validate_time 防未来数据泄露装饰器。
            if self._data_feeder is None:
                GLOG.ERROR(f"ATRSizer:{self.name} has no data_feeder bound")
                return None
            start_date = self.now - datetime.timedelta(days=self.period + 7)
            end_date = self.now
            df = self._data_feeder.get_historical_data(
                symbols=[code],
                start_time=start_date,
                end_time=end_date,
            )
            if df is None or df.shape[0] == 0:
                GLOG.WARN(f"ATRSizer: no bars for {code}, signal dropped")
                return None

            # 检查数据是否足够
            if len(df) < self.period + 1:
                GLOG.WARN(f"ATRSizer: insufficient data for {code}, need {self.period + 1} bars")
                return None

            # 提取价格列表
            high_prices = df['high'].tolist()
            low_prices = df['low'].tolist()
            close_prices = df['close'].tolist()

            # 使用新API计算ATR
            atr = ATR.cal(self.period, high_prices[-(self.period+1):], low_prices[-(self.period+1):], close_prices[-(self.period+1):]) * self.risk_ratio

            if atr == 0 or pd.isna(atr):
                GLOG.WARN(f"ATRSizer: ATR is {atr} for {code}, signal dropped")
                return None
            # #5490: floor ATR to a minimum fraction of close so a collapsed ATR
            # (halt / limit board / stale quotes) cannot inflate max_shares.
            close = df.iloc[-1]["close"]
            min_atr = close * self.min_atr_percent
            if atr < min_atr:
                GLOG.WARN(
                    f"ATRSizer: ATR {atr} below floor {min_atr:.4f} "
                    f"({self.min_atr_percent * 100:.2f}% of close {close}) for {code}; flooring"
                )
                atr = min_atr
            max_money = portfolio_info["cash"] * self.risk
            max_shares = self.align_to_lot(int(max_money / atr))  # 向下对齐到 lot_size 整数倍（#6498，原硬编码 100）
            price = close * 1.1
            o = self.create_order(
                code=signal.code,
                direction=signal.direction,
                volume=max_shares,
                limit_price=0,
                frozen_money=round(price * max_shares, 4),
                transaction_price=0,
                transaction_volume=0,
                remain=0,
                fee=0,
                timestamp=self.now,
            )
            GLOG.INFO("Order Generated.")
            GLOG.INFO(o)
        return o


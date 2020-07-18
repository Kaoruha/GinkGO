"""
信息类
包含加个信息，市场信息
"""
import pandas as pd
from ginkgo.libs.enums import InfoType


class Info(object):
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.DailyPrice
        self.data = data


class DailyPrice(Info):
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.DailyPrice
        self.data = data


class MinutePrice(Info):
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.MinutePrice
        self.data = data


class MarketMSG(Info):
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.Message
        self.data = data

"""
信息类
包含加个信息，市场信息
"""
import pandas as pd
from ginkgo.libs.enums import InfoType


class Info(object):
    """
    信息类
    """
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.DailyPrice
        self.data = data


class DailyPrice(Info):
    """
    日交易数据
    """
    def __init__(self, data: pd.DataFrame):
        """
        初始化日交易数据

        :param data: 包含股票成交日交易级别相关信息，具体格式参见DataPortal部分
        :type data: pd.DataFrame
        """
        self.type = InfoType.DailyPrice
        self.data = data


class MinutePrice(Info):
    """
    分钟交易数据
    """
    def __init__(self, data: pd.DataFrame):
        """
        初始化分钟交易数据

        :param data: 包含股票成交5分钟级相关信息，具体格式参见DataPortal部分
        :type data: pd.DataFrame
        """
        self.type = InfoType.MinutePrice
        self.data = data


class MarketMSG(Info):
    def __init__(self, data: pd.DataFrame):
        self.type = InfoType.Message
        self.data = data

"""
信息类
包含加个信息，市场信息
"""
import pandas as pd
from ginkgo.libs.enums import InfoType


class Info(object):
    def __init__(self, data:pd.DataFrame):
        self.type = InfoType.Price
        self.data = data


class InfoPrice(Info):
    def __init__(self, data:pd.DataFrame):
        self.type = InfoType.Price
        self.data = data

class InfoMsg(Info):
    def __init__(self, data:pd.DataFrame):
        self.type = InfoType.Message
        self.data = data

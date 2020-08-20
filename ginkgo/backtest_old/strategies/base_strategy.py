"""
基础策略
生存第一
生存第一
生存第一
生存第一
"""


class BaseStrategy(object):
    """
    策略基类

    定义一些策略的基本方法
    """

    def __init__(self):
        self.data = {}

    def data_transfer(self, data):
        self.data = data

    def signal_generator(self):
        raise NotImplementedError("Must implement check()")

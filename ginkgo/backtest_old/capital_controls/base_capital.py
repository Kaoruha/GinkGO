"""
基础的资金管理策略
"""
from ginkgo.backtest_old.events import SignalEvent


class BaseCapitial(object):
    signal: SignalEvent

    def __init__(self):
        self.data = {}

    def data_transfer(self, data):
        self.data = data

    def signal_transfer(self, signal):
        self.signal = signal

    def check(self):
        raise NotImplementedError("Must implement check()")
